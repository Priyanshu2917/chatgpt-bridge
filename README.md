[README.md](https://github.com/user-attachments/files/31617694/README.md)
# ChatGPT Bridge

A local bridge that exposes an OpenAI-compatible API and connects it to ChatGPT running in a browser via Playwright automation. The project consists of a FastAPI server, a browser automation bridge, and a local web interface—all communicating through local text files.

⚠️ This project is experimental and under active development.

---

## Overview

ChatGPT Bridge allows you to interact with ChatGPT (via chatgpt.com) using an OpenAI-compatible REST API. It runs entirely on your machine:

1. **FastAPI Server** (`server.py`) — Exposes `/v1/models` and `/v1/chat/completions` endpoints
2. **Browser Bridge** (`bridge2.py`) — Uses Playwright to automate ChatGPT in Chromium
3. **Local Web UI** (`index.html`) — A chat interface served at `http://127.0.0.1:8000`

Communication between the API server and the browser bridge happens through two local files:
- `input.txt` — The server writes user prompts here; the bridge reads and sends them to ChatGPT
- `output.txt` — The bridge writes ChatGPT's response here; the server reads and returns it via the API

---

## Features

| Feature | Description |
|---------|-------------|
| **OpenAI-Compatible API** | `/v1/models` and `/v1/chat/completions` endpoints |
| **Streaming Support** | `stream: true` returns Server-Sent Events (SSE) |
| **Non-Streaming Support** | Standard JSON response when `stream: false` |
| **Browser Automation** | Playwright drives a visible Chromium window at chatgpt.com |
| **Clipboard-Based Extraction** | Clicks "Copy response" button and reads from system clipboard |
| **Local Web Interface** | Chat UI at `http://127.0.0.1:8000` |
| **Request Serialization** | Thread lock ensures one request at a time |
| **Health Check** | `GET /health` endpoint |
| **PowerShell Scripts** | `setup.ps1` for first-time setup, `start.ps1` to launch everything |

---

## Requirements

- **Windows** (tested on Windows 10/11)
- **Python 3.10+** (added to PATH)
- **PowerShell** (default on Windows)
- Internet connection (to load chatgpt.com and download Playwright Chromium)

---

## Installation

### 1. Clone or Download

```powershell
git clone https://github.com/Priyanshu2917/chatgpt-bridge.git
cd chatgpt-bridge
```

Or download and extract the ZIP, then open PowerShell in the project folder.

### 2. Run Setup

```powershell
.\setup.ps1
```

**What `setup.ps1` does:**
- Verifies Python is installed and in PATH
- Creates a virtual environment at `.\venv` (if not exists)
- Activates the virtual environment
- Upgrades pip
- Installs: `fastapi`, `uvicorn`, `pydantic`, `playwright`, `pyperclip`
- Installs Playwright Chromium browser

> If you get a script execution policy error, run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### 3. Start the Bridge

```powershell
.\start.ps1
```

**What `start.ps1` does:**
- Clears `input.txt` and `output.txt`
- Launches `bridge2.py` in a new PowerShell window (opens Chromium at chatgpt.com)
- Waits 3 seconds for browser to load
- Starts FastAPI server via Uvicorn at `http://127.0.0.1:8000` in another PowerShell window
- Verifies `/health` endpoint responds

You should see two new PowerShell windows: one running the browser bridge, one running the API server. The API is ready when you see "API IS READY! 🚀"

---

## API Usage

**Base URL:** `http://127.0.0.1:8000`

### GET /v1/models

Returns available models (OpenAI-compatible format).

```bash
curl http://127.0.0.1:8000/v1/models
```

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "chatgpt-local",
      "object": "model",
      "owned_by": "local"
    }
  ]
}
```

### POST /v1/chat/completions

OpenAI-compatible chat completions endpoint.

#### Non-Streaming Request

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "chatgpt-local",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "stream": false
  }'
```

**Response:**
```json
{
  "id": "chatcmpl-abc123...",
  "object": "chat.completion",
  "model": "chatgpt-local",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "I'm doing well, thank you for asking! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ]
}
```

#### Streaming Request

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "chatgpt-local",
    "messages": [
      {"role": "user", "content": "Write a short poem about code"}
    ],
    "stream": true
  }'
```

**Response (Server-Sent Events):**
```
data: {"id": "chatcmpl-xyz789...", "object": "chat.completion.chunk", "model": "chatgpt-local", "choices": [{"index": 0, "delta": {"role": "assistant", "content": "Code flows like rivers..."}, "finish_reason": "stop"}]}

data: [DONE]
```

> **Note:** Current streaming implementation sends the full response in a single chunk, then `[DONE]`. True token-by-token streaming is not yet implemented.

### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `model` | string | No | `chatgpt-local` | Model identifier (ignored, passed through) |
| `messages` | array | Yes | — | Array of message objects with `role` and `content` |
| `temperature` | float | No | `null` | Accepted but not forwarded to ChatGPT |
| `max_tokens` | int | No | `null` | Accepted but not forwarded to ChatGPT |
| `stream` | bool | No | `false` | Enable SSE streaming |

---

## Example Python Usage

```python
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# Non-streaming
response = requests.post(
    f"{BASE_URL}/v1/chat/completions",
    json={
        "model": "chatgpt-local",
        "messages": [{"role": "user", "content": "What is 2+2?"}],
        "stream": False
    }
)
print(response.json()["choices"][0]["message"]["content"])

