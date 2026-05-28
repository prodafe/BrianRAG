"""可插拔 LLM / Embedding Provider —— 换模型只需改 config"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator

logger = logging.getLogger(__name__)


# ── LLM Provider ─────────────────────────────────────────


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, model: str = None, **kwargs) -> str:
        """非对话式文本生成。model=None 使用默认模型"""
        ...

    @abstractmethod
    def chat(self, messages: list[dict], model: str = None, **kwargs) -> str:
        """对话式生成"""
        ...

    @abstractmethod
    def chat_stream(self, messages: list[dict], model: str = None, **kwargs) -> Iterator[str]:
        """流式对话生成"""
        ...


class OllamaLLMProvider(BaseLLMProvider):
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        import ollama

        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client = ollama.Client(host=self.base_url)

    def generate(self, prompt: str, model: str = None, **kwargs) -> str:
        opts = kwargs.pop("options", {})
        m = model or self.model
        resp = self._client.generate(model=m, prompt=prompt, options=opts, **kwargs)
        return resp["response"].strip()

    def chat(self, messages: list[dict], model: str = None, **kwargs) -> str:
        opts = kwargs.pop("options", {})
        m = model or self.model
        resp = self._client.chat(model=m, messages=messages, options=opts, **kwargs)
        return resp["message"]["content"].strip()

    def chat_stream(self, messages: list[dict], model: str = None, **kwargs) -> Iterator[str]:
        opts = kwargs.pop("options", {})
        m = model or self.model
        for chunk in self._client.chat(model=m, messages=messages, stream=True, options=opts, **kwargs):
            if "message" in chunk and "content" in chunk["message"]:
                yield chunk["message"]["content"]


class OpenAIProvider(BaseLLMProvider):
    """兼容 OpenAI / DeepSeek / 通义千问 等 OpenAI-compatible API"""

    def __init__(self, model: str, base_url: str, api_key: str):
        from openai import OpenAI

        self.model = model
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    def generate(self, prompt: str, model: str = None, **kwargs) -> str:
        return self.chat([{"role": "user", "content": prompt}], model=model, **kwargs)

    def chat(self, messages: list[dict], model: str = None, **kwargs) -> str:
        temperature = kwargs.pop("temperature", 0)
        max_tokens = kwargs.pop("max_tokens", kwargs.pop("num_predict", 1024))
        resp = self._client.chat.completions.create(
            model=model or self.model, messages=messages, temperature=temperature, max_tokens=max_tokens, **kwargs
        )
        return resp.choices[0].message.content.strip()

    def chat_stream(self, messages: list[dict], model: str = None, **kwargs) -> Iterator[str]:
        temperature = kwargs.pop("temperature", 0)
        max_tokens = kwargs.pop("max_tokens", kwargs.pop("num_predict", 1024))
        stream = self._client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, model: str, api_key: str):
        from anthropic import Anthropic

        self.model = model
        self._client = Anthropic(api_key=api_key)

    def generate(self, prompt: str, model: str = None, **kwargs) -> str:
        return self.chat([{"role": "user", "content": prompt}], model=model, **kwargs)

    def chat(self, messages: list[dict], model: str = None, **kwargs) -> str:
        # Anthropic 要求 system 单独提取
        system = None
        user_msgs = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                user_msgs.append(m)
        max_tokens = kwargs.pop("max_tokens", kwargs.pop("num_predict", 1024))
        resp = self._client.messages.create(
            model=self.model, system=system, messages=user_msgs, max_tokens=max_tokens, **kwargs
        )
        return resp.content[0].text.strip()

    def chat_stream(self, messages: list[dict], **kwargs) -> Iterator[str]:
        system = None
        user_msgs = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                user_msgs.append(m)
        max_tokens = kwargs.pop("max_tokens", kwargs.pop("num_predict", 1024))
        with self._client.messages.stream(
            model=self.model, system=system, messages=user_msgs, max_tokens=max_tokens, **kwargs
        ) as stream:
            yield from stream.text_stream


# ── Embedding Provider ───────────────────────────────────


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        import ollama

        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client = ollama.Client(host=self.base_url)

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embed(model=self.model, input=texts)
        return resp["embeddings"]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model: str, base_url: str, api_key: str):
        from openai import OpenAI

        self.model = model
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in resp.data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


# ── Factory ──────────────────────────────────────────────

_llm_provider: BaseLLMProvider | None = None
_embed_provider: BaseEmbeddingProvider | None = None
_small_llm: BaseLLMProvider | None = None


def get_llm_provider() -> BaseLLMProvider:
    global _llm_provider
    if _llm_provider is None:
        from config import Config
        import os

        provider = getattr(Config, "LLM_PROVIDER", "ollama")
        model = Config.LLM_MODEL
        base_url = getattr(Config, "OLLAMA_BASE_URL", "http://localhost:11434")
        api_key = getattr(Config, "LLM_API_KEY", "")

        # Auto-detect from environment if not explicitly configured
        if provider == "ollama":
            if api_key := os.getenv("OPENAI_API_KEY", ""):
                provider = "openai"
                model = model or "gpt-4o-mini"
                base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
                logger.info("Auto-detected OPENAI_API_KEY, switching to OpenAI provider")
            elif api_key := os.getenv("ANTHROPIC_API_KEY", ""):
                provider = "anthropic"
                model = model or "claude-sonnet-4-6"
                logger.info("Auto-detected ANTHROPIC_API_KEY, switching to Anthropic provider")

        if provider == "openai":
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY", "")
                base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            _llm_provider = OpenAIProvider(model=model, base_url=base_url, api_key=api_key)
        elif provider == "anthropic":
            if not api_key:
                api_key = os.getenv("ANTHROPIC_API_KEY", "")
            _llm_provider = AnthropicProvider(model=model, api_key=api_key)
        else:
            _llm_provider = OllamaLLMProvider(model=model, base_url=base_url)
        logger.info(f"LLM Provider: {provider}/{model}")

    return _llm_provider


def get_small_llm() -> BaseLLMProvider:
    """用于轻量任务（纠错、分类）的小模型"""
    global _small_llm
    if _small_llm is None:
        from config import Config

        provider = getattr(Config, "LLM_PROVIDER", "ollama")
        model = getattr(Config, "EVALUATOR_MODEL", "qwen2.5:1.5b")
        base_url = getattr(Config, "OLLAMA_BASE_URL", "http://localhost:11434")
        api_key = getattr(Config, "LLM_API_KEY", "")

        if provider == "openai":
            _small_llm = OpenAIProvider(model=model, base_url=base_url, api_key=api_key)
        elif provider == "anthropic":
            _small_llm = AnthropicProvider(model=model, api_key=api_key)
        else:
            _small_llm = OllamaLLMProvider(model=model, base_url=base_url)

    return _small_llm


def get_embed_provider() -> BaseEmbeddingProvider:
    global _embed_provider
    if _embed_provider is None:
        from config import Config

        provider = getattr(Config, "LLM_PROVIDER", "ollama")
        model = Config.EMBEDDING_MODEL
        base_url = getattr(Config, "OLLAMA_BASE_URL", "http://localhost:11434")
        api_key = getattr(Config, "LLM_API_KEY", "")

        if provider == "openai":
            _embed_provider = OpenAIEmbeddingProvider(model=model, base_url=base_url, api_key=api_key)
        else:
            _embed_provider = OllamaEmbeddingProvider(model=model, base_url=base_url)
        logger.info(f"Embedding Provider: {type(_embed_provider).__name__}/{model}")

    return _embed_provider


def reset_providers():
    """切换 provider 后重置全局实例"""
    global _llm_provider, _embed_provider, _small_llm
    _llm_provider = None
    _embed_provider = None
    _small_llm = None
