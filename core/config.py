from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv

# Load env file
load_dotenv()

class Settings(BaseSettings):
    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5173",
        "*"
    ]
    # Database url
    DATABASE_URL: str = ""
    ENVIRONMENT: str = ""
    PROJECT_NAME: str = "NalvixChat"
    API_V1_STR: str = "/api/v1"

    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    GROQ_MODEL: str = ""
    LLM_TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 1024
    AGENT_CONFIG_PATH: str = "../agents_config"
    MAX_AGENT_ITERATIONS: int = 1

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # API Keys
    GROQ_API_KEY: str = "" 
    DEEPSEEK_API_KEY: str = ""
    
    # Model Selection
    USE_DEEPSEEK_EMBEDDINGS: bool = False
    USE_DEEPSEEK_CHAT: bool = False
    
    # Vector DB Settings
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    COLLECTION_NAME: str = "documents"
    
    # Chunking Settings
    MIN_CHUNK_SIZE: int = 50
    CHUNK_SEPARATOR: str = "\n\n"
    
    # RAG Settings
    TOP_K_RESULTS: int = 3
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

@lru_cache()
def get_settings():
    return Settings()

# Global settings instance
settings = get_settings()