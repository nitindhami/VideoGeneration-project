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
            logger.warning("LLM: no API keys found, using Gemini free tier")
        except Exception as e:
            logger.error("No LLM provider available: %s", e)
            self._provider = "mock"

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

    # ── LangChain-compatible wrapper ───────────────────────────────────────
    def get_langchain_llm(self):
        """Return a LangChain-compatible chat model for LangGraph compatibility."""
        if settings.GEMINI_API_KEY:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
                return ChatGoogleGenerativeAI(
                    model=self._model,
                    google_api_key=settings.GEMINI_API_KEY,
                    temperature=0.9,
                )
            except Exception as e:
                logger.warning("LangChain Gemini failed: %s", e)

        if settings.OPENAI_API_KEY:
            try:
                from langchain_openai import ChatOpenAI  # type: ignore
                return ChatOpenAI(model="gpt-4o", api_key=settings.OPENAI_API_KEY, temperature=0.9)
            except Exception as e:
                logger.warning("LangChain OpenAI failed: %s", e)

        if settings.ANTHROPIC_API_KEY:
            try:
                from langchain_anthropic import ChatAnthropic  # type: ignore
                return ChatAnthropic(model="claude-sonnet-4-5", api_key=settings.ANTHROPIC_API_KEY)
            except Exception as e:
                logger.warning("LangChain Anthropic failed: %s", e)

        # Free fallback
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
        return ChatGoogleGenerativeAI(model=settings.FALLBACK_LLM_MODEL, temperature=0.9)


# Singleton instance
llm_service = LLMService()
