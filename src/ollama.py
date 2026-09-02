"""Minimal ollama client. Native /api/chat, because /v1 hides num_ctx, top_k and seed."""

import json
import time
import urllib.error
import urllib.request

from src.utils.config import REQUEST_TIMEOUT
from src.utils.constants import OLLAMA_HOST


class OllamaError(RuntimeError):
    pass


def _post(path: str, payload: dict, timeout: int = REQUEST_TIMEOUT) -> dict:
    req = urllib.request.Request(
        f"{OLLAMA_HOST}{path}", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise OllamaError(f"{path} -> HTTP {e.code}: {e.read().decode()[:400]}") from e
    except urllib.error.URLError as e:
        raise OllamaError(f"cannot reach ollama at {OLLAMA_HOST} -- is it running? ({e.reason})") from e


def chat(model_tag: str, prompt: str, options: dict) -> dict:
    """One completion. Returns the text plus everything the trace header needs."""
    started = time.monotonic()
    body = _post("/api/chat", {
        "model": model_tag,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": options,
    })
    return {
        "text": body["message"]["content"],
        "done_reason": body.get("done_reason"),
        "prompt_tokens": body.get("prompt_eval_count"),
        "output_tokens": body.get("eval_count"),
        "wall_ms": round((time.monotonic() - started) * 1000),
    }


def show(model_tag: str) -> dict:
    """Model metadata: the default parameter dump R5 asks for, plus the digest."""
    return _post("/api/show", {"model": model_tag})


def installed() -> dict[str, str]:
    """tag -> digest for everything pulled locally."""
    with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=30) as resp:
        body = json.loads(resp.read())
    return {m["name"]: m.get("digest", "") for m in body.get("models", [])}
