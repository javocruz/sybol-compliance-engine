import os
from typing import Literal

from llama_index.core.llms import LLM
from llama_index.llms.mistralai import MistralAI

LlmProvider = Literal["mistral", "ollama"]

MISTRAL_MODEL = "mistral-large-latest"

SYNTHESIS_PROMPT = """
You are a EU regulatory compliance expert. Using ONLY the provided regulation excerpts,
answer the query. Be precise about which article you are citing.
If a requirement is not covered by the excerpts, say so explicitly.
"""


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
            "MISTRAL_API_KEY is not set. Configure it in src/.env or switch to Ollama."
        )

    return MistralAI(
        model=MISTRAL_MODEL,
        api_key=api_key,
        system_prompt=SYNTHESIS_PROMPT,
    )
