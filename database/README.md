# Database của hệ thống (đã ẩn danh)

`QLCC_an_danh.db` là bản sao **dữ liệu thật** của hệ thống đang chạy (SQLite), đã thay mọi thông tin nhận ra được một người. Cấu trúc giống hệt database đang chạy: 37 bảng, 7 view, các chỉ mục, ràng buộc và trigger sau mọi migration.

**Giữ nguyên:** căn hộ, hợp đồng, xác nhận căn hộ, hóa đơn và số tiền, thanh toán, xe, vé vãng lai, phiếu sửa chữa, khiếu nại, thông báo, câu hỏi chatbot, trạng thái, ngày giờ và liên kết giữa các bảng.

**Đã thay hoặc bỏ:**

| Thông tin | Trong bản này |
|---|---|
| Họ tên | `Cư dân 26`, `Quản lý 16`, `Kỹ thuật viên 18`… (một người giữ một tên giả ở mọi nơi) |
| Tên đăng nhập, email | `cudan19`, `bql16`, `ktv18`…; email dạng `@example.invalid` |
| Mật khẩu | vô hiệu, không tài khoản nào đăng nhập được |
| Số điện thoại | số giả `0900…`, `0910…` |
| CCCD | bỏ |
| Biển số xe thật | biển giả `99X9-…` (mã xe đạp theo căn hộ như `B804-XD-2` giữ nguyên) |
| Số và tên tài khoản ngân hàng, mã tham chiếu, mã giao dịch | `0000000000`, `BAN QUAN LY AN CU`, `REF…`, `SEPAY-…`, `HD-GD…` |
| Tên, số điện thoại, email trong nội dung thông báo, khiếu nại, nhật ký | thay bằng tên giả hoặc `[đã ẩn]` |
| Ảnh đính kèm khiếu nại, địa chỉ IP, token thiết bị, hàng đợi gửi thông báo | bỏ |

## Cách mở

- **DB Browser for SQLite**: File → Open Database Read Only → chọn `QLCC_an_danh.db`. Tab *Database Structure* xem bảng, *Browse Data* xem dữ liệu.
- **DBeaver**: tạo kết nối SQLite tới file này, chọn database → *View Diagram* để có sơ đồ ERD.
- Bảng `schema_migrations` ghi lại các migration đã áp dụng.

## Database thật nằm ở đâu

Hệ thống đang chạy dùng file `QLCC.db` trong volume Docker `qlcc-data`, không nằm trong thư mục project. Lần đầu chạy `docker compose up`, `scripts/init_db.py` tạo file đó từ dữ liệu mẫu `tests/fixtures/demo.sql` rồi áp dụng các file trong `migrations/`; những lần sau chỉ áp dụng migration mới, không ghi đè dữ liệu. Bản gốc không đưa lên Git vì repo công khai và có thông tin cá nhân.

## Cập nhật bản ẩn danh

Khi dữ liệu hoặc cấu trúc thay đổi (sau khi triển khai migration mới), tạo bản sao lưu mới rồi xuất lại:

```powershell
docker compose exec -T backup python scripts/backup_db.py --output /backups
python scripts/export_public_db.py
```

Script đọc bản sao lưu mới nhất trong `backups/`, không mở database đang chạy, và **ghi đè đúng file `QLCC_an_danh.db`** (bản cũ vẫn còn trong lịch sử Git). Nó dừng, không tạo file, nếu sau khi thay còn tìm thấy bất kỳ giá trị cá nhân nào. Bước `scripts/ci/check_repository.py` chỉ cho phép file `.db` này trong Git và chặn nếu nó chưa được ẩn danh; test `tests/test_public_database.py` báo lỗi nếu file lỗi thời so với migration.

Tên một chữ (ví dụ "Ngọc") chỉ được thay trong cột họ tên và trong thông báo đăng ký, vì tìm một chữ trong văn bản tự do sẽ làm hỏng từ thường ("Ánh" trong "phản ánh"). Nếu nhập tên một chữ ở chỗ khác, hãy mở file kiểm tra trước khi commit.
