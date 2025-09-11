#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Borgo-Batone Kontext-Editor (Flask)
-----------------------------------

Funktionen:
- Passwortgeschütztes Webformular (HTTP Basic Auth) zum Bearbeiten eines Kontext-Files
- "Speichern"-Button schreibt Änderungen atomar auf die Platte (mit Locking) 
- "Bot Neustart"-Button führt ein konfigurierbares Kommando aus (z. B. systemd service restart)
- Ampel-Status (rot/gelb/grün):
    * grün  = alles okay
    * gelb  = Neustart läuft
    * rot   = letzter Neustart fehlgeschlagen
- Doppel-Klick-Schutz: Neustart ist während laufendem Vorgang deaktiviert
- Leichte CSRF-Absicherung über Session-Token

Konfiguration über Umgebungsvariablen:
- CONTEXT_FILE   (Pfad zur zu bearbeitenden Datei) – Pflicht
- HOST           (Default: 127.0.0.1)
- PORT           (Default: 8080)
- USERNAME       (Default: admin)
- PASSWORD       (Default: bitte-setzen)
- BOT_RESTART_CMD (Default: "systemctl --user restart borgobot.service")
- RESTART_TIMEOUT_SEC (Default: 30) – Debounce-Zeit, während der Button gesperrt bleibt

Start (lokal):
    export CONTEXT_FILE=/Users/svenfriess/Projekte/borgobatone.de/borgobatone.txt
    export USERNAME=admin
    export PASSWORD=supersecret
    export BOT_RESTART_CMD="systemctl --user restart borgobot.service"
    python3 app.py

