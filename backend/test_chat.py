import requests
import json
import jwt
from datetime import datetime, timedelta, timezone

SECRET_KEY = "super-secret-key-for-demo-change-in-prod"
ALGORITHM = "HS256"

def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Create buyer token
token = create_token({"sub": "customer@demo.local"})

# The merchant ID for demo.local
merchant_id = "4b6458a0-a3a3-4bc1-a6d5-82ca136be4a9"
session_id = "test-session-123"

url = "http://localhost:8080/api/agent/chat"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

payload = {
    "session_id": session_id,
    "merchant_id": merchant_id,
    "message": "Hello agent"
}

print("Testing with payload:")
print(json.dumps(payload, indent=2))

try:
    # Set stream=True to handle streaming responses
    response = requests.post("http://localhost:8080/api/agent/chat", json=payload, headers=headers, stream=True)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                print("Stream chunk:", line.decode('utf-8'))
    else:
        print("Response body:")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)
except Exception as e:
    print(f"Error: {e}")
