import os
import time
import logging
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self, api_key: str = None, max_retries: int = 60, retry_delay: float = 1.0):
        """
        Initialize Gemini client with retry logic
        
        Args:
            api_key: API key for Gemini. If None, loads from GEMINI_API_KEY env var
            max_retries: Maximum number of retry attempts for rate limits
            retry_delay: Delay between retries in seconds
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be set in environment variables or passed as parameter")
        
        self.client = genai.Client(api_key=self.api_key)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def generate_content(self, model: str = "gemini-2.0-flash", contents: str = "", **kwargs):
        """
        Generate content with automatic retry on rate limits
        
        Args:
            model: Model name to use
            contents: Content/prompt to send
            **kwargs: Additional parameters for the API call
            
        Returns:
            Generated response text
        """
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    **kwargs
                )
                return response.text
                
            except Exception as e:
                error_message = str(e).lower()
                
                # Check for rate limit errors
                if any(keyword in error_message for keyword in [
                    'rate limit', 'quota', 'too many requests', 'rate_limit_exceeded'
                ]):
                    if attempt < self.max_retries:
                        logger.warning(f"Rate limit hit. Attempt {attempt + 1}/{self.max_retries + 1}. Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        logger.error(f"Rate limit exceeded after {self.max_retries} retries")
                        raise Exception(f"Rate limit exceeded after {self.max_retries} retries") from e
                
                # For non-rate-limit errors, raise immediately
                logger.error(f"API error: {e}")
                raise e
        
        # This should never be reached, but just in case
        raise Exception("Unexpected error in retry loop")

# Create a default client instance
def get_client():
    """Get a default Gemini client instance"""
    return GeminiClient()

# Example usage
if __name__ == "__main__":
    try:
        client = get_client()
        response = client.generate_content(
            model="gemini-2.0-flash", 
            contents="Explain how AI works in a few words"
        )
        print(response)
    except Exception as e:
        print(f"Error: {e}")