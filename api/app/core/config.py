from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_KEY: str
    UPLOAD_DIR: str = "uploads"
    CHROME_DIR: str = "./chroma"
    JWT_KEY: str
    
    class Config:
        env_file = ".env"

settings = Settings() # type: ignore