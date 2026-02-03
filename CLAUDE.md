# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an autonomous web navigator that uses vision models (Claude/GPT-4V/Gemini) to navigate GitHub and extract release information **without hardcoded CSS selectors or XPath**. The tool takes screenshots, sends them to vision models for analysis, and executes actions based on the model's decisions.

The core design philosophy is **robustness over speed** - the vision-first architecture makes the navigator resilient to UI changes at the cost of slower execution and API costs.

## Setup and Installation

### Install Dependencies
```bash
# Recommended one-command install
./install.sh

# Manual installation
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
venv/bin/playwright install chromium
```

### API Key Configuration
Set API keys in `.env` file (already in `.gitignore`):
```bash
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here          # Optional for GPT-4V
GOOGLE_API_KEY=your-key-here          # Optional for Gemini
```

## Common Commands

### Run Navigator
```bash
# Basic usage with default provider
python navigate.py --repo "owner/repo"

# With specific provider
python navigate.py --repo "owner/repo" --provider claude
python navigate.py --repo "owner/repo" --provider gpt4v
python navigate.py --repo "owner/repo" --provider gemini

# Debug mode (saves screenshots)
python navigate.py --repo "owner/repo" --debug

# Visible browser window
python navigate.py --repo "owner/repo" --no-headless --debug

# Custom prompt
python navigate.py --url "https://github.com" \
    --prompt "search for repo and get current release"

# Enhanced navigator
python navigate_enhanced.py --repo "owner/repo" --debug
```

### Run Tests
```bash
# Run all tests
pytest test_navigator.py -v

# Run specific test
pytest test_navigator.py::TestOutputFormat -v
```

### Clean Up
```bash
# Remove generated files
rm -rf screenshots/ output/ output.json
```

## Architecture

### Core Components

1. **VisionNavigator** (`navigate.py`): Main navigator with support for Claude, GPT-4V, and Gemini
   - Stateless design with action history passed in prompts
   - Maximum 20 navigation steps by default
   - Screenshots saved in `screenshots/` when `--debug` is enabled

2. **EnhancedVisionNavigator** (`navigate_enhanced.py`): Enhanced version with:
   - Retry logic for failed actions (max 3 retries)
   - UI element hints for common GitHub pages (non-hardcoded)
   - Resource blocking for faster page loads
   - More detailed logging and state tracking

### Navigation Flow
```
1. Load start URL → 2. Take screenshot → 3. Send to vision model
→ 4. Receive action (click/type/scroll/extract/done)
→ 5. Execute action → 6. Repeat until goal achieved or max steps
```

### Action Types
- **click**: Click at (x, y) coordinates estimated by vision model
- **type**: Type text and press Enter (for search boxes)
- **scroll**: Scroll viewport up/down
- **extract**: Parse data from current page (when on releases page)
- **wait**: Wait for page to load
- **done**: Navigation complete

### Vision Provider Selection
Default provider auto-selected from available API keys:
1. Claude (if `ANTHROPIC_API_KEY` set) - **Recommended**
2. GPT-4V (if `OPENAI_API_KEY` set and no Anthropic key)
3. Gemini (if `GOOGLE_API_KEY` or `GEMINI_API_KEY` set)
4. Claude (default fallback)

Override with `--provider` flag.

## Key Design Decisions

### Why Vision-First Architecture?
- **Robust to UI changes**: No brittle CSS selectors that break when GitHub changes HTML
- **Transferable**: Same approach works on different websites
- **Natural language goals**: Users specify intent, not implementation

### Trade-offs
- **Speed**: 5-15 seconds per step vs. milliseconds for traditional scraping
- **Cost**: ~$0.10-0.30 per navigation vs. free for traditional scraping
- **Predictability**: Same page may be analyzed differently on different runs
- **Coordinate precision**: Vision models estimate click coordinates (not pixel-perfect)

### Rate Limiting & Throttling
- `VISION_API_DELAY_SEC` environment variable controls delay between vision API calls (default: 2.0s)
- Retry logic for `rate_limit_exceeded` errors (max 3 retries with exponential backoff)
- No retries for `insufficient_quota` errors (prints helpful message instead)
- Gemini gets 5 retries (vs. 3 for others) due to frequent 429 responses

## Important Implementation Details

### Coordinate System
- Viewport is **1280x900 pixels**
- Vision model estimates click coordinates based on visual analysis
- Typical locations (hints, not hardcoded):
  - Search box: ~(640, 40) at top center
  - Search results: ~(300-500, 200-400) left side
  - Releases link: ~(1000-1150, 300-500) right sidebar

### Wait Strategies
- `navigate.py`: Uses `wait_until="load"` (GitHub never reaches networkidle)
- `navigate_enhanced.py`: Uses `wait_until="networkidle"` with timeout handling
- Additional `asyncio.sleep()` delays for page settling

### Screenshot Management
- Saved in `screenshots/` directory (created if not exists)
- Naming: `step_NNN.png` where NNN is zero-padded step number
- Only saved when `--debug` flag is enabled
- Full-page screenshots disabled (uses viewport only)

### Vision Model Prompts
Two prompt types:
1. **Navigation prompts**: Ask model to analyze page and decide next action
2. **Extraction prompts**: Ask model to extract structured release data when on releases page

Prompts include:
- Current goal
- Recent action history (last 5 actions)
- Coordinate guidelines and viewport size
- Expected JSON response format

## Output Format

```json
{
  "repository": "owner/repo",
  "latest_release": {
    "version": "v1.0.0",
    "tag": "abc123",
    "author": "username",
    "release_notes": "Notes text or null",
    "publish_date": "Jan 1, 2026 or null",
    "download_links": ["url1", "url2"] or null
  }
}
```

## Limitations & Known Issues

1. **Public repos only**: No authentication support
2. **Viewport dependent**: Coordinates tuned for 1280x900 viewport
3. **API costs**: Each navigation step costs ~$0.01-0.03 in API calls
4. **No complex interactions**: Can't handle modals requiring hover, multi-step dropdowns
5. **GitHub-optimized prompts**: While architecture is general, prompts tuned for GitHub
6. **Dynamic content**: JavaScript-heavy pages may be analyzed in loading state

## Testing

The `test_navigator.py` file contains:
- Import tests for both navigator modules
- Data class creation tests
- Output format validation (checks `sample_output.json`)
- JSON response parsing tests (including markdown-wrapped JSON)

Tests use `pytest.skip()` for missing dependencies rather than failing.

## Extending the Tool

### Add Support for Other Websites
Modify the goal prompt in navigation calls:
```python
navigator.navigate(
    start_url="https://gitlab.com",
    goal="Find numpy repo and extract latest tag"
)
```

### Add Custom Data Extraction
Modify extraction prompt in `_analyze_with_vision()` or `_analyze_with_claude()`:
```python
prompt = """Extract from this page:
- Download links
- File sizes
- Changelog entries
Return as JSON..."""
```

### Add New Vision Provider
1. Import provider client library
2. Add to `VisionProvider` enum
3. Implement `_analyze_with_<provider>()` method
4. Add to `_init_vision_client()` method
5. Update provider selection logic in `main()`
