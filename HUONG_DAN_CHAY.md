# Hướng dẫn chạy An Cư (Quản lý chung cư)

Hướng dẫn cài và chạy hệ thống trên máy tính, mở trên điện thoại và xử lý sự cố thường gặp.

**Mục lục**

1. [Chuẩn bị](#1-chuẩn-bị)
2. [Chạy trên máy tính](#2-chạy-trên-máy-tính)
3. [Đăng nhập và dùng thử](#3-đăng-nhập-và-dùng-thử)
4. [Mở trên điện thoại](#4-mở-trên-điện-thoại)
5. [Xem database](#5-xem-database)
6. [Xử lý sự cố](#6-xử-lý-sự-cố)

## 1. Chuẩn bị

| Cần có | Ghi chú |
| --- | --- |
| Máy tính Windows 10/11, macOS hoặc Linux | Nên có từ 8 GB RAM |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Cài xong, mở Docker Desktop và đợi trạng thái **Engine running** |
| Mã nguồn | Tải bằng Git hoặc tải file ZIP từ GitHub (bên dưới) |

Không cần cài Python, Node.js hay tạo file cấu hình: Docker lo toàn bộ.

**Tải mã nguồn.** Cách 1, có Git:

```powershell
git clone https://github.com/Hoaithu2501/Quan-ly-chung-cu.KLTN.git
cd Quan-ly-chung-cu.KLTN
```

Cách 2, không có Git: mở trang GitHub của dự án, bấm **Code → Download ZIP**, giải nén, rồi mở PowerShell (hoặc Terminal) trong thư mục vừa giải nén.

**Máy chỉ có 8 GB RAM (Windows):** nên giới hạn bộ nhớ của Docker để máy không bị treo. Tạo file `%UserProfile%\.wslconfig` với nội dung dưới, chạy `wsl --shutdown`, rồi mở lại Docker Desktop:

```ini
[wsl2]
memory=2GB
```

## 2. Chạy trên máy tính

Trong thư mục dự án, chạy:

```powershell
docker compose up --build -d
```

Lần đầu mất vài phút để tải và build. Kiểm tra trạng thái:

```powershell
docker compose ps
```

Khi các service hiện `healthy`, mở **http://localhost:5000** bằng trình duyệt.

Hệ thống gồm 8 service nghiệp vụ (Auth, Resident, Billing, Parking, Maintenance, Notification, Complaint, Chatbot), mỗi service một container, cùng một gateway phục vụ giao diện ở cổng 5000. Ngoài ra có một job khởi tạo database chạy xong rồi thoát, và một container sao lưu tự động.

| Việc cần làm | Lệnh |
| --- | --- |
| Xem trạng thái | `docker compose ps` |
| Xem nhật ký một service | `docker compose logs -f billing` (thay `billing` bằng tên service) |
| Dừng hệ thống (giữ dữ liệu) | `docker compose down` |
| Chạy lại | `docker compose up -d` |
| Xóa dữ liệu, làm lại từ dữ liệu mẫu | `docker compose down -v`, rồi `docker compose up --build -d` |

## 3. Đăng nhập và dùng thử

**Cư dân mới tham gia:**

1. Ở trang đăng nhập, cư dân chọn **Đăng ký tài khoản**, điền thông tin và mã căn hộ, rồi bấm **Tạo tài khoản cư dân**.
2. Ban quản lý vào **Cư dân & hợp đồng**, tìm cư dân đó và chọn **Xác nhận căn hộ**.
3. Từ lúc này, cư dân xem được hóa đơn, gửi yêu cầu và nhận thông báo của căn hộ.

**Gợi ý dùng thử theo vai trò:**

- **Ban quản lý:** quản lý căn hộ, xác nhận cư dân, lập hợp đồng, lập hóa đơn điện nước hằng tháng và dịch vụ 6 tháng, duyệt đơn đăng ký gửi xe, trả lời khiếu nại, gửi thông báo, xem báo cáo, đổi vai trò tài khoản, cập nhật câu trả lời cho chatbot.
- **Cư dân:** xem hóa đơn và lịch sử thanh toán, gửi khiếu nại hoặc đơn đăng ký (kể cả đăng ký gửi xe), yêu cầu sửa chữa, đọc thông báo, hỏi chatbot qua nút **Trợ lý**.
- **Kỹ thuật viên:** nhận và cập nhật phiếu sửa chữa, ghi nhận cắt/cấp lại dịch vụ khi hóa đơn quá hạn, ghi doanh thu gửi xe vãng lai theo ngày, quản lý hóa đơn như Ban quản lý.

Thanh toán VietQR qua SePay, thông báo đẩy qua Firebase và chatbot diễn đạt bằng AI cần khóa kết nối riêng, nên tắt trong bản chạy thử:

- nút **Thanh toán VietQR** bị khóa kèm lý do;
- thông báo vẫn hiện trong mục **Thông báo**;
- chatbot trả lời từ nội dung có sẵn.

Các chức năng còn lại hoạt động đầy đủ.

## 4. Mở trên điện thoại

An Cư là trang web, không có trên App Store hay CH Play. Điện thoại mở trang web của máy đang chạy hệ thống qua cùng mạng Wi-Fi:

1. Trên máy chạy hệ thống, mở PowerShell, chạy `ipconfig` và lấy dòng **IPv4 Address** của card Wi-Fi hoặc Ethernet, ví dụ `192.168.1.20`.
2. Điện thoại kết nối cùng mạng đó rồi mở `http://192.168.1.20:5000`.
3. Nếu Windows hỏi quyền tường lửa cho Docker Desktop, cho phép trên mạng **Riêng (Private)**. Mạng khách hoặc mạng có chế độ cách ly thiết bị sẽ chặn điện thoại.

**Thêm An Cư ra màn hình chính** để mở như một ứng dụng:

- **iPhone, iPad** (Safari): nhấn nút **Chia sẻ** (ô vuông có mũi tên hướng lên; trên iOS mới có thể nằm trong nút **•••**), chọn **Thêm vào MH chính**, rồi nhấn **Thêm**.
- **Android** (Chrome): nhấn **⋮** ở góc trên bên phải, chọn **Thêm vào màn hình chính**, rồi xác nhận.

## 5. Xem database

Hệ thống dùng SQLite. Database đang chạy nằm trong volume Docker, không nằm trong thư mục dự án. Lần chạy đầu, database được tạo từ dữ liệu mẫu `tests/fixtures/demo.sql` rồi áp dụng lần lượt các file trong `migrations/`.

Để xem, tạo một bản sao database ra thư mục `backups/` trong thư mục dự án (hệ thống vẫn chạy bình thường):

```powershell
docker compose exec -T backup python scripts/backup_db.py --output /backups
```

Lệnh in ra tên file, dạng `/backups/QLCC-auto-<ngày>-<giờ>.db`; file nằm trong thư mục `backups/` của dự án. Mở file đó bằng:

- **DB Browser for SQLite** ([sqlitebrowser.org](https://sqlitebrowser.org/)): chọn **File → Open Database Read Only**, rồi chọn file. Tab **Database Structure** để xem bảng, tab **Browse Data** để xem dữ liệu.
- **DBeaver**: tạo kết nối SQLite tới file, chọn database → **View Diagram** để xem sơ đồ quan hệ.

Container `backup` cũng tự tạo mỗi ngày một bản trong `backups/` và giữ 14 bản gần nhất.

## 6. Xử lý sự cố

| Hiện tượng | Cách xử lý |
| --- | --- |
| `docker` báo không kết nối được, hoặc lỗi `500 Internal Server Error` | Docker Desktop chưa chạy hoặc bị treo. Thoát Docker Desktop từ khay hệ thống, mở lại, đợi **Engine running**, rồi chạy `docker compose up -d` |
| Trang `localhost:5000` tải mãi không xong | Máy thiếu RAM. Đóng bớt ứng dụng, đặt giới hạn bộ nhớ cho Docker (mục 1), rồi khởi động lại Docker Desktop |
| Báo cổng 5000 đang được dùng | Một chương trình khác đang dùng cổng 5000. Tắt chương trình đó, hoặc chạy `docker compose down` rồi chạy lại |
| Một service không `healthy` | Xem nhật ký: `docker compose logs <tên service>` |
| Điện thoại không mở được `http://<IP>:5000` | Kiểm tra cùng mạng Wi-Fi, đúng IP, tường lửa Windows cho phép Docker Desktop trên mạng Private, mạng không bật cách ly thiết bị |
| Nút **Thanh toán VietQR** bị khóa | Bình thường trong bản chạy thử: thanh toán QR cần cấu hình SePay riêng (mục 3) |
| Tài khoản bị khóa khi đăng nhập | Ban quản lý đã khóa tài khoản (thường do hợp đồng thuê đã hết hạn). Ban quản lý mở khóa tại **Cư dân & hợp đồng → Chi tiết** |
