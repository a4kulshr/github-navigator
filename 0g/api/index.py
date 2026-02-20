from flask import Flask, render_template, jsonify
import os
import json
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder='templates')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'arsenal-scout-ai-secret-key-2024')

# Load 0G Compute configuration (file or env var for Vercel)
zg_config = None
zg_headers = None
try:
    config_json = os.getenv('ZG_CONFIG_JSON')
    if config_json and config_json.strip():
        zg_config = json.loads(config_json)
    else:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '0g-config.json')
        with open(config_path, 'r') as f:
            zg_config = json.load(f)
    zg_headers = zg_config.get('headers', {})
    print("✅ 0G Compute configuration loaded")
except FileNotFoundError:
    print("⚠️  0G configuration not found - using mock AI mode")
except Exception as e:
    print(f"⚠️  Error loading 0G config: {e} - using mock AI mode")

# Load player data
def load_players():
    """Load players from JSON file"""
    try:
        players_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'players.json')
        with open(players_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"players": [], "budget": {"total": "€500M", "spent": "€150M", "remaining": "€350M"}}

def get_player_by_id(player_id):
    """Get a single player by ID"""
    data = load_players()
    for player in data.get('players', []):
        if player['id'] == player_id:
            return player
    return None

# Routes
@app.route('/')
def index():
    """Landing page with AI recommendations"""
    data = load_players()
    stats = {
        'total_players': len(data.get('players', [])),
        'current_squad': len([p for p in data.get('players', []) if p.get('category') == 'current']),
        'legends': len([p for p in data.get('players', []) if p.get('category') == 'legend']),
        'transfers': len([p for p in data.get('players', []) if p.get('category') == 'transfer']),
        'budget': data.get('budget', {})
    }
    transfer_players = [p for p in data.get('players', []) if p.get('category') == 'transfer']
    recommendations = sorted(transfer_players, key=lambda x: x.get('overall', 0), reverse=True)[:3]
    return render_template('index.html', stats=stats, recommendations=recommendations)

@app.route('/players/<category>')
def show_players(category):
    """Display players by category"""
    data = load_players()
    players = [p for p in data.get('players', []) if p.get('category') == category]
    positions = sorted(set(p.get('position', '') for p in players))
    return render_template('players.html', players=players, category=category, positions=positions, budget=data.get('budget', {}))

@app.route('/analyze/<int:player_id>')
def analyze_player(player_id):
    """AI analysis endpoint"""
    player = get_player_by_id(player_id)
    if not player:
        return jsonify({"success": False, "error": "Player not found"}), 404

    if zg_config and zg_headers:
        try:
            system_msg = "You are an Arsenal FC scout. Analyze players concisely for tactical fit, value, and potential."
            user_msg = f"""Analyze {player['name']} ({player['position']}, {player['age']} years old) for Arsenal.
Current rating: {player['overall']}/100
Value: {player['value']}
Provide in 4-5 sentences:
1. Key strengths
2. Tactical fit for Arsenal's style (under Mikel Arteta)
3. Value assessment
4. Final recommendation (Sign/Scout/Pass)"""

            endpoint = zg_config['endpoint']
            model = zg_config['model']
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                "max_tokens": 300,
                "temperature": 0.7
            }
            response = requests.post(
                f"{endpoint}/v1/chat/completions",
                json=payload,
                headers=zg_headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            analysis = data['choices'][0]['message']['content']
            return jsonify({
                "success": True,
                "player": player['name'],
                "analysis": analysis,
                "powered_by": f"0G Compute ({zg_config.get('service_name', 'Unknown Service')})"
            })
        except Exception as e:
            print(f"0G API error: {e}")
            return mock_analysis(player)
    else:
        return mock_analysis(player)

def mock_analysis(player):
    """Generate mock AI analysis"""
    strengths_map = {
        'GK': 'shot-stopping and distribution',
        'CB': 'aerial duels and positional awareness',
        'RB': 'overlapping runs and defensive discipline',
        'LB': 'progressive carries and crossing',
        'CDM': 'ball retention and defensive positioning',
        'CM': 'box-to-box energy and passing range',
        'CAM': 'creativity and final third decision-making',
        'RW': 'pace, dribbling, and cutting inside',
        'LW': 'direct running and goal threat',
        'ST': 'finishing and movement in the box'
    }
    pos_group = player['position']
    strengths = strengths_map.get(pos_group, 'technical ability and tactical intelligence')
    rating = player['overall']
    recommendation = "SIGN" if rating >= 85 else "SCOUT" if rating >= 80 else "MONITOR"
    analysis = f"""{player['name']} shows {'excellent' if rating >= 85 else 'strong' if rating >= 80 else 'promising'} potential for Arsenal.
Strengths: Exceptional {strengths}, rated {rating}/100 with consistent performances.
Tactical Fit: Would integrate into Arsenal's possession-based approach, strengthening {pos_group} position.
Value: At {player['value']}, represents {'excellent' if rating >= 85 else 'good' if rating >= 80 else 'reasonable'} market value.
Recommendation: {recommendation} - {'Priority signing' if rating >= 85 else 'Continue monitoring' if rating >= 80 else 'One for the shortlist'}."""
    return jsonify({"success": True, "player": player['name'], "analysis": analysis, "powered_by": "Mock AI (0G Compute Ready)"})
