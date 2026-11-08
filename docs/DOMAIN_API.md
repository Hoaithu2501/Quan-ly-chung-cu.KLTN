# API các dịch vụ nghiệp vụ

Các đường dẫn dưới đây được phục vụ bởi từng Flask app độc lập. Qua giao diện web, gateway chuyển tiếp cùng đường dẫn `/api/...` tới dịch vụ tương ứng. Không có truy vấn JOIN giữa bảng thuộc các dịch vụ khác nhau trong mã ứng dụng.

| Dịch vụ | Cổng mặc định | Tiền tố |
| --- | --- | --- |
| Auth | 5001 | `/api/auth` |
| Resident | 5002 | `/api/residents`, `/api/apartments`, `/api/contracts` |
| Billing | 5003 | `/api/billing` |
| Parking | 5004 | `/api/parking` |
| Maintenance | 5005 | `/api/maintenance` |
| Notification | 5006 | `/api/notifications` |
| Complaint | 5007 | `/api/complaints` |
| Chatbot | 5008 | `/api/chatbot` |

Danh sách trả về `{"items": [...]}`; tạo mới trả HTTP 201; dữ liệu không hợp lệ trả 400; chưa đăng nhập trả 401; không đủ quyền trả 403; không tìm thấy trả 404; trùng lặp/xung đột trạng thái trả 409. Lỗi có dạng `{"error": "Thông báo tiếng Việt"}`. Các yêu cầu thông thường sử dụng `Authorization: Bearer <JWT>`. Lời gọi nội bộ chỉ được chấp nhận trên những endpoint được khai báo, thông qua `X-Service-Token` lấy từ cấu hình máy chủ. Trình duyệt không được nhận khóa nội bộ.

Mỗi dịch vụ có `/health`, `/openapi.json` và `/docs`. API Explorer cung cấp danh sách route và xác thực; các bảng bên dưới bổ sung quy tắc nghiệp vụ và trường dữ liệu.

## Xác nhận căn hộ và phạm vi cư dân

| Phương thức và đường dẫn | Quyền | Nội dung |
| --- | --- | --- |
| `GET /api/residents/me` | Cư dân | Hồ sơ và danh sách căn hộ đã có quyền truy cập của chính tài khoản. |
| `GET /api/residents` | Quản lý, nội bộ | Hồ sơ cư dân kèm mã căn hộ đăng ký và phạm vi đã xác nhận. |
| `GET /api/residents/{resident_id}` | Quản lý, cư dân sở hữu hồ sơ, nội bộ | Một hồ sơ cư dân. |
| `POST /api/residents/{resident_id}/apartments` | Quản lý | `{"apartment_id":1}`; xác nhận cư dân sống tại căn hộ. Trả hồ sơ cập nhật, 201 nếu mới, 200 nếu đã xác nhận. |
| `DELETE /api/residents/{resident_id}/apartments/{apartment_id}` | Quản lý | Gỡ xác nhận cư trú riêng; trả hồ sơ cập nhật 200. Không sửa hợp đồng. |

Trường `registered_apartment_code` là mã người dùng khai khi đăng ký, không tự cấp quyền xem hóa đơn hoặc thông báo căn hộ. Ban quản lý phải kiểm tra đúng cư dân và dùng **Xác nhận căn hộ** trên web hoặc POST ở trên. Không cần tạo hợp đồng trùng khi xác nhận người cùng ở với người đứng tên hợp đồng.

Hồ sơ trả các trường:

| Trường | Ý nghĩa |
| --- | --- |
| `apartment_ids`, `apartment_codes` | Hợp của căn hộ theo hợp đồng còn hiệu lực và căn hộ được Ban quản lý xác nhận riêng. Đây là phạm vi áp dụng cho hóa đơn và các chức năng theo căn hộ. |
| `contract_apartment_ids` | Căn hộ theo hợp đồng `active` và còn hiệu lực theo ngày thực tế. |
| `verified_apartment_ids` | Căn hộ được xác nhận cư trú riêng, không bao gồm hợp đồng nếu chưa có xác nhận riêng. |
| `verified_apartments` | Các xác nhận riêng, mỗi mục có `apartment_id`, `code`, `confirmed_by_user_id`, `confirmed_at`. |