Hinweis: Für den systemd-Command muss der Prozess genügend Rechte haben. Alternativ kann 
BOT_RESTART_CMD auf ein eigenes Skript zeigen, das den Bot sauber neu startet.
"""

import base64
import fcntl
import json
import os
import secrets
import shlex
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple

from flask import (
    Flask, request, Response, abort, redirect, url_for,
    render_template_string, session, jsonify, flash
)

# ----------------------
# Konfiguration
# ----------------------
CONTEXT_FILE = os.environ.get("CONTEXT_FILE")  # Pflicht
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8080"))
USERNAME = os.environ.get("USERNAME", "admin")
PASSWORD = os.environ.get("PASSWORD", "bitte-setzen")
BOT_RESTART_CMD = os.environ.get("BOT_RESTART_CMD", "systemctl --user restart borgobot.service")
RESTART_TIMEOUT_SEC = int(os.environ.get("RESTART_TIMEOUT_SEC", "30"))

if not CONTEXT_FILE:
    raise SystemExit("ERROR: CONTEXT_FILE ist nicht gesetzt. Bitte Umgebungsvariable setzen.")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", secrets.token_hex(16))

# Restart-Status (in-memory)
_restart_lock = threading.Lock()
_restart_in_progress = False
_last_restart_ok = True
_last_restart_ts = 0.0
_last_restart_msg = ""

# ----------------------
# Hilfsfunktionen
# ----------------------

def _basic_auth_ok(auth_header: str) -> bool:
    if not auth_header or not auth_header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
        user, pw = decoded.split(":", 1)
    except Exception:
        return False
    return (user == USERNAME) and (pw == PASSWORD)


def require_auth() -> None:
    auth = request.headers.get("Authorization")
    if not _basic_auth_ok(auth):
        return Response(
            "Authentifizierung erforderlich", 401,
            {"WWW-Authenticate": "Basic realm=\"Borgo-Batone Editor\""}
        )


def read_file_atomic(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        # Shared-Lock fürs Lesen (optional auf Linux)
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        except Exception:
            pass
        data = f.read()
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
    return data


def write_file_atomic(path: Path, content: str) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        except Exception:
            pass
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
    os.replace(tmp_path, path)


def detect_format_preview(text: str) -> Tuple[str, str]:
    """Versucht, das Format zu erkennen (JSON/YAML/Plain) und gibt eine kurze Info zurück."""
    fmt = "plain"
    info = "Plaintext"
    try:
        json.loads(text)
        fmt = "json"
        info = "JSON erkannt"
        return fmt, info
    except Exception:
        pass
    # YAML nur heuristisch (kein yaml import, um Abh. klein zu halten)
    if any(line.strip().endswith(":") or ":" in line for line in text.splitlines()):
        info = "Evtl. YAML/Key-Value"
    return fmt, info


def generate_csrf() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def verify_csrf(token: str) -> bool:
    return token and session.get("csrf_token") and token == session.get("csrf_token")


# ----------------------
# Templates (inline)
# ----------------------
BASE_HTML = r"""
<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Borgo-Batone Kontext-Editor</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; }
    header { display:flex; align-items:center; gap:12px; margin-bottom: 16px; }
    .ampel { width:14px; height:14px; border-radius:50%; display:inline-block; margin-right:8px; border:1px solid #999; }
    .ampel.red { background:#e03131; }
    .ampel.yellow { background:#f08c00; }
    .ampel.green { background:#2f9e44; }
    .toolbar { display:flex; gap:12px; align-items:center; flex-wrap: wrap; margin: 12px 0; }
    textarea { width:100%; height: 55vh; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 14px; padding:10px; border:1px solid #ddd; border-radius:10px; }
    button { padding:10px 14px; border:1px solid #ccc; border-radius:10px; background:#fafafa; cursor:pointer; }
    button[disabled] { opacity: 0.6; cursor:not-allowed; }
    .msg { padding:8px 12px; border:1px solid #ddd; border-radius:10px; background:#f6f8fa; margin:10px 0; }
    .info { color:#666; font-size: 13px; }
    .right { margin-left:auto; }
    .badge { font-size: 12px; padding:3px 8px; border-radius: 9999px; background:#eef; color:#225; border:1px solid #ccd; }
    footer { margin-top: 16px; color:#777; font-size: 12px; }
  </style>
</head>
<body>
  <header>
    <div id="ampel" class="ampel green" title="Status"></div>
    <h2 style="margin:0">Borgo-Batone Kontext-Editor</h2>
    <span id="fmt" class="badge">{{ fmt_info }}</span>
    <span class="right info">Datei: <code>{{ ctx_path }}</code></span>
  </header>

  {% with messages = get_flashed_messages() %}
    {% if messages %}
      {% for m in messages %}<div class="msg">{{ m }}</div>{% endfor %}
    {% endif %}
  {% endwith %}

  <form method="post" action="{{ url_for('save') }}">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}" />
    <textarea name="content" spellcheck="false">{{ content }}</textarea>
    <div class="toolbar">
      <button type="submit">💾 Speichern</button>
      <button id="restartBtn" type="button" onclick="triggerRestart()">🔁 Bot neu starten</button>
      <span id="statusText" class="info">Bereit.</span>
    </div>
  </form>

  <footer>
    <div class="info">Letztes Laden: {{ now }} • Neustart-Timeout: {{ timeout }}s</div>
  </footer>

<script>
async function pollStatus(){
  try{
    const r = await fetch("{{ url_for('status') }}", {cache:'no-store'});
    if(!r.ok) return;
    const s = await r.json();
    const ampel = document.getElementById('ampel');
    const btn = document.getElementById('restartBtn');
    const txt = document.getElementById('statusText');

    ampel.classList.remove('red','yellow','green');
    if(s.in_progress){
      ampel.classList.add('yellow');
      btn.disabled = true;
      txt.textContent = 'Neustart läuft…';
    } else if(!s.last_ok) {
      ampel.classList.add('red');
      btn.disabled = false;
      txt.textContent = 'Letzter Neustart fehlgeschlagen.';
    } else {
      ampel.classList.add('green');
      // Debounce-Window beachten
      if(s.cooldown_remaining > 0){
        btn.disabled = true;
        txt.textContent = 'Wartezeit: ' + s.cooldown_remaining + 's';
      } else {
        btn.disabled = false;
        txt.textContent = 'Bereit.';
      }
    }
  }catch(e){
    // noop
  }
}

async function triggerRestart(){
  const btn = document.getElementById('restartBtn');
  btn.disabled = true;
  const txt = document.getElementById('statusText');
  txt.textContent = 'Neustart wird gestartet…';
  try{
    const r = await fetch("{{ url_for('restart') }}", {method:'POST', headers: {'X-CSRF-Token': '{{ csrf_token }}'}});
    if(r.ok){
      const j = await r.json();
      txt.textContent = j.message || 'Neustart ausgelöst.';
    } else {
      txt.textContent = 'Fehler beim Auslösen des Neustarts.';
    }
  }catch(e){
    txt.textContent = 'Netzwerkfehler beim Neustart.';
  }
}

setInterval(pollStatus, 1000);
window.addEventListener('load', pollStatus);
</script>
</body>
</html>
"""

# ----------------------
# Routes
# ----------------------
@app.before_request
def _auth_guard():
    ra = require_auth()
    if isinstance(ra, Response):
        return ra


@app.get("/")
def index():
    path = Path(CONTEXT_FILE)
    if not path.exists():
        abort(404, f"Kontextdatei nicht gefunden: {path}")
    text = read_file_atomic(path)
    fmt, fmt_info = detect_format_preview(text)
    csrf_token = generate_csrf()
    return render_template_string(
        BASE_HTML,
        content=text,
        ctx_path=str(path),
        fmt=fmt,
        fmt_info=fmt_info,
        csrf_token=csrf_token,
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        timeout=RESTART_TIMEOUT_SEC,
    )


@app.post("/save")
def save():
    token = request.form.get("csrf_token", "")
    if not verify_csrf(token):
        abort(400, "CSRF-Token ungültig")
    new_content = request.form.get("content", "")
    path = Path(CONTEXT_FILE)
    try:
        write_file_atomic(path, new_content)
        flash("Änderungen gespeichert.")
    except Exception as e:
        flash(f"Speichern fehlgeschlagen: {e}")
    return redirect(url_for("index"))


@app.get("/status")
def status():
    # Cooldown-Berechnung
    now = time.time()
    cooldown_remaining = 0
    if _last_restart_ts > 0:
        elapsed = now - _last_restart_ts
        if elapsed < RESTART_TIMEOUT_SEC:
            cooldown_remaining = int(RESTART_TIMEOUT_SEC - elapsed)

    return jsonify({
        "in_progress": _restart_in_progress,
        "last_ok": _last_restart_ok,
        "last_ts": int(_last_restart_ts),
        "last_msg": _last_restart_msg,
        "cooldown_remaining": cooldown_remaining,
    })


@app.post("/restart")
def restart():
    # CSRF auch für Fetch-POST via Header
    token = request.headers.get("X-CSRF-Token", "")
    if not verify_csrf(token):
        abort(400, "CSRF-Token ungültig")

    global _restart_in_progress, _last_restart_ok, _last_restart_ts, _last_restart_msg

    # Debounce: wenn noch in Progress oder Cooldown, ablehnen
    now = time.time()
    if _restart_in_progress:
        return jsonify({"ok": False, "message": "Neustart läuft bereits."}), 429
    if _last_restart_ts > 0 and (now - _last_restart_ts) < RESTART_TIMEOUT_SEC:
        remaining = int(RESTART_TIMEOUT_SEC - (now - _last_restart_ts))
        return jsonify({"ok": False, "message": f"Bitte {remaining}s warten."}), 429

    def _runner():
        global _restart_in_progress, _last_restart_ok, _last_restart_ts, _last_restart_msg
        with _restart_lock:
            _restart_in_progress = True
        try:
            cmd = shlex.split(BOT_RESTART_CMD)
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            _last_restart_ok = (proc.returncode == 0)
            _last_restart_msg = proc.stdout.strip() or proc.stderr.strip()
        except Exception as e:
            _last_restart_ok = False
            _last_restart_msg = f"Fehler: {e}"
        finally:
            _last_restart_ts = time.time()
            with _restart_lock:
                _restart_in_progress = False

    threading.Thread(target=_runner, daemon=True).start()
    return jsonify({"ok": True, "message": "Neustart ausgelöst."})


# ----------------------
# Entry
# ----------------------
if __name__ == "__main__":
    print(f"* Kontextdatei: {CONTEXT_FILE}")
    print(f"* Host: {HOST}  Port: {PORT}")
    print(f"* Benutzer: {USERNAME}")
    print(f"* Restart: {BOT_RESTART_CMD}")
    app.run(host=HOST, port=PORT)
