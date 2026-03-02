import time
import logging
from typing import Optional

try:
    from anthropic import AsyncAnthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from app.adapters.base import BaseAdapter, AdapterConfig, GenerationResult

logger = logging.getLogger(__name__)


class AnthropicAdapter(BaseAdapter):
    """
    Adapter for Anthropic models (Claude 3.5 Sonnet, Haiku, etc).
    """

    def __init__(self, api_key: Optional[str] = None):
        if not HAS_ANTHROPIC:
            raise ImportError("The 'anthropic' package is not installed.")
        self.client = AsyncAnthropic(api_key=api_key) if api_key else AsyncAnthropic()

    async def generate(self, prompt: str, config: AdapterConfig) -> GenerationResult:
        start_time = time.perf_counter()

        request_kwargs = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

        if config.system_prompt:
            request_kwargs["system"] = config.system_prompt
            
        # Claude does not have a strict `response_format={"type": "json_object"}` 
        # like OpenAI. JSON mode requires prompt engineering and structural hints 
        # (which should be handled by the evaluator/user prompt design).

        try:
            response = await self.client.messages.create(**request_kwargs)
            
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            content = response.content[0].text if response.content else ""
            
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            return GenerationResult(
                content=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
            )

        except Exception as e:
            end_time = time.perf_counter()
            logger.error("Anthropic generation failed: %s", str(e))
            return GenerationResult(
                content="",
                input_tokens=self.count_tokens(prompt),
                output_tokens=0,
                latency_ms=(end_time - start_time) * 1000,
                error=str(e),
            )

    def count_tokens(self, text: str) -> int:
        """
        Anthropic SDK provides a local tokenizer via client.count_tokens()
        However, it is synchronous and relies on HTTP calls in older versions.
        Here we use a rough heuristic as a placeholder if precise local counting 
        before runtime isn't strictly required (the API returns exact usage post-generation).
        """
        return len(text) // 4  

    def get_provider_name(self) -> str:
        return "anthropic"
