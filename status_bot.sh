#!/usr/bin/env bash
cd "$(dirname "$0")"
echo "=== Bot Status ==="
if [ -f logs/bot.pid ]; then
  PID=$(cat logs/bot.pid)
  if kill -0 "$PID" 2>/dev/null; then echo "✅ Bot läuft (PID $PID)"; else echo "❌ Bot nicht aktiv"; fi
else
  echo "❌ Kein PID"
fi
tail -n 40 logs/borgo-bot.log || true