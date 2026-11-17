# Kiểm thử hệ thống

## Giao diện Tailwind CSS

Sau khi sửa markup hoặc CSS, biên dịch trước khi chạy kiểm thử trình duyệt:

```powershell
npm ci
npm run build:css
node --check frontend/app.js
```

`npm ci` chỉ cần chạy khi chưa cài dependencies hoặc `package-lock.json` thay đổi. Khi phát triển, dùng `npm run watch:css` để tự biên dịch sau mỗi lần lưu.

## Thanh toán VietQR và SePay (06/11/2026)

Các ca Billing kiểm tra xác thực webhook, đối chiếu đúng tài khoản/ngân hàng/mã chuyển khoản, API v2 dự phòng và scheduler. Bao gồm hai thành viên cùng mở phiên, webhook gửi lặp, hai giao dịch ngân hàng khác nhau, tiền thiếu/dư và tiền về sau khi QR hết phiên. Test dùng database riêng và phản hồi nhà cung cấp giả lập, không chuyển tiền.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_billing.py tests/test_billing_http.py tests/test_billing_household_regressions.py tests/test_sepay_check.py -q
$env:RUN_BROWSER_TESTS='1'
.\.venv\Scripts\python.exe -m pytest tests/test_browser.py -k 'sepay or admin_creation_and_resident_payment' -q
Remove-Item Env:RUN_BROWSER_TESTS
```

Browser kiểm tra người giữ phiên mới được xem QR, nút báo đã chuyển không tự ghi đã thanh toán, cập nhật QR theo phần còn thiếu, cảnh báo Test/Live, biên nhận và sổ đối soát BQL. Nghiệm thu đầu cuối với tài khoản SePay riêng theo [TEST_THANH_TOAN_HOA_DON.md](TEST_THANH_TOAN_HOA_DON.md).

## Chạy bộ kiểm thử

Chạy từ thư mục dự án sau khi cài dependencies:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Chạy riêng kiểm thử năm dịch vụ nghiệp vụ:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_domains.py -q
```

Chạy riêng kiểm thử bảo mật và độ ổn định (giới hạn đăng nhập, thu hồi phiên, quyền căn hộ, mở khóa phiên thanh toán, sao lưu):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_security_regressions.py -q
```

## Cách cô lập dữ liệu

Kiểm thử trình duyệt (tùy chọn, cần Chrome/Edge hoặc Chromium của Playwright):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:RUN_BROWSER_TESTS='1'
.\.venv\Scripts\python.exe -m pytest tests/test_browser.py -q
Remove-Item Env:RUN_BROWSER_TESTS
```

Test tự dùng Chrome/Edge đã cài trên Windows. Nếu không có, chạy `python -m playwright install chromium` bằng Python của `.venv`, hoặc đặt `BROWSER_EXECUTABLE` đến trình duyệt tương thích. Các ca bao gồm đăng ký/cập nhật hồ sơ/đổi mật khẩu, điều hướng từng vai trò, chatbot, bố cục/menu di động, cỡ chữ tối thiểu và vùng an toàn iPhone ở màn hình 390 px, tạo căn hộ/hóa đơn, cư dân thanh toán và tải biên nhận với phản hồi SePay giả lập. Các ca bổ sung kiểm tra điện thoại bắt buộc, giữ đơn gửi xe khi đóng nội quy, chuyển thẳng sang đơn khi chọn Đăng ký thủ tục và giữ nội dung trong lúc chuyển tab. Các ca này dùng DB tạm riêng, không lưu ảnh chụp màn hình và được bỏ qua trong lệnh pytest mặc định.

Fixture `service_cluster` trong `tests/conftest.py` dựng SQLite từ dữ liệu mẫu `tests/fixtures/demo.sql` trong thư mục tạm của từng test, áp dụng migrations và bổ sung diện tích kiểm thử. Tám Flask app chạy trên tám cổng HTTP ngẫu nhiên. Các dịch vụ xác thực và gọi nhau bằng `requests` thật. Không cần khởi động stack đang sử dụng và không thay đổi dữ liệu mẫu gốc.

Tài khoản kiểm thử lấy từ dữ liệu nguồn: quản lý ID 1, cư dân ID 3, kỹ thuật viên ID 11. Mật khẩu trong bản sao là `TestPassword!2026`; đây không phải mật khẩu triển khai. Firebase bị tắt trong fixture để không phát thông báo ra ngoài. Webhook và API SePay được giả lập riêng trong các test tự động.

