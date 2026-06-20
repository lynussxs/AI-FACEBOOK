#!/bin/bash
echo "=== ĐANG KHỞI TẠO MÔI TRƯỜNG PYTHON CHO BOT ==="
# Cài đặt các thư viện từ requirements.txt bằng quyền break-system-packages
python3 -m pip install -r facebook-bot/requirements.txt --break-system-packages

echo "=== ĐANG KÍCH HOẠT FACEBOOK AI BOT ==="
# Chạy bot trực tiếp
python3 -u facebook-bot/main.py
