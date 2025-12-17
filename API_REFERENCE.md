# API Reference: Gemini & Groq Integration

## Quick Start

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables in .env
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

## Gemini API

### Available Models
- `gemini-2.0-flash-exp` - Latest experimental model, fast and efficient
- `gemini-1.5-pro` - Production-ready, advanced reasoning
- `gemini-1.5-flash` - Fast responses, good for simple tasks

### Usage Example

```python
from src.models.gemini_llm import create_gemini_llm, get_default_gemini_config

# Basic usage
llm = create_gemini_llm(
    model="gemini-2.0-flash-exp",
    temperature=0.7,
    max_tokens=2048
)

# Generate text
response = llm._call("Explain how Python decorators work")
print(response)

# Get default config for agent type
configs = get_default_gemini_config()
code_config = configs["code_analyzer"]
# {'model': 'gemini-2.0-flash-exp', 'temperature': 0.3, 'max_tokens': 4096}
```

### Agent-Specific Configurations

```python
# Code Analysis
llm = create_gemini_llm(
    model="gemini-2.0-flash-exp",
    temperature=0.3,  # Low temp for consistent analysis
    max_tokens=4096
)

# Documentation
llm = create_gemini_llm(
    model="gemini-1.5-pro",
    temperature=0.7,  # Balanced for creative writing
    max_tokens=2048
)

# Security Auditing
llm = create_gemini_llm(
    model="gemini-2.0-flash-exp",
    temperature=0.3,  # Low temp for precise detection
    max_tokens=4096
)
```

## Groq API

### Available Models
- `mixtral-8x7b-32768` - Mixtral model, great for general tasks
- `llama-3.3-70b-versatile` - Llama 3.3, excellent for research
- `llama-3.1-8b-instant` - Fast Llama model for simple tasks

### Usage Example

```python
from src.models.groq_llm import create_groq_llm, get_default_groq_config

# Basic usage
llm = create_groq_llm(
    model="mixtral-8x7b-32768",
    temperature=0.7,
    max_tokens=2048
)

# Generate text
response = llm._call("What are the latest trends in AI?")
print(response)

# Get default config for agent type
configs = get_default_groq_config()
research_config = configs["research"]
# {'model': 'llama-3.3-70b-versatile', 'temperature': 0.5, 'max_tokens': 4096}
```

### Agent-Specific Configurations

```python
# Research
llm = create_groq_llm(
    model="llama-3.3-70b-versatile",
    temperature=0.5,  # Balanced for research
    max_tokens=4096
)

# Routing/Quick Tasks
llm = create_groq_llm(
    model="mixtral-8x7b-32768",
    temperature=0.3,  # Low temp for routing decisions
    max_tokens=1024
)
```

## Model Factory Integration

### Using Model Factory

```python
from src.models.model_factory import ModelFactory

factory = ModelFactory()

# Get Gemini LLM
gemini_llm = factory.get_gemini_llm("code_analyzer")

# Get Groq LLM
groq_llm = factory.get_groq_llm("research")

# Unified interface
llm = factory.get_llm("code_analyzer", provider="gemini")
llm = factory.get_llm("research", provider="groq")
```

## AutoGen Agent Factory Integration

### Creating Agents with Gemini/Groq

```python
from src.autogen_adapters.agent_factory import create_agent_factory

# Create factory
factory = create_agent_factory()

# Create agents (automatically uses Gemini/Groq based on config)
code_analyzer = factory.create_agent("code_analyzer")
# Uses Gemini 2.0 Flash Exp

research_agent = factory.create_agent("research_agent")
# Uses Groq Llama 3.3 70B

# All agents are configured from autogen_agents.yaml
```

## Model Selection Guide

### When to Use Gemini

✅ **Best For:**
- Code analysis and review
- Complex reasoning tasks
- Documentation generation
- Deployment planning
- Project management
- Security auditing

✅ **Advantages:**
- Advanced reasoning capabilities
- Large context window
- Good code understanding
- Multimodal support (future)

⚠️ **Considerations:**
- Rate limits on free tier (15 RPM)
- Slightly slower than Groq

### When to Use Groq

✅ **Best For:**
- Research tasks
- Fast routing decisions
- Quick responses needed
- High-throughput scenarios

✅ **Advantages:**
- Extremely fast inference
- Good for high-volume tasks
- OpenAI-compatible API

⚠️ **Considerations:**
- Limited model selection
- Best for simpler tasks

## Configuration Reference

### autogen_agents.yaml Structure

```yaml
llm_configs:
  code_analysis_config:
    model: "gemini-2.0-flash-exp"
    api_type: "gemini"
    api_key: "${GEMINI_API_KEY}"
    temperature: 0.3
    max_tokens: 4096
    timeout: 120
    cache_seed: 42

  research_config:
    model: "llama-3.3-70b-versatile"
    api_type: "openai"  # Groq uses OpenAI-compatible format
    base_url: "https://api.groq.com/openai/v1"
    api_key: "${GROQ_API_KEY}"
    temperature: 0.5
    max_tokens: 4096
    timeout: 120
    cache_seed: 42
```

