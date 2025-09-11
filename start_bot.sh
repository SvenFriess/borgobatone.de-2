#!/usr/bin/env bash
cd "$(dirname "$0")"
mkdir -p logs
if [ -d ".venv" ]; then source .venv/bin/activate; fi
pip3 install -r requirements.txt
nohup python3 bot_v2.py >> logs/console.out 2>&1 &
echo $! > logs/bot.pid
echo "Started, PID $(cat logs/bot.pid)"