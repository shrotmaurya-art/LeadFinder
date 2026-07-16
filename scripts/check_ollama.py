import subprocess
import sys
from pathlib import Path

import urllib.request
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

def check_ollama_running() -> tuple[bool, str]:
    try:
        req = urllib.request.Request("http://localhost:11434", method="GET")
        urllib.request.urlopen(req, timeout=5)
        return True, "Ollama service is running"
    except urllib.error.URLError as e:
        return False, f"Ollama service is not responding: {e.reason}"
    except Exception as e:
        return False, f"Ollama service check failed: {e}"

def check_model_available() -> tuple[bool, str]:
    model = config.OLLAMA_MODEL
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            lines = [l for l in result.stderr.strip().splitlines() if "level=" not in l]
            reason = lines[-1] if lines else result.stderr.strip()
            return False, f"`ollama list` exited with code {result.returncode}: {reason}"
        if model in result.stdout:
            return True, f"Model '{model}' found in `ollama list`"
        return False, f"Model '{model}' not found in `ollama list`"
    except FileNotFoundError:
        return False, "`ollama` executable not found on PATH"
    except subprocess.TimeoutExpired:
        return False, "`ollama list` timed out after 30 seconds"
    except Exception as e:
        return False, f"`ollama list` failed: {e}"

def main() -> int:
    results = [
        ("Ollama running", check_ollama_running),
        ("Model available", check_model_available),
    ]
    exit_code = 0
    for label, fn in results:
        ok, msg = fn()
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {label}: {msg}")
        if not ok:
            exit_code = 1
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
