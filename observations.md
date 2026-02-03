# Observations Document

## Approach

### Core Design Philosophy

I chose a **vision-first architecture** where all navigation decisions are made by analyzing screenshots rather than parsing HTML. This approach was selected for several reasons:

1. **Robustness to UI changes**: Traditional web scrapers break when selectors change. Vision models see the page as a human would, making them resilient to markup restructuring.

2. **Natural language goals**: Users can express their intent naturally ("find the latest release") rather than writing complex selectors.

3. **Transferability**: The same approach can theoretically work on any website without code changes.

### Technology Choices

| Choice | Rationale |
|--------|-----------|
| **Python** | Rich ecosystem for browser automation and AI APIs |
| **Playwright** | Modern, fast, reliable browser automation with async support |
| **Claude (Anthropic)** | Excellent vision capabilities, reliable JSON output, my familiarity with the API |
| **Async/await** | Better performance for I/O-bound operations |

### Navigation Strategy

The navigator follows a simple loop:
1. Screenshot → Vision Model → Action Decision → Execute → Repeat

Actions are atomic:
- **click**: Click at specific coordinates
- **type**: Type text and press Enter
- **scroll**: Scroll the viewport
- **extract**: Parse data from current page
- **done**: Goal achieved

## What Worked Well

### 1. Vision Model Accuracy
Claude's vision capabilities proved remarkably accurate at:
- Identifying page types (homepage vs. search results vs. repo page)
- Locating interactive elements
- Estimating click coordinates
- Reading and extracting structured data

### 2. Coordinate-Based Clicking
Rather than trying to generate selectors, having the model output `(x, y)` coordinates worked surprisingly well. The model can visually estimate where the center of a button or link is located.

### 3. Structured JSON Responses
By asking the model to respond in strict JSON format, parsing became trivial. Claude follows JSON format instructions reliably.

### 4. Debug Mode
Saving screenshots at each step proved invaluable for understanding what the model "saw" and why it made certain decisions.

## What Didn't Work / Challenges

### 1. Coordinate Precision
Vision models don't have pixel-perfect accuracy. A click intended for "Releases" might land on an adjacent element. 

**Mitigation**: Added retry logic and allowed the model to self-correct in subsequent steps.

### 2. Dynamic Content
GitHub uses JavaScript to load content dynamically. Sometimes the model would see a loading state or partially rendered page.

**Mitigation**: Added `wait_for_load_state("networkidle")` and explicit wait actions.

### 3. Context Window Limitations
The model only sees the current screenshot—it has no memory of previous pages beyond what we tell it in the prompt.

**Mitigation**: Maintain a history of recent actions and include them in each prompt.

### 4. API Latency
Each vision API call takes 1-3 seconds, making navigation slower than traditional scraping.

**Trade-off accepted**: Robustness over speed is the explicit goal.

### 5. Model Hallucinations
Occasionally the model would claim to see elements that weren't visible or return coordinates outside the viewport.

**Mitigation**: Input validation, bounds checking, and retry logic.

## Trade-offs Made

### Speed vs. Robustness
- **Chose**: Robustness
- **Cost**: ~5-15 seconds per navigation step vs. milliseconds for traditional scraping
- **Justification**: The explicit goal was to avoid hardcoded selectors

### Simplicity vs. Features
- **Chose**: Simpler architecture
- **Cost**: No parallel browsing, limited error recovery
- **Justification**: Easier to understand, debug, and extend

### Single Model vs. Ensemble
- **Chose**: Single vision model
- **Cost**: Single point of failure for analysis
- **Alternative**: Could use multiple models and vote on actions

### Stateless Steps vs. Memory
- **Chose**: Pass recent history in prompts
- **Cost**: Context grows, potential for information loss
- **Alternative**: Could maintain structured state object

## Limitations

1. **GitHub-specific optimization**: While the approach is general, the prompts are tuned for GitHub's layout.

2. **No authentication**: Only works with public repositories.

3. **No JavaScript interaction**: Can't handle complex modals, dropdowns that require hover, etc.

4. **Cost**: Each step costs ~$0.01-0.03 in API calls. A full navigation might cost $0.10-0.30.

5. **Rate limiting**: Rapid API calls may hit rate limits on either Anthropic or GitHub.

6. **Viewport dependency**: The 1280x900 viewport is assumed; different sizes would need coordinate adjustments.

## Future Improvements

### Short-term
- [ ] Add support for more vision providers (Google Gemini, local models)
- [ ] Implement element detection using bounding boxes
- [ ] Cache screenshots to reduce redundant API calls
- [ ] Add support for authentication (GitHub login)

### Medium-term
- [ ] Train a specialized model for web navigation
- [ ] Implement parallel navigation for multiple repositories
- [ ] Add natural language query interface for arbitrary GitHub data
- [ ] Support for other code hosting platforms (GitLab, Bitbucket)

### Long-term
- [ ] Self-improving navigator that learns from failures
- [ ] General-purpose web agent for any website
- [ ] Integration with browser extensions for real-time assistance

## Honest Reflection

This project demonstrates that **vision-based web navigation is viable but not yet optimal**. The approach succeeds at its primary goal—avoiding hardcoded selectors—but introduces new challenges:

1. **It's slower**: What takes a scraper 100ms takes this tool 10-30 seconds.
2. **It's more expensive**: API costs add up for frequent use.
3. **It's less predictable**: The same page might be analyzed differently on different runs.

However, for use cases where **robustness matters more than speed**—such as monitoring, one-time data extraction, or navigating frequently-changing UIs—this approach has clear advantages.

The technology is also rapidly improving. As vision models get faster, cheaper, and more accurate, the trade-offs will shift in favor of this approach.

## Testing Approach

### Manual Testing
- Ran the navigator against multiple repositories
- Tested with different viewport sizes
- Verified JSON output structure
- Tested error recovery by simulating failures

### Scenarios Tested
1. Happy path: openclaw/openclaw → Releases → Extract
2. Repository with no releases
3. Repository with complex release page
4. Slow loading pages
5. Search with multiple similar results

### Validation
- Compared extracted data against manual verification
- Checked coordinate accuracy by reviewing screenshots
- Verified all JSON fields are populated correctly

## Conclusion

This project successfully demonstrates that vision models can autonomously navigate websites without hardcoded selectors. While the approach has trade-offs in speed and cost, it provides a level of robustness that traditional scraping cannot match. The architecture is extensible and could be adapted for many other web automation tasks.
