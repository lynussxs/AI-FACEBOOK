# 🤖 Facebook AI Bot

Bot AI cho Facebook (giống Meta AI) — trả lời khi bị @mention trong group hoặc nhắn riêng. Dùng OpenRouter API, gửi log về Discord, chạy lâu dài trên Railway.

---

## 📁 Cấu trúc project

```
facebook-bot/
├── main.py              # File chạy chính (asyncio loop + auto-reconnect)
├── config.py            # Load config từ .env
├── facebook_client.py   # Login Facebook, load/save cookies, lắng nghe & gửi tin
├── ai_handler.py        # Gọi OpenRouter API (context-aware)
├── logger.py            # Gửi log đẹp về Discord Webhook + console
├── requirements.txt     # Thư viện Python cần thiết
├── .env.example         # Mẫu file biến môi trường
├── cookies.json         # Session cookies Facebook (tự động tạo/cập nhật)
└── README.md            # File này
```

---

## ⚡ Cài đặt nhanh

### 1. Clone / tải về project

```bash
git clone <repo-url>
cd facebook-bot
```

### 2. Cài thư viện

```bash
pip install -r requirements.txt
```

### 3. Tạo file `.env`

```bash
cp .env.example .env
```

Mở `.env` và điền thông tin (xem hướng dẫn từng biến bên dưới).

---

## 🔧 Hướng dẫn setup `.env`

| Biến | Bắt buộc | Mô tả |
|---|---|---|
| `FACEBOOK_EMAIL` | ✅ | Email tài khoản Facebook |
| `FACEBOOK_PASSWORD` | ✅ | Mật khẩu Facebook |
| `OPENROUTER_API_KEY` | ✅ | API key từ openrouter.ai |
| `DISCORD_WEBHOOK_URL` | ❌ | URL Webhook Discord để nhận log |
| `BOT_NAME` | ❌ | Tên mention bot, ví dụ `@MyAI` |
| `MODEL_NAME` | ❌ | Model AI, mặc định `google/gemini-flash-1.5` |
| `SYSTEM_PROMPT` | ❌ | Prompt hệ thống tiếng Việt |
| `GROUP_IDS` | ❌ | JSON array Group ID được phép, ví dụ `["111","222"]` |
| `ALLOWED_USER_IDS` | ❌ | JSON array User ID được chat riêng |
| `MAX_CONTEXT_MESSAGES` | ❌ | Số tin nhắn giữ context, mặc định `10` |
| `TEMPERATURE` | ❌ | Độ sáng tạo AI, mặc định `0.7` |
| `MAX_TOKENS` | ❌ | Số token tối đa mỗi lần, mặc định `1000` |
| `RECONNECT_DELAY` | ❌ | Giây chờ trước khi reconnect, mặc định `10` |
| `MAX_RECONNECT_ATTEMPTS` | ❌ | Số lần reconnect tối đa, `0` = vô hạn |

---

## 🍪 Cách export Cookies Facebook → `cookies.json`

Dùng extension trình duyệt để export cookies dạng JSON:

