# ======================================================================================================
# PROYECTO INTEGRADOR MULTIDISCIPLINAR · UNIVERSIDAD DEL VALLE (Cali, Colombia)
# Sistema Multiagente de IA para Procesamiento y Análisis de Datos Genéricos
# Autoría: ANDRES SANCHEZ Y SAMUEL MORA — Todos los derechos reservados.
# ======================================================================================================
"""Capa de modelo de lenguaje, independiente del proveedor.

 - AnthropicLLM : API de Mensajes de Anthropic vía HTTPS (sin dependencias). Se activa con ANTHROPIC_API_KEY.
 - OpenAICompatLLM: cualquier endpoint compatible con /chat/completions (OpenAI, Azure, Ollama, LM Studio...).
 - NullLLM      : sin modelo. El sistema usa entonces el motor determinista de respaldo de cada agente.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class LLMError(RuntimeError):
    pass


class LLM:
    name = "none"
    available = False

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:  # pragma: no cover
        raise NotImplementedError


class NullLLM(LLM):
    name = "motor determinista (sin LLM)"
    available = False


def _post(url: str, headers: dict, body: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"content-type": "application/json", **headers}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise LLMError(f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}") from e
    except Exception as e:  # red, timeout, etc.
        raise LLMError(str(e)) from e


class AnthropicLLM(LLM):
    available = True

    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or os.environ.get("SMA_MODEL", "claude-sonnet-5-5")
        self.name = f"Anthropic · {self.model}"

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:
        out = _post("https://api.anthropic.com/v1/messages", {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                    {"model": self.model, "max_tokens": max_tokens, "temperature": 0.2, "system": system, "messages": [{"role": "user", "content": user}]})
        return "".join(b.get("text", "") for b in out.get("content", []))


class OpenAICompatLLM(LLM):
    available = True

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key, self.model, self.base_url = api_key, model, base_url.rstrip("/")
        self.name = f"OpenAI-compatible · {model}"

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:
        out = _post(f"{self.base_url}/chat/completions", {"authorization": f"Bearer {self.api_key}"},
                    {"model": self.model, "temperature": 0.2, "max_tokens": max_tokens, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        return out["choices"][0]["message"]["content"]


class ScriptedLLM(LLM):
    """Modelo simulado para pruebas: devuelve respuestas predefinidas (útil para sondear guardrails)."""
    available = True
    name = "LLM simulado (pruebas)"

    def __init__(self, responder):
        self.responder = responder
        self.calls = []

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:
        self.calls.append((system, user))
        return self.responder(system, user)


def llm_from_env() -> LLM:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicLLM(os.environ["ANTHROPIC_API_KEY"])
    if os.environ.get("OPENAI_API_KEY") or os.environ.get("SMA_OPENAI_BASE_URL"):
        return OpenAICompatLLM(os.environ.get("OPENAI_API_KEY", "none"), os.environ.get("SMA_MODEL", "gpt-4o-mini"), os.environ.get("SMA_OPENAI_BASE_URL", "https://api.openai.com/v1"))
    return NullLLM()
