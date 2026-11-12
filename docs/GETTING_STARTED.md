# Chạy và trình diễn hệ thống Quản lý chung cư

## 1. Cấu trúc đã xây dựng

Ứng dụng gồm 8 Flask service chạy bằng Waitress trên 8 tiến trình riêng, giao tiếp bằng HTTP qua `requests`. Gateway ở cổng 5000 phục vụ giao diện tiếng Việt HTML/CSS/JavaScript và chuyển tiếp API đến service phù hợp.

| Thành phần | Cổng | Tài liệu API |
|---|---:|---|
| Giao diện / gateway | 5000 | http://localhost:5000 |
| Auth | 5001 | http://localhost:5001/docs |
| Resident | 5002 | http://localhost:5002/docs |
| Billing | 5003 | http://localhost:5003/docs |
| Parking | 5004 | http://localhost:5004/docs |
| Maintenance | 5005 | http://localhost:5005/docs |
| Notification | 5006 | http://localhost:5006/docs |
| Complaint | 5007 | http://localhost:5007/docs |
| Chatbot | 5008 | http://localhost:5008/docs |

**Cách chạy mặc định: Docker.** Chạy `./start.ps1` sau khi bật Docker Desktop; toàn bộ ứng dụng dùng `/app/data/QLCC.db` trong volume `qlcc_qlcc-data`. `data/QLCC.db` chỉ dùng khi chủ động chạy Python riêng, được tạo từ dữ liệu mẫu ở lần chạy đầu. Thông tin diện tích bị thiếu trong dữ liệu gốc được để trống đến khi Ban quản lý cập nhật.

## 2. Chạy Python riêng trên Windows (tùy chọn cho phát triển)

Yêu cầu Python 3.11 trở lên. Mở PowerShell tại thư mục dự án:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/init_db.py --demo
.\.venv\Scripts\python.exe scripts/run.py
```

Sau dòng `Ready`, mở **http://localhost:5000**. Không cần Node.js để chạy ứng dụng. Cũng có thể chạy `./start.ps1 -Mode Python` để thực hiện các bước này tự động, nếu chính sách PowerShell của máy cho phép chạy script. Chế độ này không đọc database Docker và không tự đồng bộ các giao dịch Live. `./start.ps1` không truyền tham số sẽ chạy Docker.

`init_db.py` tự tạo `.env` với JWT secret và service token ngẫu nhiên; không đưa `.env` lên Git. Chạy lại lệnh khởi tạo không xóa dữ liệu hoặc đặt lại mật khẩu.

Trên một database **mới, không phải Live**, `--demo` (hoặc `INIT_DEMO=true` trong `.env` khi chạy Docker) tạo các tài khoản sau để đăng nhập lần đầu:

| Vai trò demo | Tài khoản | Mật khẩu |
|---|---|---|
| Ban quản lý | `admin` | `Admin@12345` |
| Cư dân | `resident` | `Resident@12345` |
| Kỹ thuật viên | `technician` | `Tech@12345` |

Các mật khẩu này công khai trong tài liệu nên chỉ dùng cho môi trường thử. Với `SEPAY_ENV=live`, hệ thống không tạo các tài khoản này và từ chối khởi động nếu một tài khoản còn dùng mật khẩu đó. Mật khẩu mới cần từ 6 đến 30 ký tự; mỗi người tự đổi mật khẩu tại Thông tin cá nhân.

Nhấn **Ctrl+C** tại terminal chạy `scripts/run.py` để dừng cả 9 tiến trình. Nhật ký từng thành phần nằm trong `logs/`. Runner phát hiện cổng đã có tiến trình sử dụng và không tự chiếm cổng.

Chạy riêng một service để debug:

```powershell
.\.venv\Scripts\python.exe scripts/run.py --service billing
```

Service cần Auth để xác minh tài khoản còn hoạt động và cần các service phụ thuộc khi thực hiện nghiệp vụ liên quan.

## 3. Chạy bằng Docker Compose

Bật Docker Desktop và chạy các lệnh dưới. Không cần tạo `.env` trước: khi thiếu file này, hệ thống tự tạo khóa nội bộ ở lần chạy đầu, dùng dữ liệu mẫu và các tài khoản mẫu ở mục 2. Chỉ cần `.env` khi muốn bật SePay, Firebase hoặc Gemini.

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose logs -f billing
```