### Bước 1: Cài extension
- **Chrome/Edge:** [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg) hoặc [Cookie-Editor](https://cookie-editor.cgagnier.ca/)
- **Firefox:** [Cookie-Editor](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)

### Bước 2: Export cookies
1. Đăng nhập Facebook tại [facebook.com](https://facebook.com).
2. Mở extension Cookie-Editor.
3. Click **Export** → chọn **JSON**.
4. Copy toàn bộ nội dung JSON.

### Bước 3: Lưu vào file
Tạo/thay thế file `cookies.json` trong thư mục project:
```json
[
  {"name": "c_user", "value": "...", "domain": ".facebook.com", ...},
  {"name": "xs", "value": "...", "domain": ".facebook.com", ...},
  ...
]
```

> **Lưu ý:** Nếu không có `cookies.json`, bot sẽ tự đăng nhập bằng email/password và tự tạo file này.

---

## 🔍 Cách lấy Group ID Facebook

### Cách 1: Từ URL group
Vào group Facebook, URL sẽ có dạng:
```
https://www.facebook.com/groups/123456789012345/
                                ^^^^^^^^^^^^^^^^^
                                Đây là Group ID
```

### Cách 2: Dùng Graph API Explorer
1. Vào [developers.facebook.com/tools/explorer](https://developers.facebook.com/tools/explorer)
2. Chọn group → xem trường `id`

### Cách 3: Từ source code trang
1. Vào group → click chuột phải → View Page Source
2. Tìm `"group_id"` hoặc `"pageID"` trong HTML

Sau khi lấy được Group ID, thêm vào `.env`:
```env
GROUP_IDS=["123456789012345", "987654321098765"]
```

---

## 💬 Cách lấy Discord Webhook URL

1. Vào Discord Server → chọn kênh muốn nhận log.
2. **Settings kênh** → **Integrations** → **Webhooks** → **New Webhook**.
3. Đặt tên, chọn kênh → **Copy Webhook URL**.
4. Dán vào `.env`:
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1234567890/abcdefgh...
```

---

## 🚀 Lệnh chạy bot

```bash
# Chạy thẳng
python main.py

# Chạy nền (Linux/Mac)
nohup python main.py > bot.log 2>&1 &

# Xem log
tail -f bot.log
```

---

## ☁️ Deploy trên Railway

### Bước 1: Push code lên GitHub
```bash
git init
git add .
git commit -m "feat: facebook ai bot"
git remote add origin https://github.com/<username>/<repo>.git
git push -u origin main
```

### Bước 2: Tạo project trên Railway
1. Vào [railway.app](https://railway.app) → **New Project**.
2. Chọn **Deploy from GitHub repo** → chọn repo vừa push.
3. Railway tự detect Python project.

### Bước 3: Set biến môi trường
1. Trong Railway project → tab **Variables**.
2. Thêm tất cả biến từ file `.env` (copy từng biến một hoặc dùng nút **RAW Editor**).
3. **QUAN TRỌNG:** Đặt `COOKIES_FILE=cookies.json` và đảm bảo file `cookies.json` đã được commit vào repo.

### Bước 4: Cấu hình Start Command
Trong Railway → tab **Settings** → **Deploy** → **Start Command**:
```
python main.py
```

### Bước 5: Deploy
Click **Deploy** → Railway sẽ cài thư viện và chạy bot.

### Bước 6: Xem logs
Tab **Deployments** → click deployment đang chạy → xem **Logs** realtime.

> **Tip Railway:** Dùng tier **Hobby ($5/tháng)** để bot chạy 24/7 không bị sleep.

---

## 🔑 Lấy OpenRouter API Key

1. Đăng ký tại [openrouter.ai](https://openrouter.ai)
2. Vào **Keys** → **Create Key**
3. Copy key (dạng `sk-or-v1-...`) vào `.env`

Các model miễn phí/rẻ phổ biến:
- `google/gemini-flash-1.5` — nhanh, miễn phí quota
- `meta-llama/llama-3.1-8b-instruct:free` — miễn phí
- `mistralai/mistral-7b-instruct:free` — miễn phí

---

## 🐛 Troubleshooting

| Vấn đề | Giải pháp |
|---|---|
| `FBchatException: Login failed` | Kiểm tra email/password, xóa `cookies.json`, thử lại |
| `2FA / Checkpoint` | Dùng cookies thay vì email/password |
| `Bot không trả lời` | Kiểm tra `GROUP_IDS` và `BOT_NAME` đúng format |
| `OpenRouter 401` | Kiểm tra `OPENROUTER_API_KEY` |
| Bot disconnect liên tục | Tăng `RECONNECT_DELAY`, kiểm tra log Discord |

---

## ⚠️ Lưu ý quan trọng

- **Bảo mật:** Không commit file `.env` chứa thông tin thật lên GitHub (đã có trong `.gitignore`).
- **Facebook ToS:** Sử dụng bot tự động có thể vi phạm điều khoản Facebook. Dùng với trách nhiệm của bạn.
- **Cookies:** Cookies có thể hết hạn sau vài ngày/tuần. Nếu bot không login được, export cookies mới.
- **Rate limit:** Tránh gửi quá nhiều tin nhắn trong thời gian ngắn để không bị Facebook block.
