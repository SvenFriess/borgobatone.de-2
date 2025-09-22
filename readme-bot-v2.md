Hier eine fertige README.md für dein neues bot_v2.py – mit Setup, Funktionsübersicht, .env-Erklärung und Betriebsanleitung:

# 🤖 Borgo-Batone-Bot v2

Ein **lokal betriebener Signal-Chatbot** für Borgo Batone & ähnliche Projekte.  
Ziele: **DSGVO-konform, ohne Cloud, modular, stabil**.  
Implementiert mit **Signal-CLI**, **lokalem LLM (Ollama)**, **persistenter Dedupe-Datenbank** und **konfigurierbarem Retry-Mechanismus**.

---

## 🚀 Features

- 📚 **Fixed Responses**  
  Antworten aus `FIXED_RESPONSES.py` (z. B. `!bot wlan`).

- 🧠 **LLM-Fallback (Ollama)**  
  Wenn keine feste Antwort gefunden wird → lokale KI-Antwort (`mistral:instruct` o. ä.).

- 🔁 **Send-Retry mit Backoff**  
  Signal-Nachrichten werden bei Fehlern mehrfach gesendet (konfigurierbar).

- 🧽 **Dedupe (SQLite)**  
  Duplikate werden gefiltert, **persistente Speicherung über Neustarts**.

- 📑 **Konfigurierbar via .env**  
  Signal-Nummer, Gruppen-ID, Timeouts, Retries, Pfade → alles über Umgebungsvariablen.

- 📝 **Logging**  
  - Rotating Logfile (`bot.log`)  
  - Optional bunt (colorlog)  
  - Logs drehen automatisch, um Dateigröße klein zu halten

---

## 📦 Voraussetzungen

- macOS oder Linux (getestet auf Mac Mini M4 mit Python 3.13)  
- `signal-cli` (installiert & mit der Bot-Nummer registriert)  
- Python 3.10+  
- Python-Pakete:

pip install python-dotenv colorlog

---

## ⚙️ Setup

1. **Repository vorbereiten**
 ```bash
 cd ~/Projekte/borgobatone.de-2
 cp bot_v2.py .

	2.	.env Datei anlegen

NUMBER=+4915755901211
GROUP_ID=<DEINE-GRUPPEN-UUID>
JSON_MODE=true
RECEIVE_TIMEOUT=120

LOG_PATH=bot.log
LOG_MAX_BYTES=524288
LOG_BACKUPS=3

SEND_RETRY=3
SEND_RETRY_WAIT=0.8

SQLITE_PATH=bot_dedupe.sqlite3
DEDUPE_TTL_DAYS=5

LLM_MODEL=mistral:instruct

👉 GROUP_ID ermitteln mit:

signal-cli -u +4915755901211 -o json listGroups | jq -r '.[] | [.name,.id] | @tsv'


	3.	Fixed Responses hinterlegen
Datei FIXED_RESPONSES.py:

FIXED_RESPONSES = {
    "status": "✅ Bot läuft. Sende `!bot hilfe`.",
    "hilfe": "ℹ️ Sende `!bot <Thema>` — Beispiele: wlan, notfall, einkauf.",
    "wlan": "📶 WLAN-Name: BorgoGuest / Passwort: borgo2025",
    "canary": "M4_CANARY_2025-09-21",
}



⸻

▶️ Starten

Direkt

PYTHONPATH=. nohup python3 -u bot_v2.py >> bot.log 2>&1 &

Status prüfen

pgrep -af 'python.*bot_v2'
tail -n 80 bot.log

Test in Signal-Gruppe

!bot status
!bot hilfe
!bot wlan
!bot canary


⸻

🛠 Verwaltung

Restart-Skript (optional restart_bot.sh)

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
FILE="bot_v2.py"
pkill -f "python.*$FILE" 2>/dev/null || true
PYTHONPATH=. nohup python3 -u "$FILE" >> bot.log 2>&1 &
sleep 1
pgrep -af "python.*$FILE"

Dedupe-Datenbank aufräumen

sqlite3 bot_dedupe.sqlite3 "DELETE FROM messages;"


⸻

🔍 Architektur
	1.	Receiver-Loop (Signal-CLI → JSON oder Plaintext)
	2.	Dedupe (SQLite: prüft, ob Message bereits verarbeitet wurde)
	3.	Routing
	•	Fixed Response
	•	LLM (lokal via Ollama)
	•	Fallback
	4.	Senden (Signal-CLI mit Retries)
	5.	Logging (Rotating File, optional bunt)

⸻

📌 Tipps
	•	Prüfe immer bot.log, wenn keine Antwort kommt.
	•	Stelle sicher, dass GROUP_ID in .env gesetzt ist.
	•	Bei Modellwechsel LLM_MODEL=phi:latest o. ä. setzen.
	•	Bot läuft 100% lokal → keine Cloud, kein Tracking.

⸻

🧪 Testfragen
	•	!bot status → sollte „✅ Bot läuft…“ zurückgeben
	•	!bot wlan → fester FIXED-Response
	•	!bot canary → zeigt eindeutige M4-Kennung

⸻
