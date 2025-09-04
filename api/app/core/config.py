import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SQLALCHEMY_DATABASE_URL: str = "sqlite:///./db.sqlite"
    OPENAI_KEY: str
    UPLOAD_DIR: str = "uploads"
    CHROME_DIR: str = "./chroma"
    JWT_KEY: str

    # Tracing and Debugging
    LANGSMITH_API_KEY: str
    LANGSMITH_TRACING: str = "true"
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_PROJECT: str ="Papertrail"
    
    class Config:
        env_file = ".env"

settings = Settings() # type: ignore

def setup_langsmith_env():
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGCHAIN_TRACING_V2"] = settings.LANGSMITH_TRACING
    os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT