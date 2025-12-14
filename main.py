import logging
from contextlib import asynccontextmanager

import google.generativeai as genai
from ddtrace import tracer
from fastapi import FastAPI, HTTPException, status
from google.api_core.exceptions import ResourceExhausted
from pydantic import BaseModel, Field

from config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    genai.configure(api_key=settings.gemini_api_key)
    app.state.model = genai.GenerativeModel(settings.gemini_model)
    logger.info(f"Started {settings.dd_service}")
    yield
    logger.info("Shutdown")


app = FastAPI(lifespan=lifespan)


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
    
    # Security check
    if any(kw.lower() in request.prompt.lower() for kw in settings.jailbreak_keywords):
        if span:
            span.set_tag("security.jailbreak_attempt", "true")
            span.error = 1
            span.set_tag("error.message", "Jailbreak keyword detected")
        
        logger.warning(f"Security violation: user_id={request.user_id}")
        return ChatResponse(
            response="I cannot comply with that request due to security policies."
        )
    
    try:
        response = app.state.model.generate_content(request.prompt)
        if span:
            span.set_tag("response.length", len(response.text))
        return ChatResponse(response=response.text)
    
    except ResourceExhausted as e:
        if span:
            span.set_exc_info(type(e), e, e.__traceback__)
        logger.error(f"Rate limit exceeded: user_id={request.user_id}")
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    
    except Exception as e:
        if span:
            span.set_exc_info(type(e), e, e.__traceback__)
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.dd_service}