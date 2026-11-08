# Sử dụng Docker cho QLCC trên Windows

## Docker chạy gì trong dự án này?

Image là gói chứa Python, thư viện và mã nguồn. Container là một phiên chạy của image. Docker Compose đọc `docker-compose.yml` để build và chạy toàn bộ hệ thống bằng một lệnh.

Dự án có 8 service nghiệp vụ, 1 gateway phục vụ giao diện và 1 container `db-init` khởi tạo dữ liệu rồi thoát. `db-init` có trạng thái `Exited (0)` là bình thường. Các container còn lại cần ở trạng thái `Up`, sau đó `healthy`.

Web: **http://localhost:5000**. Kiểm tra các service: **http://localhost:5000/api-status**. Các service nghiệp vụ dùng cổng 5001–5008 và có Swagger ở `/docs`.

## Khởi chạy

1. Mở Docker Desktop và chờ Engine hoạt động. Dự án dùng Linux containers.
2. Mở PowerShell tại thư mục dự án. Dừng bản chạy Python nếu đang dùng các cổng 5000–5008.
3. Chạy:

```powershell
cd D:\Downloads_new\QLCC
docker version
docker compose config --quiet
docker compose up --build -d
docker compose ps -a
```

`--build` dựng image từ mã nguồn; `-d` chạy nền nên đóng terminal không làm tắt web. Lần đầu cần Internet để tải image Python và thư viện. Lệnh kiểm tra cấu hình không in gì khi hợp lệ.

Trong VS Code, chạy `npm ci` một lần, rồi nhấn **Ctrl+Shift+B** để biên dịch Tailwind và chạy task `QLCC: Docker - build and start`, sau đó mở http://localhost:5000. Menu **Terminal → Run Task** có task theo dõi Tailwind, xem trạng thái Docker và chạy bản Python local. Chỉ chạy một trong hai bản Python/Docker vì chúng dùng chung các cổng 5000–5008.

### Cập nhật giao diện từ VS Code hoặc Antigravity

Gateway mount thư mục `./frontend` của dự án vào `/app/frontend` ở chế độ chỉ đọc. Khi sửa giao diện, giữ `npm run watch:css` chạy để biên dịch Tailwind sau mỗi lần lưu, rồi tải lại **http://localhost:5000**. Sửa `frontend/theme.css` hoặc utility classes trong `app.js`; không sửa trực tiếp `styles.css` vì đó là tệp đầu ra. Không cần build lại image khi chỉ sửa frontend. Mở đúng thư mục `D:\Downloads_new\QLCC` trong cả hai IDE; Live Server không thay thế gateway và các API. Chi tiết: [FRONTEND.md](FRONTEND.md).

Nếu container được tạo trước khi có cấu hình mount này, áp dụng một lần:

```powershell
docker compose up -d --build --no-deps gateway
```

Lệnh trên cập nhật gateway và giữ dữ liệu trong volume. `docker compose start` hoặc `restart` chỉ chạy lại container cũ, không thêm mount và không lấy mã nguồn mới từ image. Khi sửa Python của gateway/backend, vẫn cần build lại service tương ứng; khi sửa `.env`, cần tạo lại container bằng `docker compose up -d --force-recreate <service>`.

Máy hiện tại đã có `.env` và `data/QLCC.db`. Trên bản sao mới chưa có `.env`, có thể tạo bằng Python có sẵn trước khi chạy Compose:

```powershell
python -c "from scripts.init_db import ensure_env; ensure_env()"
```

Lệnh này chỉ tạo/cập nhật cấu hình với secret ngẫu nhiên; phần khởi tạo DB và tài khoản demo do container `db-init` thực hiện. Không cần cài thư viện Python trên Windows để chạy các container. Không đưa `.env` lên Git.

## Đăng nhập và thử web

### Mở trên điện thoại qua Wi-Fi

Điện thoại và máy tính cần cùng mạng Wi-Fi/LAN. Máy tính phải đang bật và Docker đang chạy. Trên điện thoại, mở **http://192.168.2.3:5000** (IP Wi-Fi của máy tính lúc cấu hình). `localhost` trên điện thoại là chính điện thoại. Nếu IP máy tính thay đổi, chạy `ipconfig` và lấy IPv4 của adapter Wi-Fi để thay trong URL.

