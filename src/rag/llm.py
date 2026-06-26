import logging
import os
import time
from typing import Literal

import httpx
from llama_index.core.llms import LLM
from llama_index.llms.mistralai import MistralAI

LlmProvider = Literal["mistral", "ollama"]

MISTRAL_MODEL = "mistral-large-latest"
MISTRAL_MAX_RETRIES = 3

SYNTHESIS_PROMPT = """
You are a EU regulatory compliance expert. Using ONLY the provided regulation excerpts,
answer the query. Be precise about which article you are citing.
If a requirement is not covered by the excerpts, say so explicitly.
"""

logger = logging.getLogger(__name__)


def get_ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


def get_ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")


def get_model_name(provider: LlmProvider) -> str:
    if provider == "ollama":
        return get_ollama_model()
    return MISTRAL_MODEL


def normalize_provider(value: str) -> LlmProvider:
    if value == "ollama":
        return "ollama"
    return "mistral"


def resolve_provider(requested: LlmProvider) -> LlmProvider:
    """Fall back to Ollama only when Mistral was requested but key is missing."""
    if requested == "mistral" and not os.environ.get("MISTRAL_API_KEY"):
        logger.warning(
            "MISTRAL_API_KEY not set — falling back to Ollama for synthesis."
        )
        return "ollama"
    return requested


def check_ollama_available() -> tuple[bool, str | None]:
    """Ping Ollama /api/tags and confirm the configured model is present."""
    base = get_ollama_base_url()
    model = get_ollama_model()
    timeout = float(os.getenv("OLLAMA_HEALTH_TIMEOUT", "3.0"))
    try:
        response = httpx.get(f"{base}/api/tags", timeout=timeout)
        response.raise_for_status()
    except httpx.ConnectError:
        return (
            False,
            f"Ollama is not reachable at {base}. Start it with `ollama serve` "
            f"(local dev) or install Ollama on the server.",
        )
    except httpx.TimeoutException:
        return False, f"Ollama at {base} timed out after {timeout}s."
    except httpx.HTTPError as exc:
        return False, f"Ollama health check failed: {exc}"

    try:
        models = response.json().get("models", [])
        names = {m.get("name", "").split(":")[0] for m in models}
        model_base = model.split(":")[0]
        if model_base not in names and model not in {m.get("name") for m in models}:
            return (
                False,
                f"Model {model!r} is not pulled. Run: `ollama pull {model}`",
            )
    except Exception:
        pass

    return True, None


def get_synthesis_llm(provider: LlmProvider = "mistral") -> LLM:
    if provider == "ollama":
        from llama_index.llms.ollama import Ollama

        return Ollama(
            model=get_ollama_model(),
            base_url=get_ollama_base_url(),
            system_prompt=SYNTHESIS_PROMPT,
            request_timeout=float(os.getenv("OLLAMA_REQUEST_TIMEOUT", "120")),
        )

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError(
            "MISTRAL_API_KEY is not set and Ollama fallback unavailable."
        )

    return MistralAI(
        model=MISTRAL_MODEL,
        api_key=api_key,
        system_prompt=SYNTHESIS_PROMPT,
    )


def complete_with_retry(llm: LLM, prompt: str, provider: LlmProvider) -> str:
    """Synthesis with exponential backoff on rate limits / 5xx (Mistral only)."""
    if provider != "mistral":
        return str(llm.complete(prompt))

    delay = 2.0
    last_exc: Exception | None = None
    for attempt in range(MISTRAL_MAX_RETRIES):
        try:
            return str(llm.complete(prompt))
        except Exception as exc:
            last_exc = exc
            text = str(exc).lower()
            if "429" in text or "rate limit" in text or "5" in text[:3]:
                if attempt < MISTRAL_MAX_RETRIES - 1:
                    time.sleep(delay)
                    delay = min(delay * 2, 30.0)
                    continue
            raise
    assert last_exc is not None
    raise last_exc
