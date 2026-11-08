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

**Cách chạy mặc định: Docker.** Chạy `./start.ps1` sau khi bật Docker Desktop; toàn bộ ứng dụng dùng `/app/data/QLCC.db` trong volume `qlcc_qlcc-data`. Xem [database chính](DATABASE.md). `QLCC.db` ở thư mục gốc là nguồn được giữ nguyên; `data/QLCC.db` chỉ dùng khi chủ động chạy Python riêng. Thông tin diện tích bị thiếu trong dữ liệu gốc được để trống đến khi Ban quản lý cập nhật.

Khi cập nhật file nguồn, xem [đồng bộ dữ liệu vào ứng dụng](DATABASE_REFRESH.md). Công cụ nhập danh mục và thông báo có sao lưu, giữ tài khoản và giao dịch đang có; hỗ trợ cả DB Python và volume Docker.

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

| Vai trò demo | Tài khoản | Mật khẩu |
|---|---|---|
| Ban quản lý | `admin` | `Admin@12345` |
| Cư dân | `resident` | `Resident@12345` |
| Kỹ thuật viên | `technician` | `Tech@12345` |

Đây là tài khoản demo được thêm bằng `--demo` trên bản sao DB. Cư dân demo liên kết hồ sơ #1, kỹ thuật viên demo liên kết nhân sự #1. Các tài khoản mẫu gốc chứa chuỗi `hash_pw_...`, không phải mật khẩu đã băm hợp lệ; quản trị có thể đặt lại mật khẩu qua màn hình tài khoản/API.

Nhấn **Ctrl+C** tại terminal chạy `scripts/run.py` để dừng cả 9 tiến trình. Nhật ký từng thành phần nằm trong `logs/`. Runner phát hiện cổng đã có tiến trình sử dụng và không tự chiếm cổng.

Chạy riêng một service để debug:

```powershell
.\.venv\Scripts\python.exe scripts/run.py --service billing
```

Service cần Auth để xác minh tài khoản còn hoạt động và cần các service phụ thuộc khi thực hiện nghiệp vụ liên quan. Test fixture có thể khởi chạy các service trên cổng ngẫu nhiên để kiểm thử độc lập với bản demo.

## 3. Chạy bằng Docker Compose

Hướng dẫn Docker cho người mới, các lệnh quản lý container, sao lưu và kết quả rà soát dữ liệu: [DOCKER_GUIDE.md](DOCKER_GUIDE.md).

