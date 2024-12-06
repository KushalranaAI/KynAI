from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()  # Load environment variables from .env


class Settings(BaseSettings):
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    print(openai_api_key)

    class Config:
        env_file = ".env"


settings = Settings()
