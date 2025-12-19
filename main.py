import sys
import logging
import hashlib
from contextlib import asynccontextmanager
from collections import deque
from datetime import datetime
from typing import Optional

import redis
import google.generativeai as genai
from ddtrace import tracer
from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from google.api_core.exceptions import ResourceExhausted
from pydantic import BaseModel, Field

from config import get_settings
from timezone_formatter import SingaporeJsonFormatter

# Create the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# This creates a file named 'app.log' in your project folder
fileHandler = logging.FileHandler('/tmp/app.log') 
formatter = SingaporeJsonFormatter('%(timestamp)s %(levelname)s %(message)s ', timestamp=True)
fileHandler.setFormatter(formatter)
logger.addHandler(fileHandler)

# 2. Console Handler (For you to see in terminal)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
logger.addHandler(consoleHandler)

settings = get_settings()

chat_history = deque(maxlen=50)

redis_client: Optional[redis.Redis] = None
cache_stats = {"hits": 0, "misses": 0, "errors": 0}


def get_redis_client() -> Optional[redis.Redis]:
    global redis_client
    
    if redis_client is None:
        try:
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            redis_client.ping()
            logger.info(f"Redis connected: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis connection failed: {e}")
            redis_client = None
        except Exception as e:
            logger.error(f"Unexpected Redis error: {e}")
            redis_client = None
    
    return redis_client


def get_cache_key(prompt: str) -> str:
    prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
    return f"gemini:response:{prompt_hash}"


def get_cached_response(prompt: str) -> Optional[str]:
    client = get_redis_client()
    if client is None:
        cache_stats["errors"] += 1
        return None
    
    try:
        cache_key = get_cache_key(prompt)
        cached = client.get(cache_key)
        
        if cached:
            cache_stats["hits"] += 1
            logger.info(f"Cache hit: {cache_key[:20]}...")
            return cached
        else:
            cache_stats["misses"] += 1
            logger.info(f"Cache miss: {cache_key[:20]}...")
            return None
            
    except (redis.ConnectionError, redis.TimeoutError) as e:
        cache_stats["errors"] += 1
        logger.error(f"Cache read error: {e}")
        return None
    except redis.RedisError as e:
        cache_stats["errors"] += 1
        logger.error(f"Redis error during read: {e}")
        return None


def cache_response(prompt: str, response: str) -> bool:
    client = get_redis_client()
    if client is None:
        cache_stats["errors"] += 1
        return False
    
    try:
        cache_key = get_cache_key(prompt)
        client.setex(
            cache_key,
            settings.CACHE_TTL_SECONDS,
            response
        )
        logger.info(f"Cached response: {cache_key[:20]}... (TTL: {settings.CACHE_TTL_SECONDS}s)")
        return True
        
    except (redis.ConnectionError, redis.TimeoutError) as e:
        cache_stats["errors"] += 1
        logger.error(f"Cache write error: {e}")
        return False
    except redis.RedisError as e:
        cache_stats["errors"] += 1
        logger.error(f"Redis error during write: {e}")
        return False


def get_cache_stats() -> dict:
    total = cache_stats["hits"] + cache_stats["misses"]
    hit_rate = (cache_stats["hits"] / total * 100) if total > 0 else 0
    
    return {
        "hits": cache_stats["hits"],
        "misses": cache_stats["misses"],
        "errors": cache_stats["errors"],
        "hit_rate_percent": round(hit_rate, 2),
        "total_requests": total
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Things here happen before startup
    genai.configure(api_key=settings.GEMINI_API_KEY)
    app.state.model = genai.GenerativeModel(settings.GEMINI_MODEL)
    
    get_redis_client()
    
    logger.info(f"Started {settings.DD_SERVICE}")
    
    # passes control to the app
    yield
    
    # Things here happen on shutdown
    global redis_client
    if redis_client:
        redis_client.close()
        logger.info("Redis connection closed")
    
    logger.info("Shutdown")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    
    chat_history.append({
        "role": "user",
        "content": request.prompt,
        "user_id": request.user_id,
        "timestamp": datetime.now().isoformat()
    })
    
    if any(kw.lower() in request.prompt.lower() for kw in settings.JAILBREAK_KEYWORDS):
        if span:
            span.set_tag("security.jailbreak_attempt", "true")
            span.error = 1
            span.set_tag("error.message", "Jailbreak keyword detected")
        
        logger.warning(f"Security violation: user_id={request.user_id}", extra={
            "user_id": request.user_id,   # So dat you can filter by user in logs or wherever in Datadog
            "event_type": "jailbreak"     # Can also filter by event type
        } )
        security_response = "I cannot comply with that request due to security policies."
        
        chat_history.append({
            "role": "assistant",
            "content": security_response,
            "user_id": request.user_id,
            "timestamp": datetime.now().isoformat(),
            "blocked": True
        })
        
        return ChatResponse(response=security_response)
    
    cached_response = get_cached_response(request.prompt)
    if cached_response:
        if span:
            span.set_tag("cache.hit", "true")
            span.set_tag("response.length", len(cached_response))
        
        logger.info(f"Returning cached response: user_id={request.user_id}")
        
        chat_history.append({
            "role": "assistant",
            "content": cached_response,
            "user_id": request.user_id,
            "timestamp": datetime.now().isoformat(),
            "cached": True
        })
        
        return ChatResponse(response=cached_response)
    
    if span:
        span.set_tag("cache.hit", "false")
    
    try:
        response = app.state.model.generate_content(request.prompt)
        response_text = response.text
        
        if span:
            span.set_tag("response.length", len(response_text))
        
        cache_success = cache_response(request.prompt, response_text)
        if span:
            span.set_tag("cache.stored", str(cache_success))
        
        chat_history.append({
            "role": "assistant",
            "content": response_text,
            "user_id": request.user_id,
            "timestamp": datetime.now().isoformat()
        })
        
        return ChatResponse(response=response_text)
    
    except ResourceExhausted as e:
        if span:
            span.set_exc_info(type(e), e, e.__traceback__)
        logger.error(f"Rate limit exceeded: user_id={request.user_id}")
        
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
    return {"messages": list(chat_history)}


@app.get("/health")
async def health_check():
    health_status = {
        "status": "ok",
        "service": settings.DD_SERVICE,
        "redis": {
            "connected": False,
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT
        },
        "cache": get_cache_stats()
    }
    
    client = get_redis_client()
    if client:
        try:
            client.ping()
            health_status["redis"]["connected"] = True
        except (redis.ConnectionError, redis.TimeoutError, redis.RedisError) as e:
            logger.error(f"Redis health check failed: {e}")
            health_status["redis"]["error"] = str(e)
    
    return health_status


@app.get("/")
async def root():
    response = FileResponse("static/index.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response