DELETE chỉ gỡ một xác nhận trong `verified_apartments`. Nếu cư dân còn hợp đồng hiệu lực với căn hộ đó, quyền theo hợp đồng vẫn còn. Tạo/gỡ xác nhận không thay đổi chủ hợp đồng, ngày hợp đồng hay lịch sử cư trú gốc. Cư dân không được tự gọi POST/DELETE để cấp quyền cho mình.

## Hóa đơn và thanh toán

| Phương thức và đường dẫn | Quyền | Nội dung |
| --- | --- | --- |
| GET /api/billing/payment-config | Quản lý, cư dân | Chế độ sepay, environment test/live, ready, missing, issues, message và reconciliation_enabled; không trả khóa/token. |
| GET /api/billing/invoices/{kind} | Quản lý, cư dân | Cư dân chỉ xem hóa đơn trong căn hộ đã xác nhận; kind là monthly/semiannual. |
| POST /api/billing/invoices/{kind} | Quản lý | Lập hóa đơn theo căn hộ/kỳ, server tính số tiền. |
| PATCH /api/billing/invoices/{kind}/{invoice_id} | Quản lý | Chỉ unpaid, không có phiên đang chờ; số tiền bị khóa sau khi đã phát hành mã chuyển khoản. |
| POST /api/billing/invoices/{kind}/{invoice_id}/pay | Quản lý | Ghi nhận toàn bộ tiền thực nhận; không ghi trùng khi đang có phiên hoặc đã nhận một phần qua SePay. |
| POST /api/billing/invoices/{kind}/{invoice_id}/checkout | Cư dân đúng căn hộ | Body {}, tạo phiên (201) hoặc dùng lại (200). Chỉ người giữ phiên nhận QR; thành viên khác chỉ xem trạng thái. |
| GET /api/billing/orders/{order_id} | Quản lý, cư dân đúng căn hộ | Trạng thái phiên, paid_amount, remaining_amount; thông tin chuyển tiền chỉ cho chủ phiên hợp lệ. |
| GET /api/billing/orders/{order_id}/qr | Cư dân giữ phiên | PNG VietQR chứa số còn thiếu, chỉ khi pending và còn quyền chuyển; 403 nếu không đủ quyền. |
| POST /api/billing/orders/{order_id}/confirm-transfer | Cư dân giữ phiên | Chuyển pending sang awaiting_confirmation; không cập nhật hóa đơn đã trả. |
| POST /api/billing/orders/{order_id}/cancel | Cư dân giữ phiên | Chỉ pending chưa nhận tiền; hủy phiên không thu hồi QR đã lưu. |
| POST /api/billing/orders/{order_id}/reconcile | Quản lý, cư dân đúng căn hộ | Đọc API SePay khi có token + UUID tài khoản; nếu chưa có thì trả trạng thái đã nhận qua webhook. |
| POST /api/billing/sepay/webhook | SePay với API Key | JSON, Authorization: Apikey <khóa>; xác minh giao dịch, chống lặp, phân bổ tiền, trả 201 và success=true. |
| GET /api/billing/sepay/transactions | Quản lý | Sổ giao dịch: tiền nhận, đã phân bổ, dư/chưa xác định và ghi chú xử lý. |
| POST /api/billing/sepay/transactions/{transaction_id}/resolve | Quản lý | Body resolution=refunded/retained/reviewed và note không rỗng; chỉ lưu xử lý, không chuyển/hoàn tiền. |

Quyền hóa đơn theo căn hộ chung; mỗi hóa đơn chỉ ghi nhận đủ tiền một lần. Một phiên pending mặc định 15 phút chỉ cấp QR cho một người; awaiting_confirmation giữ khóa cho tới đối soát, không tự hết theo đồng hồ. Hai lần chuyển tiền thực tế vẫn có thể về ngân hàng; phần không được phân bổ lưu để BQL xử lý. Thanh toán đủ tạo biên nhận và thông báo BQL một lần.

