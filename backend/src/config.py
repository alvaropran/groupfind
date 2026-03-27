from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://groupfind:groupfind@localhost:5432/groupfind"
    groq_api_key: str = ""
    llm_provider: str = "ollama"  # "ollama" for local dev, "groq" for production
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    groq_model: str = "llama-3.1-8b-instant"
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_prefix": "GROUPFIND_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
