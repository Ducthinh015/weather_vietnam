FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install only required packages
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy only the backend folder
COPY . /app/backend

# Cloud Run settings
ENV PORT=8080
EXPOSE 8080

# Run Flask using gunicorn
CMD ["gunicorn", "backend.app:app", "--bind", "0.0.0.0:8080"]
