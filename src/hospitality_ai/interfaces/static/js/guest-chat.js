// Guest Chat Interface - Hospitality AI
class GuestChat {
    constructor() {
        this.apiBaseUrl = window.location.origin;
        this.messages = [];
        this.isProcessing = false;
        
        this.initializeElements();
        this.bindEvents();
        this.loadChatHistory();
    }

    initializeElements() {
        this.chatMessages = document.getElementById('chat-messages');
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.sendText = document.getElementById('send-text');
        this.loadingSpinner = document.getElementById('loading-spinner');
        this.statusIndicator = document.getElementById('status-indicator');
        this.statusText = document.getElementById('status-text');
        this.guestIdSelect = document.getElementById('guest-id');
        this.quickButtons = document.querySelectorAll('.quick-btn');
    }

    bindEvents() {
        // Send button click
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Enter key to send
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Quick action buttons
        this.quickButtons.forEach(button => {
            button.addEventListener('click', () => {
                const message = button.getAttribute('data-message');
                this.messageInput.value = message;
                this.sendMessage();
            });
        });

        // Guest ID change
        this.guestIdSelect.addEventListener('change', () => {
            this.clearChatHistory();
            this.addSystemMessage('Switched to Guest ID: ' + this.guestIdSelect.value);
        });
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isProcessing) {
            return;
        }

        // Add guest message to chat
        this.addGuestMessage(message);
        this.clearInput();
        this.setProcessingState(true);

        try {
            const response = await this.callGuestAPI(message);
            this.handleAPIResponse(response);
        } catch (error) {
            this.handleError(error);
        } finally {
            this.setProcessingState(false);
        }
    }

    async callGuestAPI(message) {
        const guestId = this.guestIdSelect.value;
        
        const response = await fetch(`${this.apiBaseUrl}/guest/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                guest_id: guestId,
                message: message
            })
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

        return await response.json();
    }

    handleAPIResponse(response) {
        if (response.reply) {
            this.addSystemMessage(response.reply, response.action);
        } else {
            this.addSystemMessage('Received an unexpected response format', 'error');
        }
    }

    handleError(error) {
        console.error('Chat Error:', error);
        this.addSystemMessage('Sorry, I encountered an error. Please try again.', 'error');
        this.setStatus('Error occurred', 'error');
    }

    addGuestMessage(message) {
        const messageDiv = this.createMessageElement(message, 'guest');
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        this.saveMessageToHistory(message, 'guest');
    }

    addSystemMessage(message, action = null) {
        const messageDiv = this.createMessageElement(message, 'system', action);
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        this.saveMessageToHistory(message, 'system', action);
    }

    createMessageElement(content, type, action = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = content;

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = type === 'guest' ? 
            this.guestIdSelect.value : 
            new Date().toLocaleTimeString();

        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timeDiv);

        // Add action badge if present
        if (action) {
            const badge = this.createActionBadge(action);
            contentDiv.appendChild(badge);
        }

        return messageDiv;
    }

    createActionBadge(action) {
        const badge = document.createElement('span');
        badge.className = `action-badge action-${action}`;
        badge.textContent = action.replace('_', ' ');
        return badge;
    }

    clearInput() {
        this.messageInput.value = '';
        this.messageInput.focus();
    }

    setProcessingState(processing) {
        this.isProcessing = processing;
        this.sendButton.disabled = processing;
        
        if (processing) {
            this.sendText.style.display = 'none';
            this.loadingSpinner.style.display = 'block';
            this.setStatus('Processing...', 'processing');
        } else {
            this.sendText.style.display = 'block';
            this.loadingSpinner.style.display = 'none';
            this.setStatus('Ready', 'ready');
        }
    }

    setStatus(text, type = 'ready') {
        this.statusText.textContent = text;
        this.statusIndicator.className = `status-indicator ${type}`;
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    saveMessageToHistory(message, type, action = null) {
        const messageData = {
            content: message,
            type: type,
            action: action,
            timestamp: new Date().toISOString(),
            guestId: this.guestIdSelect.value
        };

        this.messages.push(messageData);
        localStorage.setItem(`guest_chat_${this.guestIdSelect.value}`, JSON.stringify(this.messages));
    }

    loadChatHistory() {
        const saved = localStorage.getItem(`guest_chat_${this.guestIdSelect.value}`);
        if (saved) {
            try {
                this.messages = JSON.parse(saved);
                this.messages.forEach(msg => {
                    if (msg.type === 'guest') {
                        this.addGuestMessage(msg.content);
                    } else {
                        this.addSystemMessage(msg.content, msg.action);
                    }
                });
            } catch (error) {
                console.error('Error loading chat history:', error);
            }
        }
    }

    clearChatHistory() {
        this.messages = [];
        this.chatMessages.innerHTML = '';
        localStorage.removeItem(`guest_chat_${this.guestIdSelect.value}`);
    }
}

// Initialize chat when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new GuestChat();
});