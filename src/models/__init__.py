"""
Model Management Module

Features:
- Hugging Face model loading with 4-bit/8-bit quantization
- GPU memory management with configurable fraction
- Model registry with lazy loading
- Prompt caching for repeated contexts
- Fallback to HuggingFace Inference API
- Token usage and cost tracking
"""

from src.models.model_factory import (  # Main factory; Enums; Data classes; Supporting classes; Cost estimation
    MODEL_COSTS_PER_1K,
    AgentModelMapping,
    CachedPrompt,
    DeploymentType,
    LoadedModel,
    ModelFactory,
    ModelRegistry,
    ModelUsageStats,
    PromptCache,
    QuantizationType,
    TokenUsage,
    estimate_cost,
    get_model_factory,
    reset_model_factory,
)

__all__ = [
    # Main factory
    "ModelFactory",
    "get_model_factory",
    "reset_model_factory",
    # Enums
    "DeploymentType",
    "QuantizationType",
    "AgentModelMapping",
    # Data classes
    "TokenUsage",
    "ModelUsageStats",
    "LoadedModel",
    "CachedPrompt",
    # Supporting classes
    "ModelRegistry",
    "PromptCache",
    # Cost estimation
    "estimate_cost",
    "MODEL_COSTS_PER_1K",
]
