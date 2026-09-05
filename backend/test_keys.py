import requests

def test_key(key):
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    data = {
        "model": "claude-3-sonnet-20240229",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 10
    }
    r = requests.post("https://api.llmsrelay.com/v1/messages", headers=headers, json=data)
    print(f"Key {key[:12]}... -> {r.status_code}")
    if r.status_code != 200:
        print("  Error:", r.text)

test_key("sk-cs4-0fe8b5c4cc25cdec06abc137605da4abdebec87f16746bf9")
import os
env_key = os.environ.get("ANTHROPIC_API_KEY")
if env_key:
    test_key(env_key)

