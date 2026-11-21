# Quản lý chung cư (Condominium Management System)

Hệ thống quản lý chung cư xây dựng theo hướng **Service-Oriented Architecture (SOA)**, phục vụ định hướng Business Analyst: nhấn mạnh phân tích nghiệp vụ, phân tích hệ thống và kiểm thử, bên cạnh việc xây dựng ứng dụng thực tế.

## 1. Người dùng & chức năng nghiệp vụ

Người sử dụng trực tiếp là ban quản lý chung cư, với 3 nhóm user chính: **ban quản lý chung cư**, **cư dân**, **kỹ thuật viên**.

### Ban quản lý chung cư
- Chỉnh sửa thông tin cá nhân
- Quản lý căn hộ (thông tin chủ sở hữu, thông tin căn hộ, trạng thái trống/đã ở, tình trạng sở hữu: thuê bao nhiêu lâu, thời gian còn lại). Chủ sở hữu và người thuê được lưu song song trên cùng một căn hộ; cột cư dân hiện tại liệt kê mọi người đang ở
- Cư dân tự đăng ký tài khoản; ban quản lý xác nhận căn hộ cho tài khoản đó, không thêm cư dân thủ công. Hợp đồng chỉ lập cho cư dân đã đăng ký
- Hợp đồng thuê: cư dân được nhắc trước 1 tháng khi sắp hết hạn; đến ngày hết hạn mà chưa gia hạn, ban quản lý nhận thông báo và có thể khoá mọi tài khoản cư dân của căn hộ (căn hộ chuyển sang còn trống). Tài khoản bị khoá thấy lý do khi đăng nhập; ban quản lý mở khoá lại khi cư dân đến gặp trực tiếp
- Quản lý hoá đơn dịch vụ hàng tháng (điện, nước, có cổng thanh toán nhanh qua QR code)
- Quản lý hoá đơn dịch vụ chung 6 tháng/lần (dịch vụ chung, gửi xe theo hộ gia đình)
- Quản lý dịch vụ gửi xe (khách vãng lai gửi theo lượt chỉ cần nhập tổng tiền mỗi ngày, không đi sâu)
- Gửi thông báo chung tới tất cả cư dân
- Gửi thông báo riêng tới từng căn hộ, qua các tài khoản đã liên kết với căn hộ đó
- Giải quyết khiếu nại, đơn đăng ký (nhận đơn, phản hồi và phê duyệt). Khi khiếu nại cần kỹ thuật xử lý, ban quản lý tạo phiếu sửa chữa và phân công kỹ thuật viên
- Báo cáo, thống kê (doanh thu dịch vụ hàng tháng và 6 tháng, vé gửi xe vãng lai, biểu đồ theo tháng/quý, số lượng khiếu nại)
- Quản lý nhân sự kỹ thuật (phân công task cho kỹ thuật viên). Tài khoản chỉ đổi vai trò; danh sách kỹ thuật viên tự cập nhật theo vai trò
- Cập nhật chính sách ở chung cư; chatbot dùng ngay nội dung vừa thêm, sửa hoặc xoá

**Quy định gửi xe:** chỉ quản lý xe đạp, xe máy và xe điện; ô tô gửi ở bãi ngoài, không kiểm soát. Mỗi căn hộ không giới hạn số xe. Thời gian gửi tính theo lịch từ ngày bắt đầu, như vé tháng: bắt đầu 20/11, 2 tháng thì gửi đến hết 19/01 (tháng không có ngày đó thì lấy ngày cuối tháng: 31/01 + 1 tháng gửi đến hết 27/02). Mỗi lần đăng ký tối thiểu 2 tháng (gia hạn xe đã đăng ký được từ 1 tháng); số tháng tính cả tháng bắt đầu và tối đa đến tháng cuối của kỳ thu phí 6 tháng (tháng 1–6 hoặc 7–12); đăng ký tháng 6 được chọn đến 7 tháng, đăng ký tháng 12 chỉ 1 tháng. Hết thời gian đăng ký, xe ngừng tính phí và cần gia hạn mới gửi tiếp. Phí tháng: xe đạp 50.000 đ, xe máy và xe điện 100.000 đ. Phí gửi xe của kỳ 6 tháng là tổng của `phí 1 tháng × số tháng gửi bắt đầu trong kỳ` theo từng xe, nên những ngày của tháng cuối lẻ sang kỳ sau không bị thu lại; xe đăng ký mới đóng thêm 100.000 đ làm thẻ một lần; xe từng đăng ký (cùng biển số, hoặc mã xe đạp cũ) đã có thẻ nên không đóng lại.

