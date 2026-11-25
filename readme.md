# Quản lý chung cư (Condominium Management System)

Hệ thống quản lý chung cư An Cư cho ba nhóm người dùng: **ban quản lý**, **cư dân** và **kỹ thuật viên**. Hệ thống xây dựng theo hướng **Service-Oriented Architecture (SOA)** với 8 service Flask độc lập: Auth, Resident, Billing, Parking, Maintenance, Notification, Complaint, Chatbot. Các service gọi nhau qua REST API, kèm một gateway phục vụ giao diện web. Toàn bộ chạy bằng Docker Compose, mỗi service một container.

**Mục lục:** [1. Chức năng](#1-chức-năng) · [2. Kiến trúc và cấu trúc project](#2-kiến-trúc-và-cấu-trúc-project) · [3. Công nghệ](#3-công-nghệ) · [4. Cài đặt và chạy](#4-cài-đặt-và-chạy) · [5. Triển khai](#5-triển-khai) · [6. Mở trên điện thoại](#6-mở-trên-điện-thoại) · [7. Xem database](#7-xem-database) · [8. Xử lý sự cố](#8-xử-lý-sự-cố)

## 1. Chức năng

**Ban quản lý**

- Quản lý căn hộ: thông tin căn hộ, trạng thái trống hoặc đã ở, danh sách cư dân đang ở.
- Cư dân tự đăng ký tài khoản; ban quản lý xác nhận căn hộ cho tài khoản đó.
- Hợp đồng thuê và sở hữu: nhắc trước 30 ngày khi hợp đồng thuê sắp hết hạn, thông báo vào ngày hết hạn; khóa và mở khóa tài khoản của căn hộ hết hợp đồng.
- Hóa đơn điện nước hằng tháng và hóa đơn dịch vụ chung kèm phí gửi xe theo kỳ 6 tháng; ghi nhận thu tiền mặt hoặc chuyển khoản, đối soát chuyển khoản.
- Gửi xe: duyệt đơn đăng ký, gia hạn, doanh thu vé vãng lai theo ngày.
- Giải quyết khiếu nại và đơn đăng ký; gửi thông báo chung hoặc riêng từng căn hộ.
- Báo cáo thống kê doanh thu theo tháng và quý, biểu đồ, xuất CSV.
- Nhân sự và tài khoản: đổi vai trò tài khoản, phân công kỹ thuật viên.
- Cập nhật chính sách và câu hỏi thường gặp cho chatbot.

**Cư dân**

- Xem và thanh toán hóa đơn bằng VietQR, tải biên nhận, xem lịch sử thanh toán.
- Gửi khiếu nại (có đính kèm ảnh) và đơn đăng ký, gồm đăng ký và gia hạn gửi xe.
- Gửi yêu cầu sửa chữa, bảo trì và theo dõi tiến độ.
- Nhận thông báo trong web và thông báo đẩy trên trình duyệt, điện thoại.
- Hỏi trợ lý (chatbot) về chính sách và vị trí tiện ích của chung cư.

**Kỹ thuật viên**

- Nhận và cập nhật phiếu sửa chữa, bảo trì.
- Quản lý dịch vụ: ghi nhận cắt hoặc cấp lại điện, nước, gửi xe, dịch vụ chung khi hóa đơn quá hạn.
- Ghi doanh thu gửi xe vãng lai theo ngày.
- Quản lý hóa đơn với cùng quyền như ban quản lý (trừ báo cáo thống kê).

## 2. Kiến trúc và cấu trúc project

Mỗi service là một Flask app riêng, chạy ở cổng riêng trong một container riêng. Các service gọi nhau bằng HTTP thật (thư viện `requests`) và không đọc bảng của service khác. Gateway ở cổng 5000 phục vụ giao diện và chuyển tiếp API tới đúng service.

| Service | Cổng | Chức năng |
|---|---|---|
| Gateway | 5000 | Giao diện web, chuyển tiếp API |
| Auth | 5001 | Đăng nhập, đăng ký, phân quyền 3 vai trò, khóa tài khoản |
| Resident | 5002 | Căn hộ, cư dân, hợp đồng, nhắc hết hạn hợp đồng |
| Billing | 5003 | Hóa đơn, thanh toán VietQR qua SePay, đối soát, báo cáo thống kê, quét hóa đơn quá hạn, cắt và cấp lại dịch vụ |
| Parking | 5004 | Đăng ký và gia hạn gửi xe, phí gửi xe theo kỳ, vé vãng lai |
| Maintenance | 5005 | Phiếu sửa chữa, bảo trì, phân công kỹ thuật viên |
| Notification | 5006 | Thông báo chung, riêng, thông báo đẩy Firebase |
| Complaint | 5007 | Khiếu nại, đơn đăng ký |
| Chatbot | 5008 | Trả lời chính sách và vị trí tiện ích |

Các service dùng chung một file SQLite (qua Docker volume) nhưng mỗi service sở hữu nhóm bảng riêng: tham chiếu trong cùng service dùng khóa ngoại, tham chiếu sang service khác chỉ lưu ID. Mỗi service có tài liệu API Swagger tại `http://localhost:<cổng>/docs`.

```
.
├── auth-service/            # mỗi service: app.py (API) và scheduler.py (job định kỳ, nếu có)
├── resident-service/
├── billing-service/         # gồm sepay_payments.py: thanh toán VietQR qua SePay
├── parking-service/
├── maintenance-service/
├── notification-service/
├── complaint-service/
├── chatbot-service/         # gồm prompts/: câu lệnh cho chatbot AI
├── gateway/                 # giao diện và chuyển tiếp API, cổng 5000
├── frontend/                # giao diện HTML/CSS/JS (app.js, theme.css, font, ảnh)
├── shared/                  # code dùng chung: database, xác thực JWT, gọi HTTP, chatbot, Firebase
├── migrations/              # câu lệnh tạo và cập nhật cấu trúc database, chạy theo thứ tự
├── scripts/                 # khởi tạo database, sao lưu, kiểm tra kết nối, script CI
├── tests/                   # kiểm thử tự động; fixtures/demo.sql là dữ liệu mẫu
├── .github/workflows/       # CI/CD GitHub Actions
├── Dockerfile               # công thức build dùng chung cho mọi image
├── docker-compose.yml       # chạy toàn bộ hệ thống
├── .env.example             # mẫu cấu hình kết nối SePay, Firebase, Gemini
└── requirements.txt         # thư viện Python
```

## 3. Công nghệ

- **Backend:** Python 3.11, Flask, Waitress; REST API kèm Swagger (OpenAPI); xác thực JWT; job định kỳ bằng APScheduler (quét hóa đơn quá hạn, nhắc hết hạn hợp đồng).
- **Database:** SQLite.
- **Frontend:** HTML, CSS, JavaScript, Tailwind CSS; thêm được ra màn hình chính điện thoại như ứng dụng.
- **Tích hợp:** VietQR qua SePay (webhook xác nhận tiền về), Firebase Cloud Messaging (thông báo đẩy), Gemini (tùy chọn, diễn đạt câu trả lời của chatbot), Tailscale Funnel (địa chỉ HTTPS cố định).
- **Kiểm thử và triển khai:** pytest, Playwright (kiểm thử giao diện), Docker, Docker Compose, GitHub Actions.

## 4. Cài đặt và chạy

1. Cài và mở [Docker Desktop](https://www.docker.com/products/docker-desktop/), đợi trạng thái **Engine running**.
2. Tải mã nguồn:

   ```
   git clone https://github.com/Hoaithu2501/Quan-ly-chung-cu.KLTN.git
   cd Quan-ly-chung-cu.KLTN
   ```

   Không có Git: trên trang GitHub của dự án bấm **Code → Download ZIP**, giải nén, rồi mở PowerShell (hoặc Terminal) trong thư mục vừa giải nén.

3. Chạy hệ thống (lần đầu mất vài phút):

   ```
   docker compose up --build -d
   ```

   Kiểm tra bằng `docker compose ps`; khi các service hiện `healthy` thì sang bước 4.

4. Mở **http://localhost:5000** và đăng nhập.

Không cần cài Python, Node.js hay tạo file cấu hình: Docker lo toàn bộ. Bản chạy thử dùng dữ liệu mẫu. Thanh toán QR, thông báo đẩy và chatbot diễn đạt bằng AI cần khóa kết nối riêng (mục 5) nên được tắt: nút **Thanh toán VietQR** bị khóa kèm lý do, thông báo vẫn hiện trong mục **Thông báo**, chatbot trả lời từ nội dung có sẵn. Các chức năng còn lại hoạt động đầy đủ.

**Cư dân mới tham gia:**

1. Ở trang đăng nhập, cư dân chọn **Đăng ký tài khoản**, điền thông tin và mã căn hộ, rồi bấm **Tạo tài khoản cư dân**.
2. Ban quản lý vào **Cư dân & hợp đồng**, tìm cư dân đó và chọn **Xác nhận căn hộ**.
3. Từ lúc này, cư dân xem được hóa đơn, gửi yêu cầu và nhận thông báo của căn hộ.

**Lệnh thường dùng:**

| Việc cần làm | Lệnh |
|---|---|
| Xem trạng thái | `docker compose ps` |
| Xem nhật ký một service | `docker compose logs -f billing` (thay `billing` bằng tên service) |
| Dừng hệ thống (giữ dữ liệu) | `docker compose down` |
| Chạy lại | `docker compose up -d` |
| Xóa dữ liệu, làm lại từ dữ liệu mẫu | `docker compose down -v`, rồi `docker compose up --build -d` |

## 5. Triển khai

**Các container.** `docker compose up` tạo 8 container service, gateway, một container sao lưu và một job khởi tạo database chạy xong rồi thoát. Các container tự chạy lại khi Docker khởi động lại. Chỉ gateway (cổng 5000) mở ra mạng; các service chỉ nhận kết nối trên máy chạy hệ thống.

**Dữ liệu.** Database nằm trong volume Docker `qlcc-data`. Lần chạy đầu, database được tạo từ dữ liệu mẫu `tests/fixtures/demo.sql` rồi áp dụng các file trong `migrations/`. Những lần sau chỉ áp dụng migration mới, dữ liệu được giữ nguyên. Container sao lưu tạo mỗi ngày một bản trong `backups/` và giữ 14 bản gần nhất.

**Cấu hình kết nối.** Chép `.env.example` thành `.env`, điền các mục cần dùng, rồi chạy `docker compose up -d`:

| Nhóm | Biến trong `.env` | Dùng cho |
|---|---|---|
| SePay | `SEPAY_ENV`, `SEPAY_BANK_CODE`, `SEPAY_ACCOUNT_NUMBER`, `SEPAY_ACCOUNT_NAME`, `SEPAY_WEBHOOK_API_KEY`, `SEPAY_WEBHOOK_URL` | Thanh toán VietQR, tự xác nhận tiền về qua webhook |
| Firebase | `FIREBASE_PROJECT_ID`, `FIREBASE_WEB_CONFIG`, `FIREBASE_VAPID_KEY`, file `secrets/firebase-credentials.json` | Thông báo đẩy |
| Gemini | `LLM_API_KEY` | Chatbot diễn đạt câu trả lời tự nhiên hơn |

Khóa nội bộ (JWT, khóa giữa các service) được tự sinh ở lần chạy đầu. `.env` chứa khóa bí mật nên không đưa lên Git.

**Truy cập từ internet.** Thông báo đẩy trên điện thoại và webhook SePay cần địa chỉ HTTPS. Hệ thống dùng Tailscale Funnel: chạy `tailscale funnel --bg 5000` trên máy chạy hệ thống để có địa chỉ cố định dạng `https://<tên-máy>.<tên-mạng>.ts.net`. Webhook SePay trỏ tới `https://<địa chỉ>/api/billing/sepay/webhook`.

**Cập nhật phiên bản.** Chạy `git pull`, rồi `docker compose up --build -d`. Migration mới được áp dụng tự động, dữ liệu giữ nguyên.

**CI/CD.** Mỗi lần push, GitHub Actions chạy:

1. kiểm tra repo không chứa database hay khóa bí mật;
2. kiểm thử backend và tích hợp liên service;
3. kiểm thử giao diện bằng Playwright;
4. build Docker và chạy thử toàn hệ thống.

Khi phát hành một release trên GitHub, workflow `release.yml` kiểm tra lại rồi đẩy các image lên GitHub Container Registry.

## 6. Mở trên điện thoại

An Cư là trang web, không có trên App Store hay CH Play. Điện thoại mở trang web của máy đang chạy hệ thống qua cùng mạng Wi-Fi:

1. Trên máy chạy hệ thống, mở PowerShell, chạy `ipconfig` và lấy dòng **IPv4 Address** của card Wi-Fi hoặc Ethernet, ví dụ `192.168.1.20`.
2. Điện thoại kết nối cùng mạng đó rồi mở `http://192.168.1.20:5000`.
3. Nếu Windows hỏi quyền tường lửa cho Docker Desktop, cho phép trên mạng **Riêng (Private)**. Mạng khách hoặc mạng có chế độ cách ly thiết bị sẽ chặn điện thoại.

**Thêm An Cư ra màn hình chính** để mở như một ứng dụng:

- **iPhone, iPad** (Safari): nhấn nút **Chia sẻ** (ô vuông có mũi tên hướng lên; trên iOS mới có thể nằm trong nút **•••**), chọn **Thêm vào MH chính**, rồi nhấn **Thêm**.
- **Android** (Chrome): nhấn **⋮** ở góc trên bên phải, chọn **Thêm vào màn hình chính**, rồi xác nhận.

Thông báo đẩy trên điện thoại cần địa chỉ HTTPS (Tailscale Funnel, mục 5) và cấu hình Firebase.

## 7. Xem database

Database đang chạy nằm trong volume Docker (mục 5). Để xem, tạo một bản sao ra thư mục `backups/` trong thư mục dự án (hệ thống vẫn chạy bình thường):

```
docker compose exec -T backup python scripts/backup_db.py --output /backups
```

Lệnh in ra tên file, dạng `/backups/QLCC-auto-<ngày>-<giờ>.db`; file nằm trong thư mục `backups/` của dự án. Mở file đó bằng:

- **DB Browser for SQLite** ([sqlitebrowser.org](https://sqlitebrowser.org/)): chọn **File → Open Database Read Only**, rồi chọn file. Tab **Database Structure** để xem bảng, tab **Browse Data** để xem dữ liệu.
- **DBeaver**: tạo kết nối SQLite tới file, chọn database → **View Diagram** để xem sơ đồ quan hệ.

Cấu trúc database cũng đọc được trực tiếp trong các file `migrations/*.sql`.

## 8. Xử lý sự cố

| Hiện tượng | Cách xử lý |
|---|---|
| `docker` báo không kết nối được, hoặc lỗi `500 Internal Server Error` | Docker Desktop chưa chạy hoặc bị treo. Thoát Docker Desktop từ khay hệ thống, mở lại, đợi **Engine running**, rồi chạy `docker compose up -d` |
| Trang `localhost:5000` tải mãi không xong | Máy thiếu RAM. Đóng bớt ứng dụng rồi khởi động lại Docker Desktop |
| Báo cổng 5000 đang được dùng | Một chương trình khác đang dùng cổng 5000. Tắt chương trình đó, hoặc chạy `docker compose down` rồi chạy lại |
| Một service không `healthy` | Xem nhật ký: `docker compose logs <tên service>` |
| Điện thoại không mở được `http://<IP>:5000` | Kiểm tra cùng mạng Wi-Fi, đúng IP, tường lửa Windows cho phép Docker Desktop trên mạng Private, mạng không bật cách ly thiết bị |
| Nút **Thanh toán VietQR** bị khóa | Bình thường trong bản chạy thử: thanh toán QR cần cấu hình SePay (mục 5) |
| Tài khoản bị khóa khi đăng nhập | Ban quản lý đã khóa tài khoản (thường do hợp đồng thuê đã hết hạn). Ban quản lý mở khóa tại **Cư dân & hợp đồng → Chi tiết** |
