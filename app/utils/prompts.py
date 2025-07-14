

"""
Advanced prompt engineering for PeerNest struggle categorization.

This module contains optimized prompts designed specifically for accurate
categorization of mental health struggles into PeerNest subcategories.
"""

from typing import List, Dict, Any
from utils.categories import get_category_hierarchy
from utils.fallback_keywords import get_crisis_categories


class PromptEngineer:
    """
    Advanced prompt engineering for struggle categorization.
    
    Creates context-aware, few-shot learning prompts optimized for
    PeerNest's specific category structure and mental health focus.
    """
    
    def __init__(self):
        """Initialize the prompt engineer with PeerNest context."""
        self.category_hierarchy = get_category_hierarchy()
        self.crisis_categories = get_crisis_categories()
        
        # Few-shot examples for better AI performance
        self.few_shot_examples = [
            {
                "input": "I've been having panic attacks at work and my heart races whenever I think about presentations. I can't sleep and feel constantly on edge.",
                "output": {
                    "categories": [
                        {"category": "Anxiety & Panic", "confidence": 0.92},
                        {"category": "Job or Work Burnout", "confidence": 0.76}
                    ],
                    "primary_category": "Anxiety & Panic",
                    "reasoning": "Classic panic attack symptoms with work-related triggers."
                }
            },
               
            {
                "input": "I've been thinking about ending my life because I don't see any point in continuing. Everything feels hopeless.",
                "output": {
                    "categories": [
                        {"category": "Suicidal Ideation", "confidence": 0.96},
                        {"category": "Depression & Mood Swings", "confidence": 0.84}
                    ],
                    "primary_category": "Suicidal Ideation",
                    "reasoning": "Direct suicidal thoughts require immediate crisis intervention."
                }
            }
        ]
    
    def create_categorization_prompt(
        self, 
        struggle_text: str, 
        available_categories: List[str],
        context: Dict[str, Any] = None
    ) -> str:
        """
        Create an optimized categorization prompt with context and examples.
        
        Args:
            struggle_text: User's struggle description
            available_categories: List of available subcategories
            context: Additional context (session info, previous categorizations, etc.)
            
        Returns:
            str: Optimized prompt for the LLM
        """
        # Organize categories by main groups for better understanding
        categorized_list = self._organize_categories_by_main(available_categories)
        
        # Create crisis category warning
        crisis_warning = self._create_crisis_warning()
        
        # Build few-shot examples
        examples_section = self._build_few_shot_examples()
        
        # Create the main prompt (optimized for token efficiency)
        prompt = f"""Analyze this mental health struggle and categorize into PeerNest subcategories.

{crisis_warning}

 GUIDELINES:
1. Select 1-3 most relevant subcategories
2. Assign confidence scores (0.0-1.0)
3.Crisis categories take priority

CATEGORIES: 
{categorized_list}

{examples_section}

USER STRUGGLE:"{struggle_text}"


JSON OUTPUT:
"categories": [{{"category": "Name", "confidence": 0.85}}],
"primary_category": "Highest Confidence Category",
"reasoning": "Brief explanation",
"crisis_detected": false

Use Only listed subcategories. Primary = highest confidence.
"""
        
        return prompt
    
    def create_crisis_detection_prompt(self, struggle_text: str) -> str:
        """
        Create a specialized prompt for crisis detection.
        
        Args:
            struggle_text: User's struggle description
            
        Returns:
            str: Crisis detection prompt
        """
        prompt = f"""CRISIS DETECTION ANALYSIS

You are a crisis intervention specialist. Analyze the following text for immediate risk indicators.

CRISIS CATEGORIES TO DETECT:
- Suicidal Ideation (thoughts of ending life, suicide plans, hopelessness)
- Non-suicidal Self-injury (cutting, burning, self-harm behaviors)
- Safety Planning (immediate safety concerns, crisis situations)
- Consent Violation (sexual assault, abuse, trauma)
- Flashbacks & Triggers (severe PTSD episodes, dissociation)

TEXT TO ANALYZE:
"{struggle_text}"

Respond with JSON only:
{{
    "crisis_detected": true/false,
    "crisis_level": "none/low/medium/high/immediate",
    "crisis_categories": ["category1", "category2"],
    "immediate_intervention_needed": true/false,
    "risk_indicators": ["indicator1", "indicator2"],
    "confidence": 0.0-1.0
}}
"""
        return prompt
    
    def _organize_categories_by_main(self, subcategories: List[str]) -> str:
        """
        Organize subcategories by their main categories for better prompt structure.
        
        Args:
            subcategories: List of subcategory names
            
        Returns:
            str: Formatted category hierarchy
        """
        organized = {}
        
        # Group subcategories by main category
        for main_cat, sub_cats in self.category_hierarchy.items():
            relevant_subs = [sub for sub in sub_cats if sub in subcategories]
            if relevant_subs:
                organized[main_cat] = relevant_subs
        
        # Compressed format:Main: sub1, sub2, sub3
        formatted = []
        for main_cat, sub_cats in organized.items():
            crisis_subs =  [sub for sub in sub_cats if sub in self.crisis_categories]
            regular_subs = [sub for sub in sub_cats if sub not in self.crisis_categories]

            if regular_subs:
                formatted.append(f"{main_cat}:{',  '.join(regular_subs)}")
            if crisis_subs:
                formatted.append(f"{main_cat} (CRISIS): {',  '.join(crisis_subs)}")     

        
        return "\n".join(formatted)
    
    def _create_crisis_warning(self) -> str:
        """Create crisis detection warning compressed"""
        crisis_list = ", ".join(self.crisis_categories)
        
        return f"""⚠️ CRISIS PRIORITY: {crisis_list}

if detected: high confidence (0.8+), primary category, crisis_detected: true"""

    
    def _build_few_shot_examples(self) -> str:
        """Build few-shot learning examples."""
        examples = []
        
        for i, example in enumerate(self.few_shot_examples, 1):
            categories_str = ", ".join([
                f'{cat["category"]} ({cat["confidence"]})'
                for cat in example["output"]["categories"]
            ])
            
            examples.append(f"""
                            
EX{i}: "{example['input']}" → {example['output']['primary_category']}, {categories_str}""")

        
        return "\nEXAMPLES:" + "".join(examples)
    
    def create_batch_prompt(self, struggle_texts: List[str]) -> str:
        """
        Create a prompt for batch processing multiple struggles.
        
        Args:
            struggle_texts: List of struggle descriptions
            
        Returns:
            str: Batch processing prompt
        """
        prompt = f"""Analyze the following {len(struggle_texts)} struggle texts and categorize each one.

Return a JSON array with results for each text in order:

[
    {{"text_index": 0, "categories": [...], "primary_category": "...", "reasoning": "..."}},
    {{"text_index": 1, "categories": [...], "primary_category": "...", "reasoning": "..."}}
]

TEXTS TO ANALYZE:
"""
        
        for i, text in enumerate(struggle_texts):
            prompt += f'{i}: "{text}"\n'
        
        return prompt
    
    def optimize_prompt_for_model(self, base_prompt: str, model_name: str) -> str:
        """
        Optimize prompt based on the specific LLM model being used.
        
        Args:
            base_prompt: Base categorization prompt
            model_name: Name of the LLM model
            
        Returns:
            str: Model-optimized prompt
        """
        if "mixtral" in model_name.lower():
            # Mixtral responds well to structured instructions
            return f"<instructions>\n{base_prompt}\n</instructions>"
        elif "llama" in model_name.lower():
            # Llama models prefer direct, clear instructions
            return f"### Task: Mental Health Categorization\n\n{base_prompt}"
        else:
            # Default format
            return base_prompt
    
    def create_confidence_calibration_prompt(self, struggle_text: str, initial_result: Dict) -> str:
        """
        Create a prompt to calibrate confidence scores for better accuracy.
        
        Args:
            struggle_text: Original struggle text
            initial_result: Initial categorization result
            
        Returns:
            str: Confidence calibration prompt
        """
        return f"""Review and calibrate the confidence scores for this categorization:

Original Text: "{struggle_text}"
Initial Categorization: {initial_result}

Confidence Calibration Guidelines:
- 0.9-1.0: Text explicitly mentions the category or uses exact terminology
- 0.7-0.9: Strong indicators present, clear connection to category
- 0.5-0.7: Moderate indicators, reasonable inference required
- 0.3-0.5: Weak indicators, significant interpretation needed
- 0.0-0.3: Very unclear or speculative connection

Provide calibrated result with the same JSON format but adjusted confidence scores.
"""