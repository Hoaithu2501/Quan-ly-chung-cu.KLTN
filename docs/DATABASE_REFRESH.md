# Đồng bộ dữ liệu nguồn vào ứng dụng

`QLCC.db` ở thư mục gốc là nguồn do người quản lý cập nhật. Bản Python dùng `data/QLCC.db`; bản Docker dùng `/app/data/QLCC.db` trong volume `qlcc_qlcc-data`. Sửa file nguồn hoặc chạy lại `init_db.py` không tự ghi đè dữ liệu đang phục vụ web.

`scripts/refresh_db.py` nhập danh mục căn hộ, FAQ, địa điểm và thông báo từ nguồn. Lệnh mặc định chỉ xem trước; `--apply` mới lưu thay đổi, sau khi tạo bản sao SQLite nhất quán. File nguồn được mở chỉ đọc; SQLite backup lấy cả dữ liệu đã commit trong WAL.

## Dữ liệu được giữ lại

- Giữ tài khoản, mật khẩu, cư dân, liên kết tài khoản, hợp đồng, hóa đơn, thanh toán, phương tiện, phiếu kỹ thuật và dữ liệu nghiệp vụ do ứng dụng tạo.
- Căn hộ cập nhật mã, tòa, tầng và diện tích nếu nguồn có cột này. Trạng thái căn hộ hiện có được giữ vì liên quan đến hợp đồng; căn hộ mới lấy trạng thái từ nguồn.
- Không xóa dòng chỉ có ở ứng dụng khi dòng đó không còn trong nguồn.
- Thông báo được so sánh theo toàn bộ nội dung trước khi nhập. Nếu ID trùng nhưng nội dung khác, thông báo nguồn nhận ID mới; giữ nguyên thông báo cũ và liên kết sự kiện, người nhận, trạng thái đã đọc. Bảng `source_notification_imports` lưu ánh xạ để lần nhập sau cập nhật đúng thông báo nguồn, không tạo trùng. Nội dung giống nhau đã có trên server được dùng lại. Các thông báo khác nội dung được giữ riêng vì chưa có bằng chứng là cùng một thông báo.
- Toàn bộ lần nhập nằm trong một giao dịch. Lỗi dữ liệu, khóa ngoại hoặc trùng mã căn hộ sẽ hoàn tác lần nhập; bản sao trước nhập vẫn còn để kiểm tra.

Không dùng chức năng này để thay toàn bộ dữ liệu nghiệp vụ bằng file nguồn. Các bảng giao dịch không nằm trong danh sách được phép đồng bộ.

## Bản Python

Dừng runner bằng Ctrl+C, rồi chạy:

```powershell
.\.venv\Scripts\python.exe scripts/refresh_db.py
.\.venv\Scripts\python.exe scripts/refresh_db.py --apply
.\.venv\Scripts\python.exe scripts/init_db.py
.\.venv\Scripts\python.exe scripts/run.py
```

Kiểm tra kết quả từng lệnh trước khi chuyển bước. JSON trả về số dòng thêm, sửa, giữ nguyên và đường dẫn bản sao trước nhập. Mặc định bản sao ở `data/backups/`. Có thể chỉ đồng bộ một số bảng bằng `--tables apartments faq_knowledge_base locations`; dùng `--source`, `--database` và `--backup-dir` để chỉ định đường dẫn khác.

`init_db.py` áp dụng migration sau khi nhập dữ liệu. Mỗi migration và dòng ghi nhận tương ứng trong `schema_migrations` commit cùng nhau; lỗi sẽ hoàn tác migration đó. Các lần khởi động sau bỏ qua migration đã hoàn tất.

Sau khi migration nội dung chính sách đã được áp dụng lần đầu, các lần đồng bộ tiếp theo tự áp dụng lại quy tắc viết “Ban quản lý” và FAQ gửi xe hiện hành trong cùng giao dịch nhập. Kết quả `content_policy` cho biết bước này có chạy hay không, tránh đưa nội dung chính sách cũ trở lại từ nguồn.

## Bản Docker

Trước tiên xuất snapshot mới từ file nguồn. Mỗi lần dùng tên mới, vì lệnh từ chối ghi đè file đã tồn tại:

```powershell
$sourceSnapshot = 'QLCC.source-refresh-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.db'
.\.venv\Scripts\python.exe scripts/refresh_db.py --snapshot-to "data/$sourceSnapshot"
docker compose build
docker compose run --rm --no-deps db-init python scripts/refresh_db.py --source "/seed/$sourceSnapshot"
```

Xem trước trong container sẽ đọc đúng DB volume đang dùng. Sau khi kiểm tra số liệu, dừng các service để đồng bộ và nâng cấp schema:

```powershell
docker compose stop
docker compose run --rm --no-deps db-init python scripts/refresh_db.py --source "/seed/$sourceSnapshot" --apply
docker compose run --rm --no-deps db-init python -c "from scripts.init_db import initialize; initialize()"
docker compose up -d --no-build
docker compose ps -a
```

Chỉ chạy bước tiếp theo khi bước trước thành công. Nếu nhập hoặc migration lỗi, giữ service dừng để kiểm tra trước khi khởi chạy lại. Không xóa volume. Bản sao tự động nằm trong `/app/data/backups/` của volume; nên xuất về Windows, dùng đúng tên file in trong kết quả nhập:

```powershell
New-Item -ItemType Directory -Path backups -Force | Out-Null
docker compose cp auth:/app/data/backups/<ten-file-backup>.db backups/
```

Sau khi khởi động, kiểm tra `http://localhost:5000/api-status`, đăng nhập và đối chiếu số căn hộ/thông báo. Kiểm tra dữ liệu giao dịch và tài khoản đã tồn tại vẫn còn. Thư mục `backups/` có thể chứa dữ liệu cá nhân và mật khẩu đã băm, cần giữ ngoài Git.

Nếu cần khôi phục, dừng toàn bộ service, dùng SQLite backup từ bản sao đã kiểm tra về DB ứng dụng, rồi khởi động bằng phiên bản mã nguồn tương ứng. Không chép riêng file `.db` đè lên DB đang chạy hoặc bỏ qua các file WAL.
