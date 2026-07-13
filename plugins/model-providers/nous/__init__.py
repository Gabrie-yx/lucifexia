"""Nous Portal provider profile."""

from typing import Any

from agent.portal_tags import nous_portal_tags
from providers import register_provider
from providers.base import ProviderProfile


class NousProfile(ProviderProfile):
    """Nous Portal — product tags, reasoning with Nous-specific omission."""

    def build_extra_body(
        self, *, session_id: str | None = None, **context
    ) -> dict[str, Any]:
        return {"tags": nous_portal_tags()}

    def build_api_kwargs_extras(
        self,
        *,
        reasoning_config: dict | None = None,
        supports_reasoning: bool = False,
        **context,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Nous: passes full reasoning_config, but OMITS when disabled."""
        extra_body = {}
        if supports_reasoning:
            if reasoning_config is not None:
                rc = dict(reasoning_config)
                if rc.get("enabled") is False:
                    pass  # Nous omits reasoning when disabled
                else:
                    extra_body["reasoning"] = rc
            else:
                extra_body["reasoning"] = {"enabled": True, "effort": "medium"}
        return extra_body, {}


nous = NousProfile(
    name="nous",
    aliases=("ollama",),
    env_vars=(),
    display_name="OLLAMA",
    description="OLLAMA (LUCIFEXIA local model processing)",
    signup_url="https://ollama.com/",
    fallback_models=(
        "llama3.1",
        "qwen2.5-coder",
    ),
    base_url="http://127.0.0.1:11434/v1",
    auth_type="api_key",
)

register_provider(nous)