PAYMENT_MODE=sepay, SEPAY_ENV=test mặc định. Test dùng mô phỏng trên SePay; không dùng ứng dụng ngân hàng thật. Live chuyển tiền thật. Các API MoMo/simulate cũ đã gỡ; bản ghi lịch sử không bị xóa. Xem [PAYMENTS.md](PAYMENTS.md) và [thiết lập SePay](SEPAY_VIETQR.md).

## Gửi xe

| Phương thức và đường dẫn | Quyền | Nội dung |
| --- | --- | --- |
| `GET /api/parking/vehicles` | Quản lý, kỹ thuật viên, cư dân, nội bộ | Cư dân chỉ thấy xe trong căn hộ của mình. Lọc tùy chọn `apartment_id`, `status`. |
| `POST /api/parking/vehicles` | Quản lý | Đăng ký xe. |
| `PATCH /api/parking/vehicles/{vehicle_id}` | Quản lý | Chỉnh thông tin hoặc đặt `status=cancelled`; giữ lịch sử. |
| `GET /api/parking/summary` | Quản lý, kỹ thuật viên, nội bộ | Tổng xe và phí tháng theo căn hộ; lọc `apartment_id`. Thêm `period=YYYY-H1/H2` để tính phí trong kỳ 6 tháng và phí thẻ lần đầu. |
| `GET /api/parking/guest-daily` | Quản lý, kỹ thuật viên | Sổ doanh thu ngày; lọc `from`, `to` theo `YYYY-MM-DD`. |
| `POST /api/parking/guest-daily` | Quản lý, kỹ thuật viên | Ghi tổng thu một ngày. |
| `PUT /api/parking/guest-daily/{record_id}` | Quản lý, kỹ thuật viên | Sửa bản ghi doanh thu hiện có. |

Payload đăng ký xe:

```json
{
  "apartment_id": 1,
  "vehicle_type": "motorbike",
  "plate_number": "29A1-12345",
  "registration_months": 2,
  "registered_date": "2026-10-04"
}
```

`vehicle_type` là `bicycle`, `motorbike` hoặc `electric_bike`; không nhận ô tô. Xe máy và xe điện phải có biển số; xe đạp để trống được cấp mã `<mã căn hộ>-XD-<vehicle_id>`. Biển số đang hoạt động không được trùng, kể cả hai yêu cầu đồng thời. Server áp dụng phí cố định: xe đạp 50.000 VND/tháng; xe máy và xe điện 100.000 VND/tháng. Có thể bỏ `monthly_fee`; nếu gửi, giá trị phải đúng mức này.

`registration_months` là số tháng cam kết trước khi được hủy, mặc định 2 và không được nhỏ hơn 2. Đăng ký tiếp tục hoạt động cho đến khi hủy; số tháng cam kết không phải ngày tự hết hạn. Bỏ `registered_date` để dùng ngày hiện tại theo UTC+7; không thể đổi ngày bắt đầu hoặc rút ngắn cam kết sau khi tạo. Bản ghi trả thêm `minimum_end_date` là ngày sớm nhất được hủy, `cancelled_date` do server ghi nhận và `card_fee`. Đăng ký đã hủy được giữ làm lịch sử; muốn gửi lại phải tạo đăng ký mới.

Xe mới chịu thêm 100.000 VND phí thẻ trong kỳ có tháng đăng ký, chỉ một lần. Khi đăng ký lại cùng biển số đã có thẻ, phí thẻ bằng 0. Migration giữ đăng ký cũ và coi thẻ cũ đã được cấp, không thu lại phí thẻ. Tổng hợp không có `period` trả `apartment_id`, `vehicle_count`, `monthly_fee` và bí danh `tong_phi_thang`. Tổng hợp có `period` tính theo các tháng dương lịch có gửi xe (không phân bổ theo ngày), dừng trước ngày hủy; trả thêm `vehicle_months`, `recurring_fee`, `card_fee`, `parking_fee`.