Fixture trả `urls`, `apps`, `modules`, `db_path`, `password`, `headers`, `call`. Ví dụ:

```python
def test_example(service_cluster):
    result = service_cluster.call(
        "parking", "/api/parking/vehicles", role="resident"
    )
    assert result.status_code == 200
```

## Ma trận kiểm thử nghiệp vụ

| Mã | Tình huống | Kết quả cần đạt | Tự động |
| --- | --- | --- | --- |
| PK-01 | Cư dân xem xe và cố đăng ký xe bằng API quản lý | Chỉ thấy xe căn hộ mình; POST bị 403 | Có |
| PK-02 | Đăng ký hai xe đang hoạt động cùng biển số | Lần thứ hai bị 409 | Có |
| PK-03 | Hai yêu cầu đăng ký cùng biển số chạy đồng thời | Một 201, một 409; không trùng bản ghi | Có |
| PK-04 | Billing truy vấn tổng phí xe của căn hộ bằng khóa nội bộ | Trả tổng phí tháng thực tế, chỉ xe `active` | Có |
| PK-05 | Nhập doanh thu vãng lai cùng một ngày hai lần | Một bản ghi; lần sau 409, sửa qua PUT | Có |
| PK-06 | Doanh thu âm hoặc ngày tương lai; cư dân đọc sổ | Dữ liệu sai bị 400, cư dân bị 403 | Có |
| PK-07 | Đăng ký lại xe từng có dữ liệu (cùng biển số dù viết khác, hoặc mã xe đạp cũ) | Không thu lại phí làm thẻ 100.000 VNĐ; biển số đang hoạt động bị 409 | Có |
| BL-01 | Lập hoặc sửa hóa đơn có hạn thanh toán đã qua | Hóa đơn chuyển Quá hạn ngay, không chờ lượt quét 00:05 | Có |
| BL-02 | Mở chi tiết hóa đơn dịch vụ 6 tháng có phí gửi xe | Từng xe: số tháng đăng ký, ngày đăng ký, ngày hết hạn, số tháng tính phí, phí làm thẻ | Có |
| BL-03 | Kỹ thuật viên mở Quản lý hóa đơn | Cùng màn hình và quyền với quản lý: lập, sửa, ghi nhận thu đủ tiền một lần, mở khóa phiên, đối soát; nhật ký ghi tên kỹ thuật viên; báo cáo vẫn 403 | Có |
| MT-01 | Kỹ thuật viên sửa nội dung phiếu | 403, phiếu giữ nguyên; chỉ được đổi trạng thái | Có |
| MT-02 | Nhảy từ chờ sang hoàn tất hoặc mở lại phiếu đã đóng | 409; chỉ cho chờ → đang xử lý → hoàn tất | Có |
| MT-03 | Kỹ thuật viên không được phân công mở và cập nhật phiếu | Thấy và cập nhật được; người nhận phiếu chưa phân công thành người phụ trách | Có |
| MT-04 | Kỹ thuật viên cắt một dịch vụ của hóa đơn quá hạn | Cư dân, Ban quản lý, kỹ thuật viên nhận thông báo; chi tiết hóa đơn hiện đã cắt | Có |
| MT-05 | Cư dân thanh toán hóa đơn đã bị cắt dịch vụ | Kỹ thuật viên được báo cần cấp lại; chi tiết hóa đơn hiện chưa cấp lại | Có |
| MT-06 | Cắt lại dịch vụ đã cắt, hoặc cấp lại khi chưa thanh toán | 409, không đổi trạng thái | Có |
| NT-01 | Cư dân khác xem hoặc đánh dấu đọc thông báo riêng | Không xuất hiện trong danh sách; POST đọc trả 403 | Có |
| NT-02 | Cư dân đánh dấu đọc cùng thông báo hai lần | Một nhật ký, trạng thái đã đọc | Có |
| NT-03 | Billing tạo báo cáo chỉ gửi quản lý | Cư dân không nhìn thấy; gửi lại event không trùng | Có |
| NT-04 | Chưa cấu hình Firebase | Lưu thông báo, `push.configured=false`, không giả báo đã gửi | Có |
| NT-05 | Kỹ thuật viên soạn thông báo | Không có nút Soạn thông báo; API trả 403 | Có |
| CP-01 | Cư dân tạo đơn dùng `resident_id` người khác | 403 | Có |
| CP-02 | Quản lý giải quyết đơn thiếu phản hồi | 400; có phản hồi thì ghi thời điểm đóng | Có |
| CB-01 | Hỏi nội quy bằng tiếng Việt không dấu | So khớp đúng câu trả lời trong kho | Có |
| CB-02 | Hỏi vị trí hiệu thuốc | Trả danh bạ địa điểm, kèm nguồn | Có |
| CB-03 | Câu hỏi ngoài kho kiến thức | `matched=false`, không tạo câu trả lời không có nguồn | Có |
| E2E-01 | Xe → phí 6 tháng → quá hạn → thanh toán | Liên dịch vụ qua HTTP, tổng tiền và trạng thái đúng, không tạo phiếu sửa chữa | Có, `test_billing_http.py` |
| UI-01 | Ba tài khoản đăng nhập trên giao diện | Menu, dữ liệu và chatbot phù hợp vai trò; menu di động mở/đóng đúng | Có, bật `RUN_BROWSER_TESTS=1` |
| UI-02 | Quản trị tạo căn hộ/hóa đơn, cư dân thanh toán và tải biên nhận | Hóa đơn đổi sang đã trả, tải được ảnh PNG, không phát sinh lỗi JavaScript | Có, bật `RUN_BROWSER_TESTS=1` |
| FCM-01 | Hai trình duyệt cho phép thông báo, gửi thông báo chung/riêng | Đúng người nhận, kiểm tra cả foreground/background | Cần Firebase thật |
| SEPAY-01 | Mô phỏng tiền vào trên SePay Test và webhook công khai | Khóa hợp lệ, đúng người nhận/mã/số tiền; webhook lặp không thu lần hai | Cần cấu hình SePay Test của người triển khai |

