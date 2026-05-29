/**
 * Scripture Bot — Chat Interface Logic
 *
 * Handles message sending, response rendering, image display,
 * denomination switching, and conversation flow.
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const messagesArea = document.getElementById('messages-area');
    const chatContainer = document.getElementById('chat-container');
    const typingIndicator = document.getElementById('typing-indicator');
    const welcomeCard = document.getElementById('welcome-card');
    const denominationChips = document.querySelectorAll('.chip');
    const suggestionBtns = document.querySelectorAll('.suggestion-btn');

    // State
    let selectedDenomination = 'general';
    let isLoading = false;

    // --- CSRF Token ---
    function getCSRFToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                return decodeURIComponent(cookie.substring(name.length + 1));
            }
        }
        return '';
    }

    // --- Auto-resize textarea ---
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
    });

    // --- Send on Enter (Shift+Enter for new line) ---
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // --- Send button click ---
    sendBtn.addEventListener('click', sendMessage);

    // --- Denomination chip switching ---
    denominationChips.forEach(chip => {
        chip.addEventListener('click', () => {
            denominationChips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            selectedDenomination = chip.dataset.denomination;
        });
    });

    // --- Suggestion buttons ---
    suggestionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            messageInput.value = btn.dataset.message;
            sendMessage();
        });
    });

    // --- Main send function ---
    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message || isLoading) return;

        isLoading = true;
        sendBtn.disabled = true;

        // Hide welcome card
        if (welcomeCard) {
            welcomeCard.style.display = 'none';
        }

        // Add user message to chat
        appendMessage('user', message);

        // Clear input
        messageInput.value = '';
        messageInput.style.height = 'auto';

        // Show typing indicator
        typingIndicator.style.display = 'flex';
        scrollToBottom();

        try {
            const response = await fetch('/api/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken(),
                },
                body: JSON.stringify({ message: message }),
            });

            const data = await response.json();

            // Hide typing indicator
            typingIndicator.style.display = 'none';

            if (data.type === 'image') {
                appendMessage('bot', data.response, {
                    imageUrl: data.image_url,
                    type: 'image',
                });
            } else if (data.type === 'moderated') {
                appendMessage('bot', data.response, {
                    type: 'moderated',
                });
            } else {
                appendMessage('bot', data.response, {
                    versesCited: data.verses_cited || [],
                    denomination: data.denomination,
                    type: 'text',
                });
            }

        } catch (error) {
            typingIndicator.style.display = 'none';
            appendMessage('bot', 'Sorry, something went wrong. Please try again.', {
                type: 'error',
            });
            console.error('Chat error:', error);
        }

        isLoading = false;
        sendBtn.disabled = false;
        messageInput.focus();
    }

    // --- Append message to chat ---
    function appendMessage(role, content, options = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        if (options.type === 'moderated') {
            messageDiv.classList.add('moderated');
        }

        // Avatar
        const avatar = document.createElement('div');
        avatar.className = role === 'bot' ? 'bot-avatar' : 'user-avatar';
        avatar.textContent = role === 'bot' ? '✝' : '👤';

        // Bubble
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';

        // Format content (convert markdown-like bold and line breaks)
        bubble.innerHTML = formatContent(content);

        // Add image if present
        if (options.imageUrl) {
            const img = document.createElement('img');
            img.className = 'message-image';
            img.src = options.imageUrl;
            img.alt = 'Generated biblical artwork';
            img.loading = 'lazy';
            img.addEventListener('click', () => openLightbox(options.imageUrl));
            img.addEventListener('error', () => {
                img.alt = 'Image is still generating... click to refresh';
                img.style.minHeight = '200px';
                img.style.background = 'var(--bg-tertiary)';
                img.style.display = 'flex';
            });
            bubble.appendChild(img);
        }

        // Add verse citations if present
        if (options.versesCited && options.versesCited.length > 0) {
            const citationsDiv = document.createElement('div');
            citationsDiv.className = 'verse-citations';
            options.versesCited.forEach(ref => {
                const badge = document.createElement('span');
                badge.className = 'verse-badge';
                badge.textContent = `📖 ${ref}`;
                citationsDiv.appendChild(badge);
            });
            bubble.appendChild(citationsDiv);
        }

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(bubble);
        messagesArea.appendChild(messageDiv);

        scrollToBottom();
    }

    // --- Format text content ---
    function formatContent(text) {
        if (!text) return '';

        // Escape HTML
        let formatted = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // Bold: **text** or *text*
        formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');

        // Line breaks
        formatted = formatted.replace(/\n\n/g, '</p><p>');
        formatted = formatted.replace(/\n/g, '<br>');
        formatted = `<p>${formatted}</p>`;

        return formatted;
    }

    // --- Scroll to bottom ---
    function scrollToBottom() {
        requestAnimationFrame(() => {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        });
    }

    // --- Image lightbox ---
    function openLightbox(imageUrl) {
        const overlay = document.createElement('div');
        overlay.className = 'lightbox-overlay';

        const img = document.createElement('img');
        img.className = 'lightbox-image';
        img.src = imageUrl;
        img.alt = 'Full size biblical artwork';

        overlay.appendChild(img);
        document.body.appendChild(overlay);

        overlay.addEventListener('click', () => {
            overlay.remove();
        });
    }

    // --- Focus input on page load ---
    messageInput.focus();
});
