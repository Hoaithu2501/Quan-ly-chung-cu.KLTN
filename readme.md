# Quản lý chung cư (Condominium Management System)

**Database chính:** toàn bộ web Docker dùng chung `/app/data/QLCC.db` trong volume `qlcc_qlcc-data`, bao gồm cả desktop và iPhone. Các file `.db` trên Windows là dữ liệu nguồn, bản Python cũ hoặc bản sao lưu. `./start.ps1` mặc định chạy Docker; xem [phân biệt database và kiểm tra dữ liệu](docs/DATABASE.md).

**VietQR và SePay:** chạy gateway tại `http://localhost:5000`, không dùng Live Server. Docker đọc trực tiếp thư mục `frontend`. Source đã chuyển sang đối soát SePay; bắt đầu với **Test Mode** để thử không chuyển tiền. Thiết lập tài khoản, ngân hàng và webhook: [SEPAY_VIETQR.md](docs/SEPAY_VIETQR.md).

**Test thanh toán hóa đơn từng bước:** xem [TEST_THANH_TOAN_HOA_DON.md](docs/TEST_THANH_TOAN_HOA_DON.md), gồm cư dân/BQL, mô phỏng giao dịch trên SePay, nhiều thành viên cùng trả, tiền chuyển thiếu/dư và hóa đơn quá hạn.

**Tiến độ hoàn thiện:** luồng SePay Live đã nghiệm thu ngày 07/11/2026; xem [bằng chứng](docs/VERIFICATION.md) và [các bước hoàn thiện project](docs/HOAN_THIEN_PROJECT.md).

**Giao diện Tailwind CSS:** thiết kế xanh lá–trắng–mint, ảnh kiến trúc thật và font tiếng Việt lưu cục bộ. Khi chỉnh giao diện, chạy `npm ci` rồi `npm run watch:css`; xem [FRONTEND.md](docs/FRONTEND.md).

**Chatbot An Cư:** truy xuất FAQ và địa điểm, hỗ trợ diễn đạt bằng LLM tùy chọn và tự trả lời từ kho kiến thức khi chưa cấu hình AI. Xem [thiết lập chatbot](docs/CHATBOT.md) và [cách cập nhật FAQ bằng SQL an toàn](docs/CHATBOT_DATA.md). Bộ SQL mới giữ ID và các FAQ tự thêm; xem trước trước khi áp dụng.

**Phản hồi khiếu nại:** Ban quản lý trả lời hoặc sửa phản hồi trong Khiếu nại & đăng ký; cư dân đã gửi yêu cầu nhận thông báo riêng. Xem [hướng dẫn thao tác và cập nhật](docs/COMPLAINTS.md).

**Firebase push:** [hướng dẫn tạo project, cấu hình Docker và kiểm thử thông báo trình duyệt](docs/FIREBASE_PUSH.md). Cần Web config, VAPID và service account của cùng Firebase project; thông báo trong web vẫn hoạt động khi chưa bật push.

> **Mã nguồn triển khai đã được bổ sung.** Bắt đầu tại [hướng dẫn chạy từng bước](docs/GETTING_STARTED.md), [kiến trúc SOA](docs/ARCHITECTURE.md), [kiểm thử](docs/TESTING.md), [thanh toán](docs/PAYMENTS.md) và [API nghiệp vụ](docs/DOMAIN_API.md). Giao diện chạy tại `http://localhost:5000`; bản Docker dùng database trong volume như mô tả ở trên, còn `data/QLCC.db` chỉ dành cho chế độ Python riêng. Phần còn lại của tài liệu này là yêu cầu ban đầu.

Hệ thống quản lý chung cư xây dựng theo hướng **Service-Oriented Architecture (SOA)**, phục vụ định hướng Business Analyst: nhấn mạnh phân tích nghiệp vụ, phân tích hệ thống và kiểm thử, bên cạnh việc xây dựng ứng dụng thực tế.

**CI/CD:** GitHub Actions tự kiểm thử backend, trình duyệt và Docker khi push/PR; phát hành image lên GHCR khi Publish Release. Xem [hướng dẫn CI/CD](docs/CI_CD.md). Pipeline dùng dữ liệu mẫu, không dùng database Live hoặc khóa riêng.

## 1. Người dùng & chức năng nghiệp vụ

Người sử dụng trực tiếp là Ban quản lý chung cư, với 3 nhóm user chính: **Ban quản lý chung cư**, **cư dân**, **kỹ thuật viên**.