Sổ doanh thu nhận `{"parking_date":"2026-10-04","daily_revenue":250000}`. Mỗi ngày chỉ có một bản ghi; ngày tương lai và số tiền âm bị từ chối. Cập nhật phải dùng ID của bản ghi hiện có, tránh ghi doanh thu lặp.

## Kỹ thuật và bảo trì

| Phương thức và đường dẫn | Quyền | Nội dung |
| --- | --- | --- |
| `GET /api/maintenance/technicians` | Quản lý, kỹ thuật viên | Hồ sơ và `open_tickets`; kỹ thuật viên chỉ thấy hồ sơ đăng nhập của mình. |
| `POST /api/maintenance/technicians` | Quản lý | `user_id`, `full_name`, `specialty`. Tài khoản phải có role kỹ thuật viên. |
| `PATCH /api/maintenance/technicians/{id}` | Quản lý | Sửa hồ sơ và liên kết tài khoản. |
| `GET /api/maintenance/tickets` | Ba vai trò | Quản lý thấy tất cả; kỹ thuật viên thấy phiếu được giao; cư dân thấy phiếu của căn hộ mình. Lọc `status`. |
| `POST /api/maintenance/tickets` | Quản lý, cư dân | Tạo phiếu. Cư dân chỉ tạo `repair` hoặc `maintenance` tại căn hộ của mình. |
| `PATCH /api/maintenance/tickets/{id}` | Quản lý, kỹ thuật viên được giao | Phân công, cập nhật ưu tiên/nội dung hoặc trạng thái. Kỹ thuật viên chỉ sửa `status`. |
| `POST /api/maintenance/events` | Nội bộ | Nhận sự kiện thanh toán từ Billing, chống xử lý trùng bằng `event_id`. |

`specialty` là `parking`, `payment` hoặc `general`. Payload tạo phiếu gồm `apartment_id`, `description`, `type` (mặc định `repair`), `priority` (`low`, `medium`, `high`, mặc định `medium`). Quản lý được thêm `technician_id` và tạo `cut_service`, `restore_service`. Cư dân không được tự phân công người xử lý. Phiếu khu vực chung do quản lý tạo có thể không có `apartment_id`.

Trạng thái chuyển `pending → in_progress → completed`. Phiếu phải có người nhận trước khi bắt đầu; không bỏ qua bước đang xử lý, không lùi trạng thái, không mở lại phiếu đã đóng. `completed_at` do máy chủ ghi. Khi cần xử lý tiếp, tạo phiếu mới để giữ lịch sử.

Sự kiện Billing:

```json
{
  "event_id": "settled:monthly:123",
  "event_type": "invoice_settled",
  "invoice_type": "monthly",
  "invoice_id": 123,
  "apartment_id": 1,
  "period": "2026-10",
  "all_debts_settled": true
}
```

Trigger gốc trong SQLite tạo phiếu cắt dịch vụ khi hóa đơn chuyển sang quá hạn. Maintenance không tạo thêm phiếu cắt từ cùng sự kiện. Sau khi tất cả nợ quá hạn của căn hộ đã thanh toán, phiếu cắt chưa bắt đầu được đóng với `outcome=cancelled`; phiếu đang thực hiện hoặc đã hoàn tất dẫn đến yêu cầu khôi phục với `outcome=restore_requested`. Phiếu khôi phục đang mở được tái sử dụng. Gửi lại cùng `event_id` không tạo phiếu hoặc thực hiện thao tác lần hai. Billing tính lại công nợ khi gửi sự kiện lưu trong outbox.

## Thông báo

