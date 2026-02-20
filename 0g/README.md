# ⚽ Arsenal FC Scout AI - Powered by 0G Compute

A next-generation football scouting platform that uses **0G decentralized compute** for AI-powered player analysis. Built for ETHDenver 2024 Hackathon.

## 🚀 Features

### Core Functionality
- **Current Squad** - View Arsenal's first-team players with detailed profiles
- **Club Legends** - Honor Arsenal greats (Thierry Henry, Arsène Wenger, and more)
- **Transfer Market** - Scout available targets with AI analysis
- **Budget Tracker** - Monitor transfer budget in real-time

### 🤖 AI-Powered Features (0G Compute)
1. **AI Scout Reports** - LLM-generated player analysis considering:
   - Tactical fit for Arsenal's system
   - Strengths and weaknesses
   - Value assessment
   - Transfer recommendations

2. **AI Recommendation Engine** - Automatically suggests top 3 transfer targets based on:
   - Overall rating
   - Squad depth analysis
   - Arsenal's playing style

3. **Sign Player Animation** - Immersive experience with:
   - Confetti burst effect
   - Transaction toast notifications
   - "Submitted to 0G Compute" messaging

## 🛠️ Tech Stack

- **Backend**: Flask 3.0 (Python)
- **AI**: 0G Compute (OpenAI-compatible API)
- **Frontend**: Tailwind CSS + Vanilla JavaScript
- **Data**: JSON-based player database
- **Animations**: canvas-confetti library

## 📦 Installation

### Prerequisites
- Python 3.8+
- pip
- 0G Compute API credentials ([Get them here](https://build.0g.ai))

### Setup

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Get 0G Compute Credentials**:

   **Option A: Using CLI (Recommended)**
   ```bash
   npm install -g @0glabs/0g-compute-cli
   0g-compute-cli setup-network
   0g-compute-cli login
   ```

   **Option B: Web Dashboard**
   - Visit [https://build.0g.ai](https://build.0g.ai)
   - Sign in and get your API key + service URL

3. **Configure Environment**:

   Edit `.env` file and add your 0G credentials:
   ```bash
   ZG_COMPUTE_API_KEY=app-sk-your-key-here
   ZG_COMPUTE_URL=https://your-0g-endpoint
   ```

4. **Run the Application**:
   ```bash
   python app.py
   ```

5. **Open in Browser**:
   ```
   http://localhost:5000
   ```

## 🎮 Demo Flow

1. **Landing Page** → View stats and AI recommendations
2. **Browse Squad** → See current Arsenal players (Saka, Odegaard, Rice, etc.)
3. **Hall of Legends** → Explore Arsenal greats (Henry featured prominently)
4. **Transfer Market** → Filter by position, view available targets
5. **AI Analysis** → Click "Analyze with AI" on any player
6. **0G Magic** ✨ → LLM generates detailed scouting report in ~2 seconds
7. **Sign Player** → Click "Sign Player" for confetti + transaction simulation

## 📊 Player Data

- **24 Total Players**:
  - 11 Current Squad (Saliba, Saka, Odegaard, Rice, etc.)
  - 8 Club Legends (Thierry Henry, Arsène Wenger, Bergkamp, Vieira, etc.)
  - 5 Transfer Targets (Osimhen, Toney, Zubimendi, Eze, Gyökeres)

- **Data Fields**:
  - Name, Position, Overall Rating (0-100)
  - Age, Market Value, Biography

## 🔧 Configuration

### 0G Compute Models

Default model: `meta-llama/Llama-3.2-3B-Instruct` (fast, optimized for demos)

Alternative models:
- `meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo`
- Other OpenAI-compatible models

### Mock AI Mode

If 0G credentials are not configured, the app automatically falls back to mock AI mode with realistic-looking analyses.

## 🎨 Features Showcase

### 1. AI Recommendation Engine
```
Automatically highlights top 3 transfer targets on homepage
Glowing cards with priority rankings
Based on rating + tactical fit analysis
```

### 2. Sign Player Animation
```javascript
fireConfetti(); // Arsenal-themed confetti burst
showToast("Transaction submitted to 0G Compute");
// Simulates blockchain transaction
```

### 3. Real-time AI Analysis
```python
# Powered by 0G Compute decentralized AI
client.chat.completions.create(
    model="meta-llama/Llama-3.2-3B-Instruct",
    messages=[system_prompt, user_prompt]
)
```

## 🏗️ Project Structure

```
0g/
├── app.py                 # Flask application (100 lines)
├── players.json           # Player database (200 lines)
├── requirements.txt       # Dependencies
├── .env                   # 0G credentials
├── templates/
│   ├── base.html         # Arsenal-themed layout
│   ├── index.html        # Landing page with AI recs
│   └── players.html      # Shared player display
└── README.md             # This file
```

## 🎯 Why 0G Compute?

### Benefits Showcased
- ⚡ **50-100ms latency** - Near-instant AI analysis
- 🔒 **TEE-powered security** - Private player data
- 💎 **90% cost reduction** - vs traditional cloud AI
- 🌐 **Decentralized** - No single point of failure

### Integration Approach
```python
# OpenAI-compatible API = easy integration
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("ZG_COMPUTE_API_KEY"),
    base_url=os.getenv("ZG_COMPUTE_URL") + "/v1/proxy"
)
```

## 🐛 Troubleshooting

### "0G Compute credentials not found"
- Check `.env` file has `ZG_COMPUTE_API_KEY` and `ZG_COMPUTE_URL`
- Verify API key format: `app-sk-xxxxx`
- App will work in mock AI mode without credentials

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### Port already in use
```bash
# Change port in app.py:
app.run(debug=True, port=5001)  # Use different port
```

## 🎥 Demo Talking Points

1. **0G Integration** - "Using decentralized AI for player analysis, 90% cheaper than cloud"
2. **Real-time Analysis** - "LLM generates scouting reports in under 2 seconds"
3. **Arsenal-Specific** - "Features club legends like Thierry Henry and Arsène Wenger"
4. **Budget Management** - "Real-world transfer budget constraints (€500M total)"
5. **UX Polish** - "Confetti animations, toast notifications, position filtering"

## 📈 Future Enhancements

- [ ] Radar chart player comparisons
- [ ] Blockchain transaction signing for transfers
- [ ] 0G Storage integration for player stats history
- [ ] Multi-club support
- [ ] Real-time data scraping from transfermarkt
- [ ] Mobile-responsive design

## 🏆 Built For

**ETHDenver 2024 Hackathon**
- Focus: 0G Compute integration
- Category: AI + Blockchain
- Demo Time: 60 minutes

## 📝 License

MIT License - Built for hackathon educational purposes

---

**Made with ❤️ and ⚽ by Arsenal fans for 0G Compute**
