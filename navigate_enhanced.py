#!/usr/bin/env python3
"""
Enhanced Navigator with Retry Logic and Fallback Strategies

This version includes:
- Retry logic for failed actions
- Fallback coordinate estimation
- Better error recovery
- More detailed logging
"""

import asyncio
import base64
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# Load .env so ANTHROPIC_API_KEY is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from playwright.async_api import async_playwright, Page, Browser, Locator

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass 
class ActionResult:
    """Result of executing an action."""
    success: bool
    message: str
    screenshot_path: Optional[str] = None
    data: Optional[dict] = None


@dataclass
class NavigationState:
    """Tracks the current state of navigation."""
    current_url: str = ""
    page_title: str = ""
    step: int = 0
    actions_taken: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    goal_achieved: bool = False


class EnhancedVisionNavigator:
    """
    Enhanced navigator with better error handling and retry logic.
    """
    
    # Known UI element locations for common GitHub pages (used as hints, not hardcoded selectors)
    UI_HINTS = {
        "github_homepage": {
            "search_box": {"area": "top-center", "approx_coords": (640, 40)},
        },
        "search_results": {
            "first_result": {"area": "left-center", "approx_coords": (400, 250)},
        },
        "repository_page": {
            "releases_link": {"area": "right-sidebar", "approx_coords": (1100, 400)},
        }
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        headless: bool = True,
        debug: bool = False,
        output_dir: str = "output"
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.headless = headless
        self.debug = debug
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.state = NavigationState()
        
        # Configuration
        self.max_retries = 3
        self.max_steps = 25
        self.action_timeout = 15000  # ms
        
        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None
    
    async def start_browser(self):
        """Initialize the browser with optimized settings."""
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
        )
        
        # Block unnecessary resources for faster loading
        await context.route("**/*.{png,jpg,jpeg,gif,svg,ico}", lambda route: route.abort())
        await context.route("**/*google-analytics*", lambda route: route.abort())
        
        self.page = await context.new_page()
        self._log("Browser started")
    
    async def stop_browser(self):
        """Close the browser."""
        if self.browser:
            await self.browser.close()
            self._log("Browser closed")
    
    def _log(self, message: str, level: str = "INFO"):
        """Log a message."""
        if self.debug or level == "ERROR":
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")
    
    async def _take_screenshot(self, name: str = "screenshot") -> tuple[bytes, str]:
        """Take and save a screenshot."""
        screenshot_bytes = await self.page.screenshot(full_page=False)
        
        filename = f"{self.state.step:03d}_{name}.png"
        filepath = self.output_dir / filename
        
        with open(filepath, 'wb') as f:
            f.write(screenshot_bytes)
        
        self._log(f"Screenshot saved: {filepath}")
        return screenshot_bytes, str(filepath)
    
    async def _analyze_with_vision(
        self,
        screenshot: bytes,
        instruction: str,
        extract_data: bool = False
    ) -> dict:
        """
        Use Claude to analyze the screenshot and determine action.
        """
        if not self.client:
            raise RuntimeError("Anthropic client not initialized. Set ANTHROPIC_API_KEY.")
        
        image_b64 = base64.standard_b64encode(screenshot).decode('utf-8')
        
        if extract_data:
            prompt = f"""Analyze this GitHub releases page screenshot and extract the release information.

Look for:
1. The latest release version (e.g., v2026.1.29 or similar version number)
2. The commit tag/hash (short alphanumeric code)
3. The author who published the release
4. Release date if visible
5. Release notes/description if visible

Respond with ONLY a JSON object:
{{
    "version": "the version string",
    "tag": "the commit hash/tag",
    "author": "username of author",
    "publish_date": "date if visible, else null",
    "release_notes": "first 200 chars of notes if visible, else null",
    "found": true/false
}}"""
        else:
            prompt = f"""You are a web navigation agent. Analyze this screenshot and determine the next action.

CURRENT TASK: {instruction}

NAVIGATION HISTORY:
{chr(10).join(self.state.actions_taken[-5:]) if self.state.actions_taken else "Starting navigation"}

Analyze what you see and respond with a JSON object:
{{
    "page_type": "what type of page is this (homepage/search_results/repo_page/releases_page/other)",
    "action": "click/type/scroll/wait/done",
    "target_description": "what element to interact with",
    "coordinates": [x, y],
    "type_text": "text to type if action is type, else null",
    "confidence": 0.0-1.0,
    "reasoning": "why this action"
}}

COORDINATE GUIDELINES:
- Viewport is 1280x900 pixels
- GitHub search box is typically around (640, 40) at the top
- Repository links in search results are typically on the left side (300-500, 200-400)
- "Releases" link on repo pages is often in the right sidebar (1000-1150, 300-500) or in tabs
- Aim for the CENTER of clickable elements

Be precise with coordinates based on what you actually see in the screenshot."""
        
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
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
                        {"type": "text", "text": prompt}
                    ],
                }
            ],
        )
        
        response_text = message.content[0].text.strip()
        
        # Clean up markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            self._log(f"Failed to parse response: {response_text}", "ERROR")
            return {"action": "wait", "reasoning": "Failed to parse vision model response"}
    
    async def _execute_click(self, x: int, y: int, retries: int = 0) -> ActionResult:
        """Execute a click action with retry logic."""
        try:
            await self.page.mouse.click(x, y)
            await self.page.wait_for_load_state("networkidle", timeout=self.action_timeout)
            await asyncio.sleep(1)  # Additional settling time
            return ActionResult(success=True, message=f"Clicked at ({x}, {y})")
        except Exception as e:
            if retries < self.max_retries:
                self._log(f"Click failed, retrying... ({retries + 1}/{self.max_retries})")
                await asyncio.sleep(1)
                return await self._execute_click(x, y, retries + 1)
            return ActionResult(success=False, message=f"Click failed: {e}")
    
    async def _execute_type(self, text: str) -> ActionResult:
        """Execute a type action."""
        try:
            await self.page.keyboard.type(text, delay=50)
            await asyncio.sleep(0.3)
            await self.page.keyboard.press("Enter")
            await self.page.wait_for_load_state("networkidle", timeout=self.action_timeout)
            return ActionResult(success=True, message=f"Typed: {text}")
        except Exception as e:
            return ActionResult(success=False, message=f"Type failed: {e}")
    
    async def navigate_to_releases(self, repo: str) -> Optional[dict]:
        """
        Navigate to a GitHub repository's releases page and extract information.
        
        Args:
            repo: Repository in format "owner/repo"
        
        Returns:
            Extracted release information or None
        """
        await self.start_browser()
        
        try:
            # Step 1: Go to GitHub
            self._log(f"Navigating to GitHub to find {repo}")
            await self.page.goto("https://github.com", wait_until="networkidle")
            self.state.current_url = self.page.url
            self.state.step += 1
            
            # Main navigation loop
            goal = f"Find repository {repo}, go to its Releases page, and extract the latest release info"
            
            while self.state.step < self.max_steps and not self.state.goal_achieved:
                screenshot, screenshot_path = await self._take_screenshot(f"step_{self.state.step}")
                
                # Determine if we're on the releases page
                current_url = self.page.url
                self._log(f"Current URL: {current_url}")
                
                if "/releases" in current_url:
                    # We're on releases page - extract data
                    self._log("On releases page - extracting data")
                    result = await self._analyze_with_vision(screenshot, "", extract_data=True)
                    
                    if result.get("found"):
                        self.state.goal_achieved = True
                        return {
                            "repository": repo,
                            "latest_release": {
                                "version": result.get("version", "unknown"),
                                "tag": result.get("tag", "unknown"),
                                "author": result.get("author", "unknown"),
                                "release_notes": result.get("release_notes"),
                                "publish_date": result.get("publish_date")
                            }
                        }
                
                # Get next action from vision model
                analysis = await self._analyze_with_vision(screenshot, goal)
                
                action = analysis.get("action", "wait")
                self._log(f"Action: {action} | {analysis.get('reasoning', '')}")
                
                if action == "done":
                    self.state.goal_achieved = True
                    break
                
                elif action == "click":
                    coords = analysis.get("coordinates", [640, 450])
                    result = await self._execute_click(coords[0], coords[1])
                    self.state.actions_taken.append(
                        f"Clicked {analysis.get('target_description', 'element')} at {coords}"
                    )
                
                elif action == "type":
                    text = analysis.get("type_text", repo)
                    result = await self._execute_type(text)
                    self.state.actions_taken.append(f"Typed: {text}")
                
                elif action == "scroll":
                    await self.page.mouse.wheel(0, 300)
                    self.state.actions_taken.append("Scrolled down")
                
                else:  # wait
                    await asyncio.sleep(2)
                
                self.state.step += 1
            
            self._log("Navigation completed without finding releases", "ERROR")
            return None
            
        except Exception as e:
            self._log(f"Navigation error: {e}", "ERROR")
            return None
            
        finally:
            await self.stop_browser()


async def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="openclaw/openclaw")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--output", "-o", default="sample_output.json")
    parser.add_argument("--no-headless", action="store_true")
    
    args = parser.parse_args()
    
    navigator = EnhancedVisionNavigator(
        headless=not args.no_headless,
        debug=args.debug
    )
    
    result = await navigator.navigate_to_releases(args.repo)
    
    if result:
        print("\n" + "=" * 50)
        print("EXTRACTED DATA:")
        print("=" * 50)
        output = json.dumps(result, indent=2)
        print(output)
        
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"\nSaved to: {args.output}")
    else:
        print("Failed to extract release information")


if __name__ == "__main__":
    asyncio.run(main())