| Phương thức và đường dẫn | Quyền | Nội dung |
| --- | --- | --- |
| `GET /api/notifications` | Ba vai trò | Thông báo phù hợp phạm vi người nhận, có `is_read`. |
| `POST /api/notifications` | Quản lý, kỹ thuật viên | Tạo thông báo và thử gửi Firebase nếu đã cấu hình. |
| `POST /api/notifications/{id}/read` | Cư dân | Đánh dấu đã đọc; gọi lặp không thêm nhật ký trùng. |
| `GET /api/notifications/{id}/receipts` | Quản lý | Nhật ký cư dân đã đọc. |
| `POST /api/notifications/events` | Nội bộ | Payload thông báo cộng `event_id`; không tạo trùng khi Billing gửi lại. |
| `GET /api/notifications/push-config` | Ba vai trò | `{configured, config}` với cấu hình Web công khai; kiểm tra file service account và project tương ứng. BQL nhận thêm `errors` nếu cấu hình thiếu/sai; không trả private key. |
| `POST /api/notifications/push-tokens` | Ba vai trò | Đăng ký `{"token":"<FCM token>"}` cho phiên người dùng hiện tại. |
| `DELETE /api/notifications/push-tokens` | Ba vai trò | Gỡ token thuộc tài khoản đang đăng nhập. |

Thông báo chung nhận `{"type":"general","title":"...","content":"..."}`. Thông báo riêng đến căn hộ dùng `type=private` và `target_apartment_id`. Thông báo riêng đến Ban quản lý dùng `type=private,target_role=admin`. Thông báo riêng cho một cư dân dùng `type=private,target_resident_id=<id>`; chỉ chọn một trong ba cách gửi riêng. Cư dân chỉ xem/đánh dấu đã đọc thông báo dành cho mình hoặc căn hộ mình; phản hồi khiếu nại không được gửi chung cho các cư dân cùng căn hộ. Kỹ thuật viên thấy thông báo chung và thông báo do mình gửi.

Thông báo được lưu trước khi gửi Firebase. Phản hồi `push` cho biết `configured`, `sent`, `failed`. Khi chưa cấu hình, hệ thống vẫn có hộp thông báo và không giả báo đã push. Khi nhà cung cấp lỗi, bản ghi trong hệ thống vẫn tồn tại; việc gửi push hiện là best-effort và chưa có hàng đợi retry riêng. Các token hết hiệu lực do FCM xác nhận được loại bỏ.

Máy chủ dùng `GOOGLE_APPLICATION_CREDENTIALS` trỏ đến tệp tài khoản dịch vụ và tùy chọn `FIREBASE_PROJECT_ID`. Web dùng `FIREBASE_WEB_CONFIG` (JSON) cùng `FIREBASE_VAPID_KEY`, hoặc trường `vapidKey` trong JSON. Khóa tài khoản dịch vụ không bao giờ được trả cho trình duyệt. Trình duyệt cần HTTPS hoặc localhost và người dùng cho phép nhận thông báo.

## Khiếu nại và đơn đăng ký

| Phương thức và đường dẫn | Quyền | Nội dung |
| --- | --- | --- |
| `GET /api/complaints` | Quản lý, cư dân | Cư dân chỉ thấy đơn của mình; lọc tùy chọn `status`. |
| `POST /api/complaints` | Quản lý, cư dân | `type`, `content`, tùy chọn `category`; quản lý phải chỉ định `resident_id`. |
| `PATCH /api/complaints/{id}` | Quản lý | `status`, `response`. |

`type` là `complaint` hoặc `registration`. Cư dân không được tạo đơn mạo danh bằng `resident_id` của người khác. Trạng thái gồm `pending`, `processing`, `resolved`, `rejected`; đóng đơn bắt buộc có phản hồi. `resolved_at` do máy chủ ghi, đơn đã đóng không được chuyển lại sang chờ. Đơn đăng ký gửi xe là hồ sơ yêu cầu: sau khi duyệt, quản lý đăng ký xe thực tế tại phân hệ Gửi xe; phản hồi giải quyết đơn không tự tạo xe hoặc tự tính phí.

Ban quản lý có thể cập nhật phản hồi của đơn đã đóng trong khi giữ nguyên trạng thái. Mỗi nội dung phản hồi mới hoặc thay đổi được lưu cùng một sự kiện thông báo, gửi riêng tới cư dân đã gửi đơn. Gửi lại cùng nội dung không tạo thêm thông báo. Nếu dịch vụ thông báo tạm lỗi, phản hồi vẫn được lưu; `complaint_outbox` giữ sự kiện để gửi lại mỗi 30 giây khi scheduler được bật. Xem [COMPLAINTS.md](COMPLAINTS.md) để thao tác trên web và nâng cấp schema.

