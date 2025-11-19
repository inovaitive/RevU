import spacy
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

# Load spaCy model (will be loaded once on module import)
try:
    nlp = spacy.load("en_core_web_lg")
    logger.info("spaCy model 'en_core_web_lg' loaded successfully")
except OSError:
    logger.warning("spaCy model 'en_core_web_lg' not found. Run: python -m spacy download en_core_web_lg")
    nlp = None


# Urgency keywords that indicate time-sensitive issues
URGENCY_KEYWORDS = [
    "urgent", "critical", "immediately", "asap", "emergency", "blocking",
    "blocker", "broken", "down", "crash", "crashing", "failed", "failing",
    "not working", "stopped working", "can't use", "cannot use", "unusable"
]

# Churn risk keywords that indicate customer dissatisfaction or intent to leave
CHURN_KEYWORDS = [
    "cancel", "canceling", "cancelling", "switch", "switching", "leave",
    "disappointed", "frustrat", "angry", "unacceptable", "terrible",
    "worst", "horrible", "awful", "useless", "waste", "regret",
    "competitor", "alternative", "looking for", "considering",
    "refund", "money back", "downgrade"
]

# Known competitors (can be expanded)
KNOWN_COMPETITORS = [
    "salesforce", "hubspot", "zendesk", "intercom", "freshdesk",
    "zoho", "pipedrive", "monday.com", "asana", "jira", "clickup"
]


def preprocess_text(text: str) -> Dict[str, Any]:
    """
    Preprocess feedback text using spaCy for entity extraction and keyword detection.

    Args:
        text: Feedback content to analyze

    Returns:
        Dictionary containing:
        - entities: Extracted named entities (ORG, PRODUCT, PERSON)
        - keywords: Important noun chunks
        - urgency_keywords: List of urgency-related keywords found
        - churn_keywords: List of churn-risk keywords found
        - has_urgency_signals: Boolean flag
        - has_churn_signals: Boolean flag
    """
    if not nlp:
        logger.warning("spaCy model not loaded. Returning minimal preprocessing.")
        return {
            "entities": {"organizations": [], "products": [], "persons": []},
            "keywords": [],
            "urgency_keywords": [],
            "churn_keywords": [],
            "has_urgency_signals": False,
            "has_churn_signals": False
        }

    try:
        # Process text with spaCy
        doc = nlp(text.lower())

        # Extract named entities
        organizations = []
        products = []
        persons = []

        for ent in doc.ents:
            if ent.label_ == "ORG":
                organizations.append(ent.text)
            elif ent.label_ == "PRODUCT":
                products.append(ent.text)
            elif ent.label_ == "PERSON":
                persons.append(ent.text)

        # Extract keywords (noun chunks)
        keywords = [chunk.text for chunk in doc.noun_chunks if len(chunk.text) > 3]

        # Detect urgency keywords
        urgency_found = []
        for keyword in URGENCY_KEYWORDS:
            if keyword in text.lower():
                urgency_found.append(keyword)

        # Detect churn risk keywords
        churn_found = []
        for keyword in CHURN_KEYWORDS:
            if keyword in text.lower():
                churn_found.append(keyword)

        # Check for competitor mentions
        competitor_mentions = []
        for competitor in KNOWN_COMPETITORS:
            if competitor.lower() in text.lower():
                competitor_mentions.append(competitor)

        return {
            "entities": {
                "organizations": list(set(organizations)),
                "products": list(set(products)),
                "persons": list(set(persons))
            },
            "keywords": list(set(keywords))[:10],  # Top 10 keywords
            "urgency_keywords": urgency_found,
            "churn_keywords": churn_found,
            "competitor_mentions": competitor_mentions,
            "has_urgency_signals": len(urgency_found) > 0,
            "has_churn_signals": len(churn_found) > 0 or len(competitor_mentions) > 0
        }

    except Exception as e:
        logger.error(f"Error in spaCy preprocessing: {str(e)}")
        return {
            "entities": {"organizations": [], "products": [], "persons": []},
            "keywords": [],
            "urgency_keywords": [],
            "churn_keywords": [],
            "has_urgency_signals": False,
            "has_churn_signals": False
        }


def extract_key_phrases(text: str, max_phrases: int = 5) -> List[str]:
    """
    Extract key phrases from text using spaCy.

    Args:
        text: Text to analyze
        max_phrases: Maximum number of phrases to return

    Returns:
        List of key phrases
    """
    if not nlp:
        return []

    try:
        doc = nlp(text)

        # Get noun chunks and filter by length
        phrases = [
            chunk.text
            for chunk in doc.noun_chunks
            if len(chunk.text.split()) >= 2 and len(chunk.text) > 5
        ]

        # Remove duplicates and limit
        unique_phrases = list(dict.fromkeys(phrases))
        return unique_phrases[:max_phrases]

    except Exception as e:
        logger.error(f"Error extracting key phrases: {str(e)}")
        return []
