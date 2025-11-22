import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    WEATHERAPI_KEY: str = os.getenv("WEATHERAPI_KEY", os.getenv("OPENWEATHER_API_KEY", ""))
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "600"))
    USE_REDIS: bool = os.getenv("USE_REDIS", "false").lower() == "true"
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CITY: str = os.getenv("CITY", "Hanoi")
    # Prefer Cloud Run style MONGO_URL, fallback to legacy MONGO_URI
    MONGO_URI: str = os.getenv("MONGO_URL", os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    DB_NAME: str = os.getenv("DB_NAME", "agricast_ai")
    DATA_PATH: str = os.getenv("DATA_PATH", "/data")
    # Fetch interval in minutes (for scheduler); default 10
    FETCH_INTERVAL: int = int(os.getenv("FETCH_INTERVAL", "10"))
