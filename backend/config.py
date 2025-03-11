import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# Pinecone settings
PINECONE_INDEX_NAME = "gitsummarizer-index"
PINECONE_NAMESPACE = "default-namespace"
PINECONE_TOP_K = 7  # Default number of results to return from similarity search

# GitHub settings
GITHUB_TEMP_DIR = "temp_repos"

# Summary settings
GENERATE_SUMMARY = True  # Control whether to generate repository summaries

# Embedding settings
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# LLM settings
DEFAULT_LLM_MODEL = "gpt-3.5-turbo"
LLM_MODELS = {
    "gpt-3.5-turbo": {
        "provider": "openai",
        "temperature": 0.3,
        "max_tokens": 1000
    },
    "gpt-4": {
        "provider": "openai",
        "temperature": 0.2,
        "max_tokens": 1500
    },
    # Add other models as needed
}

# Chunking settings
DEFAULT_CHUNK_TOKEN_LIMIT = 500
SUPPORTED_LANGUAGES = {
    ".py": "py",
    ".java": "java",
    ".cpp": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".js": "js",
    ".jsx": "js",
    ".ts": "js",
    ".tsx": "js",
    ".go": "go",
    ".html": "html",
    ".htm": "html",
    ".md": "markdown"
} 