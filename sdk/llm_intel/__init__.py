import logging

logger = logging.getLogger("llm_intel")

try:
    from llm_intel.client import InstrumentedAsyncOpenAI as AsyncOpenAI
except ImportError:
    pass
    
try:
    from llm_intel.client import InstrumentedAsyncAnthropic as AsyncAnthropic
except ImportError:
    pass

__all__ = ["AsyncOpenAI", "AsyncAnthropic"]
