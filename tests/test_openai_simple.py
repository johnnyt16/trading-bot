#!/usr/bin/env python3
"""
Test OpenAI with different approaches
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')

print("🔍 Testing OpenAI API directly with curl-like request")
print("="*50)

# Test with direct API call
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# First, check account status
print("\n1️⃣ Checking API key validity...")
models_response = requests.get(
    "https://api.openai.com/v1/models",
    headers=headers
)

if models_response.status_code == 200:
    print("✅ API key is valid!")
    models = models_response.json()
    print(f"   Can access {len(models['data'])} models")
else:
    print(f"❌ API key check failed: {models_response.status_code}")
    print(f"   {models_response.text}")

# Try with gpt-4o-mini (newest, might have different quota)
print("\n2️⃣ Testing with gpt-4o-mini (latest mini model)...")
data = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hi"}],
    "max_tokens": 5
}

response = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers=headers,
    json=data
)

if response.status_code == 200:
    result = response.json()
    print(f"✅ Success with gpt-4o-mini!")
    print(f"   Response: {result['choices'][0]['message']['content']}")
else:
    print(f"❌ Failed: {response.status_code}")
    error = response.json().get('error', {})
    print(f"   Error: {error.get('message', 'Unknown error')}")

print("\n💡 Account Status Check:")
print("1. Log into platform.openai.com as the team owner")
print("2. Go to Settings → Billing")
print("3. Check:")
print("   - Is there a 'Current balance' showing?")
print("   - Are there any 'Pending' payments?")
print("   - Is the payment method verified?")
print("4. Also check Settings → Limits")
print("   - Are there any rate limits set to $0?")
print("\nNote: New OpenAI accounts sometimes need 5-10 minutes")
print("for payment processing to complete.")