### Temperature Guidelines

| Temperature | Use Case | Example |
|-------------|----------|---------|
| 0.1 - 0.3 | Deterministic, factual | Code analysis, security audits |
| 0.4 - 0.6 | Balanced | Research, general tasks |
| 0.7 - 0.9 | Creative | Documentation, brainstorming |
| 1.0+ | Very creative | Not recommended for production |

### Max Tokens Guidelines

| Tokens | Use Case |
|--------|----------|
| 512 - 1024 | Short responses, routing |
| 1024 - 2048 | Standard responses |
| 2048 - 4096 | Detailed analysis |
| 4096+ | Long-form content |

## Error Handling

### Gemini API Errors

```python
from src.models.gemini_llm import create_gemini_llm
import google.generativeai as genai

try:
    llm = create_gemini_llm()
    response = llm._call("test prompt")
except ImportError:
    print("google-generativeai not installed")
except ValueError as e:
    print(f"API key error: {e}")
except Exception as e:
    print(f"Gemini API error: {e}")
```

### Groq API Errors

```python
from src.models.groq_llm import create_groq_llm
import requests

try:
    llm = create_groq_llm()
    response = llm._call("test prompt")
except ValueError as e:
    print(f"API key error: {e}")
except requests.exceptions.HTTPError as e:
    print(f"HTTP error: {e}")
except Exception as e:
    print(f"Groq API error: {e}")
```

## Rate Limits & Best Practices

### Gemini Rate Limits
- **Free Tier:** 15 requests per minute (RPM)
- **Paid Tier:** 360 requests per minute

**Best Practices:**
- Implement exponential backoff
- Cache responses when possible
- Use `cache_seed` in AutoGen for consistency

### Groq Rate Limits
- **Free Tier:** Very generous, check console
- **Paid Tier:** Even higher limits

**Best Practices:**
- Use for high-throughput tasks
- Great for parallel agent workflows

## Performance Comparison

| Metric | Gemini 2.0 Flash | Gemini 1.5 Pro | Groq Mixtral | Groq Llama 3.3 |
|--------|------------------|----------------|--------------|----------------|
| Speed | Fast | Medium | Very Fast | Very Fast |
| Quality | High | Very High | Good | Very Good |
| Context | 1M tokens | 1M tokens | 32K tokens | 128K tokens |
| Cost | Low | Medium | Very Low | Very Low |

## Troubleshooting

### Common Issues

**1. API Key Not Found**
```
ValueError: Gemini API key not found
```
**Solution:** Check `.env` file has `GEMINI_API_KEY` or `GROQ_API_KEY`

**2. Import Error**
```
ImportError: google-generativeai is required
```
**Solution:** `pip install google-generativeai`

**3. Rate Limit Exceeded**
```
429 Too Many Requests
```
**Solution:** Implement retry with exponential backoff

**4. Model Not Found**
```
Model 'gemini-xyz' not found
```
**Solution:** Check available models in Google AI Studio

## Advanced Usage

### Custom LLM Config

```python
from src.models.gemini_llm import GeminiLLM

# Custom configuration
llm = GeminiLLM(
    model="gemini-2.0-flash-exp",
    temperature=0.5,
    max_tokens=3000,
    api_key="your-api-key"
)

# Direct call
response = llm._call("Your prompt here")

# Batch generation
responses = llm._generate([
    "Prompt 1",
    "Prompt 2",
    "Prompt 3"
])
```

### AutoGen Integration

```python
from autogen import AssistantAgent

# Gemini config
config_list = [{
    "model": "gemini-2.0-flash-exp",
    "api_key": "your-gemini-key",
    "api_type": "google"
}]

agent = AssistantAgent(
    name="GeminiAgent",
    llm_config={
        "config_list": config_list,
        "temperature": 0.7
    }
)

# Groq config (OpenAI-compatible)
config_list = [{
    "model": "mixtral-8x7b-32768",
    "api_key": "your-groq-key",
    "base_url": "https://api.groq.com/openai/v1",
    "api_type": "openai"
}]

agent = AssistantAgent(
    name="GroqAgent",
    llm_config={
        "config_list": config_list,
        "temperature": 0.7
    }
)
```

## Resources

- **Gemini API Docs:** https://ai.google.dev/docs
- **Groq API Docs:** https://console.groq.com/docs
- **AutoGen Docs:** https://microsoft.github.io/autogen/
- **Google AI Studio:** https://makersuite.google.com/app/apikey
- **Groq Console:** https://console.groq.com/

---
**Last Updated:** December 8, 2025
