from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    gitee_webhook_secret: str = Field(..., env="GITEE_WEBHOOK_SECRET")
    notion_token: str = Field(..., env="NOTION_TOKEN")
    sqlite_path: str = Field(default="mapping.db", env="SQLITE_PATH")
    
    class Config:
        env_file = ".env"  # To load environment variables from a .env file