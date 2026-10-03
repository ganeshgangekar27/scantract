"""
Check OpenRouter API key configuration without printing the key itself.
"""
import os
import requests

def main():
    # Read key from environment
    key = os.environ.get('OPENAI_API_KEY', '')
    
    if not key:
        print("ERROR: OPENAI_API_KEY not set in environment")
        return
    
    # Print metadata only
    print(f"Key length: {len(key)}")
    print(f"Last 4 chars: {key[-4:] if len(key) >= 4 else 'N/A'}")
    
    stripped_key = key.strip()
    print(f"Strip changed it: {stripped_key != key}")
    
    # Make API call to check key
    print("\n=== OpenRouter API Key Check ===")
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {stripped_key}"},
            timeout=10
        )
        
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # Redact any field containing the key
            redacted_data = {}
            for k, v in data.items():
                if isinstance(v, str) and stripped_key in v:
                    redacted_data[k] = "[REDACTED - contains key]"
                else:
                    redacted_data[k] = v
            
            print(f"Response: {redacted_data}")
        else:
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
