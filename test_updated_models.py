"""
Test script to verify updated Groq models work correctly
"""
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("=" * 70)
print("Testing Updated Groq Models")
print("=" * 70)
print()

groq_key = os.getenv("GROQ_API_KEY")

# Test both models that are being used in the config
models_to_test = [
    ("llama-3.3-70b-versatile", "Research Agent Model"),
    ("llama-3.1-8b-instant", "Routing/Manager Model"),
]

for model_id, description in models_to_test:
    print(f"Testing: {description} ({model_id})")
    print("-" * 70)

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=groq_key,
            base_url="https://api.groq.com/openai/v1"
        )

        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "Say 'Hello' in one word."}],
            max_tokens=10
        )

        result = response.choices[0].message.content
        print(f"  [OK] {description} working!")
        print(f"  Response: {result}")

    except Exception as e:
        print(f"  [FAIL] {description} failed: {e}")

    print()

print("=" * 70)
print("Test Complete - If both models work, your config is ready!")
print("=" * 70)
