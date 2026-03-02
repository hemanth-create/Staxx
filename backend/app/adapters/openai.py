import time
import logging
from typing import Optional

from openai import AsyncOpenAI
import tiktoken

from app.adapters.base import BaseAdapter, AdapterConfig, GenerationResult

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseAdapter):
    """
    Adapter for OpenAI models (GPT-4o, GPT-3.5-turbo, etc).
    """

    def __init__(self, api_key: Optional[str] = None):
        # In a real app, API keys should be injected or loaded from securely managed configs.
        self.client = AsyncOpenAI(api_key=api_key) if api_key else AsyncOpenAI()

    async def generate(self, prompt: str, config: AdapterConfig) -> GenerationResult:
        start_time = time.perf_counter()
        
        messages = []
        if config.system_prompt:
            messages.append({"role": "system", "content": config.system_prompt})
        
        messages.append({"role": "user", "content": prompt})

        request_kwargs = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

        if config.json_mode:
            # Requires `response_format` for strict JSON handling in newer OpenAI models.
            request_kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self.client.chat.completions.create(**request_kwargs)
            
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            content = response.choices[0].message.content or ""
            usage = response.usage
            
            input_tokens = usage.prompt_tokens if usage else self.count_tokens(prompt)
            output_tokens = usage.completion_tokens if usage else self.count_tokens(content)

            return GenerationResult(
                content=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
            )

        except Exception as e:
            end_time = time.perf_counter()
            logger.error("OpenAI generation failed: %s", str(e))
            return GenerationResult(
                content="",
                input_tokens=self.count_tokens(prompt),
                output_tokens=0,
                latency_ms=(end_time - start_time) * 1000,
                error=str(e),
            )

    def count_tokens(self, text: str) -> int:
        try:
            # Defaulting to o200k_base or cl100k_base depending on model capability.
            # Using cl100k_base as a safe default for gpt-4 class models
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            return len(text) // 4  # Rough heuristic fallback

    def get_provider_name(self) -> str:
        return "openai"
