# Hướng dẫn test thanh toán hóa đơn bằng VietQR và SePay

File này đọc trực tiếp trong VS Code bằng Ctrl+Shift+V.

## 1. Chọn đúng cách kiểm thử

**Lần đầu dùng SePay Test Mode, không chuyển tiền thật.**

- Đặt SEPAY_ENV=test.
- Tạo tài khoản ngân hàng mới trong SePay Test, webhook JSON/API Key và URL tunnel HTTPS.
- Điền thông tin vào .env, nạp lại Billing; xem [hướng dẫn thiết lập](GETTING_STARTED.md#6-kết-nối-sepay-và-firebase).
- Dùng hóa đơn riêng cho việc demo. Thanh toán Test vẫn cập nhật trạng thái hóa đơn trong database ứng dụng, nên không dùng hóa đơn công nợ thật đang vận hành.

Test Mode của SePay có mô phỏng QR và giao dịch tại dashboard. Không dùng ứng dụng ngân hàng thật để thử QR Test. Nếu nhập tài khoản ngân hàng thật vào cấu hình, nhãn test trong .env không ngăn được ứng dụng ngân hàng chuyển tiền thật.

## 2. Kiểm tra Docker và web

Mở PowerShell tại thư mục QLCC:

~~~powershell
docker compose ps
~~~

Đăng nhập web tại http://localhost:5000. Hệ thống phải truy cập được các chức năng thông thường. Trong phần hóa đơn, cư dân thấy nhãn **VietQR · SePay Test**. Nếu nút Thanh toán VietQR bị khóa hoặc báo thiếu cấu hình, hoàn tất các bước trong [hướng dẫn thiết lập](GETTING_STARTED.md#6-kết-nối-sepay-và-firebase), không sửa database để bỏ khóa.

Giữ tunnel HTTPS hoạt động để SePay gửi webhook. URL tunnel đổi thì cập nhật trên SePay và .env rồi tạo lại container Billing.

## 3. BQL xác nhận thành viên và tạo hóa đơn Test

1. Đăng nhập tài khoản BQL.
2. Mở **Cư dân & hợp đồng**, kiểm tra người sẽ thử đã có căn hộ đúng theo hợp đồng hoặc mục **Xác nhận căn hộ**.
3. Vào **Quản lý hóa đơn → Điện & nước hàng tháng → Lập hóa đơn**.
4. Chọn căn hộ thử, kỳ chưa có hóa đơn. Nhập điện **4 kWh**, đơn giá **2.000 VNĐ/kWh**; nước **0,2 m³**, đơn giá **10.000 VNĐ/m³**. Đây là số liệu thử; xem trước tổng **10.000đ**, chọn hạn thanh toán rồi phát hành hóa đơn.
5. Ghi lại mã hóa đơn và căn hộ.

BQL chỉ quản lý hoặc ghi nhận khoản đã thực nhận. Kỹ thuật viên dùng chung màn Quản lý hóa đơn và các quyền này với BQL, nên các bước về hóa đơn (lập, ghi nhận thu, mở khóa phiên, đối soát) cũng làm được bằng tài khoản kỹ thuật viên; xác nhận thành viên căn hộ vẫn do BQL. Không có nút thanh toán online thay cư dân. Mọi thành viên đã được xác nhận trong căn hộ đều có quyền bắt đầu thanh toán hóa đơn chung.

## 4. Cư dân mở phiên thanh toán

1. Đăng xuất BQL, đăng nhập cư dân của căn hộ vừa chọn.
2. Mở **Hóa đơn & thanh toán**, tìm đúng kỳ và số tiền.
3. Mở chi tiết rồi bấm **Thanh toán VietQR**.
4. Kiểm tra nhãn Test, số tiền, ngân hàng, số tài khoản và **Nội dung chuyển khoản**.
5. Giữ hộp thoại mở; ghi lại nguyên nội dung chuyển khoản do web tạo, dạng TTHD kèm 12 ký tự chữ và số theo cấu hình hiện tại. Phiên cũ có thể còn tiền tố QLCC; không tự sửa mã của phiên.

Đồng hồ **Thời gian giữ phiên** mặc định 15 phút chỉ giữ quyền hiển thị QR cho một thành viên; không phải ngày hạn hóa đơn và không vô hiệu hóa QR đã chụp. Nếu đã chuyển tiền, đừng mở phiên khác.

## 5. Tạo giao dịch trên SePay Test

Mở SePay bằng tab khác, vẫn ở Test Mode. Có hai cách:

Với cấu hình hiện tại, chọn tài khoản **MBBank Test 0000000001**, chủ tài khoản **TRAN HOAI THU**; để trống VA. Kiểm tra cấu trúc mã TTHD có hậu tố **12 đến 12 ký tự**, loại **Số và chữ**. Không tự đặt mã khác với mã của phiên đang mở trên web.

| Cách | Thao tác |
| --- | --- |
| Mô phỏng giao dịch | Chọn tài khoản Test trùng .env, chiều tiền vào, số tiền đúng hóa đơn và nội dung chuyển khoản vừa lấy từ web |
| Mô phỏng tạo mã VietQR | Chọn cùng tài khoản, số tiền và nội dung đó; bấm Mô phỏng chuyển khoản rồi xác nhận trong giao diện SePay |

Đây là thao tác trên SePay, không phải dùng ứng dụng ngân hàng chuyển tiền. Phải giữ đúng nội dung của phiên trong QLCC; mã tự tạo khác sẽ không tự gắn được vào hóa đơn.

Sau khi mô phỏng, kiểm tra giao dịch Test và nhật ký webhook của SePay. Request đến web phải nhận JSON có success=true với HTTP 200/201. Nếu nhật ký báo thất bại, xử lý theo bước 9.

Nguồn chính thức: [mô phỏng giao dịch](https://developer.sepay.vn/vi/tien-ich-khac/test-mode/mo-phong-giao-dich), [mô phỏng QR](https://developer.sepay.vn/vi/tien-ich-khac/test-mode/mo-phong-tao-ma-vietqr).

## 6. Kiểm tra phía cư dân

Hộp thoại thanh toán không có nút kiểm tra hay báo đã chuyển. Web tự hỏi trạng thái khoảng 4 giây một lần khi hộp thoại đang mở; webhook SePay (và đối soát API mỗi phút nếu có token) xác nhận khoản nhận. Hộp thoại chỉ báo lỗi khi không lấy được trạng thái, không tải được QR, phiên hết thời gian hoặc mới nhận một phần tiền.

Kết quả cần thấy sau khi server xác minh đủ tiền:

- Hộp thoại báo **Đã xác nhận thanh toán**.
- QR bị ẩn, không còn nút chuyển khoản.
- Hóa đơn chuyển **Đã thanh toán**.
- Có thể tải biên nhận trong hộp thoại hoặc **Lịch sử thanh toán**.
- Giao dịch và biên nhận có nhãn **SePay Test**, không xác nhận thu tiền thật.

Nếu thiếu token API dự phòng, web chỉ thấy kết quả khi webhook đã tới; không thể khắc phục một webhook chưa được gửi tới.

## 7. Kiểm tra BQL và các thành viên cùng ở

Đăng nhập BQL ở cửa sổ riêng:

1. Vào **Quản lý hóa đơn**, kiểm tra đúng hóa đơn đã trả.
2. Mở **Các khoản đã thu**, kiểm tra đúng một khoản thanh toán và biên nhận.
3. Kiểm tra thông báo **Thanh toán hóa đơn thành công**: có **Căn hộ**, thời gian lập hóa đơn và thời gian thanh toán đến giây theo giờ Việt Nam. Danh sách/chi tiết hóa đơn tự cập nhật khoảng 5 giây khi tab đang mở.
4. Trong **Đối soát chuyển khoản**, giao dịch đúng/đủ được phân bổ vào hóa đơn.

Đăng nhập thành viên khác của cùng căn hộ. Trước khi người đầu trả xong, người thứ hai chỉ thấy phiên đang được giữ, không nhận QR hoặc nội dung chuyển tiền. Sau khi đủ tiền, người thứ hai cũng thấy hóa đơn đã thanh toán.

## 8. Các trường hợp nên thử khi demo

Chỉ dùng SePay Test cho các tình huống có nhiều khoản chuyển:

| Ca kiểm thử | Thao tác | Kết quả mong đợi |
| --- | --- | --- |
| Hai thành viên cùng mở hóa đơn | Dùng hai cửa sổ/tài khoản cùng căn hộ | Chỉ người giữ phiên có QR; người còn lại chờ |
| Gửi lại cùng webhook | Dùng chức năng gửi lại tại nhật ký SePay | Không thêm tiền hoặc biên nhận lần hai |
| Hai lần chuyển thực tế khác nhau | Tạo hai giao dịch Test có ID/tham chiếu khác, cùng nội dung hóa đơn | Chỉ thu hóa đơn một lần; khoản còn lại hiện trong sổ đối soát |
| Chuyển thiếu | Với hóa đơn 10.000đ, mô phỏng nhận 4.000đ | Chưa trả đủ; giữ 4.000đ đã nhận, QR mới chỉ còn 6.000đ |
| Chuyển nốt phần thiếu | Giữ mã chuyển khoản, mô phỏng thêm 6.000đ | Đủ 10.000đ, một biên nhận thanh toán hóa đơn |
| Chuyển dư | Mô phỏng 12.000đ cho hóa đơn 10.000đ mới | Hóa đơn đã trả; 2.000đ còn lại BQL phải xử lý |
| Nội dung không đúng | Mô phỏng khoản tiền không có mã phiên | Không tự đánh dấu hóa đơn đã trả; giao dịch hiện chưa xác định nếu webhook không lọc bỏ |
| Chưa có giao dịch | Mở phiên, không mô phỏng chuyển tiền | Hộp thoại giữ QR và chờ; không có biên nhận |
| Hủy khi chưa chuyển | Bấm Hủy phiên và đọc cảnh báo | Phiên đóng; không cập nhật đã thanh toán |
| Hóa đơn quá hạn | Tạo hóa đơn thử có hạn trước hôm nay | Vẫn cho thanh toán; không tự cộng phí phạt |
| Giao dịch về trễ | Giữ mã phiên rồi mô phỏng sau khi phiên hiển thị hết hạn | Server vẫn đối soát khoản nhận theo mã gốc |

Nếu QR đã được lưu trước đó, ngân hàng vẫn có thể chấp nhận lần chuyển thứ hai. Hệ thống chỉ giới hạn quyền hiển thị và chống ghi nhận trùng; không có quyền chặn ứng dụng ngân hàng của người khác.

Tiền chuyển dư được BQL kiểm tra và hoàn ngoài hệ thống nếu cần. **Ghi nhận xử lý → Đã hoàn trả thực tế** chỉ lưu ghi chú/chứng từ sau khi hoàn, không thực hiện hoàn tiền tự động.

## 9. Xử lý lỗi thường gặp

| Hiện tượng | Cần kiểm tra |
| --- | --- |
| Nút thanh toán bị khóa | Ngân hàng, tài khoản, tên chủ, khóa webhook, URL HTTPS, môi trường và log Billing |
| Không thấy hóa đơn | Xác nhận căn hộ của cư dân, đúng loại hóa đơn/kỳ; mã đăng ký tự khai chưa cấp quyền |
| QR không tải | Kết nối tới dịch vụ ảnh VietQR, chủ phiên và thời gian giữ phiên; không mở nhiều phiên để thử |
| Webhook 401/403 | Chọn API Key; giá trị khớp .env; header Authorization dạng Apikey |
| Webhook 404/502 hoặc không kết nối | Gateway 5000, tunnel còn chạy, đúng đường dẫn /api/billing/sepay/webhook |
| Có giao dịch trên SePay nhưng web chưa cập nhật | Xem nhật ký webhook, gửi lại request sau khi sửa lỗi; kiểm tra mã, ngân hàng, tài khoản nhận và số tiền |
| Đối soát API không lấy được giao dịch từ SePay | Có đủ token + UUID tài khoản API v2 đúng môi trường chưa; nếu chưa có thì chỉ đọc dữ liệu webhook |
| BQL thấy tiền chưa xác định/chuyển dư | Kiểm tra sổ Đối soát chuyển khoản và tham chiếu, không tạo thêm lần thu hóa đơn |
| Ứng dụng ngân hàng báo không tồn tại tài khoản Test | Dừng dùng ứng dụng thật, quay về mô phỏng trong dashboard SePay |
| HTTP 403 ở trang tài liệu ngoài | Đọc file hướng dẫn này; lỗi tài liệu chưa chứng minh endpoint ứng dụng lỗi |

Không đánh dấu đã thanh toán chỉ vì quét QR thành công hoặc có ảnh chuyển khoản. Không xóa phiên/giao dịch trong database để thử lại.

## 10. Nếu muốn quét bằng ứng dụng ngân hàng thật

Đó là luồng **Live**, cần tài khoản nhận thật đã kết nối SePay và cấu hình Live riêng. Dùng khoản thử nhỏ sau khi đã kiểm chứng Test; việc xác nhận chuyển khoản sẽ chuyển tiền thật.

SePay Test giúp demo luồng đối soát tự động mà không cần tiền thật. Việc kiểm thử bằng payload cục bộ của pytest không thay thế lần thử end-to-end từ dashboard SePay của bạn.
