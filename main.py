import logging
from contextlib import asynccontextmanager
from collections import deque
from datetime import datetime

import google.generativeai as genai
from ddtrace import tracer
from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from google.api_core.exceptions import ResourceExhausted
from pydantic import BaseModel, Field

from config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

# Store recent chat history (last 50 messages)
chat_history = deque(maxlen=50)


@asynccontextmanager
async def lifespan(app: FastAPI):
    genai.configure(api_key=settings.gemini_api_key)
    app.state.model = genai.GenerativeModel(settings.gemini_model)
    logger.info(f"Started {settings.dd_service}")
    yield
    logger.info("Shutdown")


app = FastAPI(lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)
    user_id: str = Field(..., min_length=1, max_length=255)


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    span = tracer.current_span()
    
    if span:
        span.set_tag("user.id", request.user_id)
        span.set_tag("prompt.length", len(request.prompt))
    
    # Store user message in history
    chat_history.append({
        "role": "user",
        "content": request.prompt,
        "user_id": request.user_id,
        "timestamp": datetime.now().isoformat()
    })
    
    # Security check
    if any(kw.lower() in request.prompt.lower() for kw in settings.jailbreak_keywords):
        if span:
            span.set_tag("security.jailbreak_attempt", "true")
            span.error = 1
            span.set_tag("error.message", "Jailbreak keyword detected")
        
        logger.warning(f"Security violation: user_id={request.user_id}")
        security_response = "I cannot comply with that request due to security policies."
        
        # Store blocked response in history
        chat_history.append({
            "role": "assistant",
            "content": security_response,
            "user_id": request.user_id,
            "timestamp": datetime.now().isoformat(),
            "blocked": True
        })
        
        return ChatResponse(response=security_response)
    
    try:
        response = app.state.model.generate_content(request.prompt)
        if span:
            span.set_tag("response.length", len(response.text))
        
        # Store assistant response in history
        chat_history.append({
            "role": "assistant",
            "content": response.text,
            "user_id": request.user_id,
            "timestamp": datetime.now().isoformat()
        })
        
        return ChatResponse(response=response.text)
    
    except ResourceExhausted as e:
        if span:
            span.set_exc_info(type(e), e, e.__traceback__)
        logger.error(f"Rate limit exceeded: user_id={request.user_id}")
        
        # Store error in history
        chat_history.append({
            "role": "assistant",
            "content": "Rate limit exceeded. Please try again later.",
            "user_id": request.user_id,
            "timestamp": datetime.now().isoformat(),
            "error": True
        })
        
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    
    except Exception as e:
        if span:
            span.set_exc_info(type(e), e, e.__traceback__)
        logger.error(f"Error: {e}", exc_info=True)
        
        # Store error in history
        chat_history.append({
            "role": "assistant",
            "content": f"Error: {str(e)}",
            "user_id": request.user_id,
            "timestamp": datetime.now().isoformat(),
            "error": True
        })
        
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/history")
async def get_chat_history():
    """Return recent chat history for display on frontend."""
    return {"messages": list(chat_history)}


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.dd_service}


@app.get("/")
async def root():
    response = FileResponse("static/index.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response