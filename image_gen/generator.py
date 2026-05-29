"""
Christian image generation using Pollinations.ai.

Generates biblical and Christian-themed images using the free Pollinations.ai API.
No API key required — just construct the URL and return it.
"""
import urllib.parse


# Base URL for Pollinations image generation
POLLINATIONS_BASE_URL = "https://image.pollinations.ai/prompt"

# Style suffix for consistent Christian art aesthetic
STYLE_SUFFIX = "biblical art style, Christian religious art, reverent, beautiful, high quality"


def generate_image(prompt: str, width: int = 1024, height: int = 1024) -> dict:
    """
    Generate a Christian-themed image URL using Pollinations.ai.

    Args:
        prompt: The user's image description.
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        A dict with:
            - image_url: The Pollinations.ai URL that generates the image
            - prompt: The enhanced prompt used
    """
    # Enhance prompt with Christian art styling
    enhanced_prompt = f"{prompt}, {STYLE_SUFFIX}"

    # URL-encode the prompt
    encoded_prompt = urllib.parse.quote(enhanced_prompt)

    # Construct the Pollinations URL with size parameters
    image_url = f"{POLLINATIONS_BASE_URL}/{encoded_prompt}?width={width}&height={height}&nologo=true"

    return {
        'image_url': image_url,
        'prompt': enhanced_prompt,
    }
