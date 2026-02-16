"""
Retry utilities - Exponential backoff and fallback mechanisms.

Provides robust error handling for browser operations.
"""

import asyncio
import random
import urllib.parse
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, TypeVar

T = TypeVar("T")


def calculate_backoff_delay(
    attempt: int,
    base_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 30.0,
) -> float:
    """
    Calculate exponential backoff delay.
    
    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        exponential_base: Base for exponential calculation
        max_delay: Maximum delay cap
        
    Returns:
        Delay in seconds
    """
    delay = base_delay * (exponential_base ** attempt)
    return min(delay, max_delay)


async def backoff_sleep(
    attempt: int,
    base_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 30.0,
) -> None:
    """
    Sleep with exponential backoff.
    
    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        exponential_base: Base for exponential calculation
        max_delay: Maximum delay cap
    """
    delay = calculate_backoff_delay(attempt, base_delay, exponential_base, max_delay)
    await asyncio.sleep(delay)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: float = 0.1


class RetryError(Exception):
    """Raised when all retries are exhausted."""
    
    def __init__(self, message: str, last_error: Optional[Exception] = None):
        super().__init__(message)
        self.last_error = last_error


async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    **kwargs: Any,
) -> T:
    """
    Execute async function with exponential backoff retry.
    
    Args:
        func: Async function to execute
        *args: Positional arguments for func
        config: Retry configuration
        on_retry: Callback on each retry (receives attempt number and exception)
        **kwargs: Keyword arguments for func
        
    Returns:
        Result of successful function execution
        
    Raises:
        RetryError: When all retries are exhausted
    """
    config = config or RetryConfig()
    last_error: Optional[Exception] = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            
            if attempt >= config.max_retries:
                break
            
            # Calculate delay with exponential backoff
            delay = min(
                config.base_delay * (config.exponential_base ** attempt),
                config.max_delay,
            )
            
            # Add jitter
            jitter = delay * config.jitter * random.uniform(-1, 1)
            delay = max(0, delay + jitter)
            
            if on_retry:
                on_retry(attempt + 1, e)
            
            await asyncio.sleep(delay)
    
    raise RetryError(
        f"Failed after {config.max_retries + 1} attempts",
        last_error=last_error,
    )


class FallbackChain:
    """
    Chain of fallback functions to try in order.
    
    Executes functions in sequence until one succeeds.
    """
    
    def __init__(self):
        self._fallbacks: list[Callable[..., Awaitable[Any]]] = []
    
    def add(self, func: Callable[..., Awaitable[Any]]) -> "FallbackChain":
        """Add a fallback function to the chain."""
        self._fallbacks.append(func)
        return self
    
    async def execute(
        self,
        *args: Any,
        on_fallback: Optional[Callable[[int, Exception], None]] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Execute fallback chain.
        
        Args:
            *args: Arguments passed to each fallback
            on_fallback: Callback when falling back (receives index and exception)
            **kwargs: Keyword arguments passed to each fallback
            
        Returns:
            Result from first successful fallback
            
        Raises:
            RetryError: When all fallbacks fail
        """
        last_error: Optional[Exception] = None
        
        for i, func in enumerate(self._fallbacks):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                if on_fallback and i < len(self._fallbacks) - 1:
                    on_fallback(i, e)
        
        raise RetryError(
            f"All {len(self._fallbacks)} fallbacks failed",
            last_error=last_error,
        )


# Search engine fallback URLs
SEARCH_ENGINE_FALLBACKS = {
    "duckduckgo": "https://duckduckgo.com/?q={query}",
    "bing": "https://www.bing.com/search?q={query}",
    "google": "https://www.google.com/search?q={query}",
    "startpage": "https://www.startpage.com/sp/search?query={query}",
}


def get_fallback_search_url(query: str, failed_engine: str) -> Optional[str]:
    """
    Get fallback search URL when primary engine fails.
    
    Args:
        query: Search query
        failed_engine: Engine that failed
        
    Returns:
        Alternative search URL or None if no fallback available
    """
    # Order of preference
    preference_order = ["duckduckgo", "bing", "google", "startpage"]
    
    for engine in preference_order:
        if engine != failed_engine:
            template = SEARCH_ENGINE_FALLBACKS[engine]
            encoded_query = urllib.parse.quote_plus(query)
            return template.format(query=encoded_query)
    
    return None