# Streaming
with requests.post(
    f"{BASE_URL}/v1/chat/completions",
    json={
        "model": "chatgpt-local",
        "messages": [{"role": "user", "content": "Count to 5"}],
        "stream": True
    },
    stream=True
) as r:
    for line in r.iter_lines():
        if line:
            decoded = line.decode("utf-8")
            if decoded.startswith("data: "):
                data = decoded[6:]
                if data != "[DONE]":
                    chunk = json.loads(data)
                    content = chunk["choices"][0]["delta"].get("content", "")
                    print(content, end="", flush=True)
                else:
                    print("\n[DONE]")
```

---

## Compatibility

The API is **designed to be OpenAI-compatible** for the endpoints implemented:

- ✅ `GET /v1/models`
- ✅ `POST /v1/chat/completions` (streaming & non-streaming)
- ❌ Other OpenAI endpoints (embeddings, fine-tuning, etc.) not implemented
- ❌ Some parameters accepted but ignored (`temperature`, `max_tokens`)
- ❌ No authentication (local-only, no API keys)

---

## Project Structure

```
chatgpt-bridge/
├── server.py          # FastAPI server with OpenAI-compatible endpoints
├── bridge2.py         # Playwright browser automation (watches input.txt, writes output.txt)
├── index.html         # Local web chat UI (served at /)
├── requirements.txt   # Python dependencies
├── setup.ps1          # First-time setup: venv, deps, Playwright Chromium
├── start.ps1          # Launches bridge2.py + FastAPI server
├── input.txt          # Bridge communication: user prompts (auto-created)
├── output.txt         # Bridge communication: ChatGPT responses (auto-created)
└── venv/              # Virtual environment (created by setup.ps1)
```

---

## Limitations

| Limitation | Details |
|------------|---------|
| **Sequential processing** | One request at a time (thread lock) |
| **No true streaming** | Full response sent in one SSE chunk |
| **ChatGPT UI dependency** | Relies on specific ChatGPT DOM selectors (`textarea`, `button[aria-label="Send message"]`, `button[aria-label="Copy response"]`) |
| **Clipboard-based** | Uses system clipboard via `pyperclip`; may conflict with other apps |
| **Visible browser required** | Chromium runs in headful mode (not headless) |
| **No conversation history** | Each request only sends the latest user message |
| **No authentication** | Anyone with local network access can call the API |
| **Windows-focused** | PowerShell scripts, clipboard handling tested on Windows |
| **Timeout hardcoded** | 120s for ChatGPT response, 30s for Playwright operations |

---

## Troubleshooting

### Python not found
```
ERROR: Python is not installed or not added to PATH.
```
Install Python from [python.org](https://python.org) and **check "Add Python to PATH"**.

### PowerShell execution policy
```
running scripts is disabled on this system
```
Run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Virtual environment issues
Delete `venv` folder and re-run `setup.ps1`:
```powershell
Remove-Item -Recurse -Force venv
.\setup.ps1
```

### Server not starting / Port 8000 in use
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Bridge fails to find ChatGPT elements
- ChatGPT UI may have changed; selectors in `bridge2.py` may need updating
- Check the bridge PowerShell window for debug output showing element counts

### API returns 504 Gateway Timeout
- ChatGPT took longer than 120 seconds to respond
- Check the bridge window—it may be stuck waiting for the "Copy response" button

### "Clipboard was empty after clicking Copy"
- ChatGPT's copy button may not have populated clipboard in time
- Try increasing `page.wait_for_timeout(500)` in `bridge2.py`

### Health check fails but server window shows Uvicorn running
- Wait a few more seconds; Uvicorn startup can take 5–10s
- Check server window for error tracebacks

---

## Security & Privacy

- **Runs entirely locally** — No external API calls except to `chatgpt.com` in the browser
- **No data leaves your machine** except what you type into ChatGPT
- **No authentication** — The API is open on `127.0.0.1:8000`; do not expose to LAN/WAN without adding auth
- **Clipboard access** — Bridge reads system clipboard after clicking "Copy"; be aware if sensitive data is in clipboard
- **File-based communication** — `input.txt` and `output.txt` contain plain-text prompts/responses

---

## Roadmap / Future Improvements

*These are planned ideas, not currently implemented.*

- [ ] **True token streaming** — Integrate with ChatGPT's streaming response instead of clipboard copy
- [ ] **Conversation context** — Send full message history to maintain context
- [ ] **Headless mode option** — Run Chromium headless for server deployments
- [ ] **Robust selector fallback** — Multiple selector strategies for ChatGPT UI changes
- [ ] **Additional OpenAI endpoints** — `/v1/embeddings`, `/v1/completions`
- [ ] **API key authentication** — Optional bearer token for local network sharing
- [ ] **Better error handling** — Structured error codes, retry logic
- [ ] **Configuration file** — Port, timeouts, model name, browser path via config
- [ ] **Docker support** — Containerized deployment (requires X11/WSLg for browser)
- [ ] **Code block / Markdown handling** — Preserve formatting in API responses

---

## License

MIT License — feel free to use, modify, and distribute.
