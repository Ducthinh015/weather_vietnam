FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend source code into a 'backend' directory
# This mimics the local structure where we run 'python -m backend.app' from the root
COPY . backend/

# Set PYTHONPATH to /app so python can find the 'backend' package
ENV PYTHONPATH=/app
ENV PORT=8080
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

CMD ["python", "-m", "backend.app"]
