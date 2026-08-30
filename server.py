from pathlib import Path
import threading
import time
import uuid
import json
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent

INDEX_FILE = BASE_DIR / "index.html"
INPUT_FILE = BASE_DIR / "input.txt"
OUTPUT_FILE = BASE_DIR / "output.txt"


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================
# REQUEST/RESPONSE SYNCHRONIZATION
# ============================================

# Lock to serialize requests since bridge2.py processes sequentially
_request_lock = threading.Lock()

# Polling configuration
_POLL_INTERVAL = 0.2
_POLL_TIMEOUT = 120.0


# ============================================
# REQUEST MODELS
# ============================================

class PromptRequest(BaseModel):
    message: str


class ChatCompletionRequest(BaseModel):
    model: str = "chatgpt-local"
    messages: list
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    model: str
    choices: list


# ============================================
# HOME
# ============================================

@app.get("/")
def home():
    return FileResponse(INDEX_FILE)


# ============================================
# HEALTH CHECK
# ============================================

@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# ============================================
# MODELS LIST (OpenAI Compatible)
# ============================================

@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "chatgpt-local",
                "object": "model",
                "owned_by": "local"
            }
        ]
    }


# ============================================
# HELPER: Extract latest user message
# ============================================

def extract_latest_user_message(messages: list) -> str:
    """Extract the latest user message from messages array."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content.strip()
            elif isinstance(content, list):
                for part in content:
                    if part.get("type") == "text":
                        return part.get("text", "").strip()
    return ""


# ============================================
# HELPER: Wait for new response in output.txt
# ============================================

def wait_for_new_response(before_mtime: int, before_content: str) -> str:
    """
    Poll output.txt until modified_time changes and new content appears.
    Returns the new response content.
    """
    start_time = time.time()
    
    while time.time() - start_time < _POLL_TIMEOUT:
        time.sleep(_POLL_INTERVAL)
        
        try:
            OUTPUT_FILE.touch(exist_ok=True)
            current_mtime = OUTPUT_FILE.stat().st_mtime_ns
            current_content = OUTPUT_FILE.read_text(encoding="utf-8")
            
            if current_mtime > before_mtime and current_content != before_content:
                new_response = current_content.strip()
                if new_response:
                    return new_response
        except Exception:
            continue
    
    raise TimeoutError("Timed out waiting for ChatGPT response")


# ============================================
# CHAT COMPLETIONS ENDPOINT
# ============================================

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completions endpoint.
    Serializes requests via lock to ensure proper request/response correlation.
    Supports both streaming and non-streaming responses.
    """
    user_message = extract_latest_user_message(request.messages)
    
    if not user_message:
        raise HTTPException(
            status_code=400,
            detail="No user message found in request"
        )
    
    request_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
    
    with _request_lock:
        try:
            OUTPUT_FILE.touch(exist_ok=True)
            before_mtime = OUTPUT_FILE.stat().st_mtime_ns
            before_content = OUTPUT_FILE.read_text(encoding="utf-8")
            
            INPUT_FILE.write_text(user_message, encoding="utf-8")
            
            response_text = wait_for_new_response(before_mtime, before_content)
            
        except TimeoutError as e:
            raise HTTPException(status_code=504, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing request: {e}")
    
    if request.stream:
        async def stream_generator():
            chunk = {
                "id": request_id,
                "object": "chat.completion.chunk",
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "content": response_text
                        },
                        "finish_reason": "stop"
                    }
                ]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    
    return {
        "id": request_id,
        "object": "chat.completion",
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }
        ]
    }


# ============================================
# RECEIVE PROMPT FROM index.html
# ============================================

@app.post("/input")
def receive_input(request: PromptRequest):

    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty."
        )

    try:
        # Overwrite input.txt with the new prompt
        INPUT_FILE.write_text(
            message,
            encoding="utf-8"
        )

        return {
            "success": True,
            "message": "Prompt saved successfully."
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not save input: {error}"
        )


# ============================================
# READ RESPONSE FROM output.txt
# ============================================


@app.get("/output")
def get_output():

    try:

        OUTPUT_FILE.touch(
            exist_ok=True
        )

        response = OUTPUT_FILE.read_text(
            encoding="utf-8"
        )

        modified_time = (
            OUTPUT_FILE.stat().st_mtime_ns
        )

        return JSONResponse(
            content={
                "response": response,
                "modified_time": modified_time
            },
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Could not read output: {error}"
        )