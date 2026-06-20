FROM python:3.11-slim

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Copy toàn bộ code từ GitHub vào trong container
COPY . .

# Cài đặt các thư viện Python từ file requirements.txt
RUN pip install --no-cache-dir -r facebook-bot/requirements.txt

# Lệnh khởi chạy bot trực tiếp khi container bắt đầu chạy
CMD ["python", "-u", "facebook-bot/main.py"]
