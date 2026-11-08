# Dữ liệu mẫu cho CI và Docker image

`demo.sql` giữ schema, khóa ngoại, ID và các tình huống nghiệp vụ phục vụ bộ kiểm thử. Tên người, tài khoản đăng nhập, liên hệ, biển số, mã giao dịch và nội dung yêu cầu/thông báo đã được thay bằng dữ liệu mẫu. Tài khoản nguồn có password hash bị vô hiệu hóa; các bài test đặt mật khẩu riêng trong database tạm.

Không xuất database Live vào file này. Không commit `.db`, bản sao lưu hoặc credentials.

Trên bản clone mới chưa có `QLCC.db`, chạy:

```powershell
python scripts/ci/prepare_database.py
```

Lệnh từ chối ghi đè nếu file đã tồn tại. `Dockerfile.init` tự tạo database nguồn trong image từ SQL này. Khi khởi động, `scripts/init_db.py` chỉ tạo database ứng dụng nếu chưa có, rồi áp dụng migration còn thiếu; không thay dữ liệu đang nằm trong volume.

Muốn có ba tài khoản demo trong một database mới, dùng `scripts/init_db.py --demo` hoặc đặt `INIT_DEMO=true` khi chạy `docker-compose.release.yml`. Mật khẩu demo được công khai trong tài liệu, chỉ dùng cho môi trường kiểm thử.
