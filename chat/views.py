"""
Chat API views and UI rendering for Scripture Bot.

Handles the main chat endpoint with intent detection (Q&A, verse verification,
image generation), denomination detection, session-based conversation memory,
and the chat UI page.
"""
import re
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from moderation.moderator import is_safe
from rag.pipeline import generate_response, detect_denomination
from image_gen.generator import generate_image


# Keywords that indicate the user wants an image
IMAGE_KEYWORDS = [
    'draw', 'paint', 'generate image', 'generate a image',
    'create image', 'create a image', 'create an image',
    'picture of', 'image of', 'illustration of',
    'show me', 'depict', 'visualize',
    'generate art', 'create art', 'make art',
    'generate a picture', 'create a picture',
]


def _is_image_request(message: str) -> bool:
    """Check if the user is requesting an image."""
    message_lower = message.lower()
    return any(kw in message_lower for kw in IMAGE_KEYWORDS)


def _extract_image_prompt(message: str) -> str:
    """Extract the image subject from the user's message."""
    message_lower = message.lower()

    # Remove common prefixes
    prefixes_to_remove = [
        'draw me', 'draw a', 'draw an', 'draw',
        'paint me', 'paint a', 'paint an', 'paint',
        'generate an image of', 'generate a image of', 'generate image of',
        'create an image of', 'create a image of', 'create image of',
        'show me a picture of', 'show me an image of', 'show me',
        'make me a picture of', 'make a picture of',
        'generate a picture of', 'create a picture of',
        'picture of', 'image of', 'illustration of',
        'depict', 'visualize',
        'please', 'can you', 'could you',
    ]

    cleaned = message
    for prefix in sorted(prefixes_to_remove, key=len, reverse=True):
        pattern = re.compile(re.escape(prefix), re.IGNORECASE)
        cleaned = pattern.sub('', cleaned).strip()

    return cleaned if cleaned else message


@ensure_csrf_cookie
def chat_ui(request):
    """Render the chat UI page."""
    return render(request, 'chat/index.html')


@api_view(['POST'])
def chat_api(request):
    """
    POST /api/chat/
    Main chat endpoint — handles Bible Q&A, verse verification, and image generation.

    Request body: {"message": "What does John 3:16 say?"}
    Response: {
        "response": "...",
        "type": "text" | "image",
        "image_url": null | "...",
        "verses_cited": [...],
        "denomination": "general" | "catholic" | "protestant" | "orthodox"
    }
    """
    message = request.data.get('message', '').strip()

    if not message:
        return Response(
            {'error': 'Please enter a message.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Step 1: Moderation check
    safe, reason = is_safe(message)
    if not safe:
        return Response({
            'response': reason,
            'type': 'moderated',
            'image_url': None,
            'verses_cited': [],
            'denomination': 'general',
        })

    # Step 2: Load conversation history from session
    if 'conversation_history' not in request.session:
        request.session['conversation_history'] = []

    conversation_history = request.session['conversation_history']

    # Step 3: Detect intent
    if _is_image_request(message):
        # Image generation flow
        image_prompt = _extract_image_prompt(message)
        result = generate_image(image_prompt)

        response_text = f"Here's a biblical illustration of: *{image_prompt}*"

        # Save to session
        conversation_history.append({'role': 'user', 'content': message})
        conversation_history.append({'role': 'assistant', 'content': response_text})
        request.session['conversation_history'] = conversation_history
        request.session.modified = True

        return Response({
            'response': response_text,
            'type': 'image',
            'image_url': result['image_url'],
            'verses_cited': [],
            'denomination': 'general',
        })

    else:
        # Bible Q&A / Verse verification flow
        try:
            # Load conversation summary from session
            conversation_summary = request.session.get('conversation_summary', '')

            result = generate_response(
                message=message,
                conversation_history=conversation_history,
                conversation_summary=conversation_summary,
            )

            # Save to session
            conversation_history.append({'role': 'user', 'content': message})
            conversation_history.append({'role': 'assistant', 'content': result['response']})

            # Keep only last 10 messages for short-term window since summary memory handles long-term context
            if len(conversation_history) > 10:
                conversation_history = conversation_history[-10:]

            request.session['conversation_history'] = conversation_history
            request.session['conversation_summary'] = result.get('conversation_summary', '')
            request.session.modified = True

            return Response({
                'response': result['response'],
                'type': 'text',
                'image_url': None,
                'verses_cited': result.get('verses_cited', []),
                'denomination': result.get('denomination', 'general'),
            })

        except Exception as e:
            return Response(
                {
                    'response': 'I encountered an issue while processing your question. Please try again.',
                    'type': 'error',
                    'image_url': None,
                    'verses_cited': [],
                    'denomination': 'general',
                    'error_detail': str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
