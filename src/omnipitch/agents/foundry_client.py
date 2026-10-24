"""Microsoft Foundry & Azure AI Services client with OpenTelemetry tracing and resilient fallback."""

import os
import time
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field


class FoundryExecutionTrace(BaseModel):
    """Execution telemetry captured for every Microsoft Foundry invocation."""
    model_name: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    status: str
    endpoint: str


class MicrosoftFoundryClient:
    """
    Client for Microsoft AI Foundry and Azure OpenAI Services.
    Handles authentication, latency budgets, OpenTelemetry instrumentation,
    and automatic failover to local intelligence if Azure endpoints are offline.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_sec: float = 2.5,
    ):
        self.endpoint = endpoint or os.getenv("AZURE_AI_FOUNDRY_ENDPOINT", "")
        self.api_key = api_key or os.getenv("AZURE_AI_FOUNDRY_API_KEY", "")
        self.model = model or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
        self.timeout_sec = timeout_sec
        self.last_trace: Optional[FoundryExecutionTrace] = None

    @property
    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key and "your_" not in self.api_key)

    async def generate_tactical_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 250,
    ) -> tuple[str, FoundryExecutionTrace]:
        """
        Executes a chat completion on a Microsoft Foundry (Azure OpenAI) deployment.
        Returns the generated text with tracing telemetry, or an empty string when the
        endpoint is not configured or does not answer within the latency budget, so the
        caller can fall back to its deterministic, pre-verified output.
        """
        start_time = time.perf_counter()

        if self.is_configured:
            try:
                url = f"{self.endpoint.rstrip('/')}/openai/deployments/{self.model}/chat/completions?api-version={self.api_version}"
                headers = {
                    "api-key": self.api_key,
                    "Content-Type": "application/json",
                }
                payload = {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        text = data["choices"][0]["message"]["content"]
                        usage = data.get("usage", {})
                        latency = (time.perf_counter() - start_time) * 1000.0

                        trace = FoundryExecutionTrace(
                            model_name=self.model,
                            latency_ms=round(latency, 1),
                            prompt_tokens=usage.get("prompt_tokens", 0),
                            completion_tokens=usage.get("completion_tokens", 0),
                            status="success_live_foundry",
                            endpoint=self.endpoint,
                        )
                        self.last_trace = trace
                        return text, trace
                    status = f"http_{resp.status_code}"
            except Exception as exc:  # timeout or network error: caller falls back
                status = f"error_{type(exc).__name__}"
        else:
            status = "not_configured"

        # No live model answer: report honestly so the UI can show 'local' vs 'live Foundry'
        latency = (time.perf_counter() - start_time) * 1000.0
        trace = FoundryExecutionTrace(
            model_name="omnipitch-local-rules" if status == "not_configured" else self.model,
            latency_ms=round(latency, 1),
            prompt_tokens=0,
            completion_tokens=0,
            status=f"local_fallback:{status}",
            endpoint="local://omnipitch" if status == "not_configured" else self.endpoint,
        )
        self.last_trace = trace
        return "", trace
