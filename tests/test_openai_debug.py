#!/usr/bin/env python3
"""
Debug OpenAI API key and account status
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

print("🔍 OpenAI API Key Debug")
print("="*50)

api_key = os.getenv('OPENAI_API_KEY')
print(f"API Key starts with: {api_key[:20]}...")
print(f"API Key ends with: ...{api_key[-10:]}")

try:
    client = OpenAI(api_key=api_key)
    
    # Try to list available models
    print("\n📋 Checking available models...")
    models = client.models.list()
    gpt_models = [m.id for m in models if 'gpt' in m.id.lower()]
    print(f"Found {len(gpt_models)} GPT models")
    print("Available GPT models:")
    for model in sorted(gpt_models)[:10]:  # Show first 10
        print(f"  - {model}")
    
    # Try a minimal request with gpt-3.5-turbo (cheapest)
    print("\n🧪 Testing with gpt-3.5-turbo...")
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=5
    )
    print(f"✅ Success! Response: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\n💡 Troubleshooting steps:")
    print("1. Go to platform.openai.com and log in as the TEAM OWNER (not invited user)")
    print("2. Go to Settings → Team → Members")
    print("3. Check if the invited user has 'Billing' permissions")
    print("4. OR: Generate the API key from the team owner account instead")
    print("5. OR: Go to Settings → Billing and check if credits are allocated")
    print("\nAlternatively:")
    print("- Create API key from the main account that paid the $60")
    print("- Check if there's a 'Default project' vs team project issue")