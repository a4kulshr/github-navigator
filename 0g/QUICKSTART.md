# 🚀 Quick Start - Arsenal Scout AI with 0G Serving Broker

## Prerequisites

You already have:
- ✅ Private key in `.env` file
- ✅ Python 3.8+
- ✅ Node.js installed

## Setup (3 steps, ~5 minutes)

### Step 1: Install Node.js dependencies

```bash
cd 0g
npm install
```

### Step 2: Run 0G Setup Script

This will:
- Connect to 0G testnet using your private key
- Discover available AI services
- Configure authentication
- Generate `0g-config.json` with credentials

```bash
npm run setup
```

**Expected output:**
```
🚀 Arsenal Scout AI - 0G Compute Setup

1️⃣ Connecting to 0G Testnet...
   Wallet Address: 0x...
   Balance: X.XX 0G

2️⃣ Initializing 0G Compute Broker...
   ✅ Broker initialized

3️⃣ Discovering AI services...
   Found X service(s):
   ...

✅ Setup Complete!
```

**If you see "Wallet has 0 balance":**
- Visit https://faucet.0g.ai
- Enter your wallet address (shown in output)
- Get free testnet tokens
- Run `npm run setup` again

### Step 3: Install Python dependencies and run

```bash
pip install -r requirements.txt
python app.py
```

Open browser: **http://localhost:5000**

## 🎮 Testing the Demo

1. **Homepage** → See AI recommendations (top 3 players)
2. **Current Squad** → Click "Analyze with AI" on any player
3. **Wait 2-3 seconds** → 0G Compute generates analysis
4. **Transfer Market** → Click "Sign Player" for confetti

## 🔧 Troubleshooting

### "No services found"
- Network may be down, check https://docs.0g.ai
- App will work in mock AI mode

### "Setup failed: insufficient funds"
- Get testnet tokens from faucet
- Minimum ~0.1 0G needed

### "Module 'requests' not found"
```bash
pip install -r requirements.txt
```

### Port 5000 already in use
Edit `app.py` line 177:
```python
app.run(debug=True, port=5001)  # Change port
```

## 📋 What the Setup Script Does

1. **Connects** to 0G testnet (`https://evmrpc-testnet.0g.ai`)
2. **Initializes** 0G Serving Broker with your wallet
3. **Lists** available AI inference services
4. **Selects** best service (usually LLaMA model)
5. **Acknowledges** provider (required for access)
6. **Generates** authentication headers
7. **Saves** configuration to `0g-config.json`
8. **Updates** `.env` with endpoint details

## 🔍 Behind the Scenes

### 0G Serving Broker Flow
```
Your Wallet → 0G Broker → Service Discovery
              ↓
        Acknowledge Provider → Get Headers
              ↓
        Flask App → HTTP Request → 0G Service
              ↓
        AI Response → Player Analysis
```

### Files Generated
- `0g-config.json` - Service endpoint, model, auth headers
- `.env` (updated) - Endpoint and provider address
- `node_modules/` - 0G broker SDK

## 🎯 Demo Talking Points

**"This uses 0G Serving Broker for decentralized AI:"**

1. **No API Keys** - "Authentication via blockchain wallet signature"
2. **Decentralized** - "AI runs on distributed GPU marketplace"
3. **90% Cheaper** - "Pay-per-use, no subscriptions"
4. **TEE Secure** - "Private player data never leaves secure enclaves"

**Show the setup:**
```bash
# Show 0g-config.json
cat 0g-config.json

# Shows: endpoint, model, provider address, auth headers
```

## 💡 Next Steps

After demo works:
- [ ] Add more models (text-to-image for player photos)
- [ ] Store scouting reports on 0G Storage
- [ ] Implement transfer transactions on 0G Chain
- [ ] Deploy to production 0G mainnet

---

**Ready to demo! 🚀⚽**
