"""
Mock LLM client for testing without real API calls.
"""

import json


class MockLLMClient:
    """
    Mock LLM client with configurable responses.
    
    Tracks call history and can simulate failures for testing retry logic.
    """
    
    def __init__(self, responses: list[str] = None, fail_count: int = 0):
        """
        Initialize mock client.
        
        Args:
            responses: List of response strings to return in order
            fail_count: Number of initial calls that should fail
        """
        self.responses = responses or []
        self.fail_count = fail_count
        self.call_count = 0
        self.call_history = []
    
    async def call(self, messages: list[dict]) -> tuple[str, int]:
        """
        Mock LLM call.
        
        Args:
            messages: Message array (recorded but not used)
        
        Returns:
            Tuple of (response_text, 150) - fixed token count
        
        Raises:
            ValueError: For first fail_count calls
        """
        self.call_count += 1
        self.call_history.append(messages)
        
        # Simulate failures for first fail_count calls
        if self.call_count <= self.fail_count:
            raise ValueError("Simulated LLM failure")
        
        # Return response from list (cycle if needed)
        response_index = (self.call_count - self.fail_count - 1) % len(self.responses)
        response_text = self.responses[response_index]
        
        return (response_text, 150)  # Mock token count


# Predefined response constants for testing

MOCK_VALID_RESPONSE = json.dumps({
    "clause_type": "payment_terms",
    "key_entities": ["tenant", "rent", "5th"],
    "confidence": 0.92,
    "reasoning": "Clear payment terms specifying due date"
})

MOCK_MALFORMED_JSON = "```json\n" + MOCK_VALID_RESPONSE + "\n```"

MOCK_INVALID_JSON = "This is not JSON at all, just plain text explanation"
