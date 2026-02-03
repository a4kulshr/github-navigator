#!/usr/bin/env python3
"""
Autonomous Web Navigation with Vision Models

This tool uses vision models (Claude / GPT-4V / Google Gemini) to autonomously
navigate GitHub and extract release information without relying on hardcoded selectors.

Usage:
    python navigate.py --repo "openclaw/openclaw"
    python navigate.py --url "https://github.com" --prompt "search for openclaw and get the current release"
"""

import argparse
import asyncio
import base64
import json
import os
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

# Load .env so API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY/GEMINI_API_KEY) are available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from playwright.async_api import async_playwright, Page, Browser

# Throttle between vision API calls to avoid rate limits (RPM); no retries for insufficient_quota
VISION_API_DELAY_SEC = float(os.environ.get("VISION_API_DELAY_SEC", "2.0"))
VISION_API_MAX_RETRIES = 3  # for rate_limit_exceeded only

# Try to import vision model clients
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from google import genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class VisionProvider(Enum):
    CLAUDE = "claude"
    GPT4V = "gpt4v"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"


@dataclass
class NavigationAction:
    """Represents an action to take on the page."""
    action_type: str  # "click", "type", "scroll", "extract", "wait", "done"
    target: Optional[str] = None  # Description of element to interact with
    value: Optional[str] = None  # Value to type or extracted data
    coordinates: Optional[tuple[int, int]] = None  # x, y coordinates for click
    confidence: float = 0.0
    reasoning: str = ""


@dataclass
class ReleaseInfo:
    """Structured release information."""
    repository: str
    version: str
    tag: str
    author: str
    release_notes: Optional[str] = None
    publish_date: Optional[str] = None
    download_links: Optional[list[str]] = None


