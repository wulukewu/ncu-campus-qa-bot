import os

DOCS_DIR = r"../../crawler/docs"
DB_DIR = r"./chroma_db"
COLLECTION_NAME = "ncu"
TOP_K = 10

# Gemini API settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_FLASH_MODEL = "gemini-2.5-flash"

# Ollama embedding settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_EMBED_MODEL = "qwen3-embedding:0.6b"

