async function sendMessage() {
    const inputField = document.getElementById('user-input');
    const message = inputField.value.trim();
    if (!message) return;

    // Add user message
    addMessage(message, 'user-message');
    inputField.value = '';

    // Show typing indicator
    document.getElementById('typing-indicator').classList.remove('hidden');
    scrollToBottom();

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message, session_id: "user1" }),
        });

        const data = await response.json();

        // Hide typing indicator
        document.getElementById('typing-indicator').classList.add('hidden');

        if (response.ok) {
            // Check if response is null/undefined or empty
            const botText = data.response;
            if (botText) {
                addMessage(botText, 'bot-message');
            } else {
                addMessage("*Thinking...* (No text response)", 'bot-message');
            }
        } else {
            console.error('Server Error:', data);
            addMessage(`❌ Server Error: ${response.status}`, 'bot-message');
        }

    } catch (error) {
        console.error('Network Error:', error);
        document.getElementById('typing-indicator').classList.add('hidden');
        addMessage("⚠️ Network error. Please check if the backend is running.", 'bot-message');
    }
}

function addMessage(text, className) {
    const chatBox = document.getElementById('chat-box');

    // Wrapper
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', className);

    // Content Container
    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');

    // Avatar (only for bot)
    if (className === 'bot-message') {
        const avatar = document.createElement('div');
        avatar.classList.add('bot-avatar');
        avatar.innerHTML = '<i class="fa-solid fa-robot"></i>';
        contentDiv.appendChild(avatar);
    }

    // Bubble
    const bubble = document.createElement('div');
    bubble.classList.add('bubble');

    if (className === 'bot-message') {
        // Render Markdown for bot
        bubble.innerHTML = marked.parse(text);
    } else {
        // Plain text for user (prevention of XSS if we were persisting)
        bubble.innerText = text;
    }

    contentDiv.appendChild(bubble);
    messageDiv.appendChild(contentDiv);
    chatBox.appendChild(messageDiv);

    scrollToBottom();
}

function scrollToBottom() {
    const chatBox = document.getElementById('chat-box');
    chatBox.scrollTop = chatBox.scrollHeight;
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}
