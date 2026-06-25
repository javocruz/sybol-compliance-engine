import logging
import os
import time
from typing import Literal

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
    """Fall back to Ollama when Mistral key is missing."""
    if requested == "mistral" and not os.environ.get("MISTRAL_API_KEY"):
        logger.warning(
            "MISTRAL_API_KEY not set — falling back to Ollama for synthesis."
        )
        return "ollama"
    return requested


def get_synthesis_llm(provider: LlmProvider = "mistral") -> LLM:
    if provider == "ollama":
        from llama_index.llms.ollama import Ollama

        return Ollama(
            model=get_ollama_model(),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
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
    """Synthesis with exponential backoff on rate limits / 5xx."""
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