Sau bước khởi tạo `.env` và DB ở trên, bật Docker Desktop và chạy:

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose logs -f billing
```

Compose tạo **8 container nghiệp vụ**, thêm gateway và một job `db-init` chạy xong rồi thoát. Tất cả dùng mạng `qlcc` và named volume `qlcc_qlcc-data:/app/data`. DB Docker tách khỏi chế độ Python. Volume mới khởi tạo từ `QLCC.db` nguồn được đóng gói trong image; volume đã có DB tiếp tục giữ dữ liệu hiện tại. Bản `QLCC.docker-seed.db` cũ đã được đưa vào gói lưu trữ và không còn cấu hình làm nguồn mặc định. Gateway cổng 5000 được bind vào `0.0.0.0` để truy cập từ mạng LAN; các service nghiệp vụ bind vào `127.0.0.1`. Mỗi service có Dockerfile riêng; build context là thư mục gốc để có thể copy `shared/`.

Gateway đọc giao diện trực tiếp từ `./frontend` qua bind mount chỉ đọc. Khi chỉnh frontend, chạy `npm ci` một lần rồi giữ `npm run watch:css` chạy để biên dịch Tailwind. Lưu thay đổi và tải lại http://localhost:5000; không cần build lại image. `styles.css` là đầu ra, sửa `theme.css` và các class trong `app.js`. Container cũ cần áp dụng mount một lần bằng `docker compose up -d --build --no-deps gateway`. Các thay đổi Python vẫn cần build lại service tương ứng. Xem [FRONTEND.md](FRONTEND.md) và [DOCKER_GUIDE.md](DOCKER_GUIDE.md).

Không chạy đồng thời bản Python và Docker trên cùng bộ cổng. Dừng bản Python trước khi bật Docker hoặc ngược lại. Dừng container bằng `docker compose down`; dữ liệu Docker vẫn nằm trong volume. Không thêm `-v` nếu cần giữ dữ liệu. Xem cách xuất bản sao DB về Windows trong [DOCKER_GUIDE.md](DOCKER_GUIDE.md).

## 4. Trình diễn theo từng nghiệp vụ

1. Đăng nhập quản trị. Dashboard lấy số liệu thật từ các API căn hộ, Billing, phiếu kỹ thuật và thông báo.
2. Tạo căn hộ, nhập diện tích; tạo cư dân hoặc liên kết tài khoản đăng ký; tạo hợp đồng thuê/sở hữu. Theo dõi lịch sử hợp đồng, ngày kết thúc và số ngày còn lại.
3. Thêm phương tiện cho căn hộ. Lập hóa đơn điện/nước theo `YYYY-MM`; hóa đơn dịch vụ theo `YYYY-H1` hoặc `YYYY-H2`. Phí gửi xe sáu tháng lấy tổng phí phương tiện đang hoạt động qua HTTP sang Parking.
4. Cấu hình VietQR/SePay theo [SEPAY_VIETQR.md](SEPAY_VIETQR.md), dùng `PAYMENT_MODE=sepay` và `SEPAY_ENV=test`. Đăng nhập cư dân đúng căn hộ, mở hóa đơn, giữ nguyên nội dung chuyển khoản và mô phỏng giao dịch trong dashboard SePay. Web chỉ cập nhật sau khi server xác minh đủ tiền, rồi cho tải biên nhận Test. Nút Tôi đã chuyển khoản không tự đánh dấu đã trả.
5. Gửi khiếu nại/đơn đăng ký gửi xe hoặc phiếu sửa chữa. Ban quản lý phản hồi, duyệt đơn, tạo phương tiện nếu hồ sơ được chấp thuận; việc duyệt đơn không tự thêm phương tiện vì đơn là nội dung tự do.
6. Quản trị phân công kỹ thuật viên. Kỹ thuật viên chỉ thấy công việc của mình, chuyển từ chờ sang đang xử lý rồi hoàn thành; ghi nhận doanh thu vé vãng lai theo ngày.
7. Gửi thông báo chung/riêng hoặc thông báo cho Ban quản lý. Cư dân xem, đánh dấu đã đọc. Bật thông báo trình duyệt sau khi cấu hình Firebase.
8. Xem báo cáo theo tháng/quý. Phát hành và thực thu được tách riêng theo kỳ hóa đơn và ngày thanh toán; vé vãng lai xem ở màn hình gửi xe.
9. Hỏi chatbot về thú cưng, giờ ra vào, gửi xe, phòng camera, hiệu thuốc. Chatbot tra cứu FAQ/địa điểm có sẵn và trả lời rõ khi không tìm thấy dữ liệu.

## 5. Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Test dùng bản sao dữ liệu trong thư mục tạm. Chúng không thanh toán tiền thật, không gửi push thật và không sửa DB đang chạy. Chi tiết các ca kiểm thử và ma trận nghiệp vụ: [TESTING.md](TESTING.md).

Kết quả và phạm vi đã xác minh: [VERIFICATION.md](VERIFICATION.md).

Kiểm tra trạng thái: http://localhost:5000/api-status. Swagger mỗi service có nút **Authorize**; lấy JWT từ `/api/auth/login`, sau đó dán JWT vào ô xác thực.

## 6. Kết nối SePay và Firebase

- **VietQR/SePay:** xem [SEPAY_VIETQR.md](SEPAY_VIETQR.md). Mặc định `PAYMENT_MODE=sepay`, `SEPAY_ENV=test`; cần điền tài khoản Test, API Key riêng và URL webhook HTTPS. `.env` đã có không bị tự ghi đè. Test mô phỏng trên dashboard SePay; Live dùng tài khoản/token/khóa riêng và chuyển tiền thật. Không dùng app ngân hàng thật trong Test.
- **Firebase:** xem [DOMAIN_API.md](DOMAIN_API.md). Cần service account, cấu hình Firebase Web, VAPID key, HTTPS hoặc localhost và người dùng đồng ý nhận thông báo. Trên Docker, mount file service account chỉ đọc và đặt đường dẫn trong container vào `GOOGLE_APPLICATION_CREDENTIALS`.
- Sau khi thay `.env`, khởi động lại các tiến trình/container. Không có khóa bên thứ ba trong mã nguồn; bản mặc định vẫn dùng được toàn bộ thông báo trong ứng dụng.

## 7. Giới hạn cần nêu trong báo cáo

- Một file SQLite vật lý dùng chung, một writer tại một thời điểm. WAL và timeout giảm xung đột nhưng không biến SQLite thành cơ sở dữ liệu phân tán.
- Trigger quá hạn gốc ghi trực tiếp từ Billing sang bảng Maintenance. Đây là ngoại lệ được giữ để đáp ứng yêu cầu dữ liệu gốc; nếu tách DB vật lý, thay trigger bằng sự kiện HTTP/outbox. Các truy vấn ứng dụng không JOIN chéo bảng giữa service.
- Hợp đồng mới không được trùng thời gian đang hoạt động của cùng căn hộ. Dữ liệu mẫu cũ có một số hồ sơ/hợp đồng và liên kết tài khoản chưa nhất quán; cần quản trị rà soát trước khi nhập dữ liệu thật. Không tự hợp nhất hai người khác tên có chung `user_id`.
- Các phiếu cắt/khôi phục dịch vụ là quy trình giao việc cho người vận hành; hệ thống không điều khiển thiết bị điện/nước.
- Biên nhận HTML là chứng từ nội bộ, chưa tích hợp nhà cung cấp hóa đơn điện tử thuế. SePay Test/Live và push Firebase cần kiểm chứng bằng tài khoản của người triển khai. Hoàn tiền thừa do BQL thực hiện ngoài ứng dụng; source chỉ lưu ghi chú xử lý.
- JWT có thời hạn 8 giờ; khóa tài khoản có hiệu lực ngay qua Auth. Chưa có refresh token/thu hồi từng phiên; đăng xuất xóa JWT ở trình duyệt.
- Chưa triển khai phân trang phía máy chủ, audit log đầy đủ, backup tự động hoặc hạ tầng nhiều replica. Đây là bản demo/khóa luận theo phạm vi readme.

Tài liệu kiến trúc và quyết định thiết kế: [ARCHITECTURE.md](ARCHITECTURE.md).