Gateway đã cấu hình `0.0.0.0:5000:5000`. Đã kiểm tra từ máy tính: URL IP Wi-Fi trả HTTP 200. Chưa kiểm tra trực tiếp từ điện thoại.

Nếu điện thoại không kết nối được, mở **PowerShell → Run as administrator** trên máy tính, chạy một lần:

```powershell
New-NetFirewallRule -Name 'QLCC-Web-LAN-5000' -DisplayName 'QLCC Web LAN TCP 5000' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5000 -RemoteAddress LocalSubnet -Profile Any
```

Rule chỉ cho phép thiết bị trong cùng subnet vào cổng 5000. Phiên trợ lý không có quyền quản trị Windows để tạo rule này. Không cần tắt firewall. Nếu rule đã tồn tại, không cần tạo lại.

Nếu vẫn lỗi: kiểm tra điện thoại không dùng Wi-Fi khách (guest network), router không bật AP/client isolation và VPN không chặn mạng LAN. Truy cập từ 4G/5G hoặc Wi-Fi khác cần phương án triển khai/tunnel riêng; địa chỉ LAN trên chỉ dùng trong mạng của máy tính.

Để gỡ rule khi không cần, chạy PowerShell quản trị: `Remove-NetFirewallRule -Name 'QLCC-Web-LAN-5000'`.

| Vai trò | Tài khoản | Mật khẩu demo |
|---|---|---|
| Ban quản lý | `admin` | `Admin@12345` |
| Cư dân | `resident` | `Resident@12345` |
| Kỹ thuật viên | `technician` | `Tech@12345` |

Mở web, đăng nhập quản trị để quản lý căn hộ, cư dân, hóa đơn và phân công kỹ thuật. Cư dân xem hóa đơn, thông báo và thanh toán VietQR khi đã xác nhận căn hộ. Cấu hình `PAYMENT_MODE=sepay`, `SEPAY_ENV=test`, tài khoản ngân hàng Test và webhook HTTPS/API Key theo [SEPAY_VIETQR.md](SEPAY_VIETQR.md). Test dùng chức năng mô phỏng của SePay, không quét bằng ứng dụng ngân hàng thật. Chỉ `SEPAY_ENV=live` với tài khoản Live đã kết nối mới dùng để nhận tiền thật. Khởi tạo lại không đặt lại mật khẩu đã thay đổi.

Đăng ký cư dân: tên đăng nhập 3–20 ký tự, gồm chữ cái không dấu, số, dấu chấm, gạch dưới hoặc gạch ngang (không chứa khoảng trắng); email bắt buộc có đuôi `@gmail.com`; điện thoại bắt buộc; mật khẩu mới 6–30 ký tự, ô mật khẩu không có gợi ý. Đăng ký thành công sẽ trở về màn hình đăng nhập và điền sẵn tên đăng nhập. Đăng nhập thành công mở dashboard Tổng quan theo vai trò. Cư dân có mục **Thông tin cá nhân → Chỉnh sửa thông tin** để sửa tên đăng nhập, họ tên, email Gmail, điện thoại và CCCD; số điện thoại bắt buộc, CCCD có thể để trống. Nút **Đổi mật khẩu** yêu cầu mật khẩu hiện tại, mật khẩu mới và nhập lại mật khẩu mới trùng khớp. Căn hộ và hợp đồng do Ban quản lý liên kết.

Sai thông tin đăng nhập hiển thị “Sai tên đăng nhập hoặc mật khẩu, vui lòng kiểm tra lại”. Khi nhập đúng mật khẩu của tài khoản bị khóa, web hiện popup báo khóa và lý do nếu có. Quản trị nhập lý do tại **Nhân sự & tài khoản → Cập nhật tài khoản → Lý do khóa**; mở khóa sẽ xóa lý do cũ.

