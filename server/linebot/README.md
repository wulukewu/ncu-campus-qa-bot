# LINE Bot for NCU Campus QA

This LINE bot provides a question-answering service for NCU campus-related inquiries using RAG (Retrieval-Augmented Generation) with Gemini API.

## Architecture

```
LINE User → LINE Bot (app.py) → RAG Server (Gemini API) → Response
```

The LINE bot acts as a messaging interface that:
1. Receives messages from LINE users via webhook
2. Forwards questions to the RAG server
3. Returns AI-generated responses based on the knowledge base

## Setup

### 1. Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Set up environment variables:

Create a `.env` file in this directory. You can use `.env.example` as a template:

```bash
cp .env.example .env
```

Then, fill in the required values in the `.env` file:

-   `LINE_CHANNEL_ACCESS_TOKEN`: Your LINE channel access token from LINE Developers Console
-   `LINE_CHANNEL_SECRET`: Your LINE channel secret from LINE Developers Console
-   `RAG_SERVER_URL`: The URL for your RAG server endpoint (default: `http://127.0.0.1:8000/v1/chat/completions`)

### 3. Start the RAG Server first:

Make sure the RAG server is running before starting the LINE bot. See `../rag_server/README.md` for instructions.

### 4. Run the LINE bot:

```bash
python app.py
```

The bot will start on port 5000.

### 5. Set up LINE webhook:

In the LINE Developers Console, set your webhook URL to:
```
https://your-domain.com/callback
```

Use ngrok for local testing:
```bash
ngrok http 5000
```

## Features

- ✅ Connects to LINE Messaging API
- ✅ Forwards user queries to RAG server
- ✅ Returns contextual answers based on NCU news database
- ✅ Uses Gemini Flash model for fast, accurate responses
- ✅ Automatic error handling and timeout management