Compose tạo **8 container nghiệp vụ**, thêm gateway, một container `backup` và một job `db-init` chạy xong rồi thoát. Tất cả dùng named volume `qlcc_qlcc-data:/app/data`. DB Docker tách khỏi chế độ Python. Volume mới khởi tạo từ `QLCC.db` nguồn được đóng gói trong image; volume đã có DB tiếp tục giữ dữ liệu hiện tại. Gateway cổng 5000 và các service nghiệp vụ đều chỉ bind vào `127.0.0.1`: trang web dùng trên trình duyệt của chính máy chạy project. Các service chạy bằng user không có quyền root và chỉ nhận những khóa cần cho nhiệm vụ của mình.

Gateway đọc giao diện trực tiếp từ `./frontend` qua bind mount chỉ đọc. Khi chỉnh frontend, chạy `npm ci` một lần rồi giữ `npm run watch:css` chạy để biên dịch Tailwind. Lưu thay đổi và tải lại http://localhost:5000; không cần build lại image. `styles.css` là đầu ra, sửa `theme.css` và các class trong `app.js`. Các thay đổi Python cần build lại service tương ứng.

Không chạy đồng thời bản Python và Docker trên cùng bộ cổng. Dừng container bằng `docker compose down`; dữ liệu Docker vẫn nằm trong volume. Không thêm `-v` nếu cần giữ dữ liệu.

**Sao lưu:** container `backup` tạo mỗi ngày một bản đã kiểm tra tại `backups/QLCC-auto-*.db` và giữ 14 bản gần nhất. Sao lưu thủ công bất cứ lúc nào bằng `docker compose exec backup python scripts/backup_db.py --output /backups`. `backups/` chứa dữ liệu cá nhân và mật khẩu đã băm, không đưa lên Git.

Khôi phục một bản sao lưu (thay `TEN-BAN-SAO-LUU.db`):

```powershell
docker compose stop
docker compose run --rm --no-deps -v "${PWD}/backups:/backups:ro" db-init python -c "import sqlite3; s=sqlite3.connect('/backups/TEN-BAN-SAO-LUU.db'); d=sqlite3.connect('/app/data/QLCC.db'); s.backup(d); d.close()"
docker compose up -d
```

## 4. Trình diễn theo từng nghiệp vụ

1. Đăng nhập quản trị. Dashboard lấy số liệu thật từ các API căn hộ, Billing, phiếu kỹ thuật và thông báo.
2. Tạo căn hộ, nhập diện tích; tạo cư dân hoặc liên kết tài khoản đăng ký; tạo hợp đồng thuê/sở hữu. Mỗi tài khoản chỉ liên kết một căn hộ; căn hộ khác cần tài khoản riêng và được dùng chung email, số điện thoại. Nếu nhiều cư dân trùng tên, chọn đúng người theo mã `#` trong danh sách gợi ý. Theo dõi lịch sử hợp đồng, ngày kết thúc và số ngày còn lại.
3. Thêm phương tiện cho căn hộ. Lập hóa đơn điện/nước theo `YYYY-MM`; hóa đơn dịch vụ theo `YYYY-H1` hoặc `YYYY-H2`. Phí gửi xe sáu tháng lấy tổng phí phương tiện đang hoạt động qua HTTP sang Parking.
4. Cấu hình VietQR/SePay theo mục 6. Đăng nhập cư dân đúng căn hộ, mở hóa đơn, giữ nguyên nội dung chuyển khoản và mô phỏng giao dịch trong dashboard SePay. Web chỉ cập nhật sau khi server xác minh đủ tiền, rồi cho tải biên nhận Test. Nút Tôi đã chuyển khoản không tự đánh dấu đã trả. Nếu cư dân đã báo chuyển nhưng ngân hàng không có tiền, Ban quản lý mở chi tiết hóa đơn và chọn **Mở khóa phiên thanh toán**.
5. Gửi khiếu nại/đơn đăng ký gửi xe hoặc phiếu sửa chữa. Ban quản lý phản hồi, duyệt đơn, tạo phương tiện nếu hồ sơ được chấp thuận; việc duyệt đơn không tự thêm phương tiện vì đơn là nội dung tự do.
6. Quản trị phân công kỹ thuật viên. Mọi kỹ thuật viên đều thấy và xử lý được mọi phiếu, chuyển từ chờ sang đang xử lý rồi hoàn thành; ghi nhận doanh thu vé vãng lai theo ngày.
7. Gửi thông báo chung/riêng hoặc thông báo cho Ban quản lý. Cư dân xem, đánh dấu đã đọc. Bật thông báo trình duyệt sau khi cấu hình Firebase.
8. Xem báo cáo theo tháng/quý. Phát hành và thực thu được tách riêng theo kỳ hóa đơn và ngày thanh toán; vé vãng lai xem ở màn hình gửi xe.
9. Hỏi chatbot về thú cưng, giờ ra vào, gửi xe, phòng camera, hiệu thuốc. Chatbot tra cứu FAQ/địa điểm có sẵn và trả lời rõ khi không tìm thấy dữ liệu.