Họ tên khi đăng ký và khi cư dân chỉnh sửa phải có 10–50 ký tự (không tính khoảng trắng đầu/cuối). Đăng ký bắt buộc nhập số căn hộ có sẵn, ví dụ `A-0101`. Căn hộ được lưu vào hồ sơ đăng ký và hiển thị cạnh tên đăng nhập, trong trang Thông tin cá nhân và cửa sổ chỉnh sửa. Nếu có hợp đồng còn hiệu lực, giao diện hiển thị căn hộ theo hợp đồng. Nhập căn hộ khi đăng ký chưa tự cấp quyền xem hóa đơn của căn hộ đó; Ban quản lý xác nhận và liên kết bằng hợp đồng. Tài khoản cũ chưa khai báo và chưa có hợp đồng còn hiệu lực hiển thị “Chưa liên kết”.

## Các lệnh thường dùng

Chạy các lệnh tại thư mục chứa `docker-compose.yml`:

| Mục đích | Lệnh |
|---|---|
| Xem trạng thái, gồm job khởi tạo | `docker compose ps -a` |
| Xem log gần nhất | `docker compose logs --tail=100` |
| Theo dõi log gateway | `docker compose logs -f gateway` |
| Theo dõi log hóa đơn | `docker compose logs -f billing` |
| Tạm dừng toàn bộ | `docker compose stop` |
| Chạy lại container đã dừng | `docker compose start` |
| Khởi động lại một service | `docker compose restart billing` |
| Dừng và xóa container, mạng Compose, giữ volume dữ liệu | `docker compose down` |
| Tạo/chạy lại hệ thống | `docker compose up -d` |
| Áp dụng mã nguồn hoặc `.env` mới | `docker compose up --build -d --force-recreate` |
| Vào shell của gateway | `docker compose exec gateway sh` |

Nhấn Ctrl+C khi theo dõi log chỉ kết thúc xem log. `restart` không nạp cấu hình `.env` mới và không build lại mã nguồn.

Trong Docker Desktop, mở **Containers**, tìm nhóm `qlcc`, mở container để xem **Logs** hoặc dùng nút Start/Stop. Có thể dùng **Images** để xem các image `qlcc-*` đã build.

## Dữ liệu và sao lưu

**Bản chính hiện tại là database Docker**, dùng chung cho gateway và tất cả service. Xem [DATABASE.md](DATABASE.md) để phân biệt các bản cũ và chạy `python scripts/check_database.py` kiểm tra đường dẫn, volume, số bảng và toàn vẹn dữ liệu. `./start.ps1` mặc định chạy Docker; không tự chuyển sang database Python nếu Docker lỗi.

`QLCC.db` ở thư mục gốc là dữ liệu nguồn. Bản Python dùng `data/QLCC.db`. Bản Docker dùng `/app/data/QLCC.db` trong named volume `qlcc_qlcc-data`, giúp SQLite WAL hoạt động trên filesystem của Linux thay vì thư mục chia sẻ Windows. Hai bản dùng dữ liệu riêng sau khi chuyển sang volume.

Khi tạo volume lần đầu, `db-init` lấy dữ liệu từ `QLCC.db` nguồn trong image. Cấu hình `DATABASE_SEED_PATH` trỏ tới bản Docker seed cũ đã được bỏ sau khi lưu trữ các file cũ. Khởi tạo lại không ghi đè DB đã có trong volume. `docker compose stop`, `start`, `restart` và `down` giữ dữ liệu. Không dùng `docker compose down -v` nếu cần giữ dữ liệu, vì `-v` xóa volume.

Sao lưu DB Docker bằng SQLite backup, sau đó xuất bản sao về Windows (có thể thực hiện khi web đang chạy):

```powershell
$backupFile = 'backups/QLCC-docker-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.db'
.\.venv\Scripts\python.exe scripts/export_database.py --output $backupFile
```

Công cụ kiểm tra bản xuất, lấy cả dữ liệu đã commit trong WAL và từ chối ghi đè file có sẵn. `data/QLCC.snapshot.db` là bản xuất đã chuẩn bị để mở bằng DB Browser; dữ liệu cũ trên Windows được lưu trong `backups/database-archive-*.zip`. Không chỉ sao chép riêng file `.db` khi ứng dụng còn đang ghi dữ liệu.

