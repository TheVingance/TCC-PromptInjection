from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "FinSecAI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://finuser:finpassword@postgres:5432/findb"

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8h — necessário para experimentos longos (700+ testes)

    # LLM
    DEFAULT_LLM_PROVIDER: str = "ollama"  # ollama | deepseek | gemini

    # Ollama
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "llama3.1:latest"


    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
