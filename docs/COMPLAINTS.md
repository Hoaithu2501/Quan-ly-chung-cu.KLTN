# Phản hồi khiếu nại và thông báo riêng

## Ban quản lý trả lời cư dân

1. Đăng nhập bằng tài khoản Ban quản lý.
2. Vào **Khiếu nại & đăng ký**, tìm yêu cầu cần trả lời.
3. Chọn **Phản hồi** hoặc **Sửa phản hồi**.
4. Nhập câu trả lời, chọn trạng thái phù hợp rồi chọn **Gửi phản hồi** hoặc **Cập nhật phản hồi**.

Yêu cầu đã hoàn tất vẫn sửa được nội dung phản hồi nhưng giữ nguyên trạng thái và ngày hoàn tất. Gửi lại nguyên nội dung đã lưu sẽ không tạo thêm thông báo. Phản hồi là nội dung mới nhất trên yêu cầu; các thông báo đã gửi trước đó được giữ để cư dân biết những lần cập nhật.

## Cư dân xem câu trả lời

Người gửi yêu cầu nhận thông báo riêng có tiêu đề **Ban quản lý đã phản hồi yêu cầu #YC…**. Vào **Thông báo → Thông báo riêng** để đọc; hoặc vào **Khiếu nại & đăng ký** và mở yêu cầu để xem đầy đủ câu trả lời.

Thông báo chỉ gửi cho người đã tạo yêu cầu, kể cả khi nhiều cư dân sống cùng căn hộ. Chuông thông báo trên web kiểm tra định kỳ khoảng 45 giây; có thể mở lại mục Thông báo hoặc tải lại trang để xem sớm hơn. Thông báo bật lên trên thiết bị còn cần cấu hình Firebase và quyền trình duyệt.

Nếu dịch vụ thông báo tạm lỗi, câu trả lời vẫn được lưu. Máy chủ thử gửi lại thông báo mỗi 30 giây khi scheduler được bật; lần gửi lại giữ cùng mã sự kiện để tránh trùng thông báo. Các phản hồi đã có trước bản cập nhật này không tự phát sinh thông báo mới; chỉnh sửa nội dung phản hồi sẽ tạo thông báo.

## Cập nhật bản chạy Docker

Mã mới cần bảng `notification_resident_audience` và `complaint_outbox` trong migration `notifications_resident_replies.sql`. Không chạy container Notification mới trước khi nạp migration này.

```powershell
docker compose build db-init chatbot complaint notification
```

Xem trước nội dung FAQ rồi áp dụng bản câu trả lời dễ hiểu. Lệnh áp dụng tự tạo backup SQLite nhất quán trước khi ghi; ghi lại đường dẫn backup được in trong kết quả:

```powershell
docker compose run --rm --no-deps db-init python scripts/apply_chatbot_faq.py
docker compose run --rm --no-deps db-init python scripts/apply_chatbot_faq.py --apply
```

Sau khi đã có backup, dừng hai service cần bảng mới, nạp migration và chạy lại bằng image vừa build:

```powershell
docker compose stop complaint notification
docker compose run --rm --no-deps db-init python -c "from scripts.init_db import initialize; initialize()"
docker compose up -d --no-deps chatbot complaint notification
docker compose ps
```

Chỉ chuyển bước khi lệnh trước thành công. Nếu migration lỗi, giữ hai service đó dừng để kiểm tra; transaction migration được hoàn tác. Việc cập nhật không xóa yêu cầu hoặc phản hồi cũ. Khôi phục toàn DB phải xem xét các giao dịch mới sau thời điểm backup; không chép đè file SQLite đang chạy. Xem [CHATBOT_DATA.md](CHATBOT_DATA.md) về backup và nạp đúng DB Docker/Python.

Với bản Python, dừng runner, áp dụng FAQ để có backup, chạy `scripts/init_db.py`, rồi chạy lại `start.ps1 -Mode Python`. Các service khởi động bằng `scripts/run.py` có tiến trình riêng cho complaint và notification. Bản Python dùng database riêng; `start.ps1` không truyền tham số mặc định chạy Docker.

## Kiểm thử

Kiểm thử HTTP kiểm tra quyền phản hồi, gửi đúng người, cư dân cùng căn hộ không xem được, gửi lại sau mất kết nối và chống trùng khi nhận nhiều yêu cầu giống nhau. Ca trình duyệt kiểm tra thao tác của cả hai vai trò trên các service thật và DB tạm; không gửi thông báo thử vào dữ liệu cư dân đang sử dụng.
