import os
from langchain_anthropic import ChatAnthropic

c = ChatAnthropic(
    model="claude-sonnet-4.6",
    api_key="sk-cs4-8458b",
    anthropic_api_url="https://api.llmsrelay.com"
)
print("api_key:", c.anthropic_api_key.get_secret_value() if c.anthropic_api_key else None)
print("api_url:", c.anthropic_api_url)
print("base_url in client:", c._client.base_url if hasattr(c, '_client') else "no client")
