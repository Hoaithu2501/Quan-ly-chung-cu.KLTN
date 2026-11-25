# Quản lý chung cư (Condominium Management System)

Hệ thống quản lý chung cư An Cư cho ba nhóm người dùng: **ban quản lý**, **cư dân** và **kỹ thuật viên**. Hệ thống xây dựng theo hướng **Service-Oriented Architecture (SOA)** với 8 service Flask độc lập: Auth, Resident, Billing, Parking, Maintenance, Notification, Complaint, Chatbot. Các service gọi nhau qua REST API, kèm một gateway phục vụ giao diện web. Toàn bộ chạy bằng Docker Compose, mỗi service một container.

## Chạy nhanh

1. Cài và mở [Docker Desktop](https://www.docker.com/products/docker-desktop/), đợi trạng thái **Engine running**.
2. Tải mã nguồn:

   ```
   git clone https://github.com/Hoaithu2501/Quan-ly-chung-cu.KLTN.git
   cd Quan-ly-chung-cu.KLTN
   ```

3. Chạy hệ thống (lần đầu mất vài phút):

   ```
   docker compose up --build -d
   ```

4. Mở **http://localhost:5000** và đăng nhập bằng một tài khoản thử bên dưới.

## Tài khoản thử

| Vai trò | Tài khoản | Mật khẩu |
|---|---|---|
| Ban quản lý | `admin` | `Admin@12345` |
| Cư dân | `resident` | `Resident@12345` |
| Kỹ thuật viên | `technician` | `Tech@12345` |

Bản chạy thử dùng dữ liệu mẫu. Thanh toán QR, thông báo đẩy và chatbot diễn đạt bằng AI cần khóa kết nối riêng nên được tắt; các chức năng còn lại hoạt động đầy đủ.

Hướng dẫn chi tiết (mở trên điện thoại, xem database, xử lý sự cố): [HUONG_DAN_CHAY.md](HUONG_DAN_CHAY.md).
