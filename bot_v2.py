import os, json, time, logging, shutil, subprocess, shlex
from logging.handlers import RotatingFileHandler
import colorlog

from config import Config
from fixed_responses import FIXED_LOADER, FALLBACK
from utils import TTLCache, run_cmd, send_signal_message
from local_llm_interface import generate_ollama, LLMError

# ---------------- logging setup ----------------
def setup_logging():
    os.makedirs(os.path.dirname(Config.LOG_FILE), exist_ok=True)
    logger = logging.getLogger("borgo")
    logger.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))
    fh = RotatingFileHandler(Config.LOG_FILE, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s [%(levelname)s] %(message)s",
        log_colors={"DEBUG":"cyan","INFO":"green","WARNING":"yellow","ERROR":"red","CRITICAL":"bold_red"}))
    logger.addHandler(ch)
    return logger

log = setup_logging()

# ---------------- helpers ----------------
def envelope(obj): return obj.get("envelope", {}) if isinstance(obj, dict) else {}

def extract_text_and_gid(obj):
    """
    Unterstützt:
      - envelope.dataMessage.message (+ groupInfo.groupId)
      - envelope.syncMessage.sentMessage.message (+ groupInfo.groupId)
    Gibt (text, groupId, kind) zurück, wobei kind 'data' | 'sync' | None ist.
    """
    env = envelope(obj)

    dm = env.get("dataMessage") or {}
    if isinstance(dm, dict):
        txt = dm.get("message") or ""
        gid = (dm.get("groupInfo") or {}).get("groupId")
        if txt or gid:
            return txt or "", gid, "data"

    sm = (env.get("syncMessage") or {}).get("sentMessage") or {}
    if isinstance(sm, dict):
        txt = sm.get("message") or ""
        gid = (sm.get("groupInfo") or {}).get("groupId")
        if txt or gid:
            return txt or "", gid, "sync"

    return "", None, None

def message_id(obj):
    env = envelope(obj)
    return f"{env.get('source','')}:{env.get('timestamp',0)}"

def from_myself(obj):
    env = envelope(obj)
    return env.get("source","") == Config.SIGNAL_NUMBER

def handle_message(text: str) -> str | None:
    if not text:
        return None
    if not text.lower().startswith(Config.BOT_TRIGGER.lower()):
        return None

    payload = text[len(Config.BOT_TRIGGER):].strip()

    # FIXED first
    hit = FIXED_LOADER.lookup(payload)
    if hit:
        return hit

    # LLM or fallback
    if Config.USE_LLM:
        try:
            return generate_ollama(payload, Config.LLM_MODEL, Config.LLM_TIMEOUT, Config.LLM_MAX_TOKENS)
        except LLMError as e:
            log.warning(f"[LLM] {e}")
            return FALLBACK
    return FALLBACK

# ---------------- main loop (streaming receive) ----------------
def receive_loop():
    Config.validate()
    seen = TTLCache(4096, 12*3600)

    log.info("[BOOT] V2 startet …")
    log.info(f"[CFG] number={Config.SIGNAL_NUMBER} trigger={Config.BOT_TRIGGER}")
    log.info(f"[CFG] llm={Config.USE_LLM} model={Config.LLM_MODEL} fixed_file={Config.FIXED_FILE}")
    log.info(f"[CFG] signal-cli path={shutil.which('signal-cli')}")

    # Alive-Ping (informativ)
    send_signal_message(Config.SIGNAL_NUMBER, "✅ V2 online. Sende `!Bot hilfe`.", Config.SIGNAL_GROUP_ID)

    def start_receiver():
        cmd = f"signal-cli -u {Config.SIGNAL_NUMBER} -o json receive"
        log.info(f"[RECV] spawn: {cmd}")
        return subprocess.Popen(
            shlex.split(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # line-buffered
        )

    backoff = 1
    proc = None

    try:
        while True:
            if proc is None or proc.poll() is not None:
                proc = start_receiver()
                backoff = 1

            line = proc.stdout.readline()
            if not line:
                # evtl. beendet / kurz still – stderr prüfen
                errbuf = ""
                if proc and proc.stderr:
                    try:
                        errbuf = proc.stderr.read(1000) if not proc.poll() else (proc.stderr.read() or "")
                    except Exception:
                        errbuf = ""
                if errbuf:
                    log.warning(f"[RECV:STDERR] {errbuf.strip()[:500]}")
                if proc.poll() is not None:
                    rc = proc.returncode
                    log.warning(f"[RECV] receiver exited rc={rc}; restarting in {backoff}s")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    continue
                time.sleep(0.2)
                continue

            s = line.strip()
            if not s:
                continue

            log.debug(f"[RECV:LINE] {s[:500]}")
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                log.debug(f"[RECV] non-json: {s[:120]}")
                continue

            mid = message_id(obj)
            if mid in seen:
                log.debug(f"[DEDUP] skip {mid}")
                continue
            seen.add(mid)

            # immer loggen, auch self
            txt, gid, kind = extract_text_and_gid(obj)
            if from_myself(obj):
                log.info(f"[RX-SELF] kind={kind} groupId={gid} text={txt!r}")
                continue

            log.info(f"[RX] kind={kind} groupId={gid} text={txt!r}")

            # Gruppen-Filter ('*' erlaubt alles)
            if Config.SIGNAL_GROUP_ID != "*" and (not gid or gid != Config.SIGNAL_GROUP_ID):
                continue
            if not txt:
                continue

            log.info(f"[HANDLE] msg={txt!r}")
            reply = handle_message(txt)
            if reply:
                ok = send_signal_message(
                    Config.SIGNAL_NUMBER, reply, Config.SIGNAL_GROUP_ID,
                    retry=Config.SEND_RETRY, wait=Config.SEND_RETRY_WAIT
                )
                log.info("[SEND] ok" if ok else "[SEND] failed")
    except KeyboardInterrupt:
        log.info("Bye.")
    finally:
        try:
            if proc and proc.poll() is None:
                proc.terminate()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        receive_loop()
    except KeyboardInterrupt:
        log.info("Bye.")