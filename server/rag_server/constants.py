import os

DOCS_DIR = r"./docs"
DB_DIR = r"./chroma_db"
COLLECTION_NAME = "ncu"
TOP_K = 10

# Gemini API settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_EMBED_MODEL = "models/text-embedding-004"
GEMINI_FLASH_MODEL = "gemini-2.5-flash"
