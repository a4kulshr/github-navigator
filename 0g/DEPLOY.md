# Deploy to Vercel

## Quick Deploy

1. **Install Vercel CLI** (optional, for CLI deploy):
   ```bash
   npm i -g vercel
   ```

2. **Deploy from the `0g` directory**:
   ```bash
   cd 0g
   vercel
   ```
   Follow the prompts to link your project or create a new one.

3. **Production deploy**:
   ```bash
   vercel --prod
   ```

## Deploy via GitHub

1. Push your repo to GitHub
2. Go to [vercel.com/new](https://vercel.com/new)
3. Import your repository
4. Set **Root Directory** to `0g` (if the repo root is the parent)
5. Deploy — Vercel auto-detects the Flask app

## Environment Variables

Set these in Vercel Dashboard → Project → Settings → Environment Variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `FLASK_SECRET_KEY` | No | Secret key for sessions (defaults to dev value) |
| `ZG_CONFIG_JSON` | No | JSON string of 0G config (for live AI). Without this, app runs in mock mode |

### 0G Compute (optional)

To enable live AI analysis instead of mock mode, add `ZG_CONFIG_JSON` with the contents of your `0g-config.json`:

```bash
# Get your config (run locally after npm run setup)
cat 0g-config.json
```

Paste the JSON as the value of `ZG_CONFIG_JSON` in Vercel. Ensure it's valid JSON (no line breaks if pasted as one line).

## Bundle Size

The deployment excludes `node_modules/` to stay under Vercel's 250MB limit. The Python app, templates, and `players.json` are included.
