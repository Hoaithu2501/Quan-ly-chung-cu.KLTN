# Bật API đối soát dự phòng SePay và kiểm thử tình huống lỗi

Áp dụng cho dự án QLCC đang chạy Docker, SePay Live, tài khoản MB đã liên kết. Luồng webhook đã thanh toán thành công hóa đơn #HD0019 ngày 07/11/2026. Các bước dưới đây bổ sung khả năng đọc giao dịch khi webhook chậm hoặc không đến.

**Kết quả ngày 07/11/2026:** bước 6 đã đạt Gateway/Webhook/API OK và cấu hình container khớp `.env`; bước 7 đạt **101 kiểm thử** trên database tạm. Chi tiết tại [VERIFICATION.md](VERIFICATION.md). Các lệnh bên dưới được giữ để kiểm tra lại khi thay đổi cấu hình hoặc source.

## 1. Phân biệt hai khóa

| Biến trong .env | Nguồn lấy | Mục đích |
| --- | --- | --- |
| SEPAY_WEBHOOK_API_KEY | Khóa đã điền khi tạo webhook QLCC Live | Kiểm tra thông báo SePay gửi vào web |
| SEPAY_API_TOKEN | Tạo trong API Access của SePay Live | Web gọi API SePay để đọc giao dịch |
| SEPAY_BANK_ACCOUNT_ID | Trường id của tài khoản trong API v2 | Giới hạn đối soát đúng tài khoản ngân hàng |

Giữ nguyên khóa webhook. Không dùng giá trị đó thay cho API Token. UUID tài khoản không phải số tài khoản MB và không phải mã `ba_...` trên URL dashboard.

## 2. Tạo API Token Live

1. Đăng nhập https://my.sepay.vn/ và kiểm tra **Test mode đang tắt**.
2. Vào **Cấu hình Công ty → API Access**; nếu giao diện có sẵn mục API Access thì mở trực tiếp mục đó.
3. Chọn **+ Thêm API**.
4. Tên: **QLCC doi soat Live**. Trạng thái: **Hoạt động**.
5. Chọn **Thêm**, sao chép token được cấp.

Đây là API Access cho tài khoản/giao dịch, không phải đăng ký sản phẩm Cổng thanh toán. Source chỉ dùng token cho yêu cầu đọc. SePay hiện không chia quyền chi tiết cho token này; lưu token ở `.env` của backend, không chép vào `.env.example` hoặc frontend.

