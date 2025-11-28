import os

DOCS_DIR = r"../../crawler/docs"
DB_DIR = r"./chroma_db"
COLLECTION_NAME = "ncu"
TOP_K = 10

# Gemini API settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_FLASH_MODEL = "gemini-2.5-flash"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")
HF_API_KEY = os.getenv("HF_API_KEY","")