### Ban quản lý chung cư
- Quản lý căn hộ (thông tin sở hữu, diện tích, trạng thái trống/đã ở, lịch sử chủ sở hữu/người thuê, tình trạng sở hữu — thuê bao nhiêu lâu, thời gian còn lại)
- Quản lý hoá đơn dịch vụ hàng tháng (điện, nước — có cổng thanh toán qua QR nhanh)
- Quản lý hoá đơn dịch vụ chung (6 tháng/lần: gửi xe, dịch vụ chung...)
- Quản lý dịch vụ gửi xe (khách vãng lai gửi vé ngày chỉ cần ô nhập tiền, không đi sâu; chỉ tính dịch vụ theo tháng và quản lý số lượng xe từng căn hộ)
- Thông báo chung
- Thông báo riêng
- Giải quyết khiếu nại, đơn đăng ký
- Báo cáo, thống kê (doanh thu dịch vụ, biểu đồ theo tháng/quý)
- Quản lý nhân sự kỹ thuật (phân công task cho kỹ thuật viên)

### Cư dân
- Khiếu nại, làm đơn đăng ký (đăng ký gửi xe,...)
- Thanh toán online tiền dịch vụ, điện nước
- Nhận thông báo chung/riêng
- Biết thông tin về chính sách ở chung cư (qua dashboard, qua chatbot AI)
- Tra cứu lịch sử thanh toán, xuất hoá đơn điện tử

### Kỹ thuật viên
- Quản lý phiếu yêu cầu sửa chữa/bảo trì (nhận task, cập nhật trạng thái xử lý, đóng ticket)
- Giải quyết vấn đề điện nước (cắt điện/nước khi cư dân không thanh toán đúng hạn — không được sử dụng dịch vụ khi không thanh toán)
- Nhập tổng tiền gửi xe vãng lai theo ngày
- Thông báo tới cư dân khi tới hạn thanh toán, thông báo tới Ban quản lý về tình hình thanh toán dịch vụ và các vấn đề phát sinh cần xử lý

### Chatbot AI
- Tư vấn 24/7 về các điều khoản, thông tin, chính sách ở chung cư
- Cho biết vị trí của các nơi quan trọng thuộc chung cư (phòng camera, hiệu thuốc,...)

## 2. Kiến trúc hệ thống

Project theo hướng SOA với **8 service nghiệp vụ**, tổ chức theo nguyên tắc **database-per-service về mặt logic**: mỗi service sở hữu một nhóm bảng riêng; tham chiếu trong cùng service dùng khoá ngoại (FK) vật lý, tham chiếu liên service chỉ lưu ID và được resolve ở tầng ứng dụng (không JOIN chéo service) — mô phỏng đúng tinh thần SOA dù hiện triển khai trên một database SQLite vật lý duy nhất để đơn giản hoá demo.

| Service | Chức năng |
|---|---|
| **Auth Service** | Đăng nhập, đăng ký, phân quyền 3 role |
| **Resident Service** | Quản lý cư dân, căn hộ, hợp đồng |
| **Billing Service** | Hoá đơn điện/nước/dịch vụ, thanh toán QR, **báo cáo & thống kê** (đọc từ các view sẵn có — không tách thành service riêng vì không có bảng dữ liệu của riêng nó) |
| **Parking Service** | Quản lý gửi xe, vé tháng/vãng lai |
| **Maintenance Service** | Sửa chữa, bảo trì (kỹ thuật viên) |
| **Notification Service** | Thông báo chung/riêng |
| **Complaint Service** | Khiếu nại, đơn đăng ký |
| **Chatbot Service** | Tư vấn, tra cứu thông tin |

### Cách tổ chức code: mỗi service là 1 Flask app độc lập, giao tiếp qua REST API

Mỗi service được viết thành **một Flask app riêng biệt**, chạy ở **một cổng riêng**, đóng gói thành **một container Docker riêng**. Các service gọi nhau qua **HTTP request thật** (dùng thư viện `requests` phía Python), không gọi hàm trực tiếp — đúng với bản chất SOA/microservices: mỗi service độc lập về runtime, có thể chạy, test, debug, scale riêng lẻ.

| Service | Cổng (local) |
|---|---|
| Auth Service | 5001 |
| Resident Service | 5002 |
| Billing Service (gồm báo cáo/thống kê) | 5003 |
| Parking Service | 5004 |
| Maintenance Service | 5005 |
| Notification Service | 5006 |
| Complaint Service | 5007 |
| Chatbot Service | 5008 |

```
project/
├── auth-service/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── resident-service/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── billing-service/
│   ├── app.py
│   ├── scheduler.py      # Job định kỳ (xem mục 3)
│   ├── Dockerfile
│   └── requirements.txt
├── parking-service/
├── maintenance-service/
├── notification-service/
├── complaint-service/
├── chatbot-service/
├── shared/
│   └── db.py             # Helper dùng chung để kết nối SQL_QLCC_sqlite.sql
├── data/
│   └── SQL_QLCC_sqlite.sql
└── docker-compose.yml     # Build & chạy toàn bộ 8 container cùng lúc
```

