class ChatbotApp {
    constructor() {
        this.baseUrl = 'http://localhost:8000';
        this.currentSessionId = null;
        this.sessions = JSON.parse(localStorage.getItem('chatSessions')) || {};
        this.currentMessages = [];
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadSessions();
        this.showWelcomeScreen();
    }
    
    bindEvents() {
        // Action cards
        document.getElementById('upload-card').addEventListener('click', () => this.handleFileUpload());
        document.getElementById('chat-card').addEventListener('click', () => this.startNewTextChat());
        
        // New chat button
        document.getElementById('new-chat-btn').addEventListener('click', () => this.showWelcomeScreen());
        
        // File input
        document.getElementById('file-input').addEventListener('change', (e) => this.processFileUpload(e));
        
        // Message input
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        
        messageInput.addEventListener('input', (e) => {
            sendBtn.disabled = !e.target.value.trim();
        });
        
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !sendBtn.disabled) {
                this.sendMessage();
            }
        });
        
        sendBtn.addEventListener('click', () => this.sendMessage());
        
        // Section toggle
        document.querySelectorAll('.section-header').forEach(header => {
            header.addEventListener('click', (e) => this.toggleSection(e.target.closest('.section-header')));
        });
    }
    
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    showWelcomeScreen() {
        this.currentSessionId = null;
        this.currentMessages = [];
        
        document.getElementById('welcome-screen').style.display = 'flex';
        document.getElementById('chat-messages').style.display = 'none';
        document.getElementById('input-area').style.display = 'none';
        
        // Clear active session highlights
        document.querySelectorAll('.chat-item.active').forEach(item => {
            item.classList.remove('active');
        });
    }
    
    showChatInterface(sessionId) {
        this.currentSessionId = sessionId;
        
        document.getElementById('welcome-screen').style.display = 'none';
        document.getElementById('chat-messages').style.display = 'flex';
        document.getElementById('input-area').style.display = 'block';
        
        this.loadMessages(sessionId);
        this.highlightActiveSession(sessionId);
    }
    
    handleFileUpload() {
        document.getElementById('file-input').click();
    }
    
    async processFileUpload(event) {
        const file = event.target.files[0];
        if (!file || file.type !== 'application/pdf') {
            alert('Please select a PDF file');
            return;
        }
        
        const sessionId = this.generateSessionId();
        this.showLoading();
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/upload`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Create new session
            const session = {
                id: sessionId,
                title: file.name,
                type: 'file',
                createdAt: new Date().toISOString(),
                messages: [
                    {
                        type: 'system',
                        content: `File "${file.name}" uploaded successfully`,
                        timestamp: new Date().toISOString()
                    },
                    {
                        type: 'assistant',
                        content: data.content,
                        timestamp: new Date().toISOString(),
                        stage: data.current_stage
                    }
                ]
            };
            
            this.sessions[sessionId] = session;
            this.saveSessionsToStorage();
            this.addSessionToSidebar(session);
            this.showChatInterface(sessionId);
            
        } catch (error) {
            console.error('File upload error:', error);
            alert('Failed to upload file. Please try again.');
        } finally {
            this.hideLoading();
            // Reset file input
            event.target.value = '';
        }
    }
    
    startNewTextChat() {
        const sessionId = this.generateSessionId();
        
        // Create new session
        const session = {
            id: sessionId,
            title: 'New Chat',
            type: 'text',
            createdAt: new Date().toISOString(),
            messages: []
        };
        
        this.sessions[sessionId] = session;
        this.saveSessionsToStorage();
        this.addSessionToSidebar(session);
        this.showChatInterface(sessionId);
        
        // Focus on input
        document.getElementById('message-input').focus();
    }
    
    async sendMessage() {
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();
        
        if (!message || !this.currentSessionId) return;
        
        const session = this.sessions[this.currentSessionId];
        const isInitialMessage = session.messages.length === 0;
        
        // Add user message to UI immediately
        const userMessage = {
            type: 'user',
            content: message,
            timestamp: new Date().toISOString()
        };
        
        session.messages.push(userMessage);
        this.addMessageToUI(userMessage);
        
        // Update session title if it's the first message
        if (isInitialMessage && session.type === 'text') {
            session.title = message.length > 50 ? message.substring(0, 50) + '...' : message;
            this.updateSessionInSidebar(session);
        }
        
        // Clear and disable input
        messageInput.value = '';
        document.getElementById('send-btn').disabled = true;
        
        this.showLoading();
        
        try {
            const endpoint = isInitialMessage ? 'initial-input' : 'input';
            const payload = isInitialMessage 
                ? { initial_input: message }
                : { user_input: message };
            
            const response = await fetch(`${this.baseUrl}/sessions/${this.currentSessionId}/${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Add assistant response
            const assistantMessage = {
                type: 'assistant',
                content: data.content,
                timestamp: new Date().toISOString(),
                stage: data.current_stage
            };
            
            session.messages.push(assistantMessage);
            this.addMessageToUI(assistantMessage);
            
            this.saveSessionsToStorage();
            
        } catch (error) {
            console.error('Send message error:', error);
            
            // Add error message
            const errorMessage = {
                type: 'system',
                content: 'Failed to send message. Please check your connection and try again.',
                timestamp: new Date().toISOString()
            };
            
            session.messages.push(errorMessage);
            this.addMessageToUI(errorMessage);
        } finally {
            this.hideLoading();
        }
    }
    
    addMessageToUI(message) {
        const messagesContainer = document.getElementById('chat-messages');
        const messageElement = document.createElement('div');
        messageElement.className = `message ${message.type}`;
        messageElement.textContent = message.content;
        
        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    loadMessages(sessionId) {
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = '';
        
        const session = this.sessions[sessionId];
        if (session && session.messages) {
            session.messages.forEach(message => {
                this.addMessageToUI(message);
            });
        }
    }
    
    loadSessions() {
        const fileChatsContainer = document.getElementById('file-chats');
        const textChatsContainer = document.getElementById('text-chats');
        
        // Clear existing sessions
        fileChatsContainer.innerHTML = '';
        textChatsContainer.innerHTML = '';
        
        // Sort sessions by creation date (newest first)
        const sortedSessions = Object.values(this.sessions).sort((a, b) => 
            new Date(b.createdAt) - new Date(a.createdAt)
        );
        
        sortedSessions.forEach(session => {
            this.addSessionToSidebar(session);
        });
    }
    
    addSessionToSidebar(session) {
        const container = session.type === 'file' 
            ? document.getElementById('file-chats')
            : document.getElementById('text-chats');
        
        const sessionElement = document.createElement('div');
        sessionElement.className = 'chat-item';
        sessionElement.textContent = session.title;
        sessionElement.dataset.sessionId = session.id;
        
        sessionElement.addEventListener('click', () => {
            this.showChatInterface(session.id);
        });
        
        // Insert at the beginning (newest first)
        container.insertBefore(sessionElement, container.firstChild);
    }
    
    updateSessionInSidebar(session) {
        const sessionElement = document.querySelector(`[data-session-id="${session.id}"]`);
        if (sessionElement) {
            sessionElement.textContent = session.title;
        }
    }
    
    highlightActiveSession(sessionId) {
        // Remove previous highlights
        document.querySelectorAll('.chat-item.active').forEach(item => {
            item.classList.remove('active');
        });
        
        // Highlight current session
        const sessionElement = document.querySelector(`[data-session-id="${sessionId}"]`);
        if (sessionElement) {
            sessionElement.classList.add('active');
        }
    }
    
    toggleSection(sectionHeader) {
        const sectionName = sectionHeader.dataset.section;
        const chatList = document.getElementById(sectionName);
        const isCollapsed = sectionHeader.classList.contains('collapsed');
        
        if (isCollapsed) {
            sectionHeader.classList.remove('collapsed');
            chatList.classList.remove('collapsed');
        } else {
            sectionHeader.classList.add('collapsed');
            chatList.classList.add('collapsed');
        }
    }
    
    saveSessionsToStorage() {
        localStorage.setItem('chatSessions', JSON.stringify(this.sessions));
    }
    
    showLoading() {
        document.getElementById('loading-overlay').style.display = 'flex';
    }
    
    hideLoading() {
        document.getElementById('loading-overlay').style.display = 'none';
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ChatbotApp();
});