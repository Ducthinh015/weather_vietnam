# Dockerfile cho Backend (Flask)
# Sử dụng Python 3.11 slim để nhẹ
FROM python:3.11-slim

# Tránh tạo .pyc và bật log không buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Thư mục làm việc trong container
WORKDIR /app

# Cài đặt dependency sớm để tận dụng cache layer
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn backend
COPY . /app

# Cổng Flask mặc định
EXPOSE 5000

# Chạy ứng dụng
CMD ["python", "app.py"]
