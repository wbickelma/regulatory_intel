"""
Shared Circuit LLM Client
=========================

Thin, reusable wrapper around the firm's Circuit enterprise LLM
gateway.  Every agent (investigator, evaluator, summarizer, etc.)
imports from here so authentication and client configuration live
in exactly one place.

Pattern follows ``circuit_scrapegraph_example.py``:

    1. ``CircuitApi`` fetches a short-lived bearer token from the
       Cisco IdP using Basic auth (client_id:client_secret, base64).
    2. ``get_circuit_llm()`` returns a LangChain ``AzureChatOpenAI``
       instance whose ``api_key`` is that bearer token, with the
       firm's ``appkey`` passed via ``model_kwargs["user"]``.
    3. Callers typically wrap the result with
       ``.with_structured_output(<PydanticModel>)`` to get validated
       objects back.

Notes:
    - Tokens are cached process-wide with a safety margin so we
      don't re-authenticate on every LLM call.  Override with
      ``force_refresh=True`` when needed.
    - All endpoints / versions default to the firm's production
      values via ``config.settings`` and can be overridden per-env.
"""

from __future__ import annotations

import base64
import time
from threading import Lock
from typing import Optional

import requests
from langchain_openai import AzureChatOpenAI

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)

# Refresh ~5 minutes before the advertised expiry to avoid edge-case 401s.
_TOKEN_REFRESH_SKEW_SECONDS = 300
_DEFAULT_TOKEN_TTL_SECONDS = 3600


