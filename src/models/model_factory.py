"""
Model Factory - Handles Hugging Face model loading and management
Implements hybrid deployment strategy (local vs API) with optimization

Features:
- Local and API-based inference
- 4-bit and 8-bit quantization using BitsAndBytes
- GPU memory management with configurable fraction
- Model registry with lazy loading
- Prompt caching for repeated contexts
- Fallback to HuggingFace Inference API
- Token usage and cost tracking
"""

import gc
import hashlib
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import huggingface_hub
import torch
from huggingface_hub import InferenceClient
from langchain_community.llms import HuggingFaceHub, HuggingFacePipeline
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    GenerationConfig,
    PreTrainedModel,
    PreTrainedTokenizer,
    pipeline,
)

from src.models.gemini_llm import create_gemini_llm, get_default_gemini_config
from src.models.groq_llm import create_groq_llm, get_default_groq_config

# Try to import bitsandbytes for quantization
try:
    import bitsandbytes as bnb

    HAS_BITSANDBYTES = True
except ImportError:
    HAS_BITSANDBYTES = False


# =============================================================================
# ENUMS AND CONFIGURATION
# =============================================================================


class DeploymentType(str, Enum):
    """Model deployment types"""

    LOCAL = "local"
    HF_API = "hf_api"
    HYBRID = "hybrid"  # Try local first, fallback to API


class QuantizationType(str, Enum):
    """Quantization options for local models"""

    NONE = "none"
    INT8 = "8bit"
    INT4 = "4bit"
    FP16 = "fp16"
    BF16 = "bf16"


