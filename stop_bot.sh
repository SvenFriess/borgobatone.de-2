#!/usr/bin/env bash
cd "$(dirname "$0")"
if [ -f logs/bot.pid ]; then kill $(cat logs/bot.pid) 2>/dev/null; rm -f logs/bot.pid; fi