class CircuitApi:
    """
    Firm-authenticated handle to the Circuit enterprise LLM gateway.

    Instances are cheap; the underlying bearer token is cached on the
    class so repeated instantiations across agents reuse a single
    authenticated session.
    """

    _cached_token: Optional[str] = None
    _cached_expiry: float = 0.0
    _lock: Lock = Lock()

    def __init__(self, appkey: str | None = None) -> None:
        self.appkey = appkey or settings.circuit_appkey
        self.api_version = settings.circuit_api_version
        self.base_url = settings.circuit_base_url
        self.token = self._get_token()

    # ── token management ────────────────────────────────────────────────

    @classmethod
    def _get_token(cls, force_refresh: bool = False) -> str:
        """Return a valid bearer token, refreshing if needed."""
        with cls._lock:
            now = time.time()
            if (
                not force_refresh
                and cls._cached_token
                and now < cls._cached_expiry
            ):
                return cls._cached_token
            cls._cached_token, cls._cached_expiry = cls._fetch_token()
            return cls._cached_token

    @staticmethod
    def _fetch_token() -> tuple[str, float]:
        client_id = settings.circuit_client_id
        client_secret = settings.circuit_client_secret
        if not client_id or not client_secret:
            raise ValueError("Missing CIRCUIT_CLIENT_ID or CIRCUIT_CLIENT_SECRET")

        value = base64.b64encode(
            f"{client_id}:{client_secret}".encode("utf-8")
        ).decode("utf-8")
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {value}",
        }
        resp = requests.post(
            settings.circuit_token_url,
            headers=headers,
            data="grant_type=client_credentials",
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        token = payload["access_token"]
        ttl = int(payload.get("expires_in", _DEFAULT_TOKEN_TTL_SECONDS))
        expiry = time.time() + max(ttl - _TOKEN_REFRESH_SKEW_SECONDS, 60)
        logger.info("Fetched Circuit token (ttl=%ss)", ttl)
        return token, expiry


# ── Module-level helpers ────────────────────────────────────────────────

def circuit_configured() -> bool:
    """True when required Circuit credentials are populated."""
    return bool(
        settings.circuit_client_id
        and settings.circuit_client_secret
        and settings.circuit_appkey
    )


def _patch_langchain_azure_for_circuit() -> None:
    """
    Ensure every ``AzureChatOpenAI`` / ``AzureOpenAIEmbeddings``
    instance constructed in this process carries the firm's
    ``appkey`` via ``model_kwargs["user"]``.

    Libraries like GPT Researcher instantiate these classes
    internally with their own arguments, so passing the appkey
    through our own factory isn't enough: we need it on every
    instance.  This patch is idempotent.
    """
    appkey = settings.circuit_appkey
    if not appkey:
        return

    from langchain_openai import AzureChatOpenAI

    try:
        from langchain_openai import AzureOpenAIEmbeddings
    except Exception:  # pragma: no cover - optional import
        AzureOpenAIEmbeddings = None  # type: ignore[assignment]

    user_value = f'{{"appkey": "{appkey}"}}'

    for cls in (AzureChatOpenAI, AzureOpenAIEmbeddings):
        if cls is None or getattr(cls, "_circuit_patched", False):
            continue
        orig_init = cls.__init__

        def make_patched(original):
            def patched_init(self, *args, **kwargs):
                mk = dict(kwargs.get("model_kwargs") or {})
                mk.setdefault("user", user_value)
                kwargs["model_kwargs"] = mk
                return original(self, *args, **kwargs)
            return patched_init

        cls.__init__ = make_patched(orig_init)
        cls._circuit_patched = True
    logger.info("Patched LangChain Azure classes to inject Circuit appkey")


def configure_gpt_researcher_env() -> None:
    """
    Export the environment variables GPT Researcher reads at import
    time so its internal LLM / embedding calls route through Circuit,
    and patch LangChain's Azure classes so the firm ``appkey`` is
    automatically attached to every request (matching the pattern in
    ``circuit_scrapegraph_example.py``).
    """
    import os

    if not circuit_configured():
        raise RuntimeError(
            "Circuit API is not configured; cannot initialize GPT Researcher."
        )
    token = CircuitApi._get_token()
    model = settings.circuit_model
    os.environ["LLM_PROVIDER"] = "azure_openai"
    # Circuit app keys aren't authorized for Azure embedding deployments,
    # so embeddings are served locally by a sentence-transformers model.
    # The model folder is resolved from settings.local_embedding_model_path
    # (falling back to the HuggingFace model ID, which requires network
    # access to huggingface.co).  Chat completions still go through
    # Circuit / Azure OpenAI.
    embedding_ref = (
        settings.local_embedding_model_path
        or "sentence-transformers/all-MiniLM-L6-v2"
    )
    os.environ["EMBEDDING"] = f"huggingface:{embedding_ref}"
    # The deprecated EMBEDDING_PROVIDER variable takes precedence over
    # EMBEDDING in gpt-researcher's config and also hardcodes the model
    # ID — so we must make sure it is NOT set.
    os.environ.pop("EMBEDDING_PROVIDER", None)
    os.environ["AZURE_OPENAI_API_KEY"] = token
    os.environ["AZURE_OPENAI_ENDPOINT"] = settings.circuit_base_url
    os.environ["AZURE_OPENAI_API_VERSION"] = settings.circuit_api_version
    os.environ["OPENAI_API_VERSION"] = settings.circuit_api_version
    os.environ["OPENAI_API_KEY"] = token  # some GPTR code paths read this
    os.environ.setdefault("FAST_LLM", f"azure_openai:{model}")
    os.environ.setdefault("SMART_LLM", f"azure_openai:{model}")
    os.environ.setdefault("STRATEGIC_LLM", f"azure_openai:{model}")

    # Retriever: DuckDuckGo (no API key required).  Google Programmable
    # Search was dropped because new engines can no longer enable
    # "search the entire web".
    os.environ["RETRIEVER"] = "duckduckgo"
    logger.info("Configured GPT Researcher retriever: duckduckgo")

    _patch_langchain_azure_for_circuit()
    logger.info("Configured GPT Researcher env for Circuit (model=%s)", model)


def get_circuit_llm(
    model_name: str | None = None,
    temperature: float = 0.0,
    **kwargs,
) -> AzureChatOpenAI:
    """
    Build a LangChain ``AzureChatOpenAI`` backed by Circuit.

    Parameters
    ----------
    model_name : str, optional
        Override the default model (``settings.circuit_model``).
    temperature : float
        Sampling temperature; defaults to 0 for deterministic output.
    **kwargs
        Forwarded to ``AzureChatOpenAI`` for additional tuning
        (e.g. ``max_tokens``, ``timeout``).

    The caller is expected to wrap the returned client with
    ``.with_structured_output(<PydanticModel>)`` when a typed
    response is required.
    """
    if not circuit_configured():
        raise RuntimeError(
            "Circuit API is not configured; set CIRCUIT_CLIENT_ID, "
            "CIRCUIT_CLIENT_SECRET, and CIRCUIT_APPKEY."
        )
    circuit = CircuitApi()
    return AzureChatOpenAI(
        azure_endpoint=circuit.base_url,
        openai_api_version=circuit.api_version,
        api_key=circuit.token,
        model_name=model_name or settings.circuit_model,
        temperature=temperature,
        model_kwargs={"user": f'{{"appkey": "{circuit.appkey}"}}'},
        **kwargs,
    )