Khi cập nhật `QLCC.db` nguồn, dùng [hướng dẫn đồng bộ dữ liệu](DATABASE_REFRESH.md) để xuất snapshot gồm WAL, xem trước thay đổi và nhập vào volume có sao lưu. Chạy lại `db-init` thông thường chỉ áp dụng migration, không nhập lại danh mục hay ghi đè dữ liệu đã có.

Lần sửa lỗi đăng ký ngày 13/10/2026: log Resident ghi `sqlite3.OperationalError: disk I/O error` khi đọc căn hộ trên bind mount Windows. Đã sao lưu thư mục cũ tại `backups/sqlite-repair-20261013-231724`, tạo bản SQLite backup nhất quán và chuyển 22 tài khoản cùng dữ liệu nghiệp vụ sang volume. File nguồn và DB Windows được giữ lại. Healthcheck các service hiện kiểm tra cả khả năng đọc SQLite.

## Kết quả rà soát dữ liệu trước khi chạy Docker

Các số liệu dưới đây là lịch sử trước khi chuyển sang Docker, không phải số liệu hiện tại. Kết quả kiểm tra ngày 08/11/2026 nằm trong [DATABASE.md](DATABASE.md).

Hai file `QLCC.db` và `data/QLCC.db` đều có `PRAGMA integrity_check = ok`, không có lỗi `foreign_key_check`. Bản ứng dụng có 15 căn hộ, 15 cư dân, 15 hợp đồng, 15 phương tiện và 18 tài khoản, gồm 3 tài khoản demo.

Các vấn đề nghiệp vụ còn trong dữ liệu mẫu:

- 15 căn hộ có diện tích NULL, cần cập nhật diện tích thật.
- 15 tài khoản gốc dùng chuỗi `hash_pw_...`, không phải mật khẩu băm hợp lệ. Dùng tài khoản demo hoặc đặt lại mật khẩu qua quản trị.
- Các `user_id` 4, 5, 6, 7 mỗi tài khoản liên kết với 2 hồ sơ cư dân. Cần xác minh người sở hữu trước khi sửa.
- Các cặp hợp đồng đang `active` trùng thời gian: #1/#11 (căn hộ #1), #2/#12 (căn hộ #2), #4/#13 (căn hộ #5), #5/#14 (căn hộ #6).

Không tự hợp nhất hoặc xóa các dữ liệu này. Billing có job tự rà soát hóa đơn quá hạn khi khởi động nên số phiếu/thông báo có thể thay đổi trong quá trình chạy.

Kết quả chạy Docker đã xác minh: build và khởi động thành công; gateway và 8 service đều `healthy`; `db-init` thoát mã 0. Trang chủ trả HTTP 200, `/api-status` báo cả 8 service `ok`. Đăng nhập cả 3 tài khoản demo và đọc API theo vai trò đều trả HTTP 200 (căn hộ, cư dân, hợp đồng, tổng hợp hóa đơn, hồ sơ cư dân và phiếu kỹ thuật). Đây là kiểm tra khởi chạy và đọc dữ liệu, chưa thay thế kiểm thử toàn bộ nghiệp vụ trên trình duyệt.

## Xử lý lỗi thường gặp

- Không kết nối Docker Engine: mở Docker Desktop, chờ Engine sẵn sàng, kiểm tra `docker version` có cả Client và Server.
- Cổng đã được sử dụng: dừng ứng dụng Python hoặc ứng dụng khác đang giữ cổng; không chạy Python và Docker cùng bộ cổng.
- Build thất bại do mạng: kiểm tra Internet và chạy lại `docker compose up --build -d`.
- `db-init` thoát với mã khác 0: xem `docker compose logs db-init`; các service sẽ không khởi chạy nếu job này thất bại.
- Service `unhealthy`: xem `docker compose logs --tail=100 <tên-service>` và kiểm tra `/api-status`.

Tài liệu chính thức: [Docker Compose](https://docs.docker.com/compose/intro/compose-application-model/), [lệnh up](https://docs.docker.com/reference/cli/docker/compose/up/), [bind mounts](https://docs.docker.com/engine/storage/bind-mounts/), [Docker Desktop Containers](https://docs.docker.com/desktop/use-desktop/container/).
