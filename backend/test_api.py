import requests
import json
import os
from datetime import datetime, timedelta
import jwt

SECRET_KEY = "super-secret-key-for-demo-change-in-prod"
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

token = create_access_token({"sub": "merchant@demo.local"})

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

print("Testing /api/agent/chat...")
res = requests.post("http://127.0.0.1:8080/api/agent/chat", headers=headers, json={"session_id": "test", "merchant_id": "4b6458a0-a3a3-4bc1-a6d5-82ca136be4a9", "message": "hello"})
print(res.status_code, res.text)
