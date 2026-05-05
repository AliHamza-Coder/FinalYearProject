import os
import requests
from dotenv import load_dotenv

# Try loading from .env if present
load_dotenv()

def test_huggingface_token():
    print("Testing Hugging Face Token...")
    token = os.environ.get("HUGGINGFACE_TOKEN")
    if not token:
        print("[FAIL] HUGGINGFACE_TOKEN is not set in environment or .env file.")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    # Check current user to verify token is valid
    response = requests.get("https://huggingface.co/api/whoami-v2", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"[PASS] Hugging Face Token is VALID. Authenticated as: {data.get('name', 'Unknown')}")
    else:
        print(f"[FAIL] Hugging Face Token is INVALID. Status Code: {response.status_code}")
        print(response.text)


def test_groq_api_key():
    print("\nTesting Groq API Key...")
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("[FAIL] GROQ_API_KEY is not set in environment or .env file.")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Simple request to list models to verify authentication
    response = requests.get("https://api.groq.com/openai/v1/models", headers=headers)
    
    if response.status_code == 200:
        print("[PASS] Groq API Key is VALID. Successfully connected to Groq.")
    else:
        print(f"[FAIL] Groq API Key is INVALID. Status Code: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    print("--- API Keys Test ---")
    test_huggingface_token()
    test_groq_api_key()
    print("---------------------\n")
