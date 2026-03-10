"""Gemini API client for code generation."""

import json
import logging
import re
import time
from typing import Optional

import google.generativeai as genai

from src.utils.errors import GeminiAPIError, JSONParseError
from src.models.data_models import Solution


logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for communicating with Gemini API."""
    
    def __init__(
        self,
        api_key: str,
        temperature: float = 0.2,
        max_retries: int = 3
    ):
        """Initialize Gemini client with API key.
        
        Args:
            api_key: Gemini API key
            temperature: Temperature for generation (default: 0.2 for deterministic output)
            max_retries: Maximum number of retries on failure (default: 3)
        """
        self.api_key = api_key
        self.temperature = temperature
        self.max_retries = max_retries
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Initialize model
        self.model = genai.GenerativeModel(
            'gemini-pro',
            generation_config=genai.GenerationConfig(
                temperature=temperature,
            )
        )
        
        logger.info(f"Gemini client initialized with temperature={temperature}, max_retries={max_retries}")
    
    def generate_solution(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> dict:
        """Generate code solution from prompt.
        
        Args:
            prompt: User prompt describing the problem
            system_instruction: Optional system instruction for behavior control
            
        Returns:
            dict: Solution JSON with structure:
                {
                    "files": [
                        {
                            "file_path": "path/to/file.py",
                            "content": "updated file content"
                        }
                    ]
                }
        
        Raises:
            GeminiAPIError: If API call fails after retries
            JSONParseError: If response is not valid JSON
        """
        # Default system instruction if not provided
        if system_instruction is None:
            system_instruction = self._get_default_system_instruction()
        
        # Combine system instruction with prompt
        full_prompt = f"{system_instruction}\n\n{prompt}"
        
        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Gemini API call attempt {attempt + 1}/{self.max_retries}")
                
                # Call Gemini API
                response = self.model.generate_content(full_prompt)
                response_text = response.text
                
                logger.debug(f"Gemini API response: {response_text[:200]}...")
                
                # Try to parse as JSON
                try:
                    solution_json = json.loads(response_text)
                    logger.info("Successfully parsed Gemini response as JSON")
                    return solution_json
                except json.JSONDecodeError:
                    # Try to extract JSON from markdown code blocks
                    logger.warning("Failed to parse response as JSON, attempting markdown extraction")
                    solution_json = self._extract_json_from_markdown(response_text)
                    if solution_json:
                        logger.info("Successfully extracted JSON from markdown")
                        return solution_json
                    
                    # If last attempt, raise error
                    if attempt == self.max_retries - 1:
                        raise JSONParseError(f"Failed to parse Gemini response as JSON: {response_text[:200]}")
                    
                    # Otherwise, retry with stricter prompt
                    logger.warning(f"Retry {attempt + 1}/{self.max_retries} with stricter prompt")
                    full_prompt = self._get_stricter_prompt(prompt)
                    
                    # Exponential backoff: 1s, 2s, 4s
                    backoff_time = 2 ** attempt
                    logger.debug(f"Backing off for {backoff_time}s")
                    time.sleep(backoff_time)
                    
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Gemini API call failed after {self.max_retries} attempts: {e}")
                    raise GeminiAPIError(f"Gemini API call failed: {e}")
                
                # Exponential backoff
                backoff_time = 2 ** attempt
                logger.warning(f"Gemini API error, retrying in {backoff_time}s: {e}")
                time.sleep(backoff_time)
        
        raise GeminiAPIError("Gemini API call failed after all retries")
    
    def _get_default_system_instruction(self) -> str:
        """Get default system instruction for JSON-only output."""
        return """You are a code generation assistant. You must respond ONLY with valid JSON.

Output format:
{
  "files": [
    {
      "file_path": "relative/path/to/file.py",
      "content": "complete updated file content"
    }
  ]
}

CRITICAL RULES:
- Return ONLY the JSON object, no explanation or markdown formatting
- Include complete file content, not diffs
- Use relative paths from repository root
- Ensure all syntax is correct"""
    
    def _get_stricter_prompt(self, original_prompt: str) -> str:
        """Get stricter prompt emphasizing JSON-only output."""
        return f"""{self._get_default_system_instruction()}

IMPORTANT: Your response must be ONLY valid JSON. Do not include any text before or after the JSON.

{original_prompt}

Remember: Return ONLY the JSON object."""
    
    def _extract_json_from_markdown(self, response: str) -> Optional[dict]:
        """Extract JSON from markdown code blocks if present.
        
        Args:
            response: Response text that may contain JSON in markdown
            
        Returns:
            Parsed JSON dict if found, None otherwise
        """
        # Try to find JSON in markdown code blocks
        patterns = [
            r'```json\s*\n(.*?)\n```',  # ```json ... ```
            r'```\s*\n(.*?)\n```',       # ``` ... ```
            r'`(.*?)`',                   # `...`
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        return None
