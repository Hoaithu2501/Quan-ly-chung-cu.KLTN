# Bản xuất đầy đủ của database

**Database đang phục vụ web nằm trong Docker:** `/app/data/QLCC.db`, volume `qlcc_qlcc-data`.

`QLCC.snapshot.db` là bản xuất chứa **toàn bộ 37 bảng** của database Docker tại thời điểm sao lưu: tài khoản, cư dân, hóa đơn, thanh toán SePay, thông báo, đăng ký push Firebase, FAQ và các dữ liệu nghiệp vụ khác. Có thể mở file này bằng DB Browser for SQLite để xem.

Bản xuất được tạo bằng SQLite backup, đã bao gồm dữ liệu đã commit trong WAL và lưu thành một file độc lập. Nó không tự cập nhật theo web; sửa bản xuất không sửa dữ liệu Docker.

Các bản cũ đã được gom trong [database-archive-20261108-075353.zip](../backups/database-archive-20261108-075353.zip); xem `manifest.json` trong gói để biết file gốc, mã kiểm tra SHA-256 và kết quả kiểm tra. Khi phục hồi một bản cũ, lấy file trong `snapshots/` của gói. Không chép đè lên database đang chạy.

File `QLCC.db` ở **gốc dự án** được giữ riêng vì bộ kiểm thử và bước khởi tạo volume mới vẫn cần dữ liệu nguồn. Không thay nó bằng bản xuất Live.

Xuất bản mới bằng lệnh sau (công cụ từ chối ghi đè nếu file đích đã tồn tại):

```powershell
.\.venv\Scripts\python.exe scripts/export_database.py --output backups/QLCC-export-moi.db
```

Xem [database chính và cách kiểm tra](../docs/DATABASE.md). Từ thư mục dự án, chạy `./start.ps1` để tiếp tục đúng dữ liệu Docker.
