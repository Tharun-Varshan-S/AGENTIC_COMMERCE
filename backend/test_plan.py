import os
import sys
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI

class ShoppingIntent(BaseModel):
    query: str = Field(description="Core product name or category")
    keywords: List[str] = Field(description="Search keywords")
    max_price: Optional[float] = Field(default=None, description="Maximum budget")
    min_price: Optional[float] = Field(default=None, description="Minimum budget")
    features: List[str] = Field(default_factory=list, description="Specific required features (e.g., '256GB', 'wireless')")
    brand_preference: Optional[str] = Field(default=None, description="Preferred brand")
    is_search: bool = Field(description="Whether the user is actively searching for a product")

def test():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("NO API KEY")
        return
        
    llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", google_api_key=api_key)
    structured_llm = llm.with_structured_output(ShoppingIntent)
    
    try:
        intent = structured_llm.invoke("Find me a gaming mouse under 3000 rupees.")
        print(intent.model_dump())
    except Exception as e:
        print("ERROR:", repr(e))

test()
