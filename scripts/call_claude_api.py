import requests
import os

def call_claude_api(prompt: str, model: str = "claude-3-5-sonnet-20241022", max_tokens: int = 300) -> str:
    """
    Call Anthropic Claude API with the given prompt and return the response text.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not found in environment variables.")
        return "Error: No API key"

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }

    data = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            return result['content'][0]['text'].strip()
        else:
            print(f"Claude API error: {response.status_code} - {response.text}")
            return f"Error: Claude API {response.status_code}"
    except Exception as e:
        print(f"Exception calling Claude API: {e}")
        return f"Error: {e}"