class VisionNavigator:
    """
    Autonomous web navigator using vision models.
    
    The navigator takes screenshots of web pages and uses vision models
    to understand the content and decide on navigation actions.
    """
    
    def __init__(
        self,
        provider: VisionProvider = VisionProvider.CLAUDE,
        headless: bool = True,
        debug: bool = False,
        screenshot_dir: Optional[str] = None
    ):
        self.provider = provider
        self.headless = headless
        self.debug = debug
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir else Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
        
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.step_count = 0
        self.max_steps = 20  # Safety limit
        
        # Initialize vision client
        self._init_vision_client()
    
    def _init_vision_client(self):
        """Initialize the appropriate vision model client."""
        if self.provider == VisionProvider.CLAUDE:
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
            self.client = anthropic.Anthropic()
            self.model = "claude-sonnet-4-20250514"
        elif self.provider == VisionProvider.GEMINI:
            if not GEMINI_AVAILABLE:
                raise ImportError("google-genai package not installed. Run: pip install google-genai")
            self.client = genai.Client(
                api_key=os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
            )
            # gemini-1.5-flash is deprecated (404); use 2.0/2.5 or 3-flash-preview (see https://ai.google.dev/gemini-api/docs)
            self.model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        elif self.provider == VisionProvider.OPENROUTER:
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package not installed. Run: pip install openai")
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY not found in environment")
            self.client = openai.OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key
            )
            # Default to Claude 3.5 Sonnet via OpenRouter (can be overridden with OPENROUTER_MODEL env var)
            self.model = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
        else:
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package not installed. Run: pip install openai")
            self.client = openai.OpenAI()
            self.model = "gpt-4o"
    
    async def start(self):
        """Start the browser."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        self.page = await context.new_page()
        
        if self.debug:
            print("[Navigator] Browser started")
    
    async def stop(self):
        """Stop the browser."""
        if self.browser:
            await self.browser.close()
            if self.debug:
                print("[Navigator] Browser closed")
    
    async def screenshot(self) -> bytes:
        """Take a screenshot of the current page."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        screenshot_bytes = await self.page.screenshot(full_page=False)
        
        # Save screenshot for debugging
        if self.debug:
            path = self.screenshot_dir / f"step_{self.step_count:03d}.png"
            with open(path, 'wb') as f:
                f.write(screenshot_bytes)
            print(f"[Navigator] Screenshot saved: {path}")
        
        return screenshot_bytes
    
    def _encode_image(self, image_bytes: bytes) -> str:
        """Encode image to base64."""
        return base64.standard_b64encode(image_bytes).decode('utf-8')
    
    async def analyze_page(self, goal: str, context: str = "") -> NavigationAction:
        """
        Use vision model to analyze the current page and determine next action.
        
        Args:
            goal: The overall navigation goal
            context: Additional context about previous actions
        
        Returns:
            NavigationAction describing what to do next
        """
        screenshot = await self.screenshot()
        image_b64 = self._encode_image(screenshot)
        
        prompt = self._build_analysis_prompt(goal, context)
        
        # Throttle to reduce burst rate and stay under provider RPM limits
        await asyncio.sleep(VISION_API_DELAY_SEC)

        if self.provider == VisionProvider.CLAUDE:
            response = await self._analyze_with_claude(image_b64, prompt)
        elif self.provider == VisionProvider.GEMINI:
            response = await self._analyze_with_gemini(image_b64, prompt)
        elif self.provider == VisionProvider.OPENROUTER:
            response = await self._analyze_with_gpt4v(image_b64, prompt)
        else:  # GPT4V
            response = await self._analyze_with_gpt4v(image_b64, prompt)
        
        return self._parse_action_response(response)
    
    def _build_analysis_prompt(self, goal: str, context: str) -> str:
        """Build the prompt for the vision model."""
        return f"""You are an autonomous web navigation agent. Analyze the screenshot and determine the next action to achieve the goal.

GOAL: {goal}

PREVIOUS CONTEXT: {context if context else "Starting navigation"}

CRITICAL RULES:
- Public GitHub repositories can be viewed WITHOUT signing in or creating an account
- NEVER click "Sign in", "Sign up", or "Create account" links
- If you see a sign-in page, you've made a mistake - go back or navigate differently

CURRENT PAGE: Analyze the screenshot to understand:
1. What page are we on?
2. What interactive elements are visible?
3. What is the next logical step toward our goal?

AVAILABLE ACTIONS:
- click: Click on an element (provide description and approximate x,y coordinates)
- type: Type text into a field (provide the text to type)
- scroll: Scroll the page (provide direction: "up" or "down")
- extract: Extract data from the page (when goal is achieved)
- wait: Wait for page to load
- done: Navigation complete

Respond with a JSON object:
{{
    "action_type": "click|type|scroll|extract|wait|done",
    "target": "description of the element to interact with",
    "value": "text to type or extracted data (as JSON string if extracting)",
    "coordinates": [x, y],  // approximate click coordinates, null if not clicking
    "confidence": 0.0-1.0,  // how confident you are this is the right action
    "reasoning": "brief explanation of why this action"
}}

IMPORTANT:
- For click actions, provide approximate pixel coordinates based on where you see the element
- The viewport is 1280x900 pixels
- Be precise with coordinates - aim for the center of clickable elements
- If you see a search box, type the search term directly
- If extracting release info, include version, tag, and author in the value field as JSON

Respond ONLY with the JSON object, no additional text."""
    
    async def _analyze_with_claude(self, image_b64: str, prompt: str) -> str:
        """Analyze page using Claude. Retries on 429 rate limit with backoff."""
        last_err = None
        for attempt in range(VISION_API_MAX_RETRIES):
            try:
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": image_b64,
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ],
                        }
                    ],
                )
                return message.content[0].text
            except anthropic.BadRequestError as e:
                err_str = str(e).lower()
                if "credit balance" in err_str or "too low" in err_str or "billing" in err_str:
                    print(
                        "Anthropic: credit balance too low. Add credits: https://console.anthropic.com/settings/plans",
                        file=sys.stderr,
                    )
                raise
            except anthropic.RateLimitError as e:
                last_err = e
                delay = (2 ** attempt) * 5
                if self.debug:
                    print(f"[Navigator] Claude rate limited, retrying in {delay}s (attempt {attempt + 1}/{VISION_API_MAX_RETRIES})", file=sys.stderr)
                await asyncio.sleep(delay)
        raise last_err
    
    async def _analyze_with_gpt4v(self, image_b64: str, prompt: str) -> str:
        """Analyze page using GPT-4V. Retries on rate_limit_exceeded; no retry on insufficient_quota."""
        last_err = None
        for attempt in range(VISION_API_MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_b64}"
                                    }
                                }
                            ],
                        }
                    ],
                    max_tokens=1024,
                )
                return response.choices[0].message.content
            except openai.RateLimitError as e:
                last_err = e
                err_str = str(e).lower()
                if "insufficient_quota" in err_str:
                    print(
                        "OpenAI returned insufficient_quota (billing/quota). Check usage: https://platform.openai.com/usage",
                        file=sys.stderr,
                    )
                    raise
                delay = (2 ** attempt) * 5
                if self.debug:
                    print(f"[Navigator] Rate limited, retrying in {delay}s (attempt {attempt + 1}/{VISION_API_MAX_RETRIES})", file=sys.stderr)
                await asyncio.sleep(delay)
        raise last_err
    
    async def _analyze_with_gemini(self, image_b64: str, prompt: str) -> str:
        """Analyze page using Google Gemini. Retries on rate limits and 503 overloaded."""
        image_bytes = base64.standard_b64decode(image_b64)
        image_part = genai_types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        last_err = None
        max_retries = VISION_API_MAX_RETRIES + 2  # 5 for Gemini (429 often says "retry in ~52s")
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[image_part, prompt],
                    config=genai_types.GenerateContentConfig(max_output_tokens=1024),
                )
                if response.text:
                    return response.text
                raise RuntimeError("Gemini returned empty response")
            except Exception as e:
                err_str = str(e).lower()
                retryable = (
                    "quota" in err_str or "billing" in err_str or "429" in err_str
                    or "503" in err_str or "unavailable" in err_str or "overloaded" in err_str
                )
                if retryable:
                    last_err = e
                    # Use API's "Please retry in X.Xs" when present, else exponential backoff
                    match = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", str(e), re.IGNORECASE)
                    delay = min(int(float(match.group(1)) + 1), 120) if match else (2 ** attempt) * 5
                    if self.debug:
                        print(f"[Navigator] Gemini rate limited/overloaded, retrying in {delay}s (attempt {attempt + 1}/{max_retries})", file=sys.stderr)
                    await asyncio.sleep(delay)
                else:
                    print(
                        "Gemini API error. Check API key and billing: https://aistudio.google.com/apikey",
                        file=sys.stderr,
                    )
                    raise
        # Exhausted retries on quota/429
        if last_err and ("429" in str(last_err) or "quota" in str(last_err).lower()):
            print(
                "Gemini free tier quota (e.g. 20 requests/day) may be exceeded. Try again later or check billing: https://ai.google.dev/gemini-api/docs/rate-limits",
                file=sys.stderr,
            )
        raise last_err
    
    def _parse_action_response(self, response: str) -> NavigationAction:
        """Parse the vision model's response into a NavigationAction."""
        # Clean up response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            lines = response.split('\n')
            response = '\n'.join(lines[1:-1])
        
        try:
            data = json.loads(response)
            return NavigationAction(
                action_type=data.get("action_type", "wait"),
                target=data.get("target"),
                value=data.get("value"),
                coordinates=tuple(data["coordinates"]) if data.get("coordinates") else None,
                confidence=data.get("confidence", 0.5),
                reasoning=data.get("reasoning", "")
            )
        except json.JSONDecodeError as e:
            if self.debug:
                print(f"[Navigator] Failed to parse response: {e}")
                print(f"[Navigator] Raw response: {response}")
            return NavigationAction(
                action_type="wait",
                reasoning=f"Failed to parse response: {e}"
            )
    
    async def execute_action(self, action: NavigationAction) -> bool:
        """
        Execute a navigation action.
        
        Returns:
            True if action was successful, False otherwise
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        if self.debug:
            print(f"[Navigator] Executing: {action.action_type} - {action.reasoning}")
        
        try:
            if action.action_type == "click":
                if action.coordinates:
                    x, y = action.coordinates
                    await self.page.mouse.click(x, y)
                    await self.page.wait_for_load_state("load", timeout=10000)
                else:
                    if self.debug:
                        print("[Navigator] Click action missing coordinates")
                    return False
                    
            elif action.action_type == "type":
                if action.value:
                    # Type and press Enter for search
                    await self.page.keyboard.type(action.value, delay=50)
                    await asyncio.sleep(0.5)
                    await self.page.keyboard.press("Enter")
                    await self.page.wait_for_load_state("load", timeout=10000)
                else:
                    return False
                    
            elif action.action_type == "scroll":
                direction = action.value or "down"
                delta = -500 if direction == "up" else 500
                await self.page.mouse.wheel(0, delta)
                await asyncio.sleep(0.5)
                
            elif action.action_type == "wait":
                await asyncio.sleep(2)
                
            elif action.action_type in ["extract", "done"]:
                # These don't require page interaction
                pass
                
            return True
            
        except Exception as e:
            if self.debug:
                print(f"[Navigator] Action failed: {e}")
            return False
    
    async def navigate(
        self,
        start_url: str,
        goal: str,
        repo: Optional[str] = None,
        allow_auth: bool = False,
        login_wait_sec: float = 0.0
    ) -> Optional[dict]:
        """
        Main navigation loop.
        
        Args:
            start_url: URL to start navigation from
            goal: Natural language description of the navigation goal
            repo: Optional repository name for simplified interface
        
        Returns:
            Extracted data if successful, None otherwise
        """
        await self.start()
        
        try:
            # Navigate to start URL (use "load" not "networkidle" - GitHub etc. never idle)
            await self.page.goto(start_url, wait_until="load", timeout=60000)
            if self.debug:
                print(f"[Navigator] Loaded: {start_url}")

            if login_wait_sec > 0:
                if self.debug:
                    print(f"[Navigator] Waiting {login_wait_sec}s for manual login")
                await asyncio.sleep(login_wait_sec)

            context_history = []
            url_history = []

            while self.step_count < self.max_steps:
                self.step_count += 1
                
                current_url = self.page.url
                url_history.append(current_url)

                # Guardrail: recover from auth pages without clicking anything
                if (not allow_auth) and await self._is_auth_page(current_url):
                    if self.debug:
                        print(f"[Navigator] Detected auth page: {current_url}")
                    # Prefer known repo; otherwise go back to GitHub root
                    if repo:
                        await self.page.goto(f"https://github.com/{repo}", wait_until="load", timeout=60000)
                    else:
                        await self.page.goto("https://github.com", wait_until="load", timeout=60000)
                    context_history.append("Detected auth page; navigated away")
                    await asyncio.sleep(1)
                    continue

                # Build context from history
                context = "\n".join(context_history[-5:])  # Last 5 actions
                
                # Analyze page and get next action
                action = await self.analyze_page(goal, context)
                
                if self.debug:
                    print(f"[Step {self.step_count}] {action.action_type}: {action.target}")
                    print(f"    Confidence: {action.confidence:.2f}")
                    print(f"    Reasoning: {action.reasoning}")
                
                # Check if we're done
                if action.action_type == "done" or action.action_type == "extract":
                    if action.value:
                        try:
                            extracted = json.loads(action.value)
                            return self._format_output(extracted, repo)
                        except json.JSONDecodeError:
                            return {"raw_data": action.value}
                    else:
                        if self.debug:
                            print("[Navigator] Done but no data extracted")
                        return None
                
                # Block clicks on auth-related elements
                if (not allow_auth) and action.action_type == "click" and self._is_auth_target(action.target):
                    context_history.append(
                        f"Step {self.step_count}: blocked auth click on '{action.target}'"
                    )
                    await asyncio.sleep(0.5)
                    continue

                # Execute the action
                success = await self.execute_action(action)
                
                # Update context
                status = "success" if success else "failed"
                context_history.append(
                    f"Step {self.step_count}: {action.action_type} on '{action.target}' - {status}"
                )
                
                # Small delay between actions
                await asyncio.sleep(1)
            
            if self.debug:
                print("[Navigator] Max steps reached without completing goal")
            return None
            
        finally:
            await self.stop()

    async def _is_auth_page(self, url: str) -> bool:
        """Detect GitHub auth/signup pages using URL and visible text."""
        if re.search(r"github\.com/(login|sessions|signup)", url):
            return True
        try:
            content = await self.page.content()
        except Exception:
            return False
        auth_markers = [
            "Sign up for GitHub",
            "Create your free account",
            "Sign in to GitHub",
            "Continue with Google",
            "Continue with Apple",
        ]
        return any(marker.lower() in content.lower() for marker in auth_markers)

    def _is_auth_target(self, target: Optional[str]) -> bool:
        """Block clicks on auth-related UI targets."""
        if not target:
            return False
        lowered = target.lower()
        blocked = [
            "sign in",
            "sign up",
            "create account",
            "log in",
            "login",
            "continue with google",
            "continue with apple",
        ]
        return any(term in lowered for term in blocked)
    
    def _format_output(self, extracted: dict, repo: Optional[str] = None) -> dict:
        """Format extracted data into the required output structure."""
        return {
            "repository": repo or extracted.get("repository", "unknown"),
            "latest_release": {
                "version": extracted.get("version", extracted.get("tag_name", "unknown")),
                "tag": extracted.get("tag", extracted.get("commit", "unknown")),
                "author": extracted.get("author", "unknown"),
                "release_notes": extracted.get("release_notes"),
                "publish_date": extracted.get("publish_date"),
                "download_links": extracted.get("download_links")
            }
        }


async def main():
    parser = argparse.ArgumentParser(
        description="Autonomous web navigation using vision models"
    )
    parser.add_argument(
        "--url",
        default="https://github.com",
        help="Starting URL (default: https://github.com)"
    )
    parser.add_argument(
        "--repo",
        help="Repository to find (e.g., 'openclaw/openclaw')"
    )
    parser.add_argument(
        "--prompt",
        help="Natural language navigation prompt"
    )
    # Default provider from env: prefer openrouter if OPENROUTER_API_KEY, else claude, else gpt4v, else gemini
    _openai_key = os.environ.get("OPENAI_API_KEY")
    _anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    _gemini_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    _openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if _openrouter_key:
        _default_provider = "openrouter"
    elif _anthropic_key:
        _default_provider = "claude"
    elif _openai_key:
        _default_provider = "gpt4v"
    elif _gemini_key:
        _default_provider = "gemini"
    else:
        _default_provider = "claude"
    parser.add_argument(
        "--provider",
        choices=["claude", "gpt4v", "gemini", "openrouter"],
        default=_default_provider,
        help=f"Vision model provider (default: {_default_provider}, from API keys in .env)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser with visible window"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output and save screenshots"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="output.json",
        help="Output file path (default: output.json)"
    )
    parser.add_argument(
        "--allow-auth",
        action="store_true",
        help="Allow navigating to GitHub login/signup pages"
    )
    parser.add_argument(
        "--login-wait",
        type=float,
        default=0.0,
        help="Seconds to wait after loading start URL for manual login"
    )
    
    args = parser.parse_args()
    
    # Determine headless mode
    headless = not args.no_headless
    
    # Build the goal
    if args.prompt:
        goal = args.prompt
    elif args.repo:
        goal = f"Search for '{args.repo}' repository, navigate to it, find the Releases section, and extract the latest release information including version, tag/commit hash, and author."
    else:
        goal = "Search for 'openclaw' repository, navigate to github.com/openclaw/openclaw, find the Releases section, and extract the latest release information."

    # Add instruction to avoid sign-in for all goals
    goal += " IMPORTANT: You can view public repositories without signing in. DO NOT click 'Sign in' or 'Create account' links."
    
    # Create navigator
    provider_map = {
        "claude": VisionProvider.CLAUDE,
        "gpt4v": VisionProvider.GPT4V,
        "gemini": VisionProvider.GEMINI,
        "openrouter": VisionProvider.OPENROUTER
    }
    provider = provider_map[args.provider]
    navigator = VisionNavigator(
        provider=provider,
        headless=headless,
        debug=args.debug
    )
    
    print(f"Starting navigation with goal: {goal}")
    print(f"Provider: {args.provider}")
    print("-" * 50)
    
    # Run navigation
    result = await navigator.navigate(
        start_url=args.url,
        goal=goal,
        repo=args.repo,
        allow_auth=args.allow_auth,
        login_wait_sec=args.login_wait
    )
    
    if result:
        # Pretty print result
        output = json.dumps(result, indent=2)
        print("\nExtracted Data:")
        print(output)
        
        # Save to file
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"\nSaved to: {args.output}")
    else:
        print("\nNavigation failed to extract data")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
