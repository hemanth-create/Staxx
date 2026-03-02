import asyncio
import time
from typing import Any, Optional

from llm_intel.instrumentation import (
    extract_openai_metrics,
    extract_anthropic_metrics,
    ship_metrics_async
)

# ---------------------------------------------------------------------------
# OpenAI Wrappers
# ---------------------------------------------------------------------------

try:
    from openai import AsyncOpenAI
    from openai.resources.chat.completions import AsyncCompletions
except ImportError:
    pass
else:
    class InstrumentedAsyncCompletions(AsyncCompletions):
        async def create(self, *args, **kwargs) -> Any:
            start_time = time.perf_counter()
            error_msg = None
            response = None
            
            try:
                response = await super().create(*args, **kwargs)
                return response
            except Exception as e:
                error_msg = str(e)
                raise
            finally:
                latency_ms = (time.perf_counter() - start_time) * 1000
                metrics = extract_openai_metrics(response, latency_ms, error=error_msg)
                
                # Add task tags if passed via custom kwargs (and pop them so OpenAI doesn't choke)
                metrics["task_type"] = kwargs.get("llm_intel_task_type", "unclassified")
                
                # Fire and forget
                asyncio.create_task(ship_metrics_async(metrics))


    class InstrumentedAsyncOpenAI(AsyncOpenAI):
        """Drop-in replacement for openai.AsyncOpenAI"""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Override the chat.completions resource with our instrumented version
            self.chat.completions = InstrumentedAsyncCompletions(self)


# ---------------------------------------------------------------------------
# Anthropic Wrappers
# ---------------------------------------------------------------------------

try:
    from anthropic import AsyncAnthropic
    from anthropic.resources.messages import AsyncMessages
except ImportError:
    pass
else:
    class InstrumentedAsyncMessages(AsyncMessages):
        async def create(self, *args, **kwargs) -> Any:
            start_time = time.perf_counter()
            error_msg = None
            response = None
            
            # Extract custom tags before sending to Anthropic
            task_type = kwargs.pop("llm_intel_task_type", "unclassified")
            
            try:
                response = await super().create(*args, **kwargs)
                return response
            except Exception as e:
                error_msg = str(e)
                raise
            finally:
                latency_ms = (time.perf_counter() - start_time) * 1000
                metrics = extract_anthropic_metrics(response, kwargs, latency_ms, error=error_msg)
                metrics["task_type"] = task_type
                
                # Fire and forget
                asyncio.create_task(ship_metrics_async(metrics))


    class InstrumentedAsyncAnthropic(AsyncAnthropic):
        """Drop-in replacement for anthropic.AsyncAnthropic"""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Override the messages resource with our instrumented version
            self.messages = InstrumentedAsyncMessages(self)
