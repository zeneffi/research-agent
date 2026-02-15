"""
LLM Client - Unified interface for LLM interactions.

Supports multiple providers via LiteLLM.
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Optional

try:
    import litellm
    from litellm import acompletion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    usage: dict
    raw: Any = None


class LLMClient:
    """
    Unified LLM client supporting multiple providers.
    
    Uses LiteLLM for provider abstraction.
    """
    
    # Default models by provider
    DEFAULT_MODELS = {
        "anthropic": "claude-sonnet-4-20250514",
        "openai": "gpt-4o-mini",
        "google": "gemini-1.5-flash",
    }
    
    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ):
        """
        Initialize LLM client.
        
        Args:
            model: Model identifier (e.g., "claude-sonnet-4-20250514", "gpt-4o")
            api_key: API key (uses environment variable if not provided)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        if not LITELLM_AVAILABLE:
            raise ImportError("LiteLLM is required. Install with: pip install litellm")
        
        # Auto-detect model based on available API keys
        if model is None:
            model = self._detect_model()
        
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Store API key as instance variable instead of modifying os.environ
        self.api_key = api_key or self._get_api_key_from_env()
    
    def _detect_model(self) -> str:
        """Detect best available model based on API keys."""
        if os.environ.get("ANTHROPIC_API_KEY"):
            return self.DEFAULT_MODELS["anthropic"]
        elif os.environ.get("OPENAI_API_KEY"):
            return self.DEFAULT_MODELS["openai"]
        elif os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
            return self.DEFAULT_MODELS["google"]
        else:
            # Default to Anthropic
            return self.DEFAULT_MODELS["anthropic"]
    
    def _get_api_key_from_env(self) -> Optional[str]:
        """Get API key from environment based on model provider."""
        if "claude" in self.model.lower():
            return os.environ.get("ANTHROPIC_API_KEY")
        elif "gpt" in self.model.lower():
            return os.environ.get("OPENAI_API_KEY")
        elif "gemini" in self.model.lower():
            return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        return None
    
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """
        Generate completion from LLM.
        
        Args:
            prompt: User prompt
            system: System prompt
            json_mode: Request JSON output
            
        Returns:
            LLMResponse with content and metadata
        """
        messages = []
        
        if system:
            messages.append({"role": "system", "content": system})
        
        messages.append({"role": "user", "content": prompt})
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        
        # Pass API key directly to acompletion instead of modifying os.environ
        if self.api_key:
            kwargs["api_key"] = self.api_key
        
        # Add JSON mode for supported models
        if json_mode:
            if "gpt" in self.model.lower() or "gemini" in self.model.lower():
                kwargs["response_format"] = {"type": "json_object"}
        
        try:
            response = await acompletion(**kwargs)
            
            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            
            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                raw=response,
            )
            
        except Exception as e:
            raise RuntimeError(f"LLM completion failed: {e}")
    
    async def parse_json(
        self,
        prompt: str,
        system: Optional[str] = None,
    ) -> dict:
        """
        Generate JSON response from LLM.
        
        Args:
            prompt: User prompt requesting JSON
            system: System prompt
            
        Returns:
            Parsed JSON dictionary
        """
        response = await self.complete(prompt, system, json_mode=True)
        
        # Parse JSON from response
        content = response.content.strip()
        
        # Handle markdown code blocks
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first and last lines (```json and ```)
            content = "\n".join(lines[1:-1])
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            # Try to extract JSON from the response
            json_match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', content)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Failed to parse JSON from response: {e}")
