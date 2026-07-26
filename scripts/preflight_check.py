"""Preflight check (T10.1)."""

from scripts.check_ollama import check_model_available
from utils.ollama_manager import ensure_ollama_running


def run() -> tuple[bool, list[str]]:
    """Run environment preflight checks and return (success, failure_reasons)."""
    failures: list[str] = []

    if not ensure_ollama_running():
        failures.append(
            "Ollama running check: Ollama could not be reached or started. "
            "Install Ollama from https://ollama.com and ensure it is on your PATH."
        )

    ok, msg = check_model_available()
    if not ok:
        failures.append(f"Ollama model check: {msg}")

    return (len(failures) == 0, failures)


if __name__ == "__main__":
    ok, failures = run()
    if ok:
        print("[PASS] Preflight checks passed.")
    else:
        print("[FAIL] Preflight checks failed:")
        for reason in failures:
            print(f"  - {reason}")
