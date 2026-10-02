"""Tiny client for an open-weight model served by Ollama (or any OpenAI-compatible server).

Env vars:
  LEASELENS_LLM_URL    default http://localhost:11434   (Ollama)
  LEASELENS_MODEL      default qwen2.5:7b               (or llama3.1:8b, qwen2.5:3b on slow laptops)
  LEASELENS_LLM_API    "ollama" (default) or "openai"  (vLLM, llama.cpp server, LM Studio, hosted open models)
  LEASELENS_LLM_KEY    API key for hosted OpenAI-compatible endpoints
"""
from __future__ import annotations

import json
import os

import requests

URL = os.getenv("LEASELENS_LLM_URL", "http://localhost:11434").rstrip("/")
MODEL = os.getenv("LEASELENS_MODEL", "qwen2.5:7b")
API = os.getenv("LEASELENS_LLM_API", "ollama")
KEY = os.getenv("LEASELENS_LLM_KEY", "")
TIMEOUT = 180


class LLMUnavailable(RuntimeError):
    pass


def is_available() -> bool:
    try:
        path = "/api/tags" if API == "ollama" else "/v1/models"
        headers = {"Authorization": f"Bearer {KEY}"} if KEY else {}
        return requests.get(URL + path, timeout=3, headers=headers).ok
    except requests.RequestException:
        return False


def chat(system: str, user: str, json_mode: bool = False, temperature: float = 0.1) -> str:
    try:
        if API == "ollama":
            body = {"model": MODEL, "stream": False,
                    "options": {"temperature": temperature, "num_ctx": 8192},
                    "messages": [{"role": "system", "content": system},
                                 {"role": "user", "content": user}]}
            if json_mode:
                body["format"] = "json"
            r = requests.post(f"{URL}/api/chat", json=body, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()["message"]["content"]

        body = {"model": MODEL, "temperature": temperature,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}]}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {KEY}"} if KEY else {}
        r = requests.post(f"{URL}/v1/chat/completions", json=body, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except requests.RequestException as e:
        raise LLMUnavailable(f"Could not reach the model at {URL}: {e}") from e


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
