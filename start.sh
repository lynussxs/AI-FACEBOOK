#!/bin/bash
echo "=== ĐANG CÀI ĐẶT THƯ VIỆN CHO BOT ==="
python3 -m pip install -r facebook-bot/requirements.txt --break-system-packages

echo "=== ĐANG KÍCH HOẠT FACEBOOK AI BOT ==="
python3 -u facebook-bot/main.py
