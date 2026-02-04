"""
LLM Client for interacting with Ollama via HTTP API.

WHY ABSTRACTION LAYER?
- Easy to swap LLM providers (OpenAI, Claude, local models)
- Centralized error handling
- Retry logic and timeout management
- Easy to mock in tests
"""

import json
import time
import requests
from typing import Optional
from config.settings import settings
from utils.logger import setup_logger, log_llm_call

logger = setup_logger(__name__)


class LLMClient:
    """
    Client for interacting with Ollama LLM.
    
    WHY CLASS?
    - Maintains connection state
    - Can implement caching, rate limiting
    - Easy to extend with different LLM backends
    """
    
    def __init__(self, model: str = None, api_url: str = None, timeout: int = None):
        """
        Initialize LLM client.
        
        Args:
            model: Model name (defaults to settings)
            api_url: API endpoint (defaults to settings)
            timeout: Request timeout in seconds (defaults to settings)
        """
        self.model = model or settings.LLM_MODEL
        self.api_url = api_url or settings.LLM_API_URL
        self.timeout = timeout or settings.LLM_TIMEOUT
        
        logger.info(f"Initialized LLM client: model={self.model}, url={self.api_url}")
    
    def generate(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        """
        Generate text using the LLM.
        
        Args:
            prompt: Input prompt for the LLM
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated text, or None if generation fails
        
        WHY RETURN OPTIONAL?
        - Explicit handling of failures
        - Caller must handle None case (fail-safe design)
        - No silent failures
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Sending prompt to LLM (length: {len(prompt)} chars)")
            
            # Ollama API request format
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,  # Get complete response at once
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.7,  # Balanced creativity
                }
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=self.timeout
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            generated_text = result.get('response', '').strip()
            
            if not generated_text:
                logger.warning("LLM returned empty response")
                log_llm_call(logger, "generate", False, duration_ms, "Empty response")
                return None
            
            logger.debug(f"LLM response length: {len(generated_text)} chars")
            log_llm_call(logger, "generate", True, duration_ms)
            
            return generated_text
        
        except requests.exceptions.Timeout:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"LLM request timed out after {self.timeout}s"
            logger.error(error_msg)
            log_llm_call(logger, "generate", False, duration_ms, "Timeout")
            return None
        
        except requests.exceptions.ConnectionError:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Cannot connect to LLM at {self.api_url}. Is Ollama running?"
            logger.error(error_msg)
            log_llm_call(logger, "generate", False, duration_ms, "Connection error")
            return None
        
        except requests.exceptions.HTTPError as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"LLM HTTP error: {e}"
            logger.error(error_msg)
            log_llm_call(logger, "generate", False, duration_ms, str(e))
            return None
        
        except json.JSONDecodeError as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Failed to parse LLM response: {e}"
            logger.error(error_msg)
            log_llm_call(logger, "generate", False, duration_ms, "JSON decode error")
            return None
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Unexpected LLM error: {e}"
            logger.error(error_msg)
            log_llm_call(logger, "generate", False, duration_ms, str(e))
            return None
    
    def check_connection(self) -> bool:
        """
        Check if LLM service is reachable.
        
        Returns:
            True if service is available, False otherwise
        
        WHY?
        - Pre-flight check before processing emails
        - Better error messages for users
        - Can fail fast if LLM is down
        """
        try:
            logger.info("Checking LLM connection...")
            
            # Try a simple generation
            test_prompt = "Say 'OK' if you can read this."
            response = self.generate(test_prompt, max_tokens=10)
            
            if response:
                logger.info("LLM connection successful")
                return True
            else:
                logger.warning("LLM connection check failed: No response")
                return False
        
        except Exception as e:
            logger.error(f"LLM connection check failed: {e}")
            return False
    
    def get_model_info(self) -> dict:
        """Get information about the current model."""
        return {
            "model": self.model,
            "api_url": self.api_url,
            "timeout": self.timeout
        }


# Singleton instance for easy import
llm_client = LLMClient()


# Example usage:
# from utils.llm_client import llm_client
# response = llm_client.generate("What is the capital of France?")
# if response:
#     print(response)
# else:
#     print("LLM generation failed")
