# NCU Campus QA Bot

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

## Run Services

After the RAG database is built, you can run the `rag-server` and `linebot` services.

1.  **Ensure you are in the `server` directory**:
    ```bash
    cd server
    ```
2.  **Start the services**:
    ```bash
    docker-compose up
    ```
    This will start `rag-server` and `linebot` containers, exposing their respective ports (8000 for `rag-server`, 5010 for `linebot`'s internal 5000).

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