Nguồn: [SePay hướng dẫn tạo API Token](https://docs.sepay.vn/tao-api-token.html).

## 3. Lấy UUID tài khoản bằng Postman

1. Mở Postman, tạo **HTTP Request**.
2. Chọn phương thức **GET** và URL:

   ```text
   https://userapi.sepay.vn/v2/bank-accounts
   ```

3. Trong tab **Authorization**, chọn **Bearer Token**. Ô Token chỉ dán token vừa tạo; Postman tự thêm chữ `Bearer`.
4. Trong tab **Params**, có thể thêm `q` với giá trị là số tài khoản MB của bạn để thu hẹp kết quả.
5. Bấm **Send**. Cần nhận **200 OK**, JSON có `status` là `success`, danh sách `data`.
6. Trong `data`, tìm tài khoản có `account_number` đúng tài khoản nhận tiền, chủ tài khoản và ngân hàng MB khớp. Sao chép **id của chính phần tử đó**.

`id` có dạng UUID gồm các nhóm ký tự phân cách bằng dấu gạch ngang. Dùng giá trị thực trong phản hồi, không lấy UUID ví dụ trong tài liệu. Nếu kết quả phân trang, xem trang tiếp theo hoặc dùng bộ lọc q để tìm đúng tài khoản.

Nguồn: [API danh sách tài khoản ngân hàng](https://developer.sepay.vn/vi/sepay-api/v2/tai-khoan-ngan-hang/danh-sach).

## 4. Điền đồng thời token và UUID vào .env

Mở `.env` ở thư mục gốc `D:\Downloads_new\QLCC`. Sửa hai dòng đã có, không thêm nhiều dòng trùng tên:

```dotenv
SEPAY_API_TOKEN=TOKEN_LIVE_VUA_TAO
SEPAY_BANK_ACCOUNT_ID=UUID_LAY_TU_API
```

Thay hai giá trị mẫu bằng giá trị thật. Giữ `SEPAY_ENV=live` cùng thông tin MB, tiền tố và webhook đã chạy được. Không lưu `Bearer ` ở đầu giá trị SEPAY_API_TOKEN.

Điền đủ cả hai trước khi nạp lại Docker. Nếu chỉ điền một biến, cấu hình thanh toán sẽ bị đánh dấu chưa sẵn sàng.

## 5. Kiểm tra trước khi nạp vào Docker

Trong PowerShell tại thư mục dự án:

```powershell
.\.venv\Scripts\python.exe scripts/check_sepay.py --check-api
```

Kết quả cần có:

```text
SEPAY_ENV: live
API đối soát: Đã cấu hình
API: OK, tài khoản đang hoạt động và khớp cấu hình.
```

Lệnh này đọc chi tiết tài khoản trên SePay; không tạo chuyển khoản và không ghi nhận thanh toán. Nếu chưa đạt, sửa cấu hình trước khi nạp lại billing. Chữ “Đã cấu hình” mới xác nhận đủ biến; cần dòng API OK mới xác nhận lần gọi chi tiết tài khoản thành công.

Để kiểm tra thêm khả năng đọc giao dịch, dùng cùng Bearer Token trong Postman, gửi GET:

```text
https://userapi.sepay.vn/v2/transactions
```

Trong Params, điền `bank_account_id` = UUID vừa lấy, `q` = `TTHD`. Tìm giao dịch Live 10.000đ đã thanh toán. Kiểm tra `account_number`, `amount_in`, `transaction_content`, `reference_number` khớp lịch sử chuyển khoản. Thao tác GET không tạo giao dịch mới.

Nguồn: [API danh sách giao dịch](https://developer.sepay.vn/vi/sepay-api/v2/giao-dich/danh-sach).

## 6. Nạp cấu hình và kiểm tra web

```powershell
docker compose up -d --no-deps --force-recreate --wait --wait-timeout 60 billing
.\.venv\Scripts\python.exe scripts/check_sepay.py --probe --check-api
```

Chỉ sửa `.env` không cần build lại image. `docker compose restart` không nạp biến môi trường mới. Nếu vừa khởi động mà gateway báo 503, chờ billing healthy rồi chạy lại lệnh kiểm tra.

Kết quả cần có gateway OK, webhook từ chối yêu cầu thiếu API Key và API tài khoản OK. Giữ tunnel hoạt động để kiểm tra webhook. Phản hồi 403 của bước probe không có API Key là kết quả đúng.

Source hiện có scheduler đối soát mỗi 60 giây khi `SCHEDULER_ENABLED=true` và không bị `DISABLE_SCHEDULER` tắt. Mỗi lượt xử lý một nhóm phiên; không bảo đảm mọi phiên được cập nhật trong đúng 60 giây. Nút **Kiểm tra trạng thái** trong phiên thanh toán cũng gọi đối soát.

Kiểm tra lại #HD0019: vẫn đã thanh toán, vẫn một khoản thu 10.000đ, không sinh thêm thông báo thành công chỉ vì API đọc lại giao dịch. Có thể xem log khi cần:

```powershell
docker compose logs --tail=80 billing
```

API tài khoản OK chưa đủ chứng minh đã phục hồi được một webhook bị mất. Cần kiểm thử logic ở bước 7; nếu muốn nghiệm thu với SePay bên ngoài, dùng một môi trường Test riêng.

## 7. Kiểm thử webhook chậm/lặp, thiếu/dư trên database tạm

Bộ test có sẵn tạo bản sao SQLite trong thư mục tạm, cấu hình SePay giả lập và không gọi ngân hàng để chuyển tiền. Không đổi `.env` Live sang Test để chạy bộ này.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_billing.py tests/test_sepay_check.py -q
```

Kết quả cần có các ca passed, không có failed/error. Các nhánh chính:

| Tình huống | Kết quả cần đạt |
| --- | --- |
| Webhook chưa tới nhưng API thấy tiền | Đối soát xác nhận hóa đơn đủ tiền |
| API xác nhận trước, webhook đến sau | Một khoản thu, một lần ghi nhận giao dịch |
| Cùng webhook được gửi lại | Không tăng tiền đã thu hoặc lặp thông báo |
| Hai thành viên cùng mở hóa đơn | Một phiên giữ quyền hiển thị QR |
| Hóa đơn 10.000đ nhận 4.000đ | Chưa paid; còn nợ 6.000đ |
| Nhận thêm 6.000đ bằng giao dịch khác | Đủ 10.000đ; một khoản thu hóa đơn |
| Nhận 12.000đ cho hóa đơn 10.000đ | Phân bổ 10.000đ; dư 2.000đ để BQL xử lý |
| Chuyển đủ lần nữa bằng giao dịch khác | Không thu hóa đơn lần hai; khoản mới cần đối soát |
| API lỗi mạng hoặc dữ liệu không khớp | Không tự ghi paid, không mất khoản đã xác minh |

Số tiền trong bảng là ví dụ về kết quả nghiệp vụ; từng ca tự động có thể dùng số tiền khác. Kiểm thử tự động không thay thế xác minh token/API Live ở bước 5–6.

## 8. Nếu muốn thử qua SePay Test thật

Dùng bản ứng dụng và database Test riêng với tài khoản ngân hàng Test, token/UUID Test và webhook trỏ tới bản Test; không gửi payload giả lập vào endpoint Live đang phục vụ hóa đơn thật.

Theo [TEST_THANH_TOAN_HOA_DON.md](TEST_THANH_TOAN_HOA_DON.md), tạo một hóa đơn mới cho từng kịch bản. Với ca thiếu tiền, mô phỏng 4.000đ rồi 6.000đ, giữ đúng mã TTHD của phiên và hai giao dịch có ID khác nhau. Với ca lặp, gửi lại cùng webhook từ lịch sử; không tạo giao dịch mới vì đó là ca chuyển tiền lần hai. Với ca mất webhook, tạm tắt webhook Test, mô phỏng khoản đủ tiền rồi đối soát bằng API Test; bật lại và gửi webhook cũ để kiểm tra không ghi trùng.

## Lỗi thường gặp

| Hiện tượng | Cách kiểm tra |
| --- | --- |
| API trả 401 | Token có hoạt động không, có nhầm token Test hoặc khóa webhook không; Bearer Token đúng chưa |
| API trả 403 | Đọc thông báo lỗi từ SePay, kiểm tra quyền/gói dịch vụ với SePay; không bỏ kiểm tra xác thực trong source |
| Báo UUID không hợp lệ | Lấy trường id từ API v2, không dùng số tài khoản hoặc mã ba_ trên dashboard |
| Tài khoản không khớp | Đối chiếu UUID, số tài khoản, tên chủ, ngân hàng và trạng thái hoạt động |
| API trả 429 | Chờ theo Retry-After rồi thử lại, không bấm gửi liên tục |
| API đọc được nhưng webhook không kết nối | Kiểm tra tunnel, DNS và URL; hai đường kết nối độc lập |
| Không tìm thấy giao dịch | Kiểm tra đúng môi trường, UUID, nội dung và giao dịch đã xuất hiện trên SePay chưa |

Tham khảo: [Xác thực và giới hạn API](https://developer.sepay.vn/vi/sepay-api/v2/xac-thuc).
