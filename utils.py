import time, subprocess, shlex, logging
from collections import OrderedDict
log = logging.getLogger("borgo")

class TTLCache:
    def __init__(self, maxsize=1024, ttl=3600):
        self.maxsize, self.ttl = maxsize, ttl
        self._data = OrderedDict()
    def add(self, key): self._data[key] = time.time(); self._data.move_to_end(key); self._evict()
    def __contains__(self, key):
        ts = self._data.get(key); now = time.time()
        if ts and now - ts <= self.ttl: return True
        if key in self._data: del self._data[key]; return False
    def _evict(self): 
        while len(self._data) > self.maxsize: self._data.popitem(last=False)

def run_cmd(cmd, input_text=None, timeout=None):
    proc = subprocess.Popen(shlex.split(cmd),
        stdin=subprocess.PIPE if input_text else None,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = proc.communicate(input=input_text, timeout=timeout)
        return proc.returncode, out, err
    except subprocess.TimeoutExpired:
        proc.kill(); return 124, "", "TIMEOUT"

def send_signal_message(number, text, group_id=None, retry=3, wait=1.0):
    if group_id:
        cmd = f"signal-cli -u {number} send -g {group_id} -m {shlex.quote(text)}"
    else:
        cmd = f"signal-cli -u {number} send {number} -m {shlex.quote(text)}"
    for _ in range(retry):
        rc, _, err = run_cmd(cmd)
        if rc == 0: return True
        log.warning(f"[SEND] rc={rc} err={err.strip()}")
        time.sleep(wait)
    return False