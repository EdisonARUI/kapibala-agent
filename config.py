import os
from dotenv import load_dotenv

# Load environment variables from .env file explicitly from the project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Model Configurations
LLM_MODEL = "gemini-3-flash-preview"
EMBEDDING_MODEL = "models/gemini-embedding-2"

# Database Configurations
CHROMA_PERSIST_DIR = "./chroma_db"
