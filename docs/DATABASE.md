# Database chính của An Cư

**Khi chạy bằng Docker, toàn bộ ứng dụng dùng một database: `/app/data/QLCC.db` trong volume `qlcc_qlcc-data`.** Đây là bản cần kiểm tra khi xem hóa đơn, thanh toán SePay, tài khoản, chatbot hoặc thông báo Firebase.

Desktop tại `http://localhost:5000` và iPhone qua tunnel HTTPS cùng truy cập gateway cổng 5000. Cả hai dùng chung database này. Không cần tạo database hay webhook riêng cho điện thoại.

## Vì sao có nhiều file `.db`?

| Vị trí | Vai trò | Có phục vụ web Docker đang dùng không? |
| --- | --- | --- |
| Volume `qlcc_qlcc-data`, file `/app/data/QLCC.db` | Database chính; tất cả service cùng đọc/ghi | **Có** |
| `QLCC.db` ở gốc dự án | Dữ liệu nguồn cho khởi tạo và fixture kiểm thử | Không |
| `data/QLCC.snapshot.db` | Bản xuất đầy đủ từ Docker để mở xem hoặc sao lưu | Không; không tự cập nhật theo web |
| `backups/database-archive-*.zip` | Gói chứa các bản Python cũ, seed cũ và snapshot nhập dữ liệu trước khi dọn | Không |
| `backups/` trong volume | Các bản sao phục hồi trước những lần nâng cấp | Không |
| Database trong thư mục tạm của pytest | Dữ liệu kiểm thử độc lập | Không |

Các file `QLCC.db-wal` và `QLCC.db-shm` là file hỗ trợ SQLite cho chính database bên cạnh chúng. Chúng không phải database nghiệp vụ riêng để gộp hoặc xóa. Giao dịch vừa ghi có thể còn trong WAL; xuất bằng SQLite backup để lấy đủ dữ liệu.

Không đồng bộ hai chiều giữa bản Python và Docker. Sửa `data/QLCC.db` bằng DB Browser trên Windows không làm thay đổi web Docker. Các màn hình quản lý của ứng dụng ghi trực tiếp vào bản chính theo quyền tài khoản.

Bản `data/QLCC.db` cũ được sao lưu vào gói ZIP trước khi dọn. Nếu chủ động chạy lại chế độ Python, nó có thể được tạo lại từ nguồn; đây vẫn là một môi trường riêng. Không dùng file xuất Live làm dữ liệu mẫu cho bộ kiểm thử.

## Cách chạy thống nhất

Bật Docker Desktop rồi chạy một trong hai lệnh:

```powershell
.\start.ps1
# Hoặc:
docker compose up --build -d
```

`start.ps1` mặc định dùng Docker. Nếu Docker lỗi, script dừng để xử lý, không tự chuyển sang dữ liệu Python. Dừng/chạy lại thông thường bằng `docker compose stop` và `docker compose start` sẽ giữ volume.

Chỉ khi chủ động phát triển bằng Python mới dùng `./start.ps1 -Mode Python`; chế độ này dùng database khác, không chứa các cập nhật mới trong Docker. Không dùng để nghiệm thu tiếp các giao dịch Live hiện tại.

Trong `.env`, `DATABASE_PATH=data/QLCC.db` dành cho Python trên Windows. Docker Compose **ghi đè** biến này thành `/app/data/QLCC.db` cho tất cả service. Không đổi biến Windows sang đường dẫn bên trong container để cố làm chúng đồng bộ.

## Kiểm tra bản đang dùng

```powershell
.\.venv\Scripts\python.exe scripts/check_database.py
```

Lệnh mặc định kiểm tra Docker, không chỉnh dữ liệu. Kết quả cần có:

- `All services share one database: OK`.
- Mỗi service trỏ tới cùng volume và cùng file `QLCC.db`.
- `Integrity: ok`, `Foreign-key issues: 0`.

`db-init` ở trạng thái `exited` là bình thường nếu lần khởi tạo đã thành công. Công cụ kiểm tra database không thay thế healthcheck của từng API.

