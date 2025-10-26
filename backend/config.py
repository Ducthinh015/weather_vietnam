import os
from dataclasses import dataclass
from dotenv import load_dotenv

_ENV_PATH = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(_ENV_PATH)

@dataclass
class Config:
    WEATHERAPI_KEY: str = os.getenv("WEATHERAPI_KEY", "")
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "600"))
    USE_REDIS: bool = os.getenv("USE_REDIS", "false").lower() == "true"
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SQLALCHEMY_DATABASE_URI: str = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///agricast.db")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

