async function sendMessage() {
    const inputField = document.getElementById('user-input');
    const message = inputField.value.trim();
    if (!message) return;

    // Get selected model
    const modelSelect = document.getElementById('model-select');
    const selectedModel = modelSelect ? modelSelect.value : "gemini-1.5-flash";

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
            body: JSON.stringify({
                message: message,
                session_id: "user1",
                model_name: selectedModel
            }),
        });

        // Hide typing indicator immediately as we will show status updates
        document.getElementById('typing-indicator').classList.add('hidden');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        let thinkingId = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            // Handle multiple lines in one chunk
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (!line.trim()) continue;

                try {
                    const data = JSON.parse(line);

                    if (data.type === 'status') {
                        // Update or Create "Thinking" bubble
                        if (!thinkingId) {
                            thinkingId = addMessage("", 'bot-message', true); // true = raw/html mode or status
                        }
                        // Update the content of the thinking bubble
                        updateMessage(thinkingId, `<i class="fa-solid fa-gear fa-spin"></i> ${data.content}`);
                    }
                    else if (data.type === 'response') {
                        // Remove thinking bubble or turn it into response?
                        // Better: Keep thinking history? No, user wants to see what it's doing.
                        // Let's finalize the thinking bubble and add a NEW bubble for response
                        // OR replace the thinking bubble if it was just a placeholder.
                        if (thinkingId) {
                            // Allow it to stay as log, or remove? 
                            // Let's keep it as "Process" log.
                            // Actually, let's remove the spinner from it.
                            updateMessage(thinkingId, `<i class="fa-solid fa-check"></i> ${document.getElementById(thinkingId).innerText}`);
                        }
                        addMessage(data.content, 'bot-message');
                    }
                    else if (data.type === 'error') {
                        addMessage(data.content, 'bot-message');
                    }
                } catch (e) {
                    console.error("Error parsing JSON chunk", e);
                }
            }
        }

    } catch (error) {
        console.error('Network Error:', error);
        document.getElementById('typing-indicator').classList.add('hidden');
        addMessage("⚠️ Network error. Please check if the backend is running.", 'bot-message');
    }
}

function addMessage(text, className, isStatus = false) {
    const chatBox = document.getElementById('chat-box');
    const msgId = 'msg-' + Date.now() + Math.random().toString(36).substr(2, 9);

    // Wrapper
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', className);
    messageDiv.id = msgId; // Set unique ID

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
    // ID for bubble content update
    bubble.id = msgId + '-bubble';

    if (className === 'bot-message') {
        if (isStatus) {
            bubble.innerHTML = text; // HTML for icons
            bubble.style.fontStyle = 'italic';
            bubble.style.color = '#666';
            bubble.style.background = '#f8f9fa';
        } else {
            bubble.innerHTML = marked.parse(text);
        }
    } else {
        bubble.innerText = text;
    }

    contentDiv.appendChild(bubble);
    messageDiv.appendChild(contentDiv);
    chatBox.appendChild(messageDiv);

    scrollToBottom();
    return bubble.id; // Return the internal bubble ID
}

function updateMessage(elementId, htmlContent) {
    const el = document.getElementById(elementId);
    if (el) {
        el.innerHTML = htmlContent;
        scrollToBottom();
    }
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

// UI Functions
function switchView(viewName) {
    // Hide all views
    document.querySelectorAll('.view-section').forEach(el => {
        el.classList.remove('active-view');
        el.classList.add('hidden');
    });

    // Show selected view
    const target = document.getElementById(viewName + '-view');
    if (target) {
        target.classList.remove('hidden');
        target.classList.add('active-view');
    }

    // Update nav state
    document.querySelectorAll('.nav-links a').forEach(el => el.classList.remove('active'));
    document.getElementById('nav-' + viewName).classList.add('active');
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.querySelectorAll('.theme-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById('theme-' + theme).classList.add('active');
}

function usePrompt(text) {
    switchView('chat');
    document.getElementById('user-input').value = text;
    // Optional: Auto send
    // sendMessage();
}
