import json
import socket
import sys
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

OLLAMA_API = "http://127.0.0.1:11434"

def check_ollama_running() -> tuple[bool, str]:
    try:
        sock = socket.create_connection(("127.0.0.1", 11434), timeout=5)
        sock.close()
        return True, "Ollama service is running"
    except OSError as e:
        return False, f"Ollama service is not responding: {e}"

def check_model_available() -> tuple[bool, str]:
    model = config.OLLAMA_MODEL
    try:
        req = urllib.request.Request(f"{OLLAMA_API}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        names = [m.get("name", "") for m in data.get("models", [])]
        if any(n == model or n.startswith(model.split(":")[0]) for n in names):
            return True, f"Model '{model}' found in `ollama list`"
        return False, f"Model '{model}' not found in `ollama list`"
    except urllib.error.HTTPError as e:
        return False, f"`ollama list` failed: HTTP {e.code} {e.reason}"
    except (urllib.error.URLError, OSError) as e:
        return False, f"`ollama list` failed: {e}"
    except (json.JSONDecodeError, KeyError) as e:
        return False, f"`ollama list` returned unexpected data: {e}"

def main() -> int:
    results = [
        ("Ollama running", check_ollama_running),
        ("Model available", check_model_available),
    ]
    exit_code = 0
    for label, fn in results:
        ok, msg = fn()
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {label}: {msg}", flush=True)
        if not ok:
            exit_code = 1
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
