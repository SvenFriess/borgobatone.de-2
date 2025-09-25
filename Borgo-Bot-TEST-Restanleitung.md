# 📘 Restanleitung Borgo-Bot TEST (Stand 25.09.2025)

## 1. Zielsetzung
- Borgo-Bot reagiert **nur** in der Signal-Gruppe **Borgo-Bot TEST**.  
- Prefix ist immer: `!bot`  
- Antworten kommen **ausschließlich** aus der Datei `FIXED_RESPONSES.txt`.  
- Gibt es keinen Eintrag → Antwort: **„Antwort nicht verfügbar“**  
- Kein LLM-Fallback mehr.

## 2. Kontextdatei FIXED_RESPONSES.txt
- Format: einfache Textdatei mit Frage/Antwort-Blöcken.  
- Beispiel:
  ```
  frage: status
  antwort_kurz: Bot läuft ✅
  antwort_lang: Der Borgo-Bot läuft und empfängt Nachrichten wie vorgesehen. Alles stabil.
  ```

- **Zwei Antwortarten**:
  - `antwort_kurz` → kurze, prägnante Antwort.  
  - `antwort_lang` → ausführlichere Erklärung.  

- Im Bot kann gesteuert werden, ob **kurz** oder **lang** ausgegeben wird:
  - `!bot status` → Kurzantwort  
  - `!bot status --lang` → Langantwort

## 3. Reload des Kontext-Files
- Änderung von `FIXED_RESPONSES.txt` → **kein Neustart nötig**.  
- Befehl:  
  ```
  !bot reload
  ```
- Antwort: `Kontextdatei neu geladen ✅`  
- Bot liest Datei sofort neu ein.

## 4. Gruppen-ID auslesen
1. Signal-CLI Befehl:  
   ```bash
   signal-cli -u +4915755901211 listGroups
   ```
2. Ausgabe enthält alle Gruppen-Namen und ihre IDs.  
3. Kopiere die ID der Gruppe **Borgo-Bot TEST** (z. B. `21oiqcpO37/...`), trage sie in die Bot-Umgebung ein:  
   ```bash
   export GROUP_ID="21oiqcpO37/ScyKFhmctf/45MQ5QYdN2h/VQp9WMKCM="
   ```

## 5. Start des Bots
```bash
cd ~/Projekte/borgobatone.de-2
NUMBER="+4915755901211" GROUP_ID="21oiqcpO37/ScyKFhmctf/45MQ5QYdN2h/VQp9WMKCM=" TIMEOUT_SEC="5" nohup python3 bot_v2.py &
```

- Logs prüfen:
  ```bash
  tail -f bot.log
  ```

## 6. Testanleitung
1. In Gruppe **Borgo-Bot TEST**:
   - `!bot status` → Erwartet: „Bot läuft ✅“  
   - `!bot status --lang` → Erwartet: längere Statusmeldung  
   - `!bot reload` → Erwartet: „Kontextdatei neu geladen ✅“  

2. Wenn Frage nicht in `FIXED_RESPONSES.txt` → Antwort: „Antwort nicht verfügbar“

## 7. Nächste Schritte
- `FIXED_RESPONSES.txt` weiter pflegen → inkrementell Inhalte ergänzen.  
- Klare Trennung **kurz/lang** einhalten.  
- Reload regelmäßig nutzen.  
- Erst nach stabilen Tests → Deployment in echte Borgo-Gruppe.
