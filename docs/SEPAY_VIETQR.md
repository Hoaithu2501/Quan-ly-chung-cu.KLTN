# Thiết lập VietQR và SePay cho QLCC

Bắt đầu bằng SePay Test Mode để thử toàn bộ luồng mà không chuyển tiền. Mã nguồn đã có tích hợp; cần điền thông tin tài khoản và webhook của bạn vào .env để bật thanh toán.

## 1. Tạo tài khoản ngân hàng Test

1. Đăng nhập [my.sepay.vn](https://my.sepay.vn/), bật **Test Mode**.
2. Vào **Test mode → Tài khoản ngân hàng → Thêm tài khoản**, chọn tạo mới trong Test Mode.
3. Chọn **MBBank** hoặc Vietcombank. Máy này đang dùng tài khoản MBBank Test bạn đã tạo. Ghi lại ngân hàng, số tài khoản và tên chủ tài khoản mà SePay cấp.
4. Không sao chép tài khoản Live hoặc dùng tài khoản cá nhân thật cho lần thử đầu tiên.

Tài khoản tạo mới trong Test Mode có thông tin riêng. Hướng dẫn chính thức: [tạo tài khoản ngân hàng Test](https://developer.sepay.vn/vi/tien-ich-khac/test-mode/tai-khoan-ngan-hang).

SEPAY_ENV=test chỉ chọn nguồn dữ liệu phía server; nó không thể chặn một ứng dụng ngân hàng chuyển tiền nếu bạn đưa tài khoản nhận thật vào QR. Trong Test Mode, chỉ dùng các chức năng mô phỏng của SePay.

Một số ngân hàng yêu cầu tài khoản ảo VA hoặc quy tắc nội dung riêng. Bản hiện tại dùng tài khoản nhận trực tiếp và chặn cấu hình OCB, KienLongBank, MSB, BIDV, VietinBank vì chưa triển khai các nhánh VA/loại tài khoản/nội dung đặc thù. Đây là giới hạn của source hiện tại, không phải SePay không hỗ trợ các ngân hàng này. Demo trước bằng Vietcombank Test. [Quy tắc QR theo ngân hàng](https://developer.sepay.vn/vi/tien-ich-khac/tao-qr-code).

## 2. Tạo khóa bảo vệ webhook

File .env của máy này đã được tạo khóa riêng tại SEPAY_WEBHOOK_API_KEY. Mở file và sao chép giá trị đó vào webhook SePay. Khi cài mới, scripts/init_db.py cũng tự tạo khóa nếu chưa có. Chỉ khi cần đổi khóa, có thể tự sinh tại máy:

~~~powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
~~~

Dùng cùng giá trị này tại SEPAY_WEBHOOK_API_KEY trong .env và mục API Key của webhook SePay. Đây là khóa nhận webhook; **khác** token API Access dùng để đọc giao dịch.

Chỉ sao chép khóa vào mục API Key của webhook trên SePay. Không đưa khóa vào mã frontend, ảnh chụp màn hình hoặc file hướng dẫn.

## 3. Mở đường nhận webhook

QLCC chạy tại localhost:5000; SePay cần URL HTTPS công khai trỏ đến gateway. Nếu đã có tunnel đang chạy, dùng URL hiện tại. Nếu dùng Cloudflare:

~~~powershell
cloudflared tunnel --url http://localhost:5000 --protocol http2
~~~

Giữ tiến trình tunnel chạy. Lấy URL HTTPS được in ra và ghép đường dẫn:

~~~text
https://TEN-TUNNEL.trycloudflare.com/api/billing/sepay/webhook
~~~

Quick tunnel có thể đổi tên khi chạy lại. Khi đổi, sửa cả .env và URL webhook trên SePay. Không thêm đăng nhập Basic Auth hoặc trang xác nhận trước đường dẫn webhook.

Lấy URL từ cửa sổ cloudflared đang chạy và đồng bộ vào SEPAY_WEBHOOK_URL; không sao chép tên miền của lần chạy trước từ ảnh chụp hoặc lịch sử trò chuyện. Nếu SePay báo tên miền không phân giải được DNS, kiểm tra tunnel hiện tại và thay URL ở cả hai nơi. Tiến trình còn xuất hiện trên máy cũng chưa bảo đảm tunnel còn hoạt động: log `Tunnel not found` nghĩa là phải dùng tunnel mới.

Chạy `scripts/check_sepay.py --probe` để kiểm tra gateway và đường webhook. Webhook trả 403 cho yêu cầu không có API Key là đúng ở bước kiểm tra này; chưa chứng minh SePay đã gửi giao dịch thành công.

## 4. Điền .env

Giữ JWT, SERVICE_TOKEN và các cấu hình khác hiện có. Điền thông tin Test vừa tạo:

~~~dotenv
PAYMENT_MODE=sepay
SEPAY_ENV=test
SEPAY_BANK_CODE=MB
SEPAY_BANK_NAME=MBBank
SEPAY_ACCOUNT_NUMBER=SO_TAI_KHOAN_TEST_SEPAY_CAP
SEPAY_ACCOUNT_NAME=TEN_CHU_TAI_KHOAN_TEST
SEPAY_WEBHOOK_API_KEY=KHOA_BI_MAT_TOI_THIEU_32_KY_TU
SEPAY_WEBHOOK_URL=https://TEN-TUNNEL.trycloudflare.com/api/billing/sepay/webhook
SEPAY_PAYMENT_PREFIX=TTHD
SEPAY_PAYMENT_WINDOW_MINUTES=15

# Tùy chọn, để trống cả hai nếu chưa sử dụng API đọc giao dịch:
SEPAY_API_TOKEN=
SEPAY_BANK_ACCOUNT_ID=
~~~

Thay các giá trị viết hoa bằng dữ liệu của bạn. SEPAY_BANK_NAME phải khớp tên ngân hàng trong payload gateway của SePay: MBBank; SEPAY_BANK_CODE là mã dùng cho ảnh QR: MB. Giữ nguyên các số 0 ở đầu số tài khoản.

Trên máy này, thông tin tài khoản MBBank Test và tiền tố TTHD đã được điền vào .env và nạp trong Billing. Webhook QLCC Test đã hoạt động: ngày 06/11/2026, hóa đơn #HD0018 của A101 nhận đủ 15.000đ qua giao dịch mô phỏng, ghi nhận thanh toán đúng một lần và hiển thị thông báo cho cư dân/BQL. Xem bằng chứng tại [VERIFICATION.md](VERIFICATION.md). Luồng này dùng tiền thử nghiệm, chưa nghiệm thu Live. Các lần thử tiếp theo làm theo [TEST_THANH_TOAN_HOA_DON.md](TEST_THANH_TOAN_HOA_DON.md); chưa cần tạo tài khoản ảo VA hoặc API token để thử luồng webhook.

Billing đã được tạo lại để nạp cấu hình. Docker dùng tên mặc định qlcc-billing-1 và qlcc-gateway-1; docker-compose.yml không đặt container_name theo số cổng.

Không dùng lại khóa MoMo. Không thêm .env vào Git. Nếu chỉ có tài khoản SePay mà chưa có ngân hàng/webhook thì thanh toán vẫn được khóa để tránh tạo QR sai.

## 5. Tạo webhook trên SePay

Trong **Test mode → Tích hợp Webhook → Thêm webhook**:

| Mục | Cấu hình cho QLCC |
| --- | --- |
| Tên | QLCC Test |
| URL | Trùng SEPAY_WEBHOOK_URL |
| Loại giao dịch | Tiền vào |
| Định dạng | JSON |
| Tài khoản | Chỉ tài khoản Test vừa điền trong .env |
| Bảo mật | API Key |
| API Key | Trùng SEPAY_WEBHOOK_API_KEY |
| Gửi lại khi HTTP lỗi | Bật để hỗ trợ khi web tạm gián đoạn |

Chưa bật lọc **Chỉ gửi khi có mã thanh toán** nếu muốn web nhận cả khoản sai nội dung để BQL kiểm tra. Nếu bật lọc, các khoản không khớp mã có thể không tới web.

Ở **Test mode → Cấu hình**, bật nhận diện mã thanh toán; thêm cấu trúc tiền tố **TTHD**, độ dài hậu tố tối thiểu **12**, tối đa **12**, loại **Số và chữ**, trạng thái **Đang hoạt động**, rồi lưu. Không chọn Số nguyên vì web tạo mã gồm cả chữ A–F và chữ số. Server cũng đọc mã từ nội dung chuyển khoản; cư dân cần giữ nguyên nội dung do hóa đơn cấp.

Đổi tiền tố chỉ áp dụng cho phiên mới. Phiên cũ vẫn giữ nguyên mã đã cấp và được đối soát khi tiền đến trễ. Trên SePay, để trống bộ lọc mã thanh toán để tiếp nhận cả mã cũ và khoản cần BQL kiểm tra.

Source hiện nhận **Authorization: Apikey ...**; không chọn Không xác thực hoặc HMAC cho cấu hình này. [Hướng dẫn webhook Test](https://developer.sepay.vn/vi/tien-ich-khac/test-mode/tao-webhook), [cấu hình mã thanh toán](https://developer.sepay.vn/vi/tien-ich-khac/test-mode/cau-hinh).

## 6. Nạp cấu hình vào Docker

Từ thư mục dự án:

~~~powershell
docker compose build db-init billing gateway
docker compose run --rm --no-deps db-init python -c "from scripts.init_db import initialize; initialize(demo=False)"
docker compose up -d --no-deps --force-recreate billing gateway
~~~

Các lệnh này cập nhật schema bằng migration và giữ volume dữ liệu. Sao lưu database trước khi nâng cấp. Không dùng down -v hoặc xóa volume để cập nhật thanh toán. Nếu chỉ sửa .env sau khi đã nâng cấp, chỉ cần lệnh up cuối cùng; docker compose restart không nạp lại biến môi trường đã đổi.

Kiểm tra cấu hình mà không tạo giao dịch:

~~~powershell
.\.venv\Scripts\python.exe scripts/check_sepay.py --probe
# Khi đã cấu hình token API và UUID tài khoản:
.\.venv\Scripts\python.exe scripts/check_sepay.py --probe --check-api
~~~

Dùng Ctrl+F5 tải lại web. Khi cấu hình đầy đủ, phần hóa đơn có nhãn **VietQR · SePay Test**, nút thanh toán của cư dân được bật. Nếu chưa sẵn sàng, kiểm tra biến thiếu, URL HTTPS, tên ngân hàng, độ dài khóa và log Billing:

~~~powershell
docker compose logs --tail=100 billing gateway
~~~

Tài khoản cần được BQL xác nhận vào đúng căn hộ; chỉ nhập mã căn hộ khi đăng ký chưa đủ quyền xem hóa đơn.

## 7. API đối soát dự phòng, tùy chọn

Với cấu hình Live đã thanh toán thành công, làm theo [hướng dẫn chi tiết tạo token, lấy UUID và kiểm thử dự phòng](SEPAY_DOI_SOAT_DU_PHONG.md).

Webhook đủ để chạy luồng cơ bản. Nếu muốn nút **Kiểm tra trạng thái** đọc giao dịch trực tiếp từ SePay khi callback chậm, vào **Test mode → API Access**, tạo token của Test Mode và lấy UUID tài khoản ngân hàng theo API v2. Điền đồng thời:

~~~dotenv
SEPAY_API_TOKEN=TOKEN_TEST_CUA_BAN
SEPAY_BANK_ACCOUNT_ID=UUID_TAI_KHOAN_TEST
~~~

UUID là định danh API v2, không phải số tài khoản, số thứ tự trên bảng hoặc đoạn ba_... trên URL trang quản lý. Nạp lại Billing sau khi sửa. Nếu chỉ điền một trong hai, hệ thống báo chưa sẵn sàng.

Server chọn userapi-sandbox.sepay.vn/v2 khi Test, userapi.sepay.vn/v2 khi Live. Token hai môi trường không dùng chung. [API Access Test](https://developer.sepay.vn/vi/tien-ich-khac/test-mode/api-access).

Không có token thì **Kiểm tra trạng thái** chỉ đọc dữ liệu web đã nhận; nó không tự xác nhận chuyển khoản hoặc thay thế một webhook bị cấu hình sai.

## 8. Kiểm thử và chuyển Live

Thực hiện [hướng dẫn test hóa đơn](TEST_THANH_TOAN_HOA_DON.md). Trong Test Mode, có thể dùng trang mô phỏng giao dịch hoặc mô phỏng QR của SePay để phát sinh webhook.

Khi cần tiền thật, kết nối ngân hàng Live, tạo webhook Live, cập nhật tài khoản nhận, đồng bộ khóa bảo mật với webhook và đặt SEPAY_ENV=live. Token Live chỉ cần khi bật API đối soát dự phòng. Đối soát các phiên đang chờ trước khi đổi môi trường. Đổi ENV không đổi một giao dịch Test thành tiền thật.

Giao diện Live cho phép quét bằng ứng dụng ngân hàng; BQL cần quy trình hoàn tiền thừa và kiểm tra thực nhận. Source chỉ lưu ghi chú xử lý, không tự hoàn tiền. Kết quả Test không thay thế việc cấu hình và nghiệm thu giao dịch Live.

### MB Live: không cần thêm tài khoản ảo

Với MB kết nối API Banking, SePay mặc định nhận biến động tại tài khoản chính. Source dùng số tài khoản chính và nội dung `TTHD` kèm 12 ký tự chữ/số để xác định hóa đơn; không cần tạo tài khoản ảo VA. [Hướng dẫn MB của SePay](https://docs.sepay.vn/ket-noi-mb-api.html).

Sau khi tạo webhook Live:

1. Trong **Live → Cấu hình mã thanh toán**, bật tiền tố `TTHD`, hậu tố đúng **12** ký tự, loại **Số và chữ**. Chọn đúng tài khoản MB thật trong webhook, chỉ nhận tiền vào, JSON, API Key trùng `.env`, bật gửi lại khi lỗi. Tắt webhook Test nếu còn trỏ cùng URL.
2. Trong `.env`, đặt `SEPAY_ENV=live`, `SEPAY_BANK_CODE=MB`, `SEPAY_BANK_NAME=MBBank`; điền số tài khoản thật và tên chủ tài khoản. Giữ `SEPAY_PAYMENT_PREFIX=TTHD`, đồng bộ `SEPAY_WEBHOOK_URL` với tunnel đang chạy. File `.env.example` chỉ là mẫu cài đặt, không chứa thông tin tài khoản/khóa riêng.
3. Nạp lại cấu hình và kiểm tra:

   ~~~powershell
   docker compose up -d --no-deps --force-recreate billing
   .\.venv\Scripts\python.exe scripts/check_sepay.py --probe
   ~~~

4. BQL lập **hóa đơn mới** để thử, chọn kỳ chưa có hóa đơn: điện 4 kWh × 2.000đ và nước 0,2 m³ × 10.000đ, tổng **10.000đ**. Đây là số liệu thử, không phải biểu giá điện/nước. Không dùng lại hóa đơn Test đã thanh toán.
5. Cư dân tải lại trang bằng Ctrl+F5, mở hóa đơn mới và bấm **Thanh toán VietQR**. Kiểm tra nhãn Live và người nhận. Dùng tài khoản ngân hàng khác quét **QR do hóa đơn trên web cấp**, giữ nguyên số tiền và nội dung `TTHD...`, chuyển một lần. QR tĩnh trên trang ngân hàng SePay không gắn với hóa đơn của web.
6. Kiểm tra tiền thực nhận ở MB, giao dịch và lịch sử gửi webhook trong SePay Live, rồi đối chiếu hóa đơn đã trả, thời gian thanh toán, một khoản thu và thông báo có căn hộ cho cư dân/BQL. Khi đã chuyển mà web chưa cập nhật, kiểm tra webhook hoặc đối soát; không chuyển lại.

Token API không bắt buộc cho luồng webhook. Để bật đối soát dự phòng, tạo token trong **API Access của Live**, lấy UUID tài khoản tương ứng từ API v2 `GET https://userapi.sepay.vn/v2/bank-accounts`, rồi điền đồng thời `SEPAY_API_TOKEN` và `SEPAY_BANK_ACCOUNT_ID`. UUID là trường `id`, không phải số tài khoản. Nạp lại billing và chạy `scripts/check_sepay.py --probe --check-api`. Xem [API danh sách tài khoản](https://developer.sepay.vn/vi/sepay-api/v2/tai-khoan-ngan-hang/danh-sach).
