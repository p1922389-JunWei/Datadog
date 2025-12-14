import os
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ddtrace import tracer

# --- CONFIGURATION ---
# Get your API key from Google AI Studio (https://aistudio.google.com/)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

app = FastAPI()


class ChatRequest(BaseModel):
    prompt: str
    user_id: str


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # FIX: Get the active HTTP span (the "Root" span)
    # This ensures tags show up in the main Trace List immediately.
    span = tracer.current_span()

    if span:
        # 1. Tag the Root Span with User ID
        span.set_tag("user.id", request.user_id)

    # 2. INNOVATION: Security Rule
    if "ignore" in request.prompt.lower():
        if span:
            span.set_tag("security.jailbreak_attempt", "true")
            # Mark the span as error so it turns RED in the dashboard
            span.error = 1
            span.set_tag("error.message", "Jailbreak keyword detected")

        print(f"🚨 BLOCKED: Jailbreak attempt from {request.user_id}")
        return {"response": "I cannot comply with that request due to security policies."}

    try:
        # 3. Call Gemini
        response = model.generate_content(request.prompt)
        return {"response": response.text}

    except ResourceExhausted as e:
            if span:
                span.set_exc_info(type(e), e, e.__traceback__)
            print(f"❌ API Rate Limited: {e}")
            raise HTTPException(status_code=429, detail="API rate limit exceeded")
    except Exception as e:
        if span:
            span.set_exc_info(type(e), e, e.__traceback__)
        print(f"❌ Error calling Gemini: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/health")
def health_check():
    return {"status": "ok"}