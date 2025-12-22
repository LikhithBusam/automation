"""
Gemini LLM Wrapper for AutoGen
Provides integration with Google Gemini API for model access
"""

import os
import logging
from typing import Any, Dict, List, Optional
from langchain_core.language_models import BaseLLM
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.outputs import LLMResult, Generation
from pydantic import Field

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class GeminiLLM(BaseLLM):
    """Custom LLM wrapper for Google Gemini API"""

    model: str = Field(default="gemini-2.0-flash-exp")
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2048)
    api_key: str = Field(...)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if genai is None:
            raise ImportError(
                "google-generativeai is required for GeminiLLM. "
                "Install it with: pip install google-generativeai"
            )
        genai.configure(api_key=self.api_key)
        self._model = genai.GenerativeModel(self.model)

    @property
    def _llm_type(self) -> str:
        return "gemini"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call Gemini API"""
        generation_config = {
            "temperature": self.temperature,
            "max_output_tokens": self.max_tokens,
        }

        if stop:
            generation_config["stop_sequences"] = stop

        response = self._model.generate_content(prompt, generation_config=generation_config)

        return response.text

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


def create_gemini_llm(
    model: str = "gemini-2.0-flash-exp",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    api_key: Optional[str] = None,
    **kwargs,
) -> BaseLLM:
    """
    Create a Gemini LLM instance compatible with AutoGen

    Args:
        model: Gemini model name (default: gemini-2.0-flash-exp)
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
        **kwargs: Additional arguments to pass to GeminiLLM

    Returns:
        BaseLLM instance configured for Gemini
    """
    logger = logging.getLogger("models.gemini")

    # Get API key from parameter or environment
    gemini_api_key = api_key or os.getenv("GEMINI_API_KEY")

    if not gemini_api_key:
        raise ValueError(
            "Gemini API key not found. Please set GEMINI_API_KEY environment variable "
            "or pass api_key parameter."
        )

    logger.info(f"Creating Gemini LLM with model: {model}")

    # Create GeminiLLM instance
    llm = GeminiLLM(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=gemini_api_key,
        **kwargs,
    )

    logger.info("Gemini LLM created successfully")
    return llm


def get_default_gemini_config() -> Dict[str, Any]:
    """
    Get default Gemini configuration for different agent types

    Returns:
        Dictionary mapping agent types to their recommended configurations
    """
    return {
        "code_analyzer": {
            "model": "gemini-2.0-flash-exp",
            "temperature": 0.3,
            "max_tokens": 4096,
        },
        "documentation": {
            "model": "gemini-1.5-pro",
            "temperature": 0.7,
            "max_tokens": 2048,
        },
        "deployment": {
            "model": "gemini-1.5-pro",
            "temperature": 0.2,
            "max_tokens": 2048,
        },
        "research": {
            "model": "gemini-2.0-flash-exp",
            "temperature": 0.5,
            "max_tokens": 4096,
        },
        "project_manager": {
            "model": "gemini-1.5-pro",
            "temperature": 0.7,
            "max_tokens": 2048,
        },
        "security_auditor": {
            "model": "gemini-2.0-flash-exp",
            "temperature": 0.3,
            "max_tokens": 4096,
        },
    }
