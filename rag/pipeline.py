"""
Full RAG pipeline — combines retrieval with Gemini LLM for grounded responses.

Retrieves relevant Bible verses from pgvector, constructs a context-aware prompt
with denomination handling, and generates a response using Google Gemini.
"""
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from django.conf import settings
from rag.retriever import retrieve_similar_verses, verify_verse_exists
from rag.embedder import get_active_api_key


# Base system prompt — instructs Gemini to stay grounded in scripture
SYSTEM_PROMPT = """You are Scripture Bot, a knowledgeable and respectful Christianity AI assistant.

STRICT RULES:
1. Answer questions ONLY using the Bible verses provided in the context below.
2. ALWAYS cite your sources using the format: Book Chapter:Verse (e.g., John 3:16).
3. If a user asks about a verse that does not exist in the provided context, clearly state: "This verse does not appear in the Bible database I have access to."
4. NEVER fabricate, invent, or guess Bible verses or references.
5. If you don't have enough context to answer, say so honestly.
6. Be warm, respectful, and pastoral in your tone.
7. When quoting scripture, use the exact text from the provided context.
8. You may explain and interpret verses, but always ground your explanation in the actual text.

{denomination_context}
"""

# Denomination-specific context additions
DENOMINATION_CONTEXTS = {
    'catholic': (
        "The user is asking from a Catholic perspective. "
        "When relevant, you may reference Catholic traditions such as: "
        "the Deuterocanonical books (Tobit, Judith, Wisdom, Sirach, Baruch, 1 & 2 Maccabees), "
        "the role of Sacred Tradition alongside Scripture, the Magisterium, "
        "Purgatory, the intercession of saints, and Marian doctrines. "
        "Be respectful of Catholic teaching while grounding answers in scripture."
    ),
    'protestant': (
        "The user is asking from a Protestant perspective. "
        "Focus on the 66-book Protestant canon. "
        "Emphasize Sola Scriptura (Scripture alone), salvation by grace through faith, "
        "and the priesthood of all believers. "
        "Be respectful of Protestant traditions while grounding answers in scripture."
    ),
    'orthodox': (
        "The user is asking from an Eastern Orthodox perspective. "
        "When relevant, reference Orthodox traditions such as: "
        "the importance of Holy Tradition alongside Scripture, "
        "the veneration (not worship) of icons, theosis (deification), "
        "the role of the Ecumenical Councils, and the Divine Liturgy. "
        "Be respectful of Orthodox teaching while grounding answers in scripture."
    ),
    'general': "",
}


def detect_denomination(message: str) -> str:
    """
    Detect if the user is asking from a specific denomination's perspective.

    Args:
        message: The user's message.

    Returns:
        One of: 'catholic', 'protestant', 'orthodox', 'general'.
    """
    message_lower = message.lower()

    catholic_keywords = ['catholic', 'catholicism', 'pope', 'mass', 'purgatory', 'rosary']
    protestant_keywords = ['protestant', 'lutheran', 'baptist', 'methodist', 'evangelical', 'reformed', 'presbyterian']
    orthodox_keywords = ['orthodox', 'eastern orthodox', 'greek orthodox', 'russian orthodox', 'icons']

    if any(kw in message_lower for kw in catholic_keywords):
        return 'catholic'
    elif any(kw in message_lower for kw in protestant_keywords):
        return 'protestant'
    elif any(kw in message_lower for kw in orthodox_keywords):
        return 'orthodox'

    return 'general'


def _detect_verse_reference(message: str) -> tuple[str, int, int] | None:
    """
    Try to parse a Bible verse reference from the message.

    Matches patterns like: John 3:16, 1 Corinthians 13:4, Psalm 23:1,
    Song of Solomon 2:1, 2 Kings 5:10
    """
    # Match: optional number prefix + book name (including multi-word) + chapter:verse
    pattern = r'(\d?\s*[A-Za-z]+(?:\s+(?:of\s+)?[A-Za-z]+)*?)\s+(\d+):(\d+)'
    matches = list(re.finditer(pattern, message))

    if not matches:
        return None

    # Use the last match — avoids capturing leading words like "What does"
    match = matches[-1]
    book = match.group(1).strip()
    chapter = int(match.group(2))
    verse = int(match.group(3))

    # Filter out common false-positive words that aren't book names
    false_positives = {'what', 'does', 'is', 'tell', 'me', 'about', 'the', 'say', 'read', 'find'}
    if book.lower() in false_positives:
        return None

    return (book, chapter, verse)


