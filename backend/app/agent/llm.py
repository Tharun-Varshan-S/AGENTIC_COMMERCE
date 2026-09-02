import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic

def get_llm():
    """
    Constructs the Chat model using Claude (via llmrelay.com) as primary,
    with a fallback to Gemini API.
    """
    primary_llm = ChatAnthropic(
        model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620"),
        api_key=os.getenv("ANTHROPIC_API_KEY") or "dummy-key",
        default_headers={"x-api-key": os.getenv("ANTHROPIC_API_KEY")} if os.getenv("ANTHROPIC_API_KEY") else None,
        base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.llmrelay.com/v1"),
        max_tokens=2048,
    )

    backup_llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "dummy-key"
    )

    return primary_llm.with_fallbacks([backup_llm])
