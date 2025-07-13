# app/utils/categories.py - NEW FILE
"""
PeerNest struggle categories and subcategories.
Users are matched based on subcategories for more precise support.
"""

from typing import Dict, List, Tuple

# Main categories with their subcategories
PEERNEST_CATEGORIES = {
    "Mental Health – Emotional Regulation": [
        "Anxiety & Panic",
        "Depression & Mood Swings", 
        "Burnout & Exhaustion",
        "Anger Management",
        "Emotional Numbness"
    ],
    "Mental Health – Cognitive Struggles": [
        "OCD & Intrusive Thoughts",
        "Dissociation & Spacing Out",
        "Overthinking & Rumination", 
        "Brain Fog & Memory Issues",
        "Decision Fatigue"
    ],
    "Neurodivergence": [
        "ADHD (Focus, Impulsivity)",
        "Autism Spectrum (Masking, Sensory Overload)",
        "Executive Dysfunction",
        "Rejection Sensitivity",
        "Navigating Diagnosis or Self-Diagnosis"
    ],
    "Identity & Self-worth": [
        "Self-esteem & Confidence",
        "Body Image (Weight Loss Struggles, Weight Gain Struggles)",
        "Perfectionism & Self-criticism",
        "Cultural & Personal Identity",
        "Acceptance & Self-love"
    ],
    "LGBTQ+ Struggles": [
        "Coming Out",
        "Gender Dysphoria", 
        "Homophobic Family or Friends",
        "Cross Dressing / Gender Expression",
        "Transgender vs Cisgender Identity"
    ],
    "Friendship & Dating Struggles": [
        "Trust Issues",
        "Jealousy & Insecurity",
        "Unhealthy Dynamics",
        "Ghosting & Rejection",
        "Pressure to Fit In"
    ],
    "Marriage & Divorce": [
        "Communication Breakdown",
        "Emotional Distance",
        "Separation & Divorce",
        "Infidelity",
        "Resentment & Forgiveness"
    ],
    "Family Pressure or Estrangement": [
        "Toxic Parenting",
        "Religious/Cultural Pressure",
        "Childhood Trauma",
        "Sibling Conflict",
        "Generational Trauma"
    ],
    "Academic or School Stress": [
        "Exam Anxiety",
        "Failing Exams",
        "Academic Pressure",
        "Bullying",
        "Balancing Social & School Life"
    ],
    "Job or Work Burnout": [
        "Toxic Work Environments",
        "Overworking",
        "Job Insecurity",
        "Career Confusion",
        "Poor Work-Life Balance"
    ],
    "Financial Pressure": [
        "Debt & Bills",
        "Job Loss",
        "Financial Dependence",
        "Budgeting Struggles",
        "Shame Around Money"
    ],
    "Life Direction & Time Struggles": [
        "Feeling Lost or Stuck",
        "Fear of Failure",
        "Lack of Motivation",
        "Time Management",
        "Existential Questions"
    ],
    "Loneliness & Isolation": [
        "Feeling Misunderstood",
        "Social Anxiety",
        "No One to Talk To",
        "Disconnected from Community",
        "Isolation Despite Being Around Others"
    ],
    "Grief & Loss": [
        "Death of a Loved One",
        "Pet Loss",
        "Delayed Grief",
        "Disenfranchised Grief",
        "Coping with Holidays/Anniversaries"
    ],
    "Suicidal Thoughts & Self-harm": [
        "Suicidal Ideation",
        "Non-suicidal Self-injury (NSSI)",
        "Safety Planning",
        "Coping Alternatives",
        "Talking About It"
    ],
    "Struggling with Therapy or Support": [
        "Fear of Vulnerability",
        "Not Connecting with Therapist",
        "Stigma About Getting Help",
        "Feeling Like It's Not Working",
        "Navigating First-Time Therapy"
    ],
    "Chronic Illness": [
        "Pain Management",
        "Medical Fatigue & Brain Fog",
        "Navigating Diagnosis",
        "Body Changes & Acceptance",
        "Feeling Misunderstood by Others"
    ],
    "Sexual Assault & Trauma": [
        "Consent Violation",
        "Flashbacks & Triggers",
        "Shame & Guilt",
        "Trust Recovery",
        "Navigating Disclosure"
    ],
    "Living with a Disability": [
        "Accessibility Barriers",
        "Navigating Daily Tasks",
        "Feeling Overlooked or Excluded",
        "Ableism & Discrimination",
        "Emotional Impact of Disability"
    ]
}

def get_all_subcategories() -> List[str]:
    """
    Get flat list of all subcategories for AI categorization.
    
    Returns:
        List[str]: All 95 subcategories
    """
    subcategories = []
    for main_cat, sub_cats in PEERNEST_CATEGORIES.items():
        subcategories.extend(sub_cats)
    return subcategories

def get_main_category_for_subcategory(subcategory: str) -> str:
    """
    Find which main category a subcategory belongs to.
    
    Args:
        subcategory: The subcategory name
        
    Returns:
        str: Main category name, or "Unknown" if not found
    """
    for main_cat, sub_cats in PEERNEST_CATEGORIES.items():
        if subcategory in sub_cats:
            return main_cat
    return "Unknown"

def get_subcategories_for_main(main_category: str) -> List[str]:
    """
    Get all subcategories for a main category.
    
    Args:
        main_category: Main category name
        
    Returns:
        List[str]: List of subcategories
    """
    return PEERNEST_CATEGORIES.get(main_category, [])

def get_category_hierarchy() -> Dict[str, List[str]]:
    """
    Get the complete category hierarchy.
    
    Returns:
        Dict: Complete categories structure
    """
    return PEERNEST_CATEGORIES.copy()

def get_categories_summary() -> Dict[str, int]:
    """
    Get summary statistics about categories.
    
    Returns:
        Dict: Category counts and statistics
    """
    return {
        "total_main_categories": len(PEERNEST_CATEGORIES),
        "total_subcategories": len(get_all_subcategories()),
        "avg_subcategories_per_main": len(get_all_subcategories()) / len(PEERNEST_CATEGORIES)
    }