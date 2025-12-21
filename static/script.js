const chatInput = document.querySelector("#chat-input");
const sendButton = document.querySelector("#send-btn");
const chatContainer = document.querySelector(".chat-container");

const userId = 'user_' + Math.random().toString(36).substr(2, 9);
let userText = null;

let lastMessageCount = 0;
let isLoadingHistory = false;

async function loadChatHistory() {
    if (isLoadingHistory) return;
    
    isLoadingHistory = true;
    
    try {
        const response = await fetch('/history', {
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
            if (data.messages.length !== lastMessageCount) {
                removeWelcomeScreen();
                
                const welcomeScreen = chatContainer.querySelector('.welcome-screen');
                if (!welcomeScreen) {
                    chatContainer.innerHTML = '';
                }
                
                data.messages.forEach(msg => {
                    const className = msg.role === "user" ? "outgoing" : "incoming";
                    const html = `<p>${msg.content}</p>`;
                    const chatDiv = createChatElement(html, className);
                    chatContainer.appendChild(chatDiv);
                });
                
                lastMessageCount = data.messages.length;
                
                chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
            }
        }
    } catch (error) {
        console.error('AJAX request failed:', error);
    } finally {
        isLoadingHistory = false;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadChatHistory();
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

const getChatResponse = async (incomingChatDiv) => {
    const API_URL = "/chat";
    const chatDetails = incomingChatDiv.querySelector(".chat-details");

    try {
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
        
        chatDetails.innerHTML = `<p>${data.response}</p>`;
        
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
    if (isGeneratingTraffic) {
        console.log("Traffic generation in progress, ignoring chat input");
        return;
    }
    
    userText = chatInput.value.trim();
    if (!userText) return;

    removeWelcomeScreen();

    chatInput.value = "";
    chatInput.style.height = "auto";

    const html = `<p>${userText}</p>`;
    const outgoingChatDiv = createChatElement(html, "outgoing");
    chatContainer.appendChild(outgoingChatDiv);
    chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
    
    setTimeout(showTypingAnimation, 500);
}

sendButton.addEventListener("click", handleOutgoingChat);

chatInput.addEventListener("keydown", (e) => {
    if (isGeneratingTraffic) {
        e.preventDefault();
        return;
    }
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleOutgoingChat();
    }
});

chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = `${chatInput.scrollHeight}px`;
});

const POLL_INTERVAL = 3000;

setInterval(() => {
    loadChatHistory();
}, POLL_INTERVAL);

console.log(`🔄 AJAX polling enabled: fetching message logs every ${POLL_INTERVAL/1000}s`);

let trafficBtn;
let loadingOverlay;
let isGeneratingTraffic = false;

function getElements() {
    if (!trafficBtn) trafficBtn = document.querySelector("#traffic-btn");
    if (!loadingOverlay) loadingOverlay = document.querySelector("#loading-overlay");
}

function showLoading() {
    getElements();
    
    if (!loadingOverlay) {
        loadingOverlay = document.querySelector("#loading-overlay");
    }
    if (!chatInput) {
        chatInput = document.querySelector("#chat-input");
    }
    if (!sendButton) {
        sendButton = document.querySelector("#send-btn");
    }
    if (!trafficBtn) {
        trafficBtn = document.querySelector("#traffic-btn");
    }
    
    if (!loadingOverlay || !chatInput || !sendButton || !trafficBtn) {
        console.error("Required elements not found:", {
            loadingOverlay: !!loadingOverlay,
            chatInput: !!chatInput,
            sendButton: !!sendButton,
            trafficBtn: !!trafficBtn
        });
        return;
    }
    
    isGeneratingTraffic = true;
    loadingOverlay.style.display = "flex";
    loadingOverlay.classList.add("active");
    chatInput.disabled = true;
    sendButton.disabled = true;
    trafficBtn.disabled = true;
    const span = trafficBtn.querySelector("span");
    if (span) span.textContent = "Generating...";
    
    console.log("Loading overlay shown");
}

function hideLoading() {
    getElements();
    
    if (!loadingOverlay) {
        loadingOverlay = document.querySelector("#loading-overlay");
    }
    if (!chatInput) {
        chatInput = document.querySelector("#chat-input");
    }
    if (!sendButton) {
        sendButton = document.querySelector("#send-btn");
    }
    if (!trafficBtn) {
        trafficBtn = document.querySelector("#traffic-btn");
    }
    
    if (!loadingOverlay || !chatInput || !sendButton || !trafficBtn) {
        return;
    }
    
    isGeneratingTraffic = false;
    loadingOverlay.classList.remove("active");
    loadingOverlay.style.display = "none";
    chatInput.disabled = false;
    sendButton.disabled = false;
    trafficBtn.disabled = false;
    const span = trafficBtn.querySelector("span");
    if (span) span.textContent = "Generate Traffic";
    
    console.log("Loading overlay hidden");
}

async function generateTraffic() {
    if (isGeneratingTraffic) {
        return;
    }

    showLoading();

    try {
        const response = await fetch("/generate-traffic?num_requests=10&delay=2", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            }
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: "Unknown error" }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log("Traffic generation started:", data);

        const estimatedTime = (data.num_requests * data.delay_seconds) + 10;
        
        getElements();
        const loadingText = loadingOverlay?.querySelector(".loading-text");
        if (loadingText) {
            let secondsRemaining = estimatedTime;
            
            const progressInterval = setInterval(() => {
                secondsRemaining--;
                if (secondsRemaining > 0) {
                    loadingText.textContent = `Generating ${data.num_requests} requests... ${secondsRemaining}s remaining`;
                } else {
                    loadingText.textContent = "Finishing up...";
                }
            }, 1000);

            setTimeout(() => {
                clearInterval(progressInterval);
                if (loadingText) {
                    loadingText.textContent = "Complete!";
                }
                setTimeout(() => {
                    hideLoading();
                    console.log("Traffic generation completed");
                }, 1000);
            }, estimatedTime * 1000);
        } else {
            setTimeout(() => {
                hideLoading();
            }, estimatedTime * 1000);
        }

    } catch (error) {
        console.error("Failed to generate traffic:", error);
        const loadingText = loadingOverlay.querySelector(".loading-text");
        loadingText.textContent = `Error: ${error.message}`;
        
        setTimeout(() => {
            hideLoading();
        }, 3000);
    }
}

function setupTrafficButton() {
    getElements();
    if (trafficBtn) {
        trafficBtn.addEventListener("click", (e) => {
            e.preventDefault();
            console.log("🚀 Traffic button clicked");
            generateTraffic();
        });
        console.log("✅ Traffic button initialized");
    } else {
        console.error("❌ Traffic button not found! Retrying...");
        setTimeout(setupTrafficButton, 100);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupTrafficButton);
} else {
    setupTrafficButton();
}
