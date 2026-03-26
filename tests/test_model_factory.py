"""Tests for model_factory.py."""
import pytest

from persona_counsel.model_factory import PROVIDER_DEFAULTS, VALID_PROVIDERS, build_model


class TestBuildModel:
    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            build_model("badprovider", None)

    def test_valid_providers_listed(self):
        assert "ollama" in VALID_PROVIDERS
        assert "anthropic" in VALID_PROVIDERS
        assert "groq" in VALID_PROVIDERS

    def test_provider_defaults_exist(self):
        for provider in VALID_PROVIDERS:
            assert provider in PROVIDER_DEFAULTS
            assert PROVIDER_DEFAULTS[provider]

    def test_ollama_returns_openai_chat_model(self):
        from pydantic_ai.models.openai import OpenAIChatModel
        model = build_model("ollama", None)
        assert isinstance(model, OpenAIChatModel)

    def test_ollama_with_custom_model(self):
        from pydantic_ai.models.openai import OpenAIChatModel
        model = build_model("ollama", "llama3.2:3b")
        assert isinstance(model, OpenAIChatModel)

    def test_anthropic_returns_anthropic_model(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
        from pydantic_ai.models.anthropic import AnthropicModel
        model = build_model("anthropic", None)
        assert isinstance(model, AnthropicModel)

    def test_groq_returns_groq_model(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "fake-key")
        from pydantic_ai.models.groq import GroqModel
        model = build_model("groq", None)
        assert isinstance(model, GroqModel)

    def test_deepseek_returns_openai_chat_model(self):
        from pydantic_ai.models.openai import OpenAIChatModel
        model = build_model("deepseek", None)
        assert isinstance(model, OpenAIChatModel)

    def test_gemini_returns_google_model(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")
        from pydantic_ai.models.google import GoogleModel
        model = build_model("gemini", None)
        assert isinstance(model, GoogleModel)

    def test_mock_returns_test_model(self):
        from pydantic_ai.models.test import TestModel
        model = build_model("mock", None)
        assert isinstance(model, TestModel)
