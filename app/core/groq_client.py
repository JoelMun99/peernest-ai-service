"""
Groq LLM client for AI-powered categorization.

This module handles all communication with the Groq API, including
error handling, retries, and response parsing.
"""

import asyncio
import json
import re
import time
from typing import Dict, List, Optional, Tuple, Any
import logging
from groq import AsyncGroq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config.settings import Settings

logger = logging.getLogger(__name__)


class GroqClientError(Exception):
    """Custom exception for Groq client errors."""
    pass


class GroqClient:
    """
    Async client for Groq LLM API.
    
    Handles categorization requests with proper error handling,
    retries, and response validation.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the Groq client.
        
        Args:
            settings: Application settings containing Groq configuration
        """
        self.settings = settings
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self.model = settings.model_name
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
        self.timeout = settings.timeout_seconds
        
        logger.info(f"Initialized Groq client with model: {self.model}")
    
    async def test_connection(self) -> bool:
        """
        Test the connection to Groq API.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            # Simple test request
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10,
                timeout=10
            )
            
            logger.info("Groq API connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Groq API connection test failed: {str(e)}")
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError))
    )
    async def categorize_struggle(
        self, 
        struggle_text: str, 
        available_categories: List[str],
        enhanced_prompt: str = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Categorize struggle text using Groq LLM.
        
        Args:
            struggle_text: User's struggle description
            available_categories: List of available category names
            enhanced_prompt: Optional enhanced prompt from PromptEngineer
            
        Returns:
            Tuple[Dict, Dict]: (categorization_result, processing_metrics)
            
        Raises:
            GroqClientError: If categorization fails after retries
        """
        start_time = time.time()
        
        try:
            # Use enhanced prompt if provided, otherwise fallback to basic prompt
            if enhanced_prompt:
                prompt = enhanced_prompt
                logger.debug("Using enhanced prompt from PromptEngineer")
            else:
                prompt = self._create_categorization_prompt(struggle_text, available_categories)
                logger.debug("Using basic fallback prompt")
            
            logger.debug(f"Sending categorization request for text length: {len(struggle_text)}")
            
            # Make the API call
            groq_start_time = time.time()
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert mental health categorization assistant. Analyze user struggles and categorize them accurately."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=self.timeout
            )
            groq_end_time = time.time()
            
            # Parse the response
            result = self._parse_groq_response(response, available_categories)
            
            # Calculate metrics
            total_time = time.time() - start_time
            groq_time = groq_end_time - groq_start_time
            
            processing_metrics = {
                "processing_time_ms": int(total_time * 1000),
                "groq_api_time_ms": int(groq_time * 1000),
                "model_used": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else None,
                "fallback_used": False,
                "cache_hit": False
            }
            
            logger.info(f"Categorization successful in {total_time:.2f}s")
            return result, processing_metrics
            
        except Exception as e:
            error_msg = f"Groq API categorization failed: {str(e)}"
            logger.error(error_msg)
            raise GroqClientError(error_msg) from e
    
    def _create_categorization_prompt(self, struggle_text: str, categories: List[str]) -> str:
        """
        Create a well-engineered prompt for categorization.
        
        Args:
            struggle_text: User's struggle description
            categories: Available categories
            
        Returns:
            str: Formatted prompt for the LLM
        """
        categories_str = ", ".join(categories)
        
        prompt = f"""
Analyze the following user struggle and categorize it into the most appropriate categories from the provided list.

USER STRUGGLE:
"{struggle_text}"

AVAILABLE CATEGORIES:
{categories_str}

INSTRUCTIONS:
1. Select 1-3 most relevant categories from the available list
2. Assign confidence scores (0.0 to 1.0) for each selected category
3. Identify the primary (highest confidence) category
4. Respond ONLY with valid JSON in this exact format:

{{
    "categories": [
        {{"category": "CategoryName", "confidence": 0.85}},
        {{"category": "AnotherCategory", "confidence": 0.72}}
    ],
    "primary_category": "CategoryName",
    "reasoning": "Brief explanation of why these categories were chosen"
}}

IMPORTANT:
- Use ONLY categories from the provided list
- Confidence scores must be between 0.0 and 1.0
- Primary category must be the highest confidence category
- Respond with valid JSON only, no additional text
"""
        return prompt
    
    def _extract_json_from_text(self, content: str) -> str:
        """
        Extract JSON from mixed text content.
        
        Args:
            content: Raw text content that may contain JSON
            
        Returns:
            str: Extracted JSON string
            
        Raises:
            ValueError: If no valid JSON is found
        """
        # First try to parse as-is (might already be pure JSON)
        try:
            json.loads(content)
            return content
        except json.JSONDecodeError:
            pass
        
        # Look for JSON in various patterns
        
        # Pattern 1: Look for JSON OUTPUT: followed by JSON
        json_output_match = re.search(r'JSON OUTPUT:\s*\n?({.*?})\s*(?:\n|$)', content, re.DOTALL)
        if json_output_match:
            return json_output_match.group(1).strip()
        
        # Pattern 1b: Look for JSON OUTPUT: followed by JSON without braces
        json_output_match = re.search(r'JSON OUTPUT:\s*\n?("categories".*?)(?:\n\n|Reasoning:|$)', content, re.DOTALL)  
        if json_output_match:
            json_content = "{" + json_output_match.group(1).strip() + "}"
            try:
                json.loads(json_content)  # Validate
                return json_content
            except json.JSONDecodeError:
                pass
        
        # Pattern 2: Look for any JSON object in the text
        json_match = re.search(r'({[^{}]*"categories"[^{}]*})', content, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        
        # Pattern 3: Try to find JSON between curly braces
        brace_matches = re.findall(r'{[^{}]*}', content)
        for match in brace_matches:
            try:
                json.loads(match)
                return match
            except json.JSONDecodeError:
                continue
        
        # Pattern 4: Look for structured data and try to reconstruct JSON
        if '"categories":' in content and '"primary_category":' in content:
            # Try to extract key-value pairs and reconstruct
            try:
                # Find the start and end of the JSON-like structure
                start_idx = content.find('"categories":')
                if start_idx > 0:
                    # Look backwards for opening brace
                    for i in range(start_idx - 1, -1, -1):
                        if content[i] == '{':
                            start_idx = i
                            break
                
                # Find the end
                brace_count = 0
                end_idx = len(content)
                for i in range(start_idx, len(content)):
                    if content[i] == '{':
                        brace_count += 1
                    elif content[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                
                potential_json = content[start_idx:end_idx].strip()
                json.loads(potential_json)  # Validate
                return potential_json
            except (json.JSONDecodeError, ValueError):
                pass
        
        # If all else fails, return the original content and let the outer handler deal with it
        return content
    
    def _parse_groq_response(
        self, 
        response: Any, 
        available_categories: List[str]
    ) -> Dict[str, Any]:
        """
        Parse and validate the Groq API response.
        
        Args:
            response: Raw response from Groq API
            available_categories: List of valid categories
            
        Returns:
            Dict: Parsed categorization result
            
        Raises:
            GroqClientError: If response parsing fails
        """
        try:
            # Extract the content
            content = response.choices[0].message.content.strip()
            
            # Remove any markdown formatting
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
                
            # Try to extract JSON from mixed text response
            json_content = self._extract_json_from_text(content)
            
            # Parse JSON
            parsed = json.loads(json_content)
            
            # Validate the structure
            if not isinstance(parsed, dict):
                raise ValueError("Response is not a JSON object")
            
            if "categories" not in parsed or "primary_category" not in parsed:
                raise ValueError("Missing required fields in response")
            
            # Validate categories
            categories = parsed["categories"]
            if not isinstance(categories, list) or len(categories) == 0:
                raise ValueError("Categories must be a non-empty list")
            
            # Validate each category
            validated_categories = []
            for cat in categories:
                if not isinstance(cat, dict) or "category" not in cat or "confidence" not in cat:
                    continue
                
                category_name = cat["category"]
                confidence = float(cat["confidence"])
                
                # Check if category is in available list
                if category_name not in available_categories:
                    logger.warning(f"LLM returned unknown category: {category_name}")
                    continue
                
                # Validate confidence score
                if not 0.0 <= confidence <= 1.0:
                    confidence = max(0.0, min(1.0, confidence))
                
                validated_categories.append({
                    "category": category_name,
                    "confidence": confidence
                })
            
            if not validated_categories:
                raise ValueError("No valid categories found in response")
            
            # Sort by confidence (highest first)
            validated_categories.sort(key=lambda x: x["confidence"], reverse=True)
            
            # Ensure primary category is the highest confidence one
            primary_category = validated_categories[0]["category"]
            
            # Calculate overall confidence (weighted average)
            total_confidence = sum(cat["confidence"] for cat in validated_categories)
            overall_confidence = total_confidence / len(validated_categories)
            
            result = {
                "categories": validated_categories,
                "primary_category": primary_category,
                "overall_confidence": min(1.0, overall_confidence),
                "reasoning": parsed.get("reasoning", "No reasoning provided")
            }
            
            logger.debug(f"Successfully parsed categorization: {primary_category} ({overall_confidence:.2f})")
            return result
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response: {str(e)}"
            logger.error(f"{error_msg}. Raw content: {content}")
            raise GroqClientError(error_msg) from e
        
        except (ValueError, KeyError, TypeError) as e:
            error_msg = f"Invalid response structure: {str(e)}"
            logger.error(error_msg)
            raise GroqClientError(error_msg) from e
    
    async def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        
        Returns:
            Dict: Model information and capabilities
        """
        return {
            "model_name": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout_seconds": self.timeout,
            "provider": "Groq",
            "capabilities": [
                "text_categorization",
                "json_output",
                "multi_category_support",
                "enhanced_prompts",
                "crisis_detection"
            ]
        }