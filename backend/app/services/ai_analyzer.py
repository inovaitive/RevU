from anthropic import Anthropic
import json
import logging
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Anthropic client
try:
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    logger.info("Anthropic client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Anthropic client: {str(e)}")
    client = None

# AI model version
AI_MODEL_VERSION = "claude-3-5-sonnet-20241022"


def build_analysis_prompt(
    feedback_text: str,
    author_name: Optional[str] = None,
    source: Optional[str] = None,
    rating: Optional[float] = None,
    entities: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build a comprehensive prompt for Claude to analyze feedback.

    Args:
        feedback_text: The main feedback content
        author_name: Name of the feedback author
        source: Source platform (g2, capterra, csv, etc.)
        rating: Numerical rating if available
        entities: Extracted entities from spaCy preprocessing

    Returns:
        Formatted prompt string
    """
    prompt = f"""You are an expert product feedback analyzer for a B2B SaaS platform. Analyze the following customer feedback and provide detailed, actionable insights.

Feedback: {feedback_text}

Additional Context:
- Author: {author_name or 'Unknown'}
- Source: {source or 'Unknown'}
- Rating: {f"{rating}/5.0" if rating else 'Not provided'}
"""

    if entities:
        prompt += f"""
- Detected Entities: {json.dumps(entities, indent=2)}
"""

    prompt += """
Provide your analysis in the following JSON format (return ONLY valid JSON, no markdown):
{
    "sentiment": "positive|negative|neutral|mixed",
    "sentiment_score": <float between -1.0 (very negative) and 1.0 (very positive)>,
    "categories": [<array of applicable categories from: "bug", "feature_request", "complaint", "praise", "question", "integration_issue", "usability", "performance">],
    "themes": [<array of specific themes mentioned, e.g., "UI", "performance", "pricing", "support", "documentation", "onboarding", "integrations", "reliability">],
    "priority_score": <integer 0-100 based on urgency and business impact>,
    "urgency": "low|medium|high|critical",
    "insights": {
        "summary": "<1-2 sentence executive summary>",
        "key_points": [<array of 2-4 key insights>],
        "action_items": [<array of 1-3 specific, actionable recommendations>],
        "churn_risk": <boolean - true if customer shows signs of leaving>,
        "churn_indicators": [<array of specific phrases/reasons if churn_risk is true, empty array otherwise>],
        "competitor_mentions": [<array of competitor names mentioned, empty if none>],
        "feature_requests": [<array of specific features requested, empty if none>]
    },
    "confidence": <float 0.0-1.0 indicating your confidence in this analysis>
}

Analysis Guidelines:
1. Be precise and specific in your analysis
2. Focus on actionable insights that product teams can use
3. Identify urgency based on language patterns (words like "critical", "urgent", "blocking")
4. Detect churn risk from phrases like "cancel", "switch to", "disappointed", "competitor"
5. Extract specific feature requests clearly
6. Provide high confidence (>0.8) only when the feedback is clear and unambiguous
7. Use lower confidence (<0.7) for vague, contradictory, or unclear feedback
8. Consider the rating in your sentiment analysis if provided

Return ONLY the JSON object, no additional text or markdown formatting."""

    return prompt


async def analyze_feedback_with_claude(
    feedback_text: str,
    author_name: Optional[str] = None,
    source: Optional[str] = None,
    rating: Optional[float] = None,
    entities: Optional[Dict[str, Any]] = None,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Analyze feedback using Claude AI with retry logic.

    Args:
        feedback_text: The feedback content to analyze
        author_name: Author name for context
        source: Source platform
        rating: Numerical rating
        entities: Pre-extracted entities from spaCy
        max_retries: Maximum number of retry attempts

    Returns:
        Dictionary with analysis results

    Raises:
        Exception: If analysis fails after all retries
    """
    if not client:
        logger.error("Anthropic client not initialized")
        return get_fallback_analysis(feedback_text)

    prompt = build_analysis_prompt(feedback_text, author_name, source, rating, entities)

    for attempt in range(max_retries):
        try:
            logger.info(f"Analyzing feedback with Claude (attempt {attempt + 1}/{max_retries})")

            # Call Claude API
            message = client.messages.create(
                model=AI_MODEL_VERSION,
                max_tokens=2048,
                temperature=0.3,  # Lower temperature for more consistent analysis
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract response text
            response_text = message.content[0].text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            # Parse JSON response
            analysis = json.loads(response_text)

            # Validate required fields
            required_fields = ["sentiment", "sentiment_score", "categories", "themes", "insights", "confidence"]
            for field in required_fields:
                if field not in analysis:
                    raise ValueError(f"Missing required field: {field}")

            # Ensure insights has required subfields
            if "insights" in analysis:
                insights = analysis["insights"]
                if "churn_risk" not in insights:
                    insights["churn_risk"] = False
                if "churn_indicators" not in insights:
                    insights["churn_indicators"] = []
                if "competitor_mentions" not in insights:
                    insights["competitor_mentions"] = []
                if "feature_requests" not in insights:
                    insights["feature_requests"] = []

            logger.info("Successfully analyzed feedback with Claude")
            return analysis

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Claude response as JSON (attempt {attempt + 1}): {str(e)}")
            if attempt == max_retries - 1:
                return get_fallback_analysis(feedback_text)

        except Exception as e:
            logger.error(f"Error analyzing feedback with Claude (attempt {attempt + 1}): {str(e)}")
            if attempt == max_retries - 1:
                return get_fallback_analysis(feedback_text)

    # Should not reach here, but return fallback just in case
    return get_fallback_analysis(feedback_text)


def get_fallback_analysis(feedback_text: str) -> Dict[str, Any]:
    """
    Provide a basic fallback analysis when Claude API fails.

    Args:
        feedback_text: Original feedback text

    Returns:
        Basic analysis structure with low confidence
    """
    logger.warning("Using fallback analysis due to Claude API failure")

    # Simple keyword-based sentiment
    positive_words = ["great", "excellent", "love", "amazing", "perfect", "awesome"]
    negative_words = ["bad", "terrible", "awful", "hate", "worst", "broken", "issue", "problem"]

    text_lower = feedback_text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)

    if positive_count > negative_count:
        sentiment = "positive"
        sentiment_score = 0.5
    elif negative_count > positive_count:
        sentiment = "negative"
        sentiment_score = -0.5
    else:
        sentiment = "neutral"
        sentiment_score = 0.0

    return {
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "categories": ["unclassified"],
        "themes": [],
        "priority_score": 50,
        "urgency": "medium",
        "insights": {
            "summary": "Analysis pending - Claude API unavailable",
            "key_points": ["Automatic analysis failed", "Manual review recommended"],
            "action_items": ["Review feedback manually"],
            "churn_risk": False,
            "churn_indicators": [],
            "competitor_mentions": [],
            "feature_requests": []
        },
        "confidence": 0.2  # Very low confidence for fallback
    }
