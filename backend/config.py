import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load .env nếu chạy local
ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


@dataclass
class Config:
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    WEATHERAPI_KEY: str = os.getenv("WEATHERAPI_KEY", os.getenv("OPENWEATHER_API_KEY", ""))

    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "600"))
    USE_REDIS: bool = os.getenv("USE_REDIS", "false").lower() == "true"
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    CITY: str = os.getenv("CITY", "Hanoi")

    # 🔥 FIX QUAN TRỌNG: luôn ưu tiên MONGO_URI
    MONGO_URI: str = os.getenv("MONGO_URI") or os.getenv("MONGO_URL")

    if not MONGO_URI:
        # Không fallback localhost — bắt lỗi để GitHub Actions khỏi chạy nhầm
        raise RuntimeError("❌ MONGO_URI is not provided. Check GitHub Secrets!")

    # DB name từ secret
    DB_NAME: str = os.getenv("DB_NAME")

    if not DB_NAME:
        raise RuntimeError("❌ DB_NAME is not provided. Check GitHub Secrets!")

    DATA_PATH: str = os.getenv("DATA_PATH", "/data")
    FETCH_INTERVAL: int = int(os.getenv("FETCH_INTERVAL", "10"))
