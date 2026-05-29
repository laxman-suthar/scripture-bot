"""
Image generation API views.
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from moderation.moderator import is_safe
from image_gen.generator import generate_image


@api_view(['POST'])
def generate_image_view(request):
    """
    POST /api/image/
    Generate a Christian-themed image from a text prompt.

    Request body: {"prompt": "Jesus walking on water"}
    Response: {"image_url": "...", "prompt": "..."}
    """
    prompt = request.data.get('prompt', '').strip()

    if not prompt:
        return Response(
            {'error': 'Please provide an image prompt.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Moderation check
    safe, reason = is_safe(prompt)
    if not safe:
        return Response(
            {'error': reason},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Generate image
    result = generate_image(prompt)

    return Response(result, status=status.HTTP_200_OK)
