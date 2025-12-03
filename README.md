# NCU Campus QA Bot
<p align="center">
  <img src="assets/icon.png" width="250px" alt="Project Icon">
</p>

This project aims to create a QA bot for National Central University (NCU) campus information using Retrieval-Augmented Generation (RAG) and integrate it with a LINE Bot.

## Project Structure

- `crawler/`: Contains scripts for crawling data from various university websites.
- `server/`: Contains the RAG server (FastAPI application) and related Docker Compose configurations.
  - `server/rag_server/`: The core RAG server Python application.
  - `server/linebot/`: The LINE Bot application.
  - `server/open_webui/`: (Potentially for a web UI, currently a venv)

## Setup

### Prerequisites

*   Docker and Docker Compose
*   Python 3.8+ (for local development/testing of scripts)

### Environment Variables

Both the `rag_server` and `linebot` require environment variables. Create a `.env` file in `server/rag_server/.env` and `server/linebot/.env` respectively.

**`server/rag_server/.env`**:
```
GEMINI_API_KEY=your_gemini_api_key_here
```
Replace `your_gemini_api_key_here` with your actual Gemini API Key obtained from Google AI Studio.

**`server/linebot/.env`**:
```
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
LINE_CHANNEL_SECRET=your_line_channel_secret_here
```
Replace with your LINE Bot channel access token and secret.

## Crawler

The `crawler/` directory contains Python scripts (e.g., in `crawler/adm/`) for fetching data from different university departments. The crawled data is stored in `crawler/docs/`.

To run the crawlers, navigate to the `crawler` directory and execute the relevant Python scripts. For example:

```bash
cd crawler
python adm/news/app.py
# ... run other crawler scripts ...
```
After running the crawlers, the `crawler/docs` directory should be populated with data (CSV and PDF files).

## Build RAG Database

The RAG database needs to be built before the `rag-server` can function. This process involves:
1.  Collecting documents from `crawler/docs`.
2.  Processing these documents (text extraction from PDFs, parsing CSVs).
3.  Generating embeddings for the processed text.
4.  Storing the embeddings in a Chroma vector database.

We use a Docker Compose service to run the `build_database.sh` script in an isolated environment.

1.  **Ensure your `.env` file is configured**: Make sure `server/rag_server/.env` contains your `GEMINI_API_KEY`.
2.  **Navigate to the `server` directory**:
    ```bash
    cd server
    ```
3.  **Run the database build command**:
    ```bash
    docker-compose -f docker-compose.build.yml up --build --remove-orphans
    ```
    This command will:
    *   Build the `db-builder` Docker image.
    *   Start a temporary container.
    *   Mount the necessary project directories (including `crawler/docs` and `server/rag_server`) into the container.
    *   Execute the `build_database.sh` script, which will create the `chroma_db` directory inside `server/rag_server`.
    *   The `--remove-orphans` flag ensures that any old, unused containers are cleaned up.

## Flexible Ollama Setup

The application is designed to work flexibly with Ollama, whether it's running locally on your host machine or within a Docker container managed by Docker Compose. You can choose the setup that best suits your needs.

### **First, a one-time setup:**

Make sure your `server/rag_server/.env` file has the `OLLAMA_BASE_URL` variable. This will be the key to switching between a Dockerized Ollama and a local one.

```
# server/rag_server/.env

# ... other variables ...

# Set this to point to your Ollama instance.
# Leave it unset if you want the application to automatically detect the Ollama URL.
# (Defaults to http://ollama:11434 in Docker, http://localhost:11434 locally)
# OLLAMA_BASE_URL=
```
*Note: If you are running the `rag-server` or `db-builder` in Docker and want to connect to a host-based Ollama, you might need to set `OLLAMA_BASE_URL=http://host.docker.internal:11434` in your `server/rag_server/.env` file and ensure your host Ollama is listening on `0.0.0.0` (start with `OLLAMA_HOST=0.0.0.0 ollama serve`).*

---

### **Case 1: Run App in Docker, Ollama in Docker (Fully Containerized)**

This is the recommended, fully portable setup. It spins up both your application services and an Ollama container, automatically pulling the required models.

```bash
# In the 'server' directory, run:
docker-compose -f docker-compose.yml -f docker-compose.ollama.yml up --build
```
*   **How it works:** This command starts `rag-server`, `linebot`, and the `ollama` container. The Python code automatically connects to the `ollama` service at `http://ollama:11434` within the Docker network.

---

### **Case 2: Run App in Docker, Ollama on Localhost (Using Host's Ollama)**

This is for when you want your application in Docker but prefer to use an Ollama instance running directly on your host machine.

1.  **Ensure your local Ollama is running and accessible:**
    *   Start your local Ollama server with `OLLAMA_HOST=0.0.0.0 ollama serve`.
    *   Make sure the `qwen3-embedding:0.6b` model is pulled (`ollama pull qwen3-embedding:0.6b`).

