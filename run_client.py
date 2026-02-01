#!/usr/bin/env python3
"""
Simple script to run the GameClient with player_id='doraking'
"""

from client import GameClient
import json
from pathlib import Path

# Set player_id
PLAYER_ID = "doraking"
PLAYER_NAME = "doraking"

# Try to load existing session
SESSION_FILE = Path("session.json")
client = None

if SESSION_FILE.exists():
    try:
        with open(SESSION_FILE) as f:
            data = json.load(f)
        if data.get("player_id") == PLAYER_ID:
            client = GameClient(api_token=data.get("api_token"))
            client.player_id = data.get("player_id")
            client.name = data.get("name")
            print(f"Loaded session for {client.player_id}")
    except Exception as e:
        print(f"Error loading session: {e}")

# Register if not loaded
if not client or not client.api_token:
    client = GameClient()
    result = client.register(PLAYER_ID, PLAYER_NAME, location="remote")
    
    if result.get("ok"):
        print(f"Registered! Token: {client.api_token[:20]}...")
        candidates = result["data"].get("starting_candidates", [])
        print(f"\nStarting candidates ({len(candidates)}):")
        for c in candidates:
            print(f"  - {c['node_id']}: {c['utility_qubits']} qubits, +{c['bonus_bell_pairs']} bonus")
        
        # Save session
        if client.api_token:
            with open(SESSION_FILE, "w") as f:
                json.dump({"api_token": client.api_token, "player_id": client.player_id, "name": client.name}, f)
            print(f"Session saved.")
    else:
        print(f"Registration failed: {result.get('error', {}).get('message')}")
        if result.get("error", {}).get("code") == "PLAYER_EXISTS":
            print("Player already exists. Using existing player.")
            client.player_id = PLAYER_ID
            client.name = PLAYER_NAME

# Print status
if client:
    client.print_status()
