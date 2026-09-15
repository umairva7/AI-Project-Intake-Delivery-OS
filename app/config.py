# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "mistral")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/intake.db")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
    RETRY_COUNT: int = int(os.getenv("RETRY_COUNT", "1"))

settings = Settings()