"""Thin wrapper around Ollama for outbound message generation.

Exposes a single `generate` function and an `OllamaUnavailableError` that
callers can catch to avoid raw connection errors reaching the UI.
"""

import re

import httpx
import ollama

import config
from utils.logger import get_logger

log = get_logger(__name__)


class OllamaUnavailableError(Exception):
    """Raised when Ollama cannot be reached after retries."""


_CODE_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*\n|\n```\s*$")


def _strip_code_fence(text: str) -> str:
    """Remove a wrapping markdown code fence if present."""
    return _CODE_FENCE_RE.sub("", text)


def generate(system_prompt: str, user_prompt: str, max_tokens: int = 250) -> str:
    """Generate a response from the configured Ollama model.

    Parameters
    ----------
    system_prompt : str
        System-level instruction sent as a separate ``system`` message.
    user_prompt : str
        User-level content sent as a separate ``user`` message.
    max_tokens : int
        Maximum tokens to generate (passed as ``num_predict``).

    Returns
    -------
    str
        The model's response with leading/trailing whitespace stripped
        and any wrapping code fence removed.

    Raises
    ------
    OllamaUnavailableError
        If the model cannot be reached after 2 attempts.
    """
    client = ollama.Client(timeout=15)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    options = {"num_predict": max_tokens}

    last_exc: Exception | None = None
    for attempt in range(1, 3):
        try:
            response = client.chat(
                model=config.OLLAMA_MODEL,
                messages=messages,
                options=options,
            )
            raw = response["message"]["content"]
            return _strip_code_fence(raw).strip()
        except (ollama.ResponseError, ollama.RequestError,
                httpx.ConnectError, httpx.TimeoutException,
                ConnectionError) as exc:
            last_exc = exc
            log.warning("Ollama attempt %d/2 failed: %s", attempt, exc)

    raise OllamaUnavailableError(
        "Ollama appears to be unreachable — run ollama list to confirm "
        "the service is running and the model is pulled."
    ) from last_exc
