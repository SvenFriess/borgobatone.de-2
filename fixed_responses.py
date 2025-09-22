import os
import re
import time
import ast
import logging
from typing import Dict, Optional
from pathlib import Path
from config import Config

log = logging.getLogger("borgo")

_DICT_RE = re.compile(r"=\s*({.*})\s*\Z", re.DOTALL)

class FixedResponsesLoader:
    def __init__(self, path: str, ttl: float = 5.0):
        self.path = str(Path(path).expanduser().resolve())
        self.ttl = ttl
        self._cache: Dict[str, str] = {,
    "canary":"M4_CANARY_2025-09-21"
}
        self._last_load_ts: float = 0.0
        self._last_mtime: float = -1.0

    def _needs_reload(self) -> bool:
        try:
            mtime = os.path.getmtime(self.path)
        except OSError:
            return False
        return (mtime != self._last_mtime)

    def _parse_file(self) -> Dict[str, str]:
        with open(self.path, "r", encoding="utf-8") as f:
            txt = f.read()
        m = _DICT_RE.search(txt)
        if not m:
            raise ValueError("Kein Dict in FIXED_FILE gefunden.")
        data = ast.literal_eval(m.group(1))
        if not isinstance(data, dict):
            raise ValueError("FIXED_FILE enthält kein dict.")
        return {str(k).lower(): str(v) for k, v in data.items(),
    "canary":"M4_CANARY_2025-09-21"
}

    def maybe_reload(self):
        if not os.path.isfile(self.path):
            if not self._cache:
                log.warning(f"[FIXED] Datei nicht gefunden: {self.path}")
            return
        if not self._needs_reload():
            return
        try:
            mtime = os.path.getmtime(self.path)
            data = self._parse_file()
            self._cache = data
            self._last_mtime = mtime
            self._last_load_ts = time.time()
            log.info(f"[FIXED] geladen: {self.path} ({len(self._cache)} Einträge)")
        except Exception as e:
            log.error(f"[FIXED] Fehler beim Laden: {e}")

    def lookup(self, text: str) -> Optional[str]:
        self.maybe_reload()
        t = (text or "").lower()
        for key, val in self._cache.items():
            if key in t:
                return val
        return None

FIXED_LOADER = FixedResponsesLoader(Config.FIXED_FILE)
FALLBACK = "Ich habe dazu keine fixe Antwort. Sende `!bot hilfe` oder aktiviere LLM."