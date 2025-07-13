# app/utils/fallback_keywords.py
"""
PeerNest fallback categorization keywords.
Maps subcategories to keywords for rule-based matching.
"""

from typing import Dict, List

# Keywords for PeerNest subcategories
PEERNEST_FALLBACK_KEYWORDS = {
    # Mental Health – Emotional Regulation
    "Anxiety & Panic": {
        "primary": ["anxiety", "anxious", "panic", "panic attack", "nervous", "worried"],
        "secondary": ["heart racing", "can't breathe", "restless", "tense", "fear"],
        "patterns": [r"panic attack", r"anxiety", r"heart (racing|pounding)"]
    },
    "Depression & Mood Swings": {
        "primary": ["depressed", "depression", "sad", "hopeless", "mood swings"],
        "secondary": ["empty", "worthless", "tired", "exhausted", "no energy"],
        "patterns": [r"feel (empty|worthless)", r"mood (swings|changes)", r"can't (get up|function)"]
    },
    "Burnout & Exhaustion": {
        "primary": ["burnout", "burned out", "exhausted", "exhaustion", "drained"],
        "secondary": ["overwhelmed", "too much", "can't cope", "overworked"],
        "patterns": [r"burned out", r"completely (exhausted|drained)", r"can't (cope|handle)"]
    },
    "Anger Management": {
        "primary": ["angry", "anger", "rage", "furious", "mad"],
        "secondary": ["irritated", "frustrated", "explosive", "temper"],
        "patterns": [r"anger (issues|problems)", r"can't control", r"explosive (anger|rage)"]
    },
    "Emotional Numbness": {
        "primary": ["numb", "numbness", "feel nothing", "emotionally numb"],
        "secondary": ["disconnected", "empty", "void", "can't feel"],
        "patterns": [r"feel (nothing|numb)", r"emotionally (numb|disconnected)"]
    },
    
    # Mental Health – Cognitive Struggles  
    "OCD & Intrusive Thoughts": {
        "primary": ["ocd", "obsessive", "compulsive", "intrusive thoughts"],
        "secondary": ["repetitive", "checking", "counting", "unwanted thoughts"],
        "patterns": [r"intrusive thoughts", r"obsessive (thoughts|behavior)", r"can't stop (thinking|checking)"]
    },
    "Overthinking & Rumination": {
        "primary": ["overthinking", "rumination", "ruminating", "can't stop thinking"],
        "secondary": ["analyzing", "replaying", "obsessing", "stuck in my head"],
        "patterns": [r"overthinking", r"can't stop (thinking|analyzing)", r"stuck in (my head|loop)"]
    },
    "Brain Fog & Memory Issues": {
        "primary": ["brain fog", "memory", "forgetful", "can't concentrate"],
        "secondary": ["fuzzy", "unclear", "confusion", "memory problems"],
        "patterns": [r"brain fog", r"memory (issues|problems)", r"can't (concentrate|focus|remember)"]
    },
    
    # Neurodivergence
    "ADHD (Focus, Impulsivity)": {
        "primary": ["adhd", "attention", "focus", "impulsive", "hyperactive"],
        "secondary": ["distractible", "restless", "can't sit still", "hyperfocus"],
        "patterns": [r"can't (focus|concentrate)", r"attention (deficit|problems)", r"adhd"]
    },
    "Autism Spectrum (Masking, Sensory Overload)": {
        "primary": ["autism", "autistic", "masking", "sensory overload"],
        "secondary": ["stimming", "meltdown", "overwhelming sounds", "social scripts"],
        "patterns": [r"sensory overload", r"autism", r"masking"]
    },
    
    # Identity & Self-worth
    "Self-esteem & Confidence": {
        "primary": ["self-esteem", "confidence", "self-worth", "insecure"],
        "secondary": ["not good enough", "worthless", "inadequate", "self-doubt"],
        "patterns": [r"low (self-esteem|confidence)", r"not good enough", r"feel (worthless|inadequate)"]
    },
    "Perfectionism & Self-criticism": {
        "primary": ["perfectionist", "perfectionism", "self-critical", "never good enough"],
        "secondary": ["harsh on myself", "high standards", "failure", "disappointed"],
        "patterns": [r"perfectionist", r"never good enough", r"harsh on myself"]
    },
    
    # LGBTQ+ Struggles
    "Coming Out": {
        "primary": ["coming out", "closeted", "tell parents", "reveal sexuality"],
        "secondary": ["scared to tell", "family reaction", "hiding who I am"],
        "patterns": [r"coming out", r"tell (my parents|family)", r"hiding who I am"]
    },
    "Gender Dysphoria": {
        "primary": ["gender dysphoria", "dysphoria", "wrong body", "gender identity"],
        "secondary": ["transgender", "trans", "gender confusion", "body dysphoria"],
        "patterns": [r"gender dysphoria", r"wrong body", r"don't feel like"]
    },
    
    # Work & Career
    "Toxic Work Environments": {
        "primary": ["toxic workplace", "toxic boss", "hostile work", "workplace bullying"],
        "secondary": ["harassment", "discrimination", "hostile", "abusive boss"],
        "patterns": [r"toxic (work|workplace|boss)", r"workplace (bullying|harassment)"]
    },
    "Job Insecurity": {
        "primary": ["job insecurity", "losing job", "layoffs", "unemployment"],
        "secondary": ["job hunting", "unemployed", "career uncertainty"],
        "patterns": [r"losing (my )?job", r"job (insecurity|uncertainty)", r"laid off"]
    },
    
    # Crisis Categories (High Priority)
    "Suicidal Ideation": {
        "primary": ["suicidal", "suicide", "kill myself", "end my life", "don't want to live"],
        "secondary": ["hopeless", "no point", "better off dead", "suicidal thoughts"],
        "patterns": [r"suicidal (thoughts|ideation)", r"kill myself", r"end (my )?life", r"don't want to live"]
    },
    "Non-suicidal Self-injury (NSSI)": {
        "primary": ["self-harm", "cutting", "self-injury", "hurt myself"],
        "secondary": ["razor", "blade", "scars", "burning", "scratching"],
        "patterns": [r"self.harm", r"hurt myself", r"cutting", r"self.injury"]
    },
    
    # Add more as needed...
}

def get_fallback_keywords() -> Dict[str, Dict[str, List[str]]]:
    """Get all fallback keywords for PeerNest categories."""
    return PEERNEST_FALLBACK_KEYWORDS

def get_crisis_categories() -> List[str]:
    """Get list of crisis categories that need immediate attention."""
    return [
        "Suicidal Ideation",
        "Non-suicidal Self-injury (NSSI)",
        "Safety Planning",
        "Consent Violation",
        "Flashbacks & Triggers"
    ]