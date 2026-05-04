"""Cisco Circuit API client for LLM access.

Handles OAuth2 authentication and provides a LangChain-compatible
AzureChatOpenAI instance backed by Circuit.
"""
from __future__ import annotations

import base64
import os

import requests
from langchain_openai import AzureChatOpenAI


class CircuitClient:
    """Thin wrapper for Cisco Circuit API authentication."""

    TOKEN_URL = "https://id.cisco.com/oauth2/default/v1/token"
    BASE_URL = "https://chat-ai.cisco.com/"
    API_VERSION = "2025-04-01-preview"
    MODEL = "gpt-5-nano"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        appkey: str | None = None,
    ):
        self.client_id = client_id or os.getenv("CIRCUIT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("CIRCUIT_CLIENT_SECRET")
        self.appkey = appkey or os.getenv("CIRCUIT_APPKEY")

        if not self.client_id or not self.client_secret:
            raise ValueError("Missing CIRCUIT_CLIENT_ID or CIRCUIT_CLIENT_SECRET")

        self.token = self._fetch_token()

    def _fetch_token(self) -> str:
        value = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        resp = requests.post(
            self.TOKEN_URL,
            headers={
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {value}",
            },
            data="grant_type=client_credentials",
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def get_llm(self, temperature: float = 0.0) -> AzureChatOpenAI:
        """Return a LangChain LLM instance backed by Circuit."""
        return AzureChatOpenAI(
            azure_endpoint=self.BASE_URL,
            openai_api_version=self.API_VERSION,
            api_key=self.token,
            model_name=self.MODEL,
            temperature=temperature,
            model_kwargs={"user": f'{{"appkey": "{self.appkey}"}}'},
        )
