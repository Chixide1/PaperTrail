from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    upload_dir: str = "uploads"
    chroma_dir: str = "./chroma"
    
    class Config:
        env_file = ".env"

settings = Settings()