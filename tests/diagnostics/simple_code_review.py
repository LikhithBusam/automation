"""
Simple Code Review Script
Works without complex MCP function calling - just reads files and analyzes them
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def read_file(file_path: str) -> str:
    """Read file content"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def review_code(file_path: str, focus_areas: str = "code quality, security, performance"):
    """
    Simple code review using Groq API directly
    """
    # Read the file
    print(f"\n[1/3] Reading file: {file_path}")
    code_content = read_file(file_path)

    if code_content.startswith("Error"):
        print(f"[ERROR] {code_content}")
        return

    print(f"[OK] Read {len(code_content)} characters")

    # Setup Groq client
    print(f"\n[2/3] Analyzing code with Groq...")
    client = OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")

    # Create review prompt
    prompt = f"""You are a Senior Code Analyst. Review this code from {file_path}:

```python
{code_content}
```

Focus areas: {focus_areas}

Provide a code review covering:
1. **Error Handling**: Any missing error handling or edge cases?
2. **Security**: Any security vulnerabilities or concerns?
3. **Performance**: Any performance issues or optimizations?
4. **Code Quality**: Any code smells, anti-patterns, or improvements?
5. **Best Practices**: Any violations of Python best practices?

Be specific and reference actual code from the file."""

    # Call Groq API
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior code analyst providing detailed, specific code reviews.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2048,
        )

        review = response.choices[0].message.content

        print(f"\n[3/3] Code Review Complete!\n")
        print("=" * 80)
        print(review)
        print("=" * 80)

        return review

    except Exception as e:
        print(f"[ERROR] Error calling Groq API: {e}")
        return None


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python simple_code_review.py <file_path> [focus_areas]")
        print("\nExample:")
        print("  python simple_code_review.py ./main.py")
        print('  python simple_code_review.py ./main.py "error handling, security"')
        sys.exit(1)

    file_path = sys.argv[1]
    focus_areas = sys.argv[2] if len(sys.argv) > 2 else "code quality, security, performance"

    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"CODE REVIEW: {file_path}")
    print(f"Focus: {focus_areas}")
    print(f"{'='*80}")

    review_code(file_path, focus_areas)


if __name__ == "__main__":
    main()
