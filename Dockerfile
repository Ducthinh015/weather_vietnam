# ---------------------------------------------------------
# 1. Base image
# ---------------------------------------------------------
FROM python:3.11-slim

# Không tạo file .pyc
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ---------------------------------------------------------
# 2. Set working directory
# ---------------------------------------------------------
WORKDIR /app

# ---------------------------------------------------------
# 3. Install system dependencies
# ---------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# 4. Copy & install Python dependencies
# ---------------------------------------------------------
COPY requirements.txt .

# Bỏ TensorFlow nếu có – THAY bằng TFLite runtime
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y tensorflow tensorflow-cpu tensorflow-gpu || true \
    && pip install --no-cache-dir tflite-runtime

# ---------------------------------------------------------
# 5. Copy toàn bộ source code
# ---------------------------------------------------------
COPY . .

# đường dẫn backend phải tồn tại: /app/backend/app.py
# nếu không → anh báo lại để mình sửa CMD

# ---------------------------------------------------------
# 6. Cloud Run port
# ---------------------------------------------------------
ENV PORT=8080

EXPOSE 8080

# ---------------------------------------------------------
# 7. Gunicorn (Flask WSGI)
# ---------------------------------------------------------
CMD ["gunicorn", "backend.app:app", "--bind", "0.0.0.0:8080", "--timeout", "0"]
