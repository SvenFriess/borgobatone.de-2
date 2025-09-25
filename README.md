# 🤖 Borgo-Bot TEST

Dies ist die Restanleitung für den **Borgo-Bot TEST**.  
Der Bot basiert auf `bot_v2.py` und reagiert ausschließlich auf vordefinierte Antworten aus der Datei `FIXED_RESPONSES.txt`.  
Es gibt **keinen LLM-Fallback** – falls keine Antwort vorhanden ist, gibt der Bot „Antwort nicht verfügbar“ zurück.

---

## 🚀 Features
- Antworten ausschließlich aus `FIXED_RESPONSES.txt`
- Unterstützung für **kurze** und **lange** Antworten (`--lang` Flag)
- Live-Reload der Kontextdatei per `!bot reload`
- Nutzung in Signal-Gruppe **Borgo-Bot TEST**
- Start/Stop über Signal-CLI + Python

---

## ⚙️ Installation & Start

```bash
cd ~/Projekte/borgobatone.de-2

NUMBER="+4915755901211" GROUP_ID="21oiqcpO37/ScyKFhmctf/45MQ5QYdN2h/VQp9WMKCM=" TIMEOUT_SEC="5" nohup python3 bot_v2.py &
```

Logs prüfen:
```bash
tail -f bot.log
```

---

## 📂 FIXED_RESPONSES.txt
Format-Beispiel:
```
frage: status
antwort_kurz: Bot läuft ✅
antwort_lang: Der Borgo-Bot läuft und empfängt Nachrichten wie vorgesehen. Alles stabil.
```

- `antwort_kurz` → kurze, prägnante Antwort  
- `antwort_lang` → ausführlichere Erklärung  

Aufruf:
- `!bot status` → Kurzantwort  
- `!bot status --lang` → Langantwort  

---

## 🔄 Reload des Kontext-Files
Ohne Neustart:
```bash
!bot reload
```
Antwort: `Kontextdatei neu geladen ✅`

---

## 🆔 Gruppen-ID ermitteln
```bash
signal-cli -u +4915755901211 listGroups
```
Die ID der Gruppe **Borgo-Bot TEST** kopieren und als `GROUP_ID` in der Startumgebung setzen.

---

## 🧪 Testanleitung
1. In Gruppe **Borgo-Bot TEST** schreiben:
   - `!bot status` → „Bot läuft ✅“  
   - `!bot status --lang` → längere Statusmeldung  
   - `!bot reload` → „Kontextdatei neu geladen ✅“  

2. Nicht vorhandene Fragen → „Antwort nicht verfügbar“

---

## 📌 Nächste Schritte
- `FIXED_RESPONSES.txt` inkrementell erweitern  
- Kurz/Lang strikt trennen  
- Reload nutzen  
- Nach stabilen Tests → Deployment in echte Borgo-Gruppe

---

© 2025 Borgo-Bot / Strategix-AI