2.  **Set your `OLLAMA_BASE_URL` in `.env`:**
    ```
    # in server/rag_server/.env
    OLLAMA_BASE_URL=http://host.docker.internal:11434
    ```

3.  **Run Docker Compose (without the ollama service file):**
    ```bash
    # In the 'server' directory, run:
    docker-compose up --build
    ```
*   **How it works:** The `rag-server` Docker container reads `OLLAMA_BASE_URL` from its environment and connects back to your host machine's Ollama instance.

---

### **Case 3: Run App on Localhost, Ollama on Localhost**

This is for running the Python scripts directly on your machine, connecting to a local Ollama instance.

1.  **Ensure your local Ollama is running and accessible:**
    *   Start your local Ollama server with `OLLAMA_HOST=0.0.0.0 ollama serve`.
    *   Make sure the `qwen3-embedding:0.6b` model is pulled (`ollama pull qwen3-embedding:0.6b`).

2.  **Navigate to the `rag_server` directory and activate venv:**
    ```bash
    cd server/rag_server
    source venv/bin/activate
    ```

3.  **Ensure `OLLAMA_BASE_URL` is unset or set to `http://localhost:11434` in your environment (or `server/rag_server/.env`):**
    ```
    # in server/rag_server/.env
    OLLAMA_BASE_URL=http://localhost:11434
    ```

4.  **Run the server:**
    ```bash
    python server.py
    ```
    *(To build the database locally, you would run `python DBHandler.py`)*

---

### **Case 4: Run App on Localhost, Ollama in Docker**

This is less common but demonstrates the flexibility.

1.  **Start ONLY the Ollama container:**
    ```bash
    # In the 'server' directory, run:
    docker-compose -f docker-compose.ollama.yml up --build
    ```

2.  **Navigate to the `rag_server` directory and activate venv:**
    ```bash
    cd server/rag_server
    source venv/bin/activate
    ```

3.  **Ensure `OLLAMA_BASE_URL` points to your host's exposed Ollama port:**
    ```
    # in server/rag_server/.env
    OLLAMA_BASE_URL=http://localhost:11434
    ```

4.  **Run the server:**
    ```bash
    python server.py
    ```
*   **How it works:** Your local Python script connects to `localhost:11434`, which is the port exposed by the Ollama container on your host machine.

---

## Build RAG Database

The RAG database needs to be built before the `rag-server` can function. This process involves:
1.  Collecting documents from `crawler/docs`.
2.  Processing these documents (text extraction from PDFs, parsing CSVs).
3.  Generating embeddings for the processed text.
4.  Storing the embeddings in a Chroma vector database.

We use a Docker Compose service to run the `build_database.sh` script in an isolated environment.

1.  **Ensure your `.env` file is configured**: Make sure `server/rag_server/.env` contains your `GEMINI_API_KEY`.
2.  **Navigate to the `server` directory**:
    ```bash
    cd server
    ```
3.  **Run the database build command (choose one):**
    *   **Using a Dockerized Ollama (recommended for portability):**
        ```bash
        docker-compose -f docker-compose.build.yml -f docker-compose.ollama.yml up --build --remove-orphans
        ```
    *   **Using a Localhost Ollama (requires host Ollama running with `OLLAMA_HOST=0.0.0.0` and `OLLAMA_BASE_URL=http://host.docker.internal:11434` in `server/rag_server/.env`):**
        ```bash
        docker-compose -f docker-compose.build.yml up --build --remove-orphans
        ```

    This command will:
    *   Build the `db-builder` Docker image.
    *   Start a temporary container.
    *   Mount the necessary project directories (including `crawler/docs` and `server/rag_server`) into the container.
    *   Execute the `build_database.sh` script, which will create the `chroma_db` directory inside `server/rag_server`.
    *   The `--remove-orphans` flag ensures that any old, unused containers are cleaned up.

## Testing

*   **RAG Server Health Check**:
    ```bash
    curl http://localhost:8000/health
    ```
*   **LINE Bot**: Interact with your LINE Bot via the LINE app. Ensure it's configured to point to your deployed `linebot` service.

## Troubleshooting

*   **`bash: build_database.sh: No such file or directory`**: Ensure you are running the `docker-compose` command from the `server` directory and that `docker-compose.build.yml` is correctly configured.
*   **`ERROR: Could not find a version that satisfies the requirement pysqlite3-binary`**: This indicates an environment issue. Ensure your Python environment is compatible or try installing `sqlite3-binary` manually if necessary.
*   **"無法回答此問題" from the bot**:
    *   Check the `rag-server` logs to see what documents are being retrieved.
    *   Ensure your `crawler/docs` directory is populated with relevant data.
    *   Rebuild the database after making any changes to documents or `DBHandler.py`.

Please note: The Docker Compose setup assumes a specific project structure. If you modify the directory layout, you may need to adjust the `volumes` and `build.context` paths in the `docker-compose` files accordingly.
