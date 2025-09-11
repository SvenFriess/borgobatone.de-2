import subprocess, shlex
from threading import Timer

class LLMError(Exception): pass

def generate_ollama(prompt: str, model="mistral:instruct", timeout=25, max_tokens=300) -> str:
    sys_prompt = (
        "You are Borgo-Batone-Bot, a concise, helpful Tuscany assistant. "
        "Answer briefly (max ~6 sentences)."
    )
    composed = f"{sys_prompt}\n\nUser: {prompt}\nAssistant:"

    cmd = f"ollama run {shlex.quote(model)}"
    try:
        proc = subprocess.Popen(
            shlex.split(cmd), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        timer = Timer(timeout, proc.kill)
        try:
            timer.start()
            out, err = proc.communicate(composed)
        finally:
            timer.cancel()

        if proc.returncode != 0:
            raise LLMError(err.strip())
        return out.strip() or "…"
    except Exception as e:
        raise LLMError(str(e))