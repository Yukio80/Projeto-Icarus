#!/bin/bash
DIR="$(cd "$(dirname "$0")/.." && pwd)"
source <(grep -E '^(RPC_URL|BOT_PRIVATE_KEY|TOKEN_ADDRESS|DAO_ADDRESS|REPUTATION_NFT_ADDRESS|BOT_CYCLE_INTERVAL|GEMINI_API_KEY|DEEPSEEK_API_KEY)=' "$DIR/.env" 2>/dev/null | sed 's/ *= */=/g')
exec python3 -u "$DIR/bot/governance_bot.py" --strategy conservative --cycle 30 >> "$DIR/logs/conservative.log" 2>&1
