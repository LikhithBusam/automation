"""
Direct test of Groq API to verify the model works
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Test Groq API directly using OpenAI client with base_url
api_key = os.getenv("GROQ_API_KEY")

print("Testing Groq API with llama-3.1-8b-instant...")
print(f"API Key: {api_key[:20]}...")

try:
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": "Say 'Hello, Groq is working!' in one sentence."}],
        temperature=0.3,
        max_tokens=50,
    )

    print("\n[SUCCESS] Groq API call successful!")
    print(f"Model: {response.model}")
    print(f"Response: {response.choices[0].message.content}")
    print(f"\nThis confirms that:")
    print("  - Your API key is valid")
    print("  - The model 'llama-3.1-8b-instant' exists and is accessible")
    print("  - Groq's endpoint is reachable")

except Exception as e:
    print(f"\n[ERROR] Groq API call failed: {e}")
    print("\nTroubleshooting:")
    print("  1. Check if your GROQ_API_KEY is valid")
    print("  2. Verify the model name is correct")
    print("  3. Check your internet connection")
