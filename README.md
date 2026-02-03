# Autonomous Web Navigator with Vision Models

A tool that uses vision models (Claude/GPT-4V) to autonomously navigate GitHub and extract release information without relying on hardcoded CSS selectors or XPath.

## Overview

This project demonstrates autonomous web navigation using vision models. Instead of relying on brittle selectors that break when websites change their HTML structure, this tool:

1. Takes screenshots of web pages
2. Sends them to a vision model (Claude or GPT-4V)
3. Asks the model to analyze what it sees and decide on the next action
4. Executes the action (click, type, scroll)
5. Repeats until the goal is achieved

## Features

- **Vision-based navigation**: Uses AI to understand page content visually
- **No hardcoded selectors**: Works even if GitHub changes its UI
- **Multiple providers**: Supports Claude (Anthropic) and GPT-4V (OpenAI)
- **Natural language goals**: Accepts flexible prompts for navigation
- **Debug mode**: Saves screenshots at each step for analysis
- **Structured output**: Returns clean JSON with extracted data

## Quick Start

### 1. Install Dependencies

Setup follows [Playwright Python — Installation](https://playwright.dev/python/docs/intro): install the package, then install browser binaries.

**One command (recommended):**
```bash
cd github-navigator
./install.sh
```

**Manual (using venv):**
```bash
cd github-navigator
python3 -m venv venv   # if you don't have venv yet
venv/bin/python -m pip install -r requirements.txt
venv/bin/playwright install chromium
```

### 2. Set Up API Keys

```bash
# For Claude (recommended)
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# For GPT-4V (alternative)
export OPENAI_API_KEY="your-openai-api-key"
```

### 3. Run the Navigator

```bash
# Simple usage - find openclaw releases
python navigate.py --repo "openclaw/openclaw"

# With custom prompt
python navigate.py --url "https://github.com" \
    --prompt "search for openclaw and get the current release and related tags"

# With GPT-4V instead of Claude
python navigate.py --repo "openclaw/openclaw" --provider gpt4v

# Debug mode (saves screenshots)
python navigate.py --repo "openclaw/openclaw" --debug

# See browser window (not headless)
python navigate.py --repo "openclaw/openclaw" --no-headless --debug
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--url` | Starting URL | `https://github.com` |
| `--repo` | Repository to find (e.g., `owner/repo`) | None |
| `--prompt` | Natural language navigation goal | Auto-generated |
| `--provider` | Vision model: `claude` or `gpt4v` | `claude` |
| `--headless` | Run browser without visible window | `True` |
| `--no-headless` | Show browser window | `False` |
| `--debug` | Enable debug output and screenshots | `False` |
| `--output`, `-o` | Output JSON file path | `output.json` |

## Example Output

```json
{
  "repository": "openclaw/openclaw",
  "latest_release": {
    "version": "v2026.1.29",
    "tag": "77e703c",
    "author": "steipete",
    "release_notes": "Bug fixes and performance improvements...",
    "publish_date": "Jan 29, 2026"
  }
}
```

## How It Works

### Navigation Flow

1. **Start**: Load GitHub homepage
2. **Search**: Vision model identifies search box, types repository name
3. **Select**: Model identifies correct repository in search results
4. **Navigate**: Model finds and clicks "Releases" link
5. **Extract**: Model reads release information from the page
6. **Output**: Structured JSON is returned

### Vision Model Integration

The tool sends each screenshot to the vision model with a prompt asking:
- What type of page is this?
- What elements are visible?
- What's the next logical action?
- What are the coordinates to click?

The model responds with structured JSON specifying the action to take.

### Error Handling

- **Retry logic**: Failed clicks are retried up to 3 times
- **Timeout handling**: Pages that take too long trigger a wait and retry
- **Max steps**: Safety limit prevents infinite loops (default: 20 steps)
- **State tracking**: All actions are logged for debugging

## Project Structure

```
github-navigator/
├── install.sh           # Install deps + Playwright browsers (see playwright.dev/python/docs/intro)
├── run.sh               # One-command runner
├── navigate.py          # Main navigator script
├── navigate_enhanced.py  # Enhanced version with more features
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── observations.md     # Development observations and trade-offs
├── sample_output.json  # Example output from running the tool
└── screenshots/        # Debug screenshots (when --debug is used)
```

## Alternative: Enhanced Navigator

The `navigate_enhanced.py` script includes additional features:

```bash
python navigate_enhanced.py --repo "openclaw/openclaw" --debug
```

Features:
- Better error recovery
- Resource blocking for faster loading
- More detailed logging
- UI element hints for common GitHub pages

## Extending the Tool

### Adding Support for Other Websites

The vision-based approach means the tool can potentially work with any website. Modify the goal prompt to navigate different sites:

```python
navigator.navigate(
    start_url="https://gitlab.com",
    goal="Find the numpy repository and extract the latest tag"
)
```

### Custom Extraction

Modify the extraction prompt in `_analyze_with_vision()` to extract different data:

```python
prompt = """
Extract the following from this page:
- All download links
- File sizes
- Changelog entries
Return as JSON...
"""
```

## Limitations

- **API costs**: Each step requires a vision model API call
- **Speed**: Slower than direct scraping (but more robust)
- **Accuracy**: Vision models may occasionally misidentify elements
- **Rate limits**: GitHub may rate-limit rapid navigation

## Troubleshooting

### "Anthropic client not initialized"
Set your API key: `export ANTHROPIC_API_KEY="your-key"`

### "Playwright browsers not installed" / "No module named 'playwright'"
Run `./install.sh` (or see [Playwright Python — Installation](https://playwright.dev/python/docs/intro)): `venv/bin/python -m pip install -r requirements.txt` then `venv/bin/playwright install chromium`.

### Navigation seems stuck
- Enable debug mode to see screenshots
- Check if GitHub is showing a CAPTCHA or login prompt
- Increase timeout values in the code

### Wrong element clicked
Vision models estimate coordinates. If clicks miss:
- Enable `--debug` to review screenshots
- The model should self-correct on subsequent steps

## License

MIT License - See LICENSE file for details.
