"""LLM Factory — Provides the best available language model with graceful fallbacks.

Priority chain:
  gemini-2.5-pro (via google-genai SDK)
  -> gpt-4o (OpenAI)
  -> claude-sonnet-4-5 (Anthropic)
  -> gemini-2.5-flash (fallback Gemini)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Unified LLM client with provider auto-detection and fallback chain."""

    def __init__(self):
        self._provider: Optional[str] = None
        self._client: Any = None
        self._model: str = ""
        self._initialize()

    def _initialize(self):
        """Detect the best available provider."""
        if settings.GEMINI_API_KEY:
            try:
                from google import genai  # type: ignore
                self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
                self._model = settings.DEFAULT_LLM_MODEL  # gemini-2.5-pro
                self._provider = "gemini"
                logger.info("LLM: using Gemini %s", self._model)
                return
            except Exception as e:
                logger.warning("Gemini init failed: %s", e)

        if settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI  # type: ignore
                self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
                self._model = "gpt-4o"
                self._provider = "openai"
                logger.info("LLM: using OpenAI gpt-4o")
                return
            except Exception as e:
                logger.warning("OpenAI init failed: %s", e)

        if settings.ANTHROPIC_API_KEY:
            try:
                from anthropic import Anthropic  # type: ignore
                self._client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                self._model = "claude-sonnet-4-5"
                self._provider = "anthropic"
                logger.info("LLM: using Anthropic claude-sonnet-4-5")
                return
            except Exception as e:
                logger.warning("Anthropic init failed: %s", e)

        # Fallback: attempt free Gemini tier without key
        try:
            from google import genai  # type: ignore
            self._client = genai.Client()
            self._model = settings.FALLBACK_LLM_MODEL
            self._provider = "gemini-free"
        except Exception as e:
            logger.error("No LLM provider available: %s", e)
            self._provider = "mock"

    def reload(self):
        """Re-initialize client and provider based on latest settings."""
        self._provider = None
        self._client = None
        self._model = ""
        self._initialize()

    @property
    def provider(self) -> str:
        return self._provider or "mock"

    @property
    def model(self) -> str:
        return self._model

    def generate(self, prompt: str, system: str = "", temperature: float = 0.9, max_tokens: int = 4096) -> str:
        """Generate text — synchronous wrapper for use inside LangGraph nodes."""
        if self._provider in ("gemini", "gemini-free"):
            return self._gemini_generate(prompt, system, temperature, max_tokens)
        elif self._provider == "openai":
            return self._openai_generate(prompt, system, temperature, max_tokens)
        elif self._provider == "anthropic":
            return self._anthropic_generate(prompt, system, temperature, max_tokens)
        else:
            logger.error("LLM provider is mock — returning empty string")
            return ""

    def _gemini_generate(self, prompt: str, system: str, temperature: float, max_tokens: int) -> str:
        from google.genai import types  # type: ignore
        contents = prompt
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system if system else None,
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=config,
        )
        return response.text or ""

    def _openai_generate(self, prompt: str, system: str, temperature: float, max_tokens: int) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def _anthropic_generate(self, prompt: str, system: str, temperature: float, max_tokens: int) -> str:
        kwargs = {"model": self._model, "max_tokens": max_tokens, "temperature": temperature,
                  "messages": [{"role": "user", "content": prompt}]}
        if system:
            kwargs["system"] = system
        response = self._client.messages.create(**kwargs)
        return response.content[0].text or ""

    async def generate_async(self, prompt: str, system: str = "", temperature: float = 0.9, max_tokens: int = 4096) -> str:
        """Asynchronous text generation with fallback."""
        if self._provider == "mock" or not self._client:
            return ""
        try:
            import asyncio
            return await asyncio.to_thread(self.generate, prompt, system, temperature, max_tokens)
        except Exception as e:
            logger.warning("generate_async failed: %s", e)
            return ""

    async def invoke_json(self, system: str, user_prompt: str, fallback_response: Any = None) -> Any:
        """Call LLM and parse JSON output safely with automatic fallback."""
        import json
        if self._provider == "mock" or not self._client:
            return fallback_response

        try:
            full_prompt = f"{user_prompt}\n\nRespond ONLY with valid JSON."
            raw_text = await self.generate_async(full_prompt, system=system, temperature=0.7)
            if not raw_text or not raw_text.strip():
                return fallback_response

            clean_text = raw_text.strip()
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()

            return json.loads(clean_text)
        except Exception as exc:
            logger.warning("invoke_json parsing or API error (%s) — using fallback", exc)
            return fallback_response


# Singleton instance
llm_service = LLMService()
