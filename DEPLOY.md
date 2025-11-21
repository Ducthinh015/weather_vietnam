# Hướng dẫn triển khai (Deployment Guide)

Để hệ thống chạy "thật 100%" trên môi trường online (production), bạn cần thực hiện 3 bước chính:
1. **Cơ sở dữ liệu**: Tạo MongoDB trên cloud (MongoDB Atlas).
2. **Backend**: Đẩy lên Fly.io (hoặc Render).
3. **Frontend**: Cập nhật cấu hình trên Render để trỏ về Backend mới.

---

## Bước 1: Tạo Database MongoDB Atlas (Miễn phí)
Vì Fly.io hay Render không lưu dữ liệu lâu dài trên container (stateless), bạn CẦN một database riêng.
1. Truy cập [MongoDB Atlas](https://www.mongodb.com/atlas) và đăng ký tài khoản.
2. Tạo một **Cluster** (chọn gói Shared/Free).
3. Vào tab **Database Access**, tạo user (ví dụ: `admin`/`password123`).
4. Vào tab **Network Access**, thêm IP `0.0.0.0/0` (cho phép truy cập từ mọi nơi).
5. Nhấn **Connect** > **Drivers** > Copy chuỗi kết nối (URI).
   - Ví dụ: `mongodb+srv://admin:password123@cluster0.mongodb.net/?retryWrites=true&w=majority`
   - *Lưu ý: thay password thật vào.*

---

## Bước 2: Deploy Backend lên Fly.io
(Giả sử bạn đã cài `flyctl` và đăng nhập)

1. Mở terminal tại thư mục `backend`:
   ```bash
   cd backend
   ```

2. Khởi tạo ứng dụng Fly:
   ```bash
   fly launch
   ```
   - App Name: (đặt tên tùy ý, vd: `agricast-backend`)
   - Region: Chọn Singapore (`sin`) hoặc Hong Kong (`hkg`) cho nhanh.
   - Configuration: Chọn mặc định (Yes/Enter).
   - **Database**: Chọn `No` (vì ta dùng MongoDB Atlas).
   - **Redis**: Chọn `No`.

3. Cấu hình biến môi trường (Secrets):
   Thay thế bằng giá trị thật của bạn:
   ```bash
   fly secrets set WEATHERAPI_KEY="API_KEY_CUA_BAN"
   fly secrets set MONGO_URI="mongodb+srv://..."
   ```

4. Deploy:
   ```bash
   fly deploy
   ```

5. Lấy URL backend:
   Sau khi xong, bạn sẽ có link dạng: `https://agricast-backend.fly.dev`.
   Hãy thử truy cập `https://agricast-backend.fly.dev/health` để xem nó sống chưa.

---

## Bước 3: Cập nhật Frontend trên Render
Frontend cần biết Backend nằm ở đâu.

1. Mở file `frontend/src/pages/weather-gru.html`.
2. Tìm dòng:
   ```javascript
   const API_BASE = window.API_BASE || "https://agricast-ai-vn-838179290451.asia-southeast1.run.app/api";
   ```
3. Sửa thành link Backend vừa có ở Bước 2:
   ```javascript
   const API_BASE = "https://agricast-backend.fly.dev/api"; 
   // (Nhớ thêm /api ở cuối nếu code backend mount tại đó, code hiện tại mount blueprint tại /api)
   ```
   *Lưu ý: Code hiện tại `app.register_blueprint(..., url_prefix="/api")` nên URL phải là `.../api`.*

4. Commit và Push code lên GitHub. Render sẽ tự động build lại Frontend.

---

## Checklist kiểm tra Production
- [ ] Backend `/health` trả về `{"status": "ok"}`.
- [ ] Backend `/api/weather/cities` trả về danh sách tỉnh.
- [ ] Frontend hiện Dashboard, không báo lỗi Network/Cors.
- [ ] Bấm "Lấy dữ liệu mới" trên Dashboard thành công (dữ liệu ghi vào Mongo Atlas).

Chúc mừng! Hệ thống của bạn đã chạy online hoàn toàn.
