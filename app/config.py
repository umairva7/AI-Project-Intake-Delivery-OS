# app/config.py
import os
from typing import Dict, List, Any
from dotenv import load_dotenv

load_dotenv()

# Config-driven team taxonomy and weighted signal definitions
DEFAULT_TEAM_SIGNALS: Dict[str, Dict[str, int]] = {
    "AI / ML": {
        "machine learning": 5,
        "model training": 5,
        "deep learning": 5,
        "computer vision": 5,
        "prediction": 4,
        "classification": 4,
        "rag": 4,
        "llm": 4,
        "chatbot": 4,
        "embeddings": 4,
        "neural": 4,
        "nlp": 4,
        "generative ai": 4,
        "ai": 3,
        "ollama": 3,
        "openai": 3,
        "api": 1,
    },
    "Web Development": {
        "frontend": 5,
        "react": 5,
        "vue": 5,
        "angular": 5,
        "website": 4,
        "web application": 4,
        "javascript": 4,
        "typescript": 4,
        "dashboard": 4,
        "portal": 4,
        "html": 4,
        "django": 4,
        "fastapi": 4,
        "flask": 4,
        "node": 4,
        "express": 4,
        "css": 3,
        "backend": 3,
        "fullstack": 4,
        "api": 2,
        "rest": 2,
    },
    "Mobile Development": {
        "mobile": 5,
        "ios": 5,
        "android": 5,
        "swift": 5,
        "kotlin": 5,
        "flutter": 5,
        "react native": 5,
        "mobile app": 5,
        "iphone": 4,
        "ipad": 4,
        "app store": 4,
        "play store": 4,
        "api": 1,
    },
    "Data Engineering": {
        "etl": 5,
        "data pipeline": 5,
        "data warehouse": 5,
        "snowflake": 4,
        "bigquery": 4,
        "databricks": 4,
        "spark": 4,
        "kafka": 4,
        "airflow": 4,
        "dbt": 4,
        "sql": 3,
        "analytics": 3,
        "database": 2,
    },
    "DevOps / Infrastructure": {
        "kubernetes": 5,
        "k8s": 5,
        "docker": 5,
        "terraform": 5,
        "devops": 5,
        "infrastructure": 4,
        "ci/cd": 4,
        "deployment": 4,
        "aws": 4,
        "gcp": 4,
        "azure": 4,
        "cloud": 3,
        "hosting": 3,
    },
}

# Config-driven team-specific checklist stage templates
DEFAULT_TEAM_CHECKLIST_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "Web Development": {
        "planning": "Define frontend component hierarchy and backend REST API architecture",
        "setup": "Set up project repository, linting, build tooling, and environment configuration",
        "testing": "Conduct cross-browser UI validation and API integration testing",
        "deployment": "Prepare production build bundles and configure deployment hosting",
        "supporting": "Develop client integration layer and UI consuming interface",
    },
    "AI / ML": {
        "planning": "Define model architecture, retrieval strategy, and evaluation metrics",
        "setup": "Set up model exploration environment, vector store, and data pipeline",
        "testing": "Validate model accuracy, inference latency, and response quality against benchmark tests",
        "deployment": "Containerize model inference service and deploy to production endpoint",
        "supporting": "Expose model inference API and document schema contracts for integration",
    },
    "Mobile Development": {
        "planning": "Define mobile navigation structure, UI wireframes, and offline caching strategy",
        "setup": "Initialize mobile project workspace, SDK dependencies, and device emulators",
        "testing": "Perform multi-device testing, OS compatibility checks, and usability verification",
        "deployment": "Configure application signing, store assets, and release build configuration",
        "supporting": "Implement mobile client API networking layer and state synchronization",
    },
    "Data Engineering": {
        "planning": "Design data pipeline schema, data models, and ETL ingestion workflow",
        "setup": "Provision data warehouse staging environment and orchestrator connections",
        "testing": "Execute data quality, completeness, and transformation integrity tests",
        "deployment": "Deploy automated pipeline scheduling and monitoring alerts",
        "supporting": "Create data access layer and materialized views for consuming systems",
    },
    "DevOps / Infrastructure": {
        "planning": "Define infrastructure topology, network security boundaries, and CI/CD strategy",
        "setup": "Provision cloud infrastructure and container runtime using Infrastructure-as-Code",
        "testing": "Perform deployment verification, disaster recovery simulation, and load testing",
        "deployment": "Configure automated monitoring dashboards, alerts, and operational runbooks",
        "supporting": "Configure automated build, test, and release pipelines for application services",
    },
}


class Settings:
    # LLM Provider selection: "groq" (default/primary) or "ollama"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")

    # Groq Configuration (Primary Provider)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    GROQ_TIMEOUT: int = int(os.getenv("GROQ_TIMEOUT", "30"))

    # Ollama Configuration (Secondary / Fallback Provider)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "mistral")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "30"))
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:////tmp/intake.db" if os.getenv("VERCEL") else "sqlite:///./data/intake.db",
    )
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
    RETRY_COUNT: int = int(os.getenv("RETRY_COUNT", "1"))
    TEAM_SIGNALS: Dict[str, Dict[str, int]] = DEFAULT_TEAM_SIGNALS
    TEAM_CHECKLIST_TEMPLATES: Dict[str, Dict[str, Any]] = DEFAULT_TEAM_CHECKLIST_TEMPLATES


settings = Settings()