import os
from langchain_google_genai import ChatGoogleGenerativeAI

def get_llm():
    """
    Constructs the Chat model using Gemini API (Google Generative AI).
    Requires GEMINI_API_KEY to be set in the environment.
    """
    # Assuming the API key is set in the environment variables, either GEMINI_API_KEY or GOOGLE_API_KEY
    # The default model is gemini-1.5-flash as per the user instruction.
    return ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        google_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )
