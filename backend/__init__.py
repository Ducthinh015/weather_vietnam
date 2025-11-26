import os

# Chỉ load app nếu không phải chạy training
if os.getenv("DISABLE_BACKEND_APP") != "1":
    from backend.app import app