## Kiểm tra thủ công khi nghiệm thu

1. Đăng nhập lần lượt ba vai trò. Tài khoản cư dân phải có hồ sơ và hợp đồng hiệu lực trước khi truy cập dữ liệu căn hộ.
2. Quản lý tạo căn hộ, hợp đồng, xe và hóa đơn; kiểm tra hóa đơn 6 tháng lấy đúng phí tháng nhân sáu. Hủy xe rồi tạo kỳ mới để xác nhận không cộng phí xe đã hủy.
3. Cư dân tạo khiếu nại/đơn đăng ký; quản lý phản hồi và đóng. Với đăng ký gửi xe, tạo đăng ký xe tại phân hệ Gửi xe sau khi duyệt.
4. Tạo phiếu sửa chữa, phân công kỹ thuật viên; đăng nhập một kỹ thuật viên bất kỳ, nhận và hoàn thành phiếu. Kiểm tra cư dân, Ban quản lý và kỹ thuật viên đều nhận thông báo khi trạng thái đổi.
5. Tạo hóa đơn có hạn thanh toán đã qua: hóa đơn hiện Quá hạn ngay. Đăng nhập kỹ thuật viên, cắt dịch vụ tại Quản lý dịch vụ; thanh toán hóa đơn rồi cấp lại, kiểm tra trạng thái trong chi tiết hóa đơn.
6. Gửi thông báo riêng cho một căn hộ và riêng cho quản lý. Đăng nhập cư dân khác kiểm tra không thấy; đánh dấu đã đọc và tải lại trang.
7. Nếu dùng Firebase thật, cấu hình server và web, cho phép thông báo trên HTTPS/localhost; kiểm tra từ hai tài khoản khác nhau. Khi thiếu credentials hoặc nhà cung cấp lỗi, kiểm tra thông báo vẫn nằm trong hộp thư.
8. Hỏi chatbot các câu nội quy, địa điểm, câu không dấu và câu ngoài phạm vi. Trả lời phải có nguồn dữ liệu hoặc nêu chưa tìm thấy. Phản hồi nhà cung cấp LLM trong test được giả lập.

## Giới hạn xác nhận

Bộ test xác minh nghiệp vụ, phân quyền, chống xử lý trùng và HTTP liên dịch vụ trên máy cục bộ. Nó không thay thế thử tải, kiểm tra bảo mật production, thử Firebase trên thiết bị thật hoặc giao dịch từ SePay Test/Live. Các trường hợp cần dịch vụ bên ngoài phải được nghiệm thu sau khi có credentials và cấu hình webhook thích hợp.
