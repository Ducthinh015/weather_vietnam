# 1) Base image
FROM python:3.11-slim

# 2) Set working directory
WORKDIR /app

# 3) Copy requirements
COPY requirements.txt .

# 4) Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5) Copy toàn bộ backend code vào container
COPY . .

# 6) Cloud Run requires PORT env
ENV PORT=8080
EXPOSE 8080

# 7) Start Flask normally
CMD ["gunicorn", "backend.app:app", "--bind", "0.0.0.0:8080", "--timeout", "0"]
