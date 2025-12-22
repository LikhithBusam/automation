"""
Groq LLM Wrapper for AutoGen
Provides integration with Groq API for model access
"""

import logging
import os
from typing import Any, Dict, List, Optional

import requests
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseLLM
from langchain_core.outputs import Generation, LLMResult
from pydantic import Field


class GroqLLM(BaseLLM):
    """Custom LLM wrapper for Groq API"""

    model: str = Field(default="mixtral-8x7b-32768")
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2048)
    api_key: str = Field(...)
    api_base: str = Field(default="https://api.groq.com/openai/v1")

    @property
    def _llm_type(self) -> str:
        return "groq"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call Groq API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if stop:
            data["stop"] = stop

        response = requests.post(
            f"{self.api_base}/chat/completions", headers=headers, json=data, timeout=60
        )
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """Generate responses for multiple prompts"""
        generations = []
        for prompt in prompts:
            text = self._call(prompt, stop=stop, run_manager=run_manager, **kwargs)
            generations.append([Generation(text=text)])

        return LLMResult(generations=generations)


def create_groq_llm(
    model: str = "mixtral-8x7b-32768",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    api_key: Optional[str] = None,
    **kwargs,
) -> BaseLLM:
    """
    Create a Groq LLM instance compatible with AutoGen

    Args:
        model: Groq model name (default: mixtral-8x7b-32768)
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        api_key: Groq API key (defaults to GROQ_API_KEY env var)
        **kwargs: Additional arguments to pass to GroqLLM

    Returns:
        BaseLLM instance configured for Groq
    """
    logger = logging.getLogger("models.groq")

    # Get API key from parameter or environment
    groq_api_key = api_key or os.getenv("GROQ_API_KEY")

    if not groq_api_key:
        raise ValueError(
            "Groq API key not found. Please set GROQ_API_KEY environment variable "
            "or pass api_key parameter."
        )

    logger.info(f"Creating Groq LLM with model: {model}")

    # Create GroqLLM instance
    llm = GroqLLM(
        model=model, temperature=temperature, max_tokens=max_tokens, api_key=groq_api_key, **kwargs
    )

    logger.info("Groq LLM created successfully")
    return llm


def get_default_groq_config() -> Dict[str, Any]:
    """
    Get default Groq configuration for different agent types

    Returns:
        Dictionary mapping agent types to their recommended configurations
    """
    return {
        "code_analyzer": {
            "model": "mixtral-8x7b-32768",
            "temperature": 0.3,
            "max_tokens": 4096,
        },
        "documentation": {
            "model": "mixtral-8x7b-32768",
            "temperature": 0.7,
            "max_tokens": 2048,
        },
        "deployment": {
            "model": "mixtral-8x7b-32768",
            "temperature": 0.2,
            "max_tokens": 2048,
        },
        "research": {
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.5,
            "max_tokens": 4096,
        },
        "project_manager": {
            "model": "mixtral-8x7b-32768",
            "temperature": 0.7,
            "max_tokens": 2048,
        },
        "security_auditor": {
            "model": "mixtral-8x7b-32768",
            "temperature": 0.3,
            "max_tokens": 4096,
        },
    }