**Lưu ý quan trọng về database dùng chung:** cả 8 service vẫn trỏ vào **cùng một file SQLite** (qua Docker volume mount), vì hiện tại chưa tách 8 database vật lý riêng. SQLite cho phép nhiều process cùng đọc, nhưng chỉ 1 process ghi tại một thời điểm (khoá ở mức file) — chấp nhận được với quy mô demo/khoá luận (ít người dùng đồng thời), nhưng không phù hợp cho production thật. Nên ghi chú rõ điểm này trong báo cáo như một giới hạn đã biết (known limitation).

**Lợi ích của cách này (đúng như bạn muốn):**
- Test từng service độc lập qua Swagger/Postman ở đúng cổng của nó, không cần chạy toàn bộ hệ thống.
- `docker-compose up` sẽ thấy rõ 8 container riêng biệt — trực quan khi demo trước hội đồng, thể hiện đúng tinh thần "độc lập triển khai" của SOA.
- Có thể tắt/bật/restart riêng từng service mà không ảnh hưởng service khác.

**Đánh đổi cần biết:** so với cách gọi hàm trực tiếp (modular monolith) đã đề xuất trước đó, cách này tốn thêm công sức ở:
- Viết thêm lớp gọi HTTP (`requests.get/post`) kèm xử lý lỗi mạng, timeout, retry giữa các service.
- Mỗi service cần Dockerfile + khai báo port + network riêng trong `docker-compose.yml`.
- Khi 1 service cần dữ liệu từ nhiều service khác (vd: Billing cần cả Resident lẫn Parking), phải gọi nhiều HTTP request tuần tự → chậm hơn và nhiều điểm có thể lỗi hơn gọi hàm trực tiếp.

Nếu khối lượng công việc này vượt quá thời gian còn lại, có thể cân nhắc làm HTTP thật cho 2-3 service "trọng tâm" (vd Billing, Parking, Auth — nơi thể hiện rõ nghiệp vụ phức tạp nhất) và giữ các service đơn giản còn lại (Chatbot, FAQ...) ở dạng gọi hàm trực tiếp, miễn là nói rõ lý do trong báo cáo.

## 3. Cơ chế xử lý hoá đơn quá hạn

Database đã có trigger tự động tạo ticket cắt điện/nước khi hoá đơn chuyển sang trạng thái `'overdue'`. Tuy nhiên trigger chỉ kích hoạt khi có lệnh `UPDATE` — bản thân việc một hoá đơn "quá hạn" theo thời gian không tự phát sinh sự kiện nào trong CSDL.

Vì vậy cần một **job chạy nền định kỳ** (mỗi ngày) để:
1. Quét các hoá đơn `unpaid` có `due_date` đã qua.
2. `UPDATE` trạng thái các hoá đơn đó thành `'overdue'`.
3. Trigger trong DB sẽ tự động kích hoạt tạo ticket `cut_service` tương ứng.

Dùng thư viện **APScheduler** (Python), chạy ngay trong tiến trình của **Billing Service** (nơi sở hữu bảng `monthly_invoices`/`semiannual_invoices`) — không cần cron job hệ điều hành riêng, không cần service riêng cho việc này.

## 4. Công nghệ sử dụng

**Backend**
- Ngôn ngữ/Framework: Python + Flask (mỗi service 1 Flask app riêng — xem mục 2)
- Giao tiếp liên service: REST API qua thư viện `requests`
- Scheduled job: APScheduler (xử lý hoá đơn quá hạn — xem mục 3)
- Authentication: JWT
- API: REST + OpenAPI (Swagger — mỗi service có Swagger UI riêng để test độc lập)
- Database: SQLite3 (dùng chung 1 file qua Docker volume — xem lưu ý ở mục 2)
- Testing: pytest (unit test cho logic tính tiền, integration test cho luồng thanh toán)
- Container: Docker + Docker Compose (mỗi service 1 container, 1 mạng ảo chung — nên dựng Docker Compose sớm hơn, ngay khi có 2-3 service chạy được, để phát hiện sớm vấn đề network/volume thay vì để dồn vào cuối)

**Frontend**: HTML/CSS/JS

**Thanh toán QR**: VietQR + SePay đối soát tự động; Test Mode để demo, Live dùng tiền thật.

**Chatbot**: truy xuất `faq_knowledge_base` và `locations`, phân biệt ý định câu hỏi; LLM tùy chọn diễn đạt lại các nguồn đã tìm được. Không có API key hoặc dịch vụ AI lỗi vẫn trả lời từ kho kiến thức. Xem [CHATBOT.md](docs/CHATBOT.md).

**Tích hợp dịch vụ bên thứ 3**: Firebase (push notification trên trình duyệt cho "Thông báo chung/riêng", thay vì chỉ thấy khi load lại trang)