Liệt kê thêm các file nguồn/bản cũ/sao lưu trên Windows:

```powershell
.\.venv\Scripts\python.exe scripts/check_database.py --inventory
```

Thêm `--json` nếu cần báo cáo số dòng từng bảng. Công cụ không in nội dung cư dân, mật khẩu hoặc token Firebase. Docker không truy cập được thì lệnh báo lỗi, không dùng file Windows thay thế.

## Kết quả kiểm tra ngày 08/11/2026

- Gateway, 8 service nghiệp vụ và job `db-init` đều cấu hình cùng volume `qlcc_qlcc-data`, cùng file `/app/data/QLCC.db`.
- Database chính có **37 bảng ứng dụng**, kiểm tra toàn vẹn `ok`, **0 lỗi khóa ngoại**.
- Tại thời điểm kiểm tra: 25 tài khoản, 22 hồ sơ cư dân, 270 căn hộ; 19 hóa đơn tháng, 18 bản ghi thanh toán tháng; 15 hóa đơn dịch vụ nửa năm, 15 bản ghi thanh toán tương ứng; 2 giao dịch ngân hàng, 31 FAQ, 69 thông báo và 4 token push.
- Đã đối chiếu 8 file `.db` trên Windows theo khóa chính và giá trị các cột chung. Không có khóa bản ghi nào chỉ nằm trong các file cũ mà thiếu ở Docker trong các bảng đã đối chiếu. Một số bản ghi cùng khóa có giá trị khác vì dữ liệu đã được cập nhật; thông báo nguồn còn có bảng ánh xạ riêng.
- Kết quả này không chứng minh mọi giá trị cũ là sai, nhưng không có căn cứ để nhập lại toàn bộ bản cũ. **Giữ database Docker làm bản chính, không gộp hoặc ghi đè dữ liệu đang dùng.** Những bản sao lưu vẫn được giữ để tra cứu/phục hồi.

Không cần chuyển database sang bind mount Windows chỉ để nhìn thấy một file ở thư mục gốc. Dự án từng gặp lỗi SQLite I/O trên mount Windows và đã chuyển sang volume; giữ cấu hình hiện tại tránh lặp lại tình trạng đó.

## Muốn mở dữ liệu bằng DB Browser

Mở `data/QLCC.snapshot.db`. Đây là bản sao đầy đủ tại thời điểm xuất; thay đổi trong bản sao không tự cập nhật web. Không chép riêng file `.db` đang hoạt động rồi bỏ qua WAL.

Để xuất lại từ Docker đang chạy:

```powershell
.\.venv\Scripts\python.exe scripts/export_database.py --output backups/QLCC-export-moi.db
```

Công cụ mở nguồn chỉ đọc, dùng SQLite backup, chuyển bản xuất sang chế độ một file độc lập và kiểm tra toàn vẹn/khóa ngoại/SHA-256 trước khi hoàn tất. Từ chối ghi đè file đích đã có. Dùng tên mới cho lần sao lưu tiếp theo; không xóa bản đang mở hoặc tự chép đè vào volume.

Gói `backups/database-archive-*.zip` lưu các bản cũ theo đường dẫn gốc dưới `snapshots/`, kèm `manifest.json`. Các file trong gói cũng là snapshot SQLite độc lập đã gồm WAL; không cần khôi phục thêm `-wal`/`-shm`. Chúng được giữ riêng trong gói thay vì trộn vào dữ liệu Live. File `QLCC.db` ở gốc vẫn được giữ vì Dockerfile khởi tạo và bộ kiểm thử cần nó. Volume mới khởi tạo từ file nguồn này; volume hiện có tiếp tục dùng dữ liệu của chính nó.

Nếu thực sự cần nhập thêm danh mục từ nguồn, dùng [DATABASE_REFRESH.md](DATABASE_REFRESH.md), xem trước và sao lưu trước khi áp dụng. Không dùng nhập danh mục để thay hóa đơn, thanh toán, tài khoản hoặc thông báo sự kiện hiện có. Không dùng `docker compose down -v` vì lệnh đó xóa volume dữ liệu.
