"""Tiny client for an open-weight model served by Ollama (or any OpenAI-compatible server).

Settings are read from Streamlit secrets first, then environment variables:
  LEASELENS_LLM_URL    default http://localhost:11434   (Ollama)
  LEASELENS_MODEL      default qwen2.5:7b               (or llama3.1:8b, qwen2.5:3b on slow laptops)
  LEASELENS_LLM_API    "ollama" (default) or "openai"  (Groq, vLLM, LM Studio, other hosted open models)
  LEASELENS_LLM_KEY    API key for hosted OpenAI-compatible endpoints

Settings are looked up when used (not at import), because Streamlit Cloud only loads
the Secrets box after the app starts.
"""
from __future__ import annotations

import json
import os

import requests

TIMEOUT = 180
_DEFAULTS = {"LEASELENS_LLM_URL": "http://localhost:11434", "LEASELENS_MODEL": "qwen2.5:7b",
             "LEASELENS_LLM_API": "ollama", "LEASELENS_LLM_KEY": ""}


def _setting(name: str) -> str:
    try:
        import streamlit as st
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, _DEFAULTS[name])


def __getattr__(name: str):
    """Keeps `llm.MODEL`, `llm.URL`, `llm.API`, `llm.KEY` working, read fresh each time."""
    key = {"URL": "LEASELENS_LLM_URL", "MODEL": "LEASELENS_MODEL",
           "API": "LEASELENS_LLM_API", "KEY": "LEASELENS_LLM_KEY"}.get(name)
    if key is None:
        raise AttributeError(name)
    value = _setting(key)
    return value.rstrip("/") if name == "URL" else value


class LLMUnavailable(RuntimeError):
    pass


def is_hosted() -> bool:
    return _setting("LEASELENS_LLM_API") != "ollama"


def _headers() -> dict:
    key = _setting("LEASELENS_LLM_KEY")
    return {"Authorization": f"Bearer {key}"} if key else {}


def is_available() -> bool:
    url = _setting("LEASELENS_LLM_URL").rstrip("/")
    try:
        path = "/v1/models" if is_hosted() else "/api/tags"
        return requests.get(url + path, timeout=5, headers=_headers()).ok
    except requests.RequestException:
        return False


def chat(system: str, user: str, json_mode: bool = False, temperature: float = 0.1) -> str:
    url, model = _setting("LEASELENS_LLM_URL").rstrip("/"), _setting("LEASELENS_MODEL")
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    try:
        if not is_hosted():
            body = {"model": model, "stream": False, "messages": messages,
                    "options": {"temperature": temperature, "num_ctx": 8192}}
            if json_mode:
                body["format"] = "json"
            r = requests.post(f"{url}/api/chat", json=body, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()["message"]["content"]

        body = {"model": model, "temperature": temperature, "messages": messages}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        r = requests.post(f"{url}/v1/chat/completions", json=body, headers=_headers(), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except requests.HTTPError as e:
        detail = e.response.text[:200] if e.response is not None else ""
        raise LLMUnavailable(f"The AI service returned an error ({e.response.status_code}): {detail}") from e
    except requests.RequestException as e:
        raise LLMUnavailable(f"Could not reach the AI model at {url}.") from e


def chat_json(system: str, user: str) -> dict:
    raw = chat(system, user, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Small models sometimes wrap JSON in prose or code fences; grab the outer object.
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            return json.loads(raw[start:end + 1])
        raise
