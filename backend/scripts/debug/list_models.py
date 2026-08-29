import os
import requests

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
resp = requests.get(url)
print(resp.json())