## Chatbot, nội quy và vị trí

| Phương thức và đường dẫn | Quyền | Nội dung |
| --- | --- | --- |
| `POST /api/chatbot/ask` | Ba vai trò | `{"question":"Hiệu thuốc ở đâu?"}`. |
| `GET /api/chatbot/faqs` | Ba vai trò | Kho câu hỏi/câu trả lời. |
| `POST /api/chatbot/faqs` | Quản lý | `question`, `answer`, tùy chọn `category`. |
| `PATCH /api/chatbot/faqs/{id}` | Quản lý | Chỉnh nội dung FAQ. |
| `DELETE /api/chatbot/faqs/{id}` | Quản lý | Xóa mục kiến thức. |
| `GET /api/chatbot/locations` | Ba vai trò | Danh bạ địa điểm. |
| `POST /api/chatbot/locations` | Quản lý | `name`, tùy chọn `block`, `floor`, `description`. |
| `PATCH /api/chatbot/locations/{id}` | Quản lý | Sửa địa điểm. |
| `DELETE /api/chatbot/locations/{id}` | Quản lý | Xóa địa điểm. |

Chatbot chuẩn hóa tiếng Việt có/không dấu, từ đồng nghĩa và ý định; truy xuất FAQ và danh bạ địa điểm. Kết quả giữ `answer`, `matched`, `source`, `source_id`, `source_title`, `confidence`, thêm `sources` và `engine` (`knowledge_base`, `llm`, `resident_data`). Thiếu dữ liệu trả `matched=false`; câu mơ hồ có thể yêu cầu làm rõ. `confidence` là điểm truy xuất, không phải xác suất đúng.

LLM tùy chọn diễn đạt lại các nguồn, lỗi hoặc chưa cấu hình thì trả nội dung gốc. Chỉ nhận `question`, không nhận nguồn, vai trò hoặc phạm vi căn hộ do client cung cấp. Tra cứu hóa đơn cá nhân cần bật cấu hình riêng, chỉ dùng JWT cư dân và không gửi dữ liệu hóa đơn cho LLM. Xem [CHATBOT.md](CHATBOT.md) và [cách nhập FAQ](CHATBOT_DATA.md).

## Dữ liệu mẫu và giới hạn đã biết

- Tệp gốc có nhiều người khác tên liên kết cùng một `user_id` trong `residents`: 3, 4, 5, 6, 7. Không thể coi những người này là một cư dân. Phiên đăng nhập dùng hồ sơ có ID nhỏ nhất; Ban quản lý cần tạo/liên kết tài khoản riêng cho các hồ sơ còn lại trước khi dùng thật.
- Bảng `technicians` có 15 người nhưng lặp các tài khoản 11, 12, 13. Mỗi đăng nhập chỉ được truy cập hồ sơ kỹ thuật viên có ID nhỏ nhất và công việc của hồ sơ đó. Quản lý vẫn thấy tất cả hồ sơ để sửa liên kết.
- Dữ liệu gốc có các hợp đồng đồng thời và một số trạng thái `active` dù ngày hết hạn đã qua. Phạm vi cư dân phải dựa vào thời gian hiệu lực thực tế. Không tự sửa lịch sử nguồn hoặc tự hợp nhất người khác tên.
- Bảng căn hộ gốc thiếu diện tích; migration bổ sung trường cho quản lý nhập. Giá trị diện tích trong fixture kiểm thử là dữ liệu thử, không khẳng định diện tích căn hộ nguồn.
- Tám dịch vụ dùng chung một tệp SQLite theo yêu cầu demo; trigger Billing tạo Maintenance ticket là ngoại lệ liên miền được giữ lại từ CSDL gốc. Việc ghi vẫn chịu giới hạn một writer của SQLite. Các danh sách hiện chưa phân trang.
- Khóa nội bộ hiện là bí mật chung giữa dịch vụ. Nếu triển khai ngoài môi trường demo, cần tách dữ liệu, phân quyền danh tính từng dịch vụ và bổ sung quản lý khóa phù hợp.
