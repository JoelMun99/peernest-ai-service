"""
Fallback categorization service using rule-based matching for PeerNest categories.

This service provides backup categorization when the Groq LLM is unavailable,
using keyword matching and pattern recognition for PeerNest subcategories.
"""

import re
import logging
from typing import Dict, List, Tuple, Any
from collections import defaultdict

from config.settings import Settings
from utils.fallback_keywords import get_fallback_keywords, get_crisis_categories

logger = logging.getLogger(__name__)


class FallbackService:
    """
    Rule-based fallback categorization service for PeerNest categories.
    
    Uses keyword matching, pattern recognition, and confidence scoring
    to provide categorization when AI services are unavailable.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the fallback service with PeerNest keywords.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        
        # Load PeerNest keyword mappings
        self.category_keywords = get_fallback_keywords()
        self.crisis_categories = get_crisis_categories()
        
        logger.info(f"Fallback service initialized with {len(self.category_keywords)} PeerNest categories")
        logger.info(f"Crisis detection enabled for {len(self.crisis_categories)} categories")
    
    async def categorize_struggle(
        self, 
        struggle_text: str, 
        available_categories: List[str]
    ) -> Dict[str, Any]:
        """
        Categorize struggle text using rule-based matching.
        
        Args:
            struggle_text: User's struggle description
            available_categories: List of available category names
            
        Returns:
            Dict: Categorization result with categories and confidence scores
        """
        logger.info("Processing fallback categorization")
        
        # Normalize text for matching
        normalized_text = self._normalize_text(struggle_text)
        
        # Calculate scores for each available category
        category_scores = {}
        for category in available_categories:
            if category in self.category_keywords:
                score = self._calculate_category_score(normalized_text, category)
                if score > 0:
                    category_scores[category] = score
        
        # Handle case where no categories match
        if not category_scores:
            logger.warning("No categories matched in fallback categorization")
            return self._create_default_response()
        
        # Sort categories by score and create response
        sorted_categories = sorted(
            category_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Take top 3 categories max
        top_categories = sorted_categories[:3]
        
        # Normalize confidence scores (scale to 0.1-0.8 range for fallback)
        max_score = top_categories[0][1]
        normalized_categories = []
        
        for category, score in top_categories:
            # Scale confidence: fallback confidence should be lower than AI
            confidence = min(0.8, max(0.1, (score / max_score) * 0.7))
            normalized_categories.append({
                "category": category,
                "confidence": round(confidence, 2)
            })
        
        # Calculate overall confidence
        overall_confidence = sum(cat["confidence"] for cat in normalized_categories) / len(normalized_categories)
        
        result = {
            "categories": normalized_categories,
            "primary_category": normalized_categories[0]["category"],
            "overall_confidence": round(overall_confidence, 2),
            "reasoning": f"Rule-based matching found {len(normalized_categories)} relevant categories"
        }
        
        logger.info(f"Fallback categorization completed: {result['primary_category']} ({result['overall_confidence']})")
        return result
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for better matching.
        
        Args:
            text: Input text to normalize
            
        Returns:
            str: Normalized text
        """
        # Convert to lowercase
        normalized = text.lower()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove punctuation that might interfere with matching
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        return normalized.strip()
    
    def _calculate_category_score(self, normalized_text: str, category: str) -> float:
        """
        Calculate matching score for a specific category.
        
        Args:
            normalized_text: Normalized struggle text
            category: Category to score against
            
        Returns:
            float: Matching score for the category
        """
        keywords = self.category_keywords[category]
        score = 0.0
        
        # Score primary keywords (higher weight)
        for keyword in keywords["primary"]:
            if keyword in normalized_text:
                score += 3.0
                # Bonus for exact word matches
                if f" {keyword} " in f" {normalized_text} ":
                    score += 1.0
        
        # Score secondary keywords (lower weight)
        for keyword in keywords["secondary"]:
            if keyword in normalized_text:
                score += 1.5
        
        # Score pattern matches (medium weight)
        for pattern in keywords["patterns"]:
            matches = re.findall(pattern, normalized_text, re.IGNORECASE)
            score += len(matches) * 2.0
        
        # Bonus for multiple keyword matches in same category
        primary_matches = sum(1 for kw in keywords["primary"] if kw in normalized_text)
        if primary_matches > 1:
            score += primary_matches * 0.5
        
        return score
    
    def _create_default_response(self) -> Dict[str, Any]:
        """
        Create a default response when no categories match.
        
        Returns:
            Dict: Default categorization response
        """
        return {
            "categories": [
                {"category": "General Support", "confidence": 0.3}
            ],
            "primary_category": "General Support",
            "overall_confidence": 0.3,
            "reasoning": "No specific categories matched - assigned to general support"
        }
    
    def test_category_matching(self, test_text: str) -> Dict[str, float]:
        """
        Test category matching for debugging purposes.
        
        Args:
            test_text: Text to test against all categories
            
        Returns:
            Dict: Scores for all categories
        """
        normalized_text = self._normalize_text(test_text)
        scores = {}
        
        for category in self.category_keywords:
            score = self._calculate_category_score(normalized_text, category)
            scores[category] = score
        
        return scores
    
    def get_category_keywords(self, category: str) -> Dict[str, List[str]]:
        """
        Get keywords for a specific category.
        
        Args:
            category: Category name
            
        Returns:
            Dict: Keywords and patterns for the category
        """
        return self.category_keywords.get(category, {})
    
    def add_category_keywords(
        self, 
        category: str, 
        primary: List[str] = None,
        secondary: List[str] = None,
        patterns: List[str] = None
    ) -> None:
        """
        Add or update keywords for a category.
        
        Args:
            category: Category name
            primary: Primary keywords (high weight)
            secondary: Secondary keywords (medium weight)  
            patterns: Regex patterns (medium weight)
        """
        if category not in self.category_keywords:
            self.category_keywords[category] = {
                "primary": [],
                "secondary": [],
                "patterns": []
            }
        
        if primary:
            self.category_keywords[category]["primary"].extend(primary)
        if secondary:
            self.category_keywords[category]["secondary"].extend(secondary)
        if patterns:
            self.category_keywords[category]["patterns"].extend(patterns)
        
        logger.info(f"Updated keywords for category: {category}")