class AgentModelMapping(str, Enum):
    """Default model types for each agent"""

    CODE_ANALYZER = "code_analyzer"
    DOCUMENTATION = "documentation"
    DEPLOYMENT = "deployment"
    RESEARCH = "research"
    PROJECT_MANAGER = "project_manager"
    DEFAULT = "default"


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class TokenUsage:
    """Track token usage for a single request"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    model_name: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ModelUsageStats:
    """Comprehensive model usage statistics"""

    total_requests: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_estimated_cost: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    api_fallbacks: int = 0
    errors: int = 0
    avg_latency_ms: float = 0.0
    _latency_samples: List[float] = field(default_factory=list)
    by_model: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def record_request(
        self,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        cost: float = 0.0,
        cache_hit: bool = False,
        api_fallback: bool = False,
    ):
        """Record a model request"""
        self.total_requests += 1
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_tokens += prompt_tokens + completion_tokens
        self.total_estimated_cost += cost

        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

        if api_fallback:
            self.api_fallbacks += 1

        # Update latency
        self._latency_samples.append(latency_ms)
        if len(self._latency_samples) > 1000:
            self._latency_samples = self._latency_samples[-1000:]
        self.avg_latency_ms = sum(self._latency_samples) / len(self._latency_samples)

        # Per-model stats
        if model_name not in self.by_model:
            self.by_model[model_name] = {
                "requests": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "cost": 0.0,
            }
        self.by_model[model_name]["requests"] += 1
        self.by_model[model_name]["prompt_tokens"] += prompt_tokens
        self.by_model[model_name]["completion_tokens"] += completion_tokens
        self.by_model[model_name]["cost"] += cost

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "total_estimated_cost": round(self.total_estimated_cost, 6),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "api_fallbacks": self.api_fallbacks,
            "errors": self.errors,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "by_model": self.by_model,
        }


@dataclass
class CachedPrompt:
    """Cached prompt response"""

    prompt_hash: str
    response: str
    model_name: str
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0


@dataclass
class LoadedModel:
    """Container for loaded model with metadata"""

    model: Any  # Can be pipeline, model, or LLM wrapper
    tokenizer: Optional[PreTrainedTokenizer]
    model_name: str
    deployment_type: DeploymentType
    quantization: QuantizationType
    loaded_at: datetime
    last_used_at: datetime
    use_count: int = 0
    memory_footprint_gb: float = 0.0


# =============================================================================
# COST ESTIMATION
# =============================================================================

# Approximate costs per 1K tokens (varies by model and provider)
MODEL_COSTS_PER_1K = {
    # Local models (electricity cost approximation)
    "local": {"prompt": 0.0001, "completion": 0.0002},
    # HuggingFace Inference API (free tier has limits)
    "hf_api": {"prompt": 0.0005, "completion": 0.001},
    # Specific model overrides
    "codellama/CodeLlama-7b-hf": {"prompt": 0.0001, "completion": 0.0002},
    "mistralai/Mistral-7B-v0.1": {"prompt": 0.0001, "completion": 0.0002},
}


def estimate_cost(
    model_name: str, prompt_tokens: int, completion_tokens: int, deployment_type: DeploymentType
) -> float:
    """Estimate cost for token usage"""
    if model_name in MODEL_COSTS_PER_1K:
        costs = MODEL_COSTS_PER_1K[model_name]
    else:
        costs = MODEL_COSTS_PER_1K.get(
            "local" if deployment_type == DeploymentType.LOCAL else "hf_api"
        )

    prompt_cost = (prompt_tokens / 1000) * costs["prompt"]
    completion_cost = (completion_tokens / 1000) * costs["completion"]
    return prompt_cost + completion_cost


# =============================================================================
# PROMPT CACHE
# =============================================================================


class PromptCache:
    """
    LRU cache for prompt responses with TTL.
    Reduces redundant inference for repeated prompts.
    """

    def __init__(self, max_size: int = 1000, default_ttl_seconds: int = 3600):
        self.max_size = max_size
        self.default_ttl = timedelta(seconds=default_ttl_seconds)
        self._cache: Dict[str, CachedPrompt] = {}
        self._lock = threading.RLock()

    def _hash_prompt(self, prompt: str, model_name: str, params: Dict[str, Any]) -> str:
        """Generate hash for prompt + model + params"""
        key_parts = [prompt, model_name, str(sorted(params.items()))]
        return hashlib.sha256("|".join(key_parts).encode()).hexdigest()[:32]

    def get(self, prompt: str, model_name: str, params: Dict[str, Any]) -> Optional[str]:
        """Get cached response if available and not expired"""
        with self._lock:
            hash_key = self._hash_prompt(prompt, model_name, params)

            if hash_key not in self._cache:
                return None

            cached = self._cache[hash_key]

            # Check expiry
            if datetime.utcnow() > cached.expires_at:
                del self._cache[hash_key]
                return None

            # Update hit count
            cached.hit_count += 1
            return cached.response

    def put(
        self,
        prompt: str,
        model_name: str,
        params: Dict[str, Any],
        response: str,
        ttl_seconds: Optional[int] = None,
    ):
        """Cache a prompt response"""
        with self._lock:
            hash_key = self._hash_prompt(prompt, model_name, params)

            # Evict if at capacity (remove oldest)
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
                del self._cache[oldest_key]

            ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else self.default_ttl

            self._cache[hash_key] = CachedPrompt(
                prompt_hash=hash_key,
                response=response,
                model_name=model_name,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + ttl,
            )

    def clear(self):
        """Clear all cached prompts"""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_hits = sum(c.hit_count for c in self._cache.values())
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "total_hits": total_hits,
            }


# =============================================================================
# MODEL REGISTRY
# =============================================================================


class ModelRegistry:
    """
    Registry of available models with lazy loading support.
    Maps agent types to model configurations.
    """

    # Default model recommendations per agent type
    DEFAULT_MODELS = {
        AgentModelMapping.CODE_ANALYZER: {
            "primary": "codellama/CodeLlama-7b-hf",
            "alternative": "Salesforce/codegen-350M-mono",
            "quantization": "4bit",
            "max_tokens": 2048,
            "temperature": 0.3,
        },
        AgentModelMapping.DOCUMENTATION: {
            "primary": "mistralai/Mistral-7B-v0.1",
            "alternative": "google/flan-t5-base",
            "quantization": "4bit",
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        AgentModelMapping.DEPLOYMENT: {
            "primary": "codellama/CodeLlama-7b-hf",
            "alternative": "bigcode/starcoder",
            "quantization": "4bit",
            "max_tokens": 2048,
            "temperature": 0.2,
        },
        AgentModelMapping.RESEARCH: {
            "primary": "mistralai/Mistral-7B-v0.1",
            "alternative": "google/flan-t5-large",
            "quantization": "4bit",
            "max_tokens": 4096,
            "temperature": 0.5,
        },
        AgentModelMapping.PROJECT_MANAGER: {
            "primary": "mistralai/Mistral-7B-v0.1",
            "alternative": "google/flan-t5-base",
            "quantization": "4bit",
            "max_tokens": 2048,
            "temperature": 0.7,
        },
        AgentModelMapping.DEFAULT: {
            "primary": "google/flan-t5-base",
            "alternative": "facebook/opt-125m",
            "quantization": "none",
            "max_tokens": 1024,
            "temperature": 0.7,
        },
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._custom_models: Dict[str, Dict[str, Any]] = {}

        # Load custom models from config
        for model_type, model_config in config.get("models", {}).items():
            self._custom_models[model_type] = model_config

    def get_model_config(self, agent_type: str) -> Dict[str, Any]:
        """Get model configuration for an agent type"""
        # Check custom config first
        if agent_type in self._custom_models:
            return self._custom_models[agent_type]

        # Fall back to defaults
        try:
            mapping = AgentModelMapping(agent_type)
            return self.DEFAULT_MODELS.get(mapping, self.DEFAULT_MODELS[AgentModelMapping.DEFAULT])
        except ValueError:
            return self.DEFAULT_MODELS[AgentModelMapping.DEFAULT]

    def register_model(self, model_type: str, config: Dict[str, Any]):
        """Register a custom model configuration"""
        self._custom_models[model_type] = config

    def list_available(self) -> List[str]:
        """List all available model types"""
        default_types = [m.value for m in AgentModelMapping]
        custom_types = list(self._custom_models.keys())
        return list(set(default_types + custom_types))


# =============================================================================
# MODEL FACTORY - MAIN CLASS
# =============================================================================


class ModelFactory:
    """
    Factory for creating and managing Hugging Face models

    Features:
    - Local and API-based inference
    - 4-bit and 8-bit quantization using BitsAndBytes
    - GPU memory management with configurable fraction
    - Model registry with lazy loading
    - Prompt caching for repeated contexts
    - Fallback to HuggingFace Inference API
    - Token usage and cost tracking
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("models.factory")

        # Model registry
        self.registry = ModelRegistry(config)

        # Loaded models cache
        self.loaded_models: Dict[str, LoadedModel] = {}
        self._load_lock = threading.RLock()

        # HuggingFace configuration
        self.hf_token = config.get("huggingface", {}).get("api_token") or os.environ.get(
            "HUGGINGFACE_TOKEN"
        )
        self.cache_dir = config.get("huggingface", {}).get("cache_dir", "./models_cache")

        # Login to HuggingFace if token provided
        if self.hf_token:
            try:
                huggingface_hub.login(token=self.hf_token, add_to_git_credential=False)
                self.logger.info("HuggingFace authentication successful")
            except Exception as e:
                self.logger.warning(f"HuggingFace login failed: {e}")

        # GPU configuration
        self.gpu_enabled = config.get("performance", {}).get("gpu_enabled", False)
        self.gpu_memory_fraction = config.get("performance", {}).get("gpu_memory_fraction", 0.8)
        self.device = self._detect_device()

        # Configure GPU memory if available
        if self.gpu_enabled and torch.cuda.is_available():
            self._configure_gpu_memory()

        # Prompt cache
        cache_config = config.get("prompt_cache", {})
        self.prompt_cache = PromptCache(
            max_size=cache_config.get("max_size", 1000),
            default_ttl_seconds=cache_config.get("ttl_seconds", 3600),
        )

        # Inference API client for fallback
        self.inference_client: Optional[InferenceClient] = None
        if self.hf_token:
            self.inference_client = InferenceClient(token=self.hf_token)

        # Usage statistics
        self.stats = ModelUsageStats()

        # Max models to keep loaded
        self.max_loaded_models = config.get("performance", {}).get("max_loaded_models", 3)

        self.logger.info(f"ModelFactory initialized (device: {self.device})")

    def _detect_device(self) -> str:
        """Detect and return the best available device"""
        if self.gpu_enabled:
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"  # Apple Silicon
        return "cpu"

    def _configure_gpu_memory(self):
        """Configure GPU memory usage"""
        if not torch.cuda.is_available():
            return

        try:
            # Set memory fraction for each GPU
            for i in range(torch.cuda.device_count()):
                total_memory = torch.cuda.get_device_properties(i).total_memory
                fraction_bytes = int(total_memory * self.gpu_memory_fraction)
                torch.cuda.set_per_process_memory_fraction(self.gpu_memory_fraction, device=i)

            self.logger.info(f"GPU memory configured: {self.gpu_memory_fraction * 100}% of total")
        except Exception as e:
            self.logger.warning(f"Failed to configure GPU memory: {e}")

    # =========================================================================
    # CORE METHODS: load_model, get_model, generate, clear_cache
    # =========================================================================

    def load_model(
        self,
        model_name: str,
        quantization: Union[str, QuantizationType] = QuantizationType.INT4,
        force_reload: bool = False,
        deployment_type: DeploymentType = DeploymentType.LOCAL,
    ) -> LoadedModel:
        """
        Load a model with specified optimization.

        Args:
            model_name: HuggingFace model name/path
            quantization: Quantization type (4bit, 8bit, fp16, bf16, none)
            force_reload: Force reload even if cached
            deployment_type: LOCAL or HF_API

        Returns:
            LoadedModel instance
        """
        with self._load_lock:
            cache_key = f"{model_name}:{quantization}"

            # Check cache
            if not force_reload and cache_key in self.loaded_models:
                loaded = self.loaded_models[cache_key]
                loaded.last_used_at = datetime.utcnow()
                loaded.use_count += 1
                self.logger.info(f"Using cached model: {model_name}")
                return loaded

            # Ensure we have room for a new model
            self._ensure_model_capacity()

            # Convert string to enum if needed
            if isinstance(quantization, str):
                quantization = QuantizationType(quantization)

            self.logger.info(f"Loading model: {model_name} ({quantization.value})")

            try:
                if deployment_type == DeploymentType.LOCAL:
                    model, tokenizer = self._load_local_model(model_name, quantization)
                    memory_gb = self._estimate_model_memory(model)
                else:
                    model = self._create_api_client(model_name)
                    tokenizer = None
                    memory_gb = 0.0

                loaded = LoadedModel(
                    model=model,
                    tokenizer=tokenizer,
                    model_name=model_name,
                    deployment_type=deployment_type,
                    quantization=quantization,
                    loaded_at=datetime.utcnow(),
                    last_used_at=datetime.utcnow(),
                    use_count=1,
                    memory_footprint_gb=memory_gb,
                )

                self.loaded_models[cache_key] = loaded
                self.logger.info(f"Model loaded: {model_name} ({memory_gb:.2f} GB)")
                return loaded

            except Exception as e:
                self.logger.error(f"Failed to load model {model_name}: {e}")
                self.stats.errors += 1
                raise

    def _load_local_model(
        self, model_name: str, quantization: QuantizationType
    ) -> Tuple[Any, PreTrainedTokenizer]:
        """Load a local model with quantization"""
        # Configure quantization
        bnb_config = None
        torch_dtype = torch.float32

        if self.gpu_enabled and HAS_BITSANDBYTES:
            if quantization == QuantizationType.INT4:
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                )
                torch_dtype = torch.float16
            elif quantization == QuantizationType.INT8:
                bnb_config = BitsAndBytesConfig(load_in_8bit=True, llm_int8_threshold=6.0)
                torch_dtype = torch.float16
            elif quantization == QuantizationType.FP16:
                torch_dtype = torch.float16
            elif quantization == QuantizationType.BF16:
                torch_dtype = torch.bfloat16

        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            model_name, cache_dir=self.cache_dir, trust_remote_code=True, padding_side="left"
        )

        # Set pad token if not set
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # Load model
        model_kwargs = {
            "cache_dir": self.cache_dir,
            "trust_remote_code": True,
            "torch_dtype": torch_dtype,
        }

        if bnb_config:
            model_kwargs["quantization_config"] = bnb_config

        if self.gpu_enabled:
            model_kwargs["device_map"] = "auto"

        model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)

        return model, tokenizer

    def _create_api_client(self, model_name: str) -> InferenceClient:
        """Create HuggingFace Inference API client"""
        if not self.hf_token:
            raise ValueError("HuggingFace API token required for API deployment")
        return InferenceClient(model=model_name, token=self.hf_token)

    def get_model(self, agent_type: str) -> LoadedModel:
        """
        Get or create a model instance for an agent type.
        Uses lazy loading with model registry.

        Args:
            agent_type: Type of agent (code_analyzer, documentation, etc.)

        Returns:
            LoadedModel instance
        """
        # Get model configuration from registry
        model_config = self.registry.get_model_config(agent_type)
        model_name = model_config.get("primary")
        quantization = model_config.get("quantization", "4bit")
        deployment = model_config.get("deployment", "local")

        try:
            return self.load_model(
                model_name=model_name,
                quantization=quantization,
                deployment_type=DeploymentType(deployment),
            )
        except Exception as e:
            # Try alternative model
            alternative = model_config.get("alternative")
            if alternative and alternative != model_name:
                self.logger.warning(f"Primary model failed, trying alternative: {alternative}")
                return self.load_model(
                    model_name=alternative,
                    quantization=quantization,
                    deployment_type=DeploymentType(deployment),
                )
            raise

    def get_gemini_llm(self, agent_type: str = "default"):
        """
        Get a Gemini LLM instance for an agent type.
        This is a lightweight alternative to loading local models.

        Args:
            agent_type: Type of agent (code_analyzer, documentation, etc.)

        Returns:
            BaseLLM instance configured for Gemini
        """
        # Get Gemini configuration for this agent type
        gemini_configs = get_default_gemini_config()
        config = gemini_configs.get(
            agent_type,
            {
                "model": "gemini-2.0-flash-exp",
                "temperature": 0.7,
                "max_tokens": 2048,
            },
        )

        self.logger.info(f"Creating Gemini LLM for agent: {agent_type}")

        return create_gemini_llm(
            model=config.get("model"),
            temperature=config.get("temperature"),
            max_tokens=config.get("max_tokens"),
        )

    def get_groq_llm(self, agent_type: str = "default"):
        """
        Get a Groq LLM instance for an agent type.
        This is a lightweight alternative to loading local models.

        Args:
            agent_type: Type of agent (code_analyzer, documentation, etc.)

        Returns:
            BaseLLM instance configured for Groq
        """
        # Get Groq configuration for this agent type
        groq_configs = get_default_groq_config()
        config = groq_configs.get(
            agent_type,
            {
                "model": "mixtral-8x7b-32768",
                "temperature": 0.7,
                "max_tokens": 2048,
            },
        )

        self.logger.info(f"Creating Groq LLM for agent: {agent_type}")

        return create_groq_llm(
            model=config.get("model"),
            temperature=config.get("temperature"),
            max_tokens=config.get("max_tokens"),
        )

    def get_llm(self, agent_type: str = "default", provider: str = "gemini"):
        """
        Get an LLM instance for an agent type with the specified provider.

        Args:
            agent_type: Type of agent (code_analyzer, documentation, etc.)
            provider: LLM provider to use ("gemini" or "groq")

        Returns:
            BaseLLM instance configured for the specified provider
        """
        if provider == "gemini":
            return self.get_gemini_llm(agent_type)
        elif provider == "groq":
            return self.get_groq_llm(agent_type)
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'gemini' or 'groq'.")

    def generate(
        self,
        model: Union[str, LoadedModel],
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.95,
        repetition_penalty: float = 1.15,
        stop_sequences: Optional[List[str]] = None,
        use_cache: bool = True,
        stream: bool = False,
        **kwargs,
    ) -> Union[str, Any]:
        """
        Unified inference method for all model types.

        Args:
            model: Model name, agent type, or LoadedModel
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            repetition_penalty: Repetition penalty
            stop_sequences: Stop sequences for generation
            use_cache: Whether to use prompt cache
            stream: Whether to stream output (API only)

        Returns:
            Generated text or stream
        """
        start_time = time.time()

        # Resolve model
        if isinstance(model, str):
            loaded_model = self.get_model(model)
        else:
            loaded_model = model

        # Check prompt cache
        cache_params = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }

        if use_cache:
            cached_response = self.prompt_cache.get(prompt, loaded_model.model_name, cache_params)
            if cached_response:
                latency_ms = (time.time() - start_time) * 1000
                self.stats.record_request(
                    model_name=loaded_model.model_name,
                    prompt_tokens=0,
                    completion_tokens=0,
                    latency_ms=latency_ms,
                    cache_hit=True,
                )
                return cached_response

        try:
            # Generate based on deployment type
            if loaded_model.deployment_type == DeploymentType.LOCAL:
                response, token_usage = self._generate_local(
                    loaded_model,
                    prompt,
                    max_tokens,
                    temperature,
                    top_p,
                    repetition_penalty,
                    stop_sequences,
                )
            else:
                response, token_usage = self._generate_api(
                    loaded_model, prompt, max_tokens, temperature, top_p, stop_sequences, stream
                )

            # Cache response
            if use_cache and not stream:
                self.prompt_cache.put(prompt, loaded_model.model_name, cache_params, response)

            # Update stats
            latency_ms = (time.time() - start_time) * 1000
            cost = estimate_cost(
                loaded_model.model_name,
                token_usage.prompt_tokens,
                token_usage.completion_tokens,
                loaded_model.deployment_type,
            )

            self.stats.record_request(
                model_name=loaded_model.model_name,
                prompt_tokens=token_usage.prompt_tokens,
                completion_tokens=token_usage.completion_tokens,
                latency_ms=latency_ms,
                cost=cost,
                cache_hit=False,
            )

            return response

        except Exception as e:
            self.logger.error(f"Generation failed: {e}")

            # Try API fallback if local fails
            if loaded_model.deployment_type == DeploymentType.LOCAL and self.inference_client:
                self.logger.info("Falling back to HuggingFace Inference API")
                self.stats.api_fallbacks += 1
                return self._generate_api_fallback(
                    loaded_model.model_name, prompt, max_tokens, temperature, top_p, stop_sequences
                )

            self.stats.errors += 1
            raise

    def _generate_local(
        self,
        loaded_model: LoadedModel,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        repetition_penalty: float,
        stop_sequences: Optional[List[str]],
    ) -> Tuple[str, TokenUsage]:
        """Generate using local model"""
        model = loaded_model.model
        tokenizer = loaded_model.tokenizer

        # Tokenize input
        inputs = tokenizer(
            prompt, return_tensors="pt", padding=True, truncation=True, max_length=2048
        )

        if self.device == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        prompt_tokens = inputs["input_ids"].shape[1]

        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature if temperature > 0 else 1.0,
                top_p=top_p,
                repetition_penalty=repetition_penalty,
                do_sample=temperature > 0,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

        # Decode output
        generated_ids = outputs[0][inputs["input_ids"].shape[1] :]
        response = tokenizer.decode(generated_ids, skip_special_tokens=True)

        # Handle stop sequences
        if stop_sequences:
            for stop in stop_sequences:
                if stop in response:
                    response = response.split(stop)[0]

        completion_tokens = len(generated_ids)

        return response.strip(), TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            model_name=loaded_model.model_name,
        )

    def _generate_api(
        self,
        loaded_model: LoadedModel,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        stop_sequences: Optional[List[str]],
        stream: bool,
    ) -> Tuple[str, TokenUsage]:
        """Generate using HuggingFace Inference API"""
        client = loaded_model.model

        if stream:
            # Return generator for streaming
            return client.text_generation(
                prompt,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop_sequences=stop_sequences,
                stream=True,
            ), TokenUsage(model_name=loaded_model.model_name)

        response = client.text_generation(
            prompt,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop_sequences=stop_sequences,
            details=True,
        )

        # Extract token counts if available
        prompt_tokens = len(prompt.split()) * 1.3  # Rough estimate
        completion_tokens = (
            response.details.generated_tokens
            if hasattr(response, "details")
            else len(response.generated_text.split()) * 1.3
        )

        return response.generated_text, TokenUsage(
            prompt_tokens=int(prompt_tokens),
            completion_tokens=int(completion_tokens),
            total_tokens=int(prompt_tokens + completion_tokens),
            model_name=loaded_model.model_name,
        )

    def _generate_api_fallback(
        self,
        model_name: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        stop_sequences: Optional[List[str]],
    ) -> str:
        """Fallback to HuggingFace Inference API"""
        if not self.inference_client:
            raise RuntimeError("No inference client available for fallback")

        response = self.inference_client.text_generation(
            prompt,
            model=model_name,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop_sequences=stop_sequences,
        )

        return response

    def clear_cache(self, model_type: Optional[str] = None):
        """
        Clear model cache to free GPU/CPU memory.

        Args:
            model_type: Specific model to clear, or None for all
        """
        with self._load_lock:
            if model_type:
                # Clear specific model
                keys_to_remove = [k for k in self.loaded_models if model_type in k]
                for key in keys_to_remove:
                    self._unload_model(key)
            else:
                # Clear all models
                for key in list(self.loaded_models.keys()):
                    self._unload_model(key)

            # Clear GPU memory
            if self.device == "cuda":
                torch.cuda.empty_cache()

            # Force garbage collection
            gc.collect()

            self.logger.info(f"Cache cleared: {model_type or 'all models'}")

    def _unload_model(self, cache_key: str):
        """Unload a specific model"""
        if cache_key in self.loaded_models:
            loaded = self.loaded_models[cache_key]

            # Delete model and tokenizer
            del loaded.model
            if loaded.tokenizer:
                del loaded.tokenizer

            del self.loaded_models[cache_key]
            self.logger.debug(f"Unloaded model: {cache_key}")

    def _ensure_model_capacity(self):
        """Ensure we have capacity for a new model"""
        while len(self.loaded_models) >= self.max_loaded_models:
            # Find least recently used model
            lru_key = min(
                self.loaded_models.keys(), key=lambda k: self.loaded_models[k].last_used_at
            )
            self._unload_model(lru_key)

            if self.device == "cuda":
                torch.cuda.empty_cache()

    def _estimate_model_memory(self, model: Any) -> float:
        """Estimate model memory footprint in GB"""
        try:
            param_count = sum(p.numel() for p in model.parameters())
            # Rough estimate: 2 bytes per param for fp16, 1 byte for int8, 0.5 for int4
            bytes_per_param = 2  # Assuming fp16
            memory_bytes = param_count * bytes_per_param
            return memory_bytes / (1024**3)
        except:
            return 0.0

    # =========================================================================
    # STATISTICS AND MONITORING
    # =========================================================================

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics"""
        return {
            "model_usage": self.stats.to_dict(),
            "prompt_cache": self.prompt_cache.get_stats(),
            "memory": self.get_memory_usage(),
            "loaded_models": {
                k: {
                    "model_name": v.model_name,
                    "deployment_type": v.deployment_type.value,
                    "quantization": v.quantization.value,
                    "loaded_at": v.loaded_at.isoformat(),
                    "last_used_at": v.last_used_at.isoformat(),
                    "use_count": v.use_count,
                    "memory_gb": round(v.memory_footprint_gb, 2),
                }
                for k, v in self.loaded_models.items()
            },
        }

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage statistics"""
        stats = {
            "loaded_models_count": len(self.loaded_models),
            "device": self.device,
            "gpu_enabled": self.gpu_enabled,
        }

        if self.device == "cuda" and torch.cuda.is_available():
            stats["gpu_memory_allocated_gb"] = round(torch.cuda.memory_allocated() / (1024**3), 2)
            stats["gpu_memory_reserved_gb"] = round(torch.cuda.memory_reserved() / (1024**3), 2)
            stats["gpu_memory_total_gb"] = round(
                torch.cuda.get_device_properties(0).total_memory / (1024**3), 2
            )
            stats["gpu_memory_fraction"] = self.gpu_memory_fraction

        return stats

    def get_token_usage(self) -> Dict[str, Any]:
        """Get token usage and cost summary"""
        return {
            "total_prompt_tokens": self.stats.total_prompt_tokens,
            "total_completion_tokens": self.stats.total_completion_tokens,
            "total_tokens": self.stats.total_tokens,
            "total_estimated_cost": round(self.stats.total_estimated_cost, 6),
            "by_model": self.stats.by_model,
        }

    # =========================================================================
    # LIFECYCLE MANAGEMENT
    # =========================================================================

    def optimize_memory(self):
        """Optimize memory usage by unloading unused models"""
        with self._load_lock:
            # Sort by last used time
            sorted_models = sorted(self.loaded_models.items(), key=lambda x: x[1].last_used_at)

            # Keep only most recently used up to max
            models_to_keep = max(1, self.max_loaded_models - 1)
            for key, _ in sorted_models[:-models_to_keep]:
                self._unload_model(key)

            if self.device == "cuda":
                torch.cuda.empty_cache()

            gc.collect()
            self.logger.info("Memory optimization complete")

    def shutdown(self):
        """Shutdown model factory and cleanup all resources"""
        self.logger.info("Shutting down model factory")

        # Clear all models
        self.clear_cache()

        # Clear prompt cache
        self.prompt_cache.clear()

        self.logger.info("Model factory shutdown complete")

    # =========================================================================
    # LEGACY COMPATIBILITY
    # =========================================================================

    def unload_model(self, model_type: str) -> bool:
        """Legacy method - unload a model from cache"""
        try:
            self.clear_cache(model_type)
            return True
        except Exception:
            return False


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_model_factory_instance: Optional[ModelFactory] = None
_instance_lock = threading.Lock()


def get_model_factory(config: Optional[Dict[str, Any]] = None) -> ModelFactory:
    """Get or create the singleton ModelFactory instance"""
    global _model_factory_instance

    with _instance_lock:
        if _model_factory_instance is None:
            if config is None:
                raise ValueError("Config required for first initialization")
            _model_factory_instance = ModelFactory(config)

    return _model_factory_instance


def reset_model_factory():
    """Reset the singleton instance (for testing)"""
    global _model_factory_instance
    with _instance_lock:
        if _model_factory_instance:
            _model_factory_instance.shutdown()
        _model_factory_instance = None