def generate_response(
    message: str,
    conversation_history: list[dict] | None = None,
    conversation_summary: str | None = None,
    denomination: str | None = None,
) -> dict:
    """
    Generate a RAG-grounded response to the user's message.

    Args:
        message: The user's current message.
        conversation_history: List of previous messages [{'role': 'user'/'assistant', 'content': '...'}]
        denomination: Override denomination context. If None, auto-detected from message.

    Returns:
        A dict with:
            - response: The AI's text response
            - verses_cited: List of verse references used
            - denomination: Detected denomination
            - is_verification: Whether this was a verse verification request
    """
    # Auto-detect denomination if not provided
    if denomination is None:
        denomination = detect_denomination(message)

    # Check if this is a verse verification request
    verse_ref = _detect_verse_reference(message)
    is_verification = any(
        kw in message.lower()
        for kw in ['is this real', 'does this exist', 'verify', 'is this a real verse', 'fake or real']
    )

    # Retrieve relevant verses via semantic search
    retrieved_verses = retrieve_similar_verses(message, top_k=5)

    # If a specific verse reference is detected, ALWAYS do a direct DB lookup
    # This ensures "What does John 3:16 say?" works even if semantic search misses it
    direct_lookup_result = None
    if verse_ref:
        book, chapter, verse = verse_ref
        direct_lookup_result = verify_verse_exists(book, chapter, verse)

        # Add the direct lookup result to retrieved verses if not already present
        if direct_lookup_result:
            already_in_results = any(
                v['reference'] == direct_lookup_result['reference']
                for v in retrieved_verses
            )
            if not already_in_results:
                retrieved_verses.insert(0, {
                    'reference': direct_lookup_result['reference'],
                    'text': direct_lookup_result['text'],
                    'score': 1.0,  # exact match
                })

    # Build context from retrieved verses
    context_lines = []
    for v in retrieved_verses:
        context_lines.append(f"- {v['reference']}: \"{v['text']}\" (similarity: {v['score']})")
    context_block = "\n".join(context_lines) if context_lines else "No relevant verses found."

    # Add verification info if applicable
    if direct_lookup_result and is_verification:
        context_block += f"\n\nVERIFICATION: The verse {direct_lookup_result['reference']} EXISTS in the Bible. Text: \"{direct_lookup_result['text']}\""
    elif verse_ref and is_verification:
        book, chapter, verse = verse_ref
        context_block += f"\n\nVERIFICATION: The verse {book} {chapter}:{verse} was NOT FOUND in the Bible database."

    # Build denomination context
    denom_context = DENOMINATION_CONTEXTS.get(denomination, '')

    # Inject conversational summary context if available
    if conversation_summary:
        denom_context += f"\n\nHere is a summary of the conversation history so far for your reference:\n{conversation_summary}"

    # Construct the system prompt
    system_prompt = SYSTEM_PROMPT.format(denomination_context=denom_context)

    # Build message list for LangChain
    messages = [SystemMessage(content=system_prompt)]

    # Add conversation history (last 10 messages for context window)
    if conversation_history:
        for msg in conversation_history[-10:]:
            if msg['role'] == 'user':
                messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                messages.append(AIMessage(content=msg['content']))

    # Add current user message with context
    user_prompt = f"""RETRIEVED BIBLE VERSES (use ONLY these as your source):
{context_block}

USER QUESTION: {message}"""

    messages.append(HumanMessage(content=user_prompt))

    # Call Gemini (using configurable model from settings)
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_LLM_MODEL,
        google_api_key=get_active_api_key(),
        temperature=0.3,
        max_output_tokens=1024,
    )

    response = llm.invoke(messages)

    # Extract cited verse references from the response
    verse_pattern = r'(\d?\s*[A-Za-z]+(?:\s+of\s+[A-Za-z]+)?\s+\d+:\d+)'
    # Clean up and deduplicate references
    cited_refs = list(set(
        match.group(0) for match in re.finditer(verse_pattern, response.content)
    ))

    # Generate updated conversation summary using direct LLM call
    new_summary = conversation_summary or ""
    try:
        summary_llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_LLM_MODEL,
            google_api_key=get_active_api_key(),
            temperature=0.0,
            max_output_tokens=256,
        )
        summary_prompt = (
            "Progressively summarize the lines of conversation provided, "
            "adding onto the previous summary returning a new summary.\n\n"
            f"Current summary:\n{conversation_summary or 'None yet.'}\n\n"
            f"New lines of conversation:\n"
            f"Human: {message}\n"
            f"AI: {response.content[:500]}\n\n"
            "New summary:"
        )
        summary_response = summary_llm.invoke([HumanMessage(content=summary_prompt)])
        new_summary = summary_response.content.strip()
    except Exception as sum_err:
        print(f"⚠️ Error generating conversation summary: {sum_err}")

    return {
        'response': response.content,
        'verses_cited': cited_refs,
        'denomination': denomination,
        'is_verification': is_verification,
        'conversation_summary': new_summary,
        'retrieved_verses': [
            {'reference': v['reference'], 'text': v['text'][:100] + '...'}
            for v in retrieved_verses[:3]
        ],
    }
