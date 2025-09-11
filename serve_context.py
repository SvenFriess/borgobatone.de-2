# serve_context.py
from flask import Flask, request, render_template_string, make_response, send_file, abort, redirect, url_for
import os, time, pathlib, hashlib

app = Flask(__name__)

FILE_PATH   = "/Users/svenfriess/Projekte/borgobatone.de-2/FIXED_RESPONSES.txt"
BACKUP_DIR  = os.path.join(os.path.dirname(FILE_PATH), "_backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

BASIC_USER  = os.getenv("BASIC_USER", "")
BASIC_PASS  = os.getenv("BASIC_PASS", "")

# ---------- Helpers ----------
def is_auth():
    # Wenn keine Credentials gesetzt → Read-Only (nicht authentifiziert)
    if not BASIC_USER or not BASIC_PASS:
        return False
    auth = request.authorization
    return bool(auth and auth.username == BASIC_USER and auth.password == BASIC_PASS)

def require_auth():
    return make_response(("Auth required", 401, {"WWW-Authenticate":"Basic realm=\"Context\""}))

def file_mtime(path):
    try:
        return os.path.getmtime(path)
    except FileNotFoundError:
        return 0.0

def ts():
    return time.strftime("%Y%m%d-%H%M%S")

def backup_file():
    if not os.path.exists(FILE_PATH): return
    stem = pathlib.Path(FILE_PATH).name
    bak  = os.path.join(BACKUP_DIR, f"{stem}.{ts()}.bak")
    with open(FILE_PATH, "rb") as src, open(bak, "wb") as dst:
        dst.write(src.read())

def text_hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]

# ---------- Routes ----------
@app.route("/context/FIXED_RESPONSES.txt", methods=["GET"])
def get_raw():
    if not os.path.exists(FILE_PATH):
        return "Datei nicht gefunden", 404
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    resp = make_response(content, 200)
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    resp.headers["Cache-Control"] = "no-store"
    # ETag für Clients (optional)
    resp.headers["ETag"] = text_hash(content)
    resp.headers["Last-Modified"] = time.ctime(file_mtime(FILE_PATH))
    return resp

@app.route("/download/context/FIXED_RESPONSES.txt")
def download():
    if not os.path.exists(FILE_PATH):
        return "Datei nicht gefunden", 404
    return send_file(FILE_PATH, as_attachment=True, download_name="FIXED_RESPONSES.txt")

EDITOR_HTML = """
<!doctype html><html lang="de"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>FIXED_RESPONSES Editor</title>
<style>
 body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Helvetica,Arial,sans-serif;margin:24px;line-height:1.4}
 .wrap{max-width:1100px;margin:auto}
 .row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
 textarea{width:100%;height:60vh;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:14px;padding:12px;border:1px solid #ddd;border-radius:10px}
 .btn{appearance:none;border:1px solid #0a58ca;background:#0d6efd;color:#fff;padding:8px 14px;border-radius:10px;cursor:pointer}
 .btn:disabled{opacity:.6;cursor:not-allowed}
 .ghost{border:1px solid #ccc;background:#f6f6f6;color:#333}
 .ok{color:#0a7d2a}.warn{color:#b36b00}.err{color:#b00020}
 .meta{color:#666;font-size:13px}
 code{background:#f3f3f3;padding:2px 6px;border-radius:6px}
 .topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
 a{color:#0d6efd;text-decoration:none}
 a:hover{text-decoration:underline}
</style></head><body><div class="wrap">
  <div class="topbar">
    <h1>FIXED_RESPONSES.txt</h1>
    <div class="row">
      <a href="/context/FIXED_RESPONSES.txt" target="_blank">Ansehen</a>
      <a href="/download/context/FIXED_RESPONSES.txt" class="ghost btn">Download</a>
    </div>
  </div>

  {% if read_only %}
    <p class="warn">Read-Only: Es sind keine BASIC_AUTH-Zugangsdaten gesetzt. Setze <code>BASIC_USER</code> und <code>BASIC_PASS</code>, um Bearbeiten zu erlauben.</p>
  {% endif %}

  {% if conflict %}<p class="err"><strong>Konflikt:</strong> Die Datei wurde inzwischen geändert.
    Bitte Inhalt prüfen/mergen und erneut speichern.</p>{% endif %}
  {% if saved %}<p class="ok">Gespeichert. Backup erstellt: {{ backup_name }}</p>{% endif %}

  <form method="post">
    <input type="hidden" name="expected_mtime" value="{{ mtime }}">
    <textarea name="content">{{ content }}</textarea>
    <div class="row" style="margin-top:12px">
      <button class="btn" {% if read_only %}disabled{% endif %}>Speichern</button>
      <span class="meta">Stand: {{ human_mtime }}</span>
    </div>
  </form>
</div></body></html>
"""

@app.route("/", methods=["GET", "POST"])
def editor():
    # Lesen
    if not os.path.exists(FILE_PATH):
        open(FILE_PATH, "a", encoding="utf-8").close()

    curr_mtime = file_mtime(FILE_PATH)
    saved = False
    conflict = False
    backup_name = ""

    if request.method == "POST":
        # Auth prüfen; ohne Auth → nur GET erlaubt
        if not is_auth():
            return require_auth()

        expected = float(request.form.get("expected_mtime", "0") or "0")
        content = request.form.get("content", "")

        # Konflikt, wenn die Datei seit dem Laden geändert wurde
        if abs(curr_mtime - expected) > 1e-6:
            conflict = True
        else:
            # Backup + Schreiben
            backup_file()
            backup_name = f"{pathlib.Path(FILE_PATH).name}.{ts()}.bak"
            with open(FILE_PATH, "w", encoding="utf-8") as f:
                f.write(content)
            saved = True
            curr_mtime = file_mtime(FILE_PATH)

    with open(FILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    return render_template_string(
        EDITOR_HTML,
        content=content,
        mtime=curr_mtime,
        human_mtime=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(curr_mtime)),
        saved=saved,
        conflict=conflict,
        backup_name=backup_name,
        read_only=not (BASIC_USER and BASIC_PASS),
    )

# Health
@app.route("/healthz")
def healthz():
    return "ok", 200

if __name__ == "__main__":
    # Tipp: App nur im LAN oder hinter Tunnel freigeben
    app.run(host="0.0.0.0", port=8060, debug=True)