### Cư dân
- Chỉnh sửa thông tin cá nhân
- Yêu cầu sửa chữa, bảo trì
- Gửi khiếu nại (có đính kèm ảnh, ảnh lớn được tự động thu nhỏ), làm đơn đăng ký (đăng ký gửi xe, dùng dịch vụ công,...)
- Thanh toán online tiền dịch vụ, điện nước
- Nhận thông báo chung/riêng
- Biết thông tin về chính sách ở chung cư (qua dashboard, qua chatbot AI)
- Tra cứu lịch sử thanh toán, tải biên nhận điện tử (biên nhận nội bộ, không thay thế hoá đơn thuế)

### Kỹ thuật viên
- Chỉnh sửa thông tin cá nhân, đổi mật khẩu
- Quản lý phiếu yêu cầu sửa chữa/bảo trì (mọi kỹ thuật viên đều thấy và có thể làm mọi phiếu; cập nhật trạng thái xử lý, đóng ticket)
- Quản lý dịch vụ: xem hoá đơn quá hạn, ghi nhận cắt điện, nước, gửi xe, dịch vụ chung khi cư dân không thanh toán đúng hạn và cấp lại sau khi cư dân thanh toán
- Cập nhật doanh thu gửi xe vãng lai theo ngày (thủ công)
- Quản lý hoá đơn giống hệt ban quản lý (hai vai trò dùng chung một bộ quyền quản lý hoá đơn): lập, điều chỉnh hoá đơn, ghi nhận thu tiền mặt/chuyển khoản, mở khoá phiên thanh toán, đối soát chuyển khoản, xem các khoản đã thu và tải biên nhận. Báo cáo thống kê vẫn chỉ ban quản lý xem
- Nhận thông báo về phiếu sửa chữa, hoá đơn quá hạn và dịch vụ cần cấp lại. Kỹ thuật viên không soạn thông báo: khi cập nhật phiếu, hệ thống tự báo cư dân căn hộ và ban quản lý. Thông báo khi hoá đơn sắp đến hạn hoặc quá hạn (hàng tháng và 6 tháng) do hệ thống tự gửi tới cư dân và báo cho ban quản lý

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
├── Dockerfile            # Công thức build dùng chung cho mọi image
├── docker-compose.yml    # Build & chạy toàn bộ hệ thống, mỗi service một container
├── requirements.txt      # Thư viện Python dùng chung
├── auth-service/
│   └── app.py
├── resident-service/
│   └── app.py
├── billing-service/
│   ├── app.py
│   ├── sepay_payments.py # Thanh toán VietQR + SePay
│   └── scheduler.py      # Job định kỳ (xem mục 3)
├── parking-service/
├── maintenance-service/
├── notification-service/
├── complaint-service/
├── chatbot-service/
├── gateway/              # Giao diện và reverse proxy, cổng 5000
├── frontend/
├── shared/
│   └── db.py             # Helper kết nối database dùng chung
├── migrations/           # Thay đổi cấu trúc database, chạy theo thứ tự
├── database/QLCC_an_danh.db  # Bản sao dữ liệu thật đã ẩn danh, để xem cấu trúc và dữ liệu (database/README.md)
└── tests/fixtures/demo.sql  # Dữ liệu mẫu cho database mới và bộ kiểm thử
```

Các service có công thức build giống hệt nhau, chỉ khác tên, nên dùng chung một `Dockerfile` với tham số `SERVICE` thay vì lặp lại 8 file. Mỗi service vẫn là một image và một container riêng, có cổng riêng, chạy và khởi động lại độc lập.

**Lưu ý quan trọng về database dùng chung:** cả 8 service vẫn trỏ vào **cùng một file SQLite** (qua Docker volume mount), vì hiện tại chưa tách 8 database vật lý riêng. SQLite cho phép nhiều process cùng đọc, nhưng chỉ 1 process ghi tại một thời điểm (khoá ở mức file) — chấp nhận được với quy mô demo/khoá luận (ít người dùng đồng thời), nhưng không phù hợp cho production thật. Nên ghi chú rõ điểm này trong báo cáo như một giới hạn đã biết (known limitation).

**Lợi ích của cách này (đúng như bạn muốn):**
- Test từng service độc lập qua Swagger/Postman ở đúng cổng của nó, không cần chạy toàn bộ hệ thống.
- `docker-compose up` sẽ thấy rõ 8 container riêng biệt — trực quan khi demo trước hội đồng, thể hiện đúng tinh thần "độc lập triển khai" của SOA.
- Có thể tắt/bật/restart riêng từng service mà không ảnh hưởng service khác.

**Đánh đổi cần biết:** so với cách gọi hàm trực tiếp (modular monolith) đã đề xuất trước đó, cách này tốn thêm công sức ở:
- Viết thêm lớp gọi HTTP (`requests.get/post`) kèm xử lý lỗi mạng, timeout, retry giữa các service.
- Mỗi service cần khai báo image, port và network riêng trong `docker-compose.yml`.
- Khi 1 service cần dữ liệu từ nhiều service khác (vd: Billing cần cả Resident lẫn Parking), phải gọi nhiều HTTP request tuần tự → chậm hơn và nhiều điểm có thể lỗi hơn gọi hàm trực tiếp.

Nếu khối lượng công việc này vượt quá thời gian còn lại, có thể cân nhắc làm HTTP thật cho 2-3 service "trọng tâm" (vd Billing, Parking, Auth — nơi thể hiện rõ nghiệp vụ phức tạp nhất) và giữ các service đơn giản còn lại (Chatbot, FAQ...) ở dạng gọi hàm trực tiếp, miễn là nói rõ lý do trong báo cáo.

## 3. Cơ chế xử lý hoá đơn quá hạn

Bản thân việc một hoá đơn "quá hạn" theo thời gian không tự phát sinh sự kiện nào trong CSDL.

Vì vậy cần một **job chạy nền định kỳ** (mỗi ngày) để:
1. Quét các hoá đơn `unpaid` có `due_date` đã qua.
2. `UPDATE` trạng thái các hoá đơn đó thành `'overdue'`.
3. Gửi thông báo cho cư dân và báo tổng hợp cho ban quản lý, kỹ thuật viên.

Kỹ thuật viên xử lý tại màn **Quản lý dịch vụ**: ghi nhận cắt từng dịch vụ của hoá đơn quá hạn. Cư dân, ban quản lý và kỹ thuật viên nhận thông báo. Khi hoá đơn được thanh toán, kỹ thuật viên được báo để cấp lại dịch vụ; trạng thái cắt và cấp lại hiện trong chi tiết hoá đơn.

Dùng thư viện **APScheduler** (Python), chạy ngay trong tiến trình của **Billing Service** (nơi sở hữu bảng `monthly_invoices`/`semiannual_invoices`) — không cần cron job hệ điều hành riêng, không cần service riêng cho việc này.

## 4. Công nghệ sử dụng

**Backend**
- Ngôn ngữ/Framework: Python + Flask (mỗi service 1 Flask app riêng — xem mục 2)
- Giao tiếp liên service: REST API qua thư viện `requests`
- Scheduled job: APScheduler (xử lý hoá đơn quá hạn — xem mục 3)
- Authentication: JWT
- CI/CD: GitHub Actions
- API: REST + OpenAPI (Swagger — mỗi service có Swagger UI riêng để test độc lập)
- Database: SQLite3 (dùng chung 1 file qua Docker volume — xem lưu ý ở mục 2)
- Testing: pytest (unit test cho logic tính tiền, integration test cho luồng thanh toán)
- Container: Docker + Docker Compose (mỗi service 1 container, 1 mạng ảo chung — nên dựng Docker Compose sớm hơn, ngay khi có 2-3 service chạy được, để phát hiện sớm vấn đề network/volume thay vì để dồn vào cuối)

**Frontend**: HTML/CSS/JS

**Thanh toán QR**: SePay

**Chatbot**: Rule-based (so khớp từ khoá với `faq_knowledge_base`) — không cần AI phức tạp

**Tích hợp dịch vụ bên thứ 3**: Firebase (push notification trên trình duyệt cho "Thông báo chung/riêng", thay vì chỉ thấy khi load lại trang)

## 5. Chạy thử

Chỉ cần cài và bật Docker Desktop, không cần tạo file cấu hình hay chạy Cloudflare:

```
docker compose up --build -d
```

Mở http://localhost:5000 và đăng nhập bằng tài khoản mẫu:

| Vai trò | Tài khoản | Mật khẩu |
|---|---|---|
| Ban quản lý | `admin` | `Admin@12345` |
| Cư dân | `resident` | `Resident@12345` |
| Kỹ thuật viên | `technician` | `Tech@12345` |

Bản chạy thử dùng dữ liệu mẫu. Thanh toán QR, thông báo đẩy và diễn đạt câu trả lời bằng AI chỉ bật khi có thông tin kết nối riêng trong `.env` (xem `docs/GETTING_STARTED.md`); các chức năng còn lại hoạt động bình thường. Cài lên iPhone hoặc Android: xem `docs/CAI_DAT_DIEN_THOAI.md`.
