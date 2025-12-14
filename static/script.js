const chatInput = document.querySelector("#chat-input");
const sendButton = document.querySelector("#send-btn");
const chatContainer = document.querySelector(".chat-container");

const userId = 'user_' + Math.random().toString(36).substr(2, 9);
let userText = null;

let lastMessageCount = 0;
let isLoadingHistory = false;

// AJAX function to load chat history from server logs
async function loadChatHistory() {
    // Prevent multiple simultaneous AJAX requests
    if (isLoadingHistory) return;
    
    isLoadingHistory = true;
    
    try {
        // AJAX call to get message logs from backend
        const response = await fetch('http://localhost:8000/history', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.messages && data.messages.length > 0) {
            // Only update if there are new messages (efficient update)
            if (data.messages.length !== lastMessageCount) {
                // Remove welcome screen
                removeWelcomeScreen();
                
                // Clear existing messages to refresh with latest logs
                const welcomeScreen = chatContainer.querySelector('.welcome-screen');
                if (!welcomeScreen) {
                    chatContainer.innerHTML = '';
                }
                
                // Render all messages from log
                data.messages.forEach(msg => {
                    const className = msg.role === "user" ? "outgoing" : "incoming";
                    const html = `<p>${msg.content}</p>`;
                    const chatDiv = createChatElement(html, className);
                    chatContainer.appendChild(chatDiv);
                });
                
                lastMessageCount = data.messages.length;
                
                // Scroll to bottom to show latest messages
                chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
            }
        }
    } catch (error) {
        console.error('AJAX request failed:', error);
    } finally {
        isLoadingHistory = false;
    }
}

// Load history when page loads
document.addEventListener('DOMContentLoaded', () => {
    loadChatHistory();
    // Initialize Lucide icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
});

const createChatElement = (content, className) => {
    const chatWrapper = document.createElement("div");
    chatWrapper.classList.add("chat-wrapper");
    
    const chatDiv = document.createElement("div");
    chatDiv.classList.add("chat", className);
    
    const avatarIcon = className === "outgoing" ? "user" : "sparkles";
    
    chatDiv.innerHTML = `
        <div class="chat-avatar">
            <i data-lucide="${avatarIcon}"></i>
        </div>
        <div class="chat-details">
            ${content}
        </div>
    `;
    
    chatWrapper.appendChild(chatDiv);
    
    // Initialize Lucide icon after adding to DOM
    setTimeout(() => {
        lucide.createIcons();
    }, 0);
    
    return chatWrapper;
}

const removeWelcomeScreen = () => {
    const welcomeScreen = chatContainer.querySelector('.welcome-screen');
    if (welcomeScreen) {
        welcomeScreen.style.opacity = '0';
        setTimeout(() => welcomeScreen.remove(), 200);
    }
}

// AJAX function to send message and get response
const getChatResponse = async (incomingChatDiv) => {
    const API_URL = "http://localhost:8000/chat";
    const chatDetails = incomingChatDiv.querySelector(".chat-details");

    try {
        // Send AJAX POST request to chat endpoint
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                prompt: userText,
                user_id: userId
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || "Something went wrong");
        }
        
        // Replace typing animation with response received from AJAX
        chatDetails.innerHTML = `<p>${data.response}</p>`;
        
        // Reload logs via AJAX to show the new message in the log
        setTimeout(() => {
            loadChatHistory();
        }, 1000);
        
    } catch (error) {
        console.error('AJAX chat request failed:', error);
        chatDetails.innerHTML = `<p style="color: #ef4444;">Oops! Something went wrong. Please try again.</p>`;
    }

    chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
}

const showTypingAnimation = () => {
    const html = `
        <div class="typing-animation">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    
    const incomingChatDiv = createChatElement(html, "incoming");
    chatContainer.appendChild(incomingChatDiv);
    chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
    getChatResponse(incomingChatDiv);
}

const handleOutgoingChat = async () => {
    userText = chatInput.value.trim();
    if (!userText) return;

    // Remove welcome screen if it exists
    removeWelcomeScreen();

    // Clear input field and reset height
    chatInput.value = "";
    chatInput.style.height = "auto";

    // Display user's message immediately (optimistic UI)
    const html = `<p>${userText}</p>`;
    const outgoingChatDiv = createChatElement(html, "outgoing");
    chatContainer.appendChild(outgoingChatDiv);
    chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
    
    // Show typing animation then send AJAX request
    setTimeout(showTypingAnimation, 500);
}

// Event listeners
sendButton.addEventListener("click", handleOutgoingChat);

chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleOutgoingChat();
    }
});

// Auto-resize textarea
chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = `${chatInput.scrollHeight}px`;
});

const POLL_INTERVAL = 3000;

setInterval(() => {
    loadChatHistory(); // AJAX call to fetch latest logs
}, POLL_INTERVAL);

console.log(`🔄 AJAX polling enabled: fetching message logs every ${POLL_INTERVAL/1000}s`);
