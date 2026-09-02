import pytest
from unittest.mock import MagicMock
from langchain_core.messages import SystemMessage, HumanMessage
from tenacity import RetryError
from google.genai.errors import ClientError

from app.agent.graph import invoke_llm_with_retry, is_retryable_exception
from langchain_google_genai.chat_models import GoogleRateLimitError

def test_is_retryable_exception():
    assert is_retryable_exception(Exception("429 RESOURCE_EXHAUSTED")) == True
    assert is_retryable_exception(Exception("quota limit reached")) == True
    assert is_retryable_exception(Exception("something else entirely")) == False
    
    # Mocking a 5xx ClientError
    class MockClientError(Exception):
        def __init__(self, code):
            self.code = code
            super().__init__(f"Client Error {code}")
            
    assert is_retryable_exception(MockClientError(500)) == True
    assert is_retryable_exception(MockClientError(503)) == True
    assert is_retryable_exception(MockClientError(404)) == False

def test_invoke_llm_with_retry_recovers():
    mock_llm = MagicMock()
    
    # First call raises a 429 error, second call succeeds
    mock_llm.invoke.side_effect = [
        Exception("Error calling model 'gemini-3.6-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED"),
        "success_response"
    ]
    
    messages = [SystemMessage(content="Hello")]
    
    response = invoke_llm_with_retry(mock_llm, messages)
    
    # Should recover and return the second response
    assert response == "success_response"
    
    # Assert invoke was called exactly twice
    assert mock_llm.invoke.call_count == 2

def test_invoke_llm_with_retry_exhausts():
    mock_llm = MagicMock()
    
    # Always raise 429
    mock_llm.invoke.side_effect = Exception("429 RESOURCE_EXHAUSTED")
    
    messages = [SystemMessage(content="Hello")]
    
    with pytest.raises(Exception) as exc_info:
        invoke_llm_with_retry(mock_llm, messages)
        
    assert "429" in str(exc_info.value)
    
    # By default we configure stop_after_attempt(3), so it should be called 3 times
    assert mock_llm.invoke.call_count == 3