## 5. Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Test dùng bản sao dữ liệu trong thư mục tạm. Chúng không thanh toán tiền thật, không gửi push thật và không sửa DB đang chạy. Chi tiết: [TESTING.md](TESTING.md).

Kiểm tra trạng thái: http://localhost:5000/api-status. Swagger mỗi service có nút **Authorize**; lấy JWT từ `/api/auth/login`, sau đó dán JWT vào ô xác thực.

## 6. Kết nối SePay và Firebase

Mọi cấu hình nằm trong `.env`, có chú thích trong `.env.example`. Sau khi sửa `.env`, chạy `docker compose up -d` để tạo lại container.

**VietQR/SePay**

1. Trên [my.sepay.vn](https://my.sepay.vn/), bật **Test Mode** và tạo tài khoản ngân hàng Test. Điền `SEPAY_BANK_CODE`, `SEPAY_BANK_NAME`, `SEPAY_ACCOUNT_NUMBER`, `SEPAY_ACCOUNT_NAME` và đặt `SEPAY_ENV=test`.
2. Mở HTTPS công khai tới gateway: `cloudflared tunnel --url http://localhost:5000 --protocol http2`. Ghép URL in ra với `/api/billing/sepay/webhook` và điền vào `SEPAY_WEBHOOK_URL`. Quick tunnel đổi tên khi chạy lại; khi đổi, sửa cả `.env` và SePay.
3. Tạo webhook trên SePay trỏ tới URL đó, xác thực bằng API Key với đúng giá trị `SEPAY_WEBHOOK_API_KEY` trong `.env`.
4. Tùy chọn đối soát dự phòng: điền cả `SEPAY_API_TOKEN` và UUID `SEPAY_BANK_ACCOUNT_ID`.
5. Kiểm tra bằng `.\.venv\Scripts\python.exe scripts/check_sepay.py --probe`. Webhook trả 403 khi không có khóa là đúng.

Trong Test Mode chỉ mô phỏng giao dịch trên dashboard SePay, không quét QR bằng ứng dụng ngân hàng thật. Live dùng tài khoản, token và khóa riêng, chuyển tiền thật.

Tunnel chỉ chuyển webhook SePay; mọi đường dẫn khác đi qua tunnel trả 404. Trang web mở tại http://localhost:5000 trên máy chạy project.

**Firebase push (tùy chọn)**

1. Trong cùng một Firebase project, lấy Web config, VAPID key và service account.
2. Lưu service account tại `secrets/firebase-credentials.json`; điền `FIREBASE_PROJECT_ID`, `FIREBASE_WEB_CONFIG` (JSON một dòng), `FIREBASE_VAPID_KEY`.
3. Kiểm tra bằng `docker compose exec notification python scripts/check_firebase.py`.

Push hoạt động trên trình duyệt máy tính tại http://localhost:5000 khi người dùng đồng ý nhận thông báo. Khi chưa cấu hình, thông báo trong web vẫn hoạt động.

## 7. Giới hạn cần nêu trong báo cáo

- Một file SQLite vật lý dùng chung, một writer tại một thời điểm. WAL và timeout giảm xung đột nhưng không biến SQLite thành cơ sở dữ liệu phân tán.
- Các service trao đổi qua HTTP và outbox; truy vấn ứng dụng không JOIN chéo bảng giữa service.
- Hợp đồng mới không được trùng thời gian đang hoạt động của cùng căn hộ.
- Cắt/cấp lại dịch vụ tại mục Quản lý dịch vụ chỉ ghi nhận trạng thái và gửi thông báo; hệ thống không điều khiển thiết bị điện/nước.
- Biên nhận HTML là chứng từ nội bộ, chưa tích hợp nhà cung cấp hóa đơn điện tử thuế. Hoàn tiền thừa do BQL thực hiện ngoài ứng dụng; source chỉ lưu ghi chú xử lý.
- JWT có thời hạn 8 giờ; đổi vai trò và đổi mật khẩu có hiệu lực ngay qua Auth. Chưa có refresh token; đăng xuất xóa JWT ở trình duyệt.
- Chưa triển khai phân trang phía máy chủ hoặc hạ tầng nhiều replica. Đây là bản demo/khóa luận theo phạm vi readme.
