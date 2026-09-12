"""Provider-neutral chat adapter for structured planning inference."""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


HF_DEFAULT_BASE_URL = "https://router.huggingface.co/v1"
_LOW_REASONING_MODEL_PREFIXES = ("Qwen/Qwen3.8-",)


class ModelConfigurationError(RuntimeError):
    """Raised when live model configuration is incomplete or unsafe."""


class ModelServiceError(RuntimeError):
    """Safe public-facing inference service failure."""


class StructuredModelError(RuntimeError):
    """Raised when the provider returns no usable chat content."""


class JsonChatModel(Protocol):
    """Small provider-neutral interface used by the planning layer."""

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> str:
        """Return one JSON object as text."""


def _service_message(status_code: int | None) -> str:
    messages = {
        400: "The inference provider rejected the request format or parameters (HTTP 400).",
        401: "Inference authentication failed. Check the HF_TOKEN secret.",
        402: "The inference provider requires available credits or billing. Check the Hugging Face account billing settings.",
        403: "Inference access was denied. The token needs permission to call Hugging Face Inference Providers.",
        404: "The configured model or provider endpoint was not found (HTTP 404).",
        429: "The inference provider rate limit was reached. Try again later.",
    }
    if status_code in messages:
        return messages[status_code]
    if status_code is not None and 500 <= status_code <= 599:
        return "The inference provider is temporarily unavailable. Try again later."
    return "The inference provider is unavailable or failed to respond. Try again later."


def _uses_low_reasoning(model_id: str) -> bool:
    """Use the documented low reasoning setting for Qwen3.8 structured output."""
    return model_id.startswith(_LOW_REASONING_MODEL_PREFIXES)


@dataclass(frozen=True)
class HuggingFaceChatClient:
    """OpenAI-compatible Hugging Face Inference Providers adapter.

    The planning engine depends on the JsonChatModel contract rather than a provider SDK.
    Credentials and model selection come from runtime configuration, not source code.
    """

    model_id: str
    token: str
    base_url: str = HF_DEFAULT_BASE_URL
    temperature: float = 0.2
    max_tokens: int = 3600
    timeout_seconds: float = 45.0
    client: Any | None = None

    @classmethod
    def from_env(
        cls,
        *,
        token: str | None = None,
        model_id: str | None = None,
        base_url: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> "HuggingFaceChatClient":
        values = env if env is not None else os.environ
        resolved_token = (token or values.get("HF_TOKEN", "")).strip()
        resolved_model = (model_id or values.get("MODEL_ID", "")).strip()
        resolved_base_url = (base_url or values.get("HF_BASE_URL", HF_DEFAULT_BASE_URL)).strip()

        if not resolved_token or resolved_token in {"your_runtime_token", "<space-secret>"}:
            raise ModelConfigurationError("HF_TOKEN is required for live inference.")
        if not resolved_model or resolved_model in {"your_model_id", "<hugging-face-provider-model-id>"}:
            raise ModelConfigurationError("MODEL_ID is required for live inference.")
        if not resolved_base_url.startswith("https://"):
            raise ModelConfigurationError("HF_BASE_URL must use https.")

        return cls(
            model_id=resolved_model,
            token=resolved_token,
            base_url=resolved_base_url,
        )

    @property
    def provider_label(self) -> str:
        return f"{self.model_id} via Hugging Face Inference Providers"

    def _get_client(self):
        if self.client is not None:
            return self.client

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - runtime dependency failure
            raise ModelConfigurationError(
                "The openai package is required for live Hugging Face inference."
            ) from exc

        return OpenAI(
            base_url=self.base_url,
            api_key=self.token,
            timeout=self.timeout_seconds,
        )

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> str:
        client = self._get_client()
        request: dict[str, Any] = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if _uses_low_reasoning(self.model_id):
            # Qwen3.8 can otherwise spend the bounded completion budget on hidden
            # reasoning before emitting the visible JSON object. This is the same
            # documented OpenAI-compatible setting used by the newer portfolio agents.
            request["reasoning_effort"] = "low"

        try:
            response = client.chat.completions.create(**request)
        except Exception as exc:
            # Import lazily so deterministic tests can inject a fake client without
            # requiring the OpenAI SDK to be imported at module load time.
            try:
                from openai import APIConnectionError, APIStatusError, APITimeoutError
            except ImportError:  # pragma: no cover - only possible in broken runtime
                raise ModelServiceError(_service_message(None)) from None

            if isinstance(exc, APIStatusError):
                raise ModelServiceError(_service_message(exc.status_code)) from None
            if isinstance(exc, (APITimeoutError, APIConnectionError)):
                raise ModelServiceError(_service_message(None)) from None
            raise

        choice = response.choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason == "length":
            raise StructuredModelError(
                f"The inference provider truncated the structured response at max_tokens={self.max_tokens}."
            )
        if finish_reason not in {None, "stop"}:
            raise StructuredModelError(
                f"The inference provider ended the structured response unexpectedly: finish_reason={finish_reason}."
            )

        content = choice.message.content
        if not isinstance(content, str) or not content.strip():
            raise StructuredModelError("The inference provider returned an empty chat response.")
        return content.strip()
