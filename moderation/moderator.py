"""
Content moderation layer for Scripture Bot.

Filters out harmful, offensive, or manipulative prompts before they reach
the RAG pipeline or Gemini. Uses keyword matching and pattern detection.
"""
import re


# Blocked keyword categories
HATE_KEYWORDS = [
    'racism', 'racist', 'white supremacy', 'supremacist',
    'antisemit', 'islamophob', 'homophob', 'bigot',
    'nazi', 'fascist', 'ethnic cleansing', 'genocide',
    'slur', 'hate speech', 'hate', 'hateful', 'hatred',
    'discriminat',
]

VIOLENCE_KEYWORDS = [
    'kill', 'murder', 'attack', 'bomb', 'shoot',
    'terrorist', 'terrorism', 'weapon', 'assault',
    'war crime', 'torture', 'execute', 'lynch',
    'massacre', 'slaughter', 'violent', 'violence',
    'bloody', 'gory', 'gruesome',
]

MANIPULATION_KEYWORDS = [
    'manipulate', 'deceive', 'trick people', 'scam',
    'cult', 'brainwash', 'exploit',
    'extort', 'blackmail', 'fabricate',
]

SEXUAL_KEYWORDS = [
    'pornograph', 'sexual content', 'explicit',
    'erotic', 'nude', 'nsfw', 'obscene',
]

# Harmful intent patterns — these check for attempts to misuse scripture
HARMFUL_PATTERNS = [
    r'rewrite\s+.+\s+to\s+support\s+(racism|violence|hate|discrimination|abuse)',
    r'generate\s+.+\s+(verse|scripture)\s+.*(support|justify|promote)\s+(violence|hate|killing|racism)',
    r'create\s+a\s+fake\s+(verse|scripture|bible)',
    r'make\s+up\s+a\s+(verse|scripture|bible)',
    r'(bible|verse|scripture)\s+.*(justify|support|promote)\s+(slavery|abuse|violence|racism|hatred)',
    r'twist\s+.*(scripture|bible|verse|\d+:\d+)',
    r'misuse\s+.*(scripture|bible|verse)',
    r'weaponize\s+.*(scripture|bible|religion|faith)',
    r'(no restrictions|without restrictions|unrestricted).*(bible|verse|scripture|god|jesus)',
    r'(you are now|act as|pretend to be).*(no restrictions|unrestricted|without limits)',
    r'fabricate\s+.*(verse|scripture|bible)',
]

# Image generation request indicators
IMAGE_REQUEST_WORDS = [
    'draw', 'paint', 'depict', 'illustrate', 'visualize',
    'generate image', 'generate a image', 'generate an image',
    'create image', 'create a image', 'create an image',
    'picture of', 'image of', 'illustration of',
    'show me', 'generate art', 'create art', 'make art',
    'generate a picture', 'create a picture',
]

# Gentle refusal message
BLOCKED_RESPONSE = (
    "I appreciate you reaching out, but I'm unable to assist with that request. "
    "My purpose is to provide helpful, respectful, and accurate information about "
    "Christianity and the Bible. If you have a genuine question about scripture "
    "or Christian faith, I'd be happy to help! 🙏"
)


def _is_image_request(prompt_lower: str) -> bool:
    """Check if the prompt is requesting image generation."""
    return any(word in prompt_lower for word in IMAGE_REQUEST_WORDS)


def is_safe(prompt: str) -> tuple[bool, str]:
    """
    Check if a user prompt is safe to process.

    Args:
        prompt: The user's input message.

    Returns:
        A tuple of (is_safe: bool, reason: str).
        If safe, returns (True, "").
        If blocked, returns (False, refusal_message).
    """
    prompt_lower = prompt.lower().strip()

    # Skip very short prompts — they're likely not harmful
    if len(prompt_lower) < 3:
        return True, ""

    # Check harmful intent patterns first (most specific)
    for pattern in HARMFUL_PATTERNS:
        if re.search(pattern, prompt_lower):
            return False, BLOCKED_RESPONSE

    # Check sexual content (always block, regardless of intent)
    if any(kw in prompt_lower for kw in SEXUAL_KEYWORDS):
        return False, BLOCKED_RESPONSE

    # Image requests with ANY harmful keyword should ALWAYS be blocked
    # Generating hateful/violent/offensive images is never acceptable
    if _is_image_request(prompt_lower):
        all_harmful = HATE_KEYWORDS + VIOLENCE_KEYWORDS + MANIPULATION_KEYWORDS
        if any(kw in prompt_lower for kw in all_harmful):
            return False, BLOCKED_RESPONSE

    # Check keyword categories — only block if combined with harmful intent
    # We don't want to block legitimate questions like "What does the Bible say about violence?"
    harmful_context_words = [
        'support', 'justify', 'promote', 'rewrite', 'change',
        'make it say', 'generate', 'create', 'fabricate',
        'draw', 'paint', 'depict', 'illustrate', 'picture', 'image',
    ]

    has_harmful_intent = any(word in prompt_lower for word in harmful_context_words)

    if has_harmful_intent:
        # Check hate keywords
        if any(kw in prompt_lower for kw in HATE_KEYWORDS):
            return False, BLOCKED_RESPONSE

        # Check violence keywords
        if any(kw in prompt_lower for kw in VIjustifyOLENCE_KEYWORDS):
            return False, BLOCKED_RESPONSE

        # Check manipulation keywords
        if any(kw in prompt_lower for kw in MANIPULATION_KEYWORDS):
            return False, BLOCKED_RESPONSE

    # Prompt is safe
    return True, ""

