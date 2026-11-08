# Thanh toán hóa đơn bằng VietQR và SePay

Billing chạy cổng 5003; người dùng truy cập qua gateway cổng 5000. Ban quản lý (BQL) lập hóa đơn, theo dõi công nợ và ghi nhận khoản tiền đã thực nhận. Cư dân đã được xác nhận thuộc căn hộ sử dụng VietQR để thanh toán. Cấu hình hiện dùng PAYMENT_MODE=sepay; các chế độ và API MoMo/mô phỏng nội bộ cũ đã được thay thế.

- [Thiết lập SePay, ngân hàng và webhook](SEPAY_VIETQR.md).
- [Các bước kiểm thử hóa đơn trên web](TEST_THANH_TOAN_HOA_DON.md).
- [Danh mục API nghiệp vụ](DOMAIN_API.md).

## Hai môi trường

| Cấu hình | Cách phát sinh giao dịch | Có tiền thật? |
| --- | --- | --- |
| SEPAY_ENV=test, mặc định | Tạo giao dịch/mô phỏng QR trong SePay Test Mode | Không |
| SEPAY_ENV=live | Chuyển tiền vào tài khoản ngân hàng thật đã kết nối | Có |

Chọn Test Mode trong tài khoản SePay và cấu hình tài khoản, webhook, token riêng của môi trường đó. QR Test được kiểm thử trên giao diện SePay, không quét bằng ứng dụng ngân hàng thật. Mô phỏng chuyển khoản tạo giao dịch thử và kích hoạt webhook Test; tài liệu chính thức: [SePay Test Mode](https://docs.sepay.vn/test-mode.html), [mô phỏng QR](https://developer.sepay.vn/vi/tien-ich-khac/test-mode/mo-phong-tao-ma-vietqr).

Web không có nút tự đánh dấu thanh toán thành công cho cư dân. Nút **Tôi đã chuyển khoản** chỉ báo đang chờ xác nhận.

## Lập hóa đơn điện, nước

Biểu mẫu BQL nhập **điện tiêu thụ (kWh)**, **nước tiêu thụ (m³)** và **đơn giá VNĐ/kWh, VNĐ/m³**. Đây là lượng đã dùng trong kỳ (chỉ số cuối trừ đầu kỳ), không phải chỉ số tích lũy của đồng hồ. BQL nhập đơn giá áp dụng; chương trình không tự chọn biểu giá bậc thang hay cộng thêm thuế/phụ phí.

Tiền từng khoản = lượng tiêu thụ × đơn giá, làm tròn đến đồng (0,5 trở lên làm tròn lên); tổng hóa đơn = tiền điện + tiền nước. Cho phép tối đa 3 chữ số thập phân cho lượng dùng, đơn giá là số nguyên dương. Ví dụ để thử: 4 kWh × 2.000đ + 0,2 m³ × 10.000đ = 10.000đ; đây chỉ là số liệu kiểm thử.

Giao diện xem trước tổng ngay khi nhập, server tính lại trước khi lưu. Hóa đơn lưu lượng dùng và đơn giá để cư dân/BQL xem công thức trong chi tiết và biên nhận. Hóa đơn cũ giữ nguyên số tiền, không tự suy ra lượng tiêu thụ hoặc đơn giá; API nhập phí trực tiếp vẫn tương thích dữ liệu cũ. Khi đã phát hành QR, không cho sửa lượng dùng/đơn giá để tránh lệch số tiền đã gửi tới ngân hàng.

Database có CHECK giới hạn lượng dùng/đơn giá và trigger kiểm tra đủ bốn đầu vào, độ chính xác ba chữ số thập phân, tiền điện/nước đúng công thức. Trigger cũ tiếp tục tự cộng tổng hai khoản. Chỉ mục UNIQUE theo `invoice_id` với `status='success'` chặn hai khoản thanh toán thành công cho cùng hóa đơn ở cả bảng tháng và sáu tháng. Ngân hàng vẫn có thể nhận hai lần chuyển tiền; từng khoản được lưu riêng ở `bank_transactions` để đối soát phần dư. Kiểm tra quyền cư dân, hạn sửa hóa đơn và xác thực webhook vẫn do API thực hiện.

## Thời gian hóa đơn và thông báo

Chi tiết hóa đơn hiển thị **Thời gian lập hóa đơn** và **Thời gian thanh toán**, gồm ngày, giờ, phút, giây theo giờ Việt Nam (UTC+7). Thời gian lập lấy từ lúc server lưu hóa đơn; thời gian thanh toán lấy từ bản ghi thanh toán thành công khi xác nhận đủ tiền, không lấy từ lúc mở QR hoặc bấm báo đã chuyển khoản. Với webhook đến chậm, đây là lúc hệ thống ghi nhận đủ tiền, không phải thời điểm thao tác trong ứng dụng ngân hàng. Dữ liệu cũ giữ nguyên; thời gian SQLite không có múi giờ được đọc là UTC.

Danh sách, chi tiết hóa đơn đang mở và thông báo tự kiểm tra dữ liệu mới mỗi 5 giây khi tab đang hiển thị. Đây là cập nhật bằng polling, không cần tải lại trang; kết nối chậm hoặc dịch vụ gián đoạn có thể làm kết quả xuất hiện trễ hơn. Biểu mẫu đang nhập được giữ nguyên. Màn hình QR tiếp tục kiểm tra trạng thái mỗi 4 giây.

Thông báo thanh toán của BQL có trường **Căn hộ**, thời gian lập và thời gian thanh toán. Căn hộ ở đây mô tả hóa đơn, không thay đổi người nhận: thông báo dành cho BQL vẫn chỉ dành cho BQL. Migration `notifications_billing_context.sql` bổ sung thông tin cho thông báo hóa đơn cũ dựa trên sự kiện đã lưu, không gửi lại thông báo và không sửa số tiền hay thời điểm thanh toán.

## Một căn hộ, nhiều thành viên, một lần thu

Mọi thành viên có hợp đồng hiệu lực hoặc liên kết cư trú được BQL xác nhận đều xem và có thể bắt đầu thanh toán hóa đơn chung. Mã căn hộ tự khai khi đăng ký không tự cấp quyền.

Khi thành viên đầu tiên mở thanh toán, server giữ một phiên cho người đó. Thành viên khác cùng căn hộ chỉ thấy trạng thái đang chờ; không nhận QR, số tài khoản hoặc nội dung chuyển tiền của phiên. Khi đủ tiền được xác minh, tất cả cùng thấy hóa đơn đã thanh toán.

Phiên pending mặc định giữ 15 phút, cấu hình từ 2 đến 60 phút. Thời gian này chỉ giới hạn hiển thị QR trên web; **không thu hồi được QR đã chụp hoặc lưu trong ngân hàng**. Hạn hóa đơn do BQL đặt là một thời hạn khác.

| Trạng thái phiên | Xử lý |
| --- | --- |
| pending | Chủ phiên nhận QR và nội dung chuyển khoản; có thể báo đã chuyển hoặc hủy khi chưa chuyển |
| awaiting_confirmation | Đã báo chuyển; chờ xác minh, giữ khóa phiên, không tự mở lại theo đồng hồ |
| success | Đủ tiền đã được đối soát; hóa đơn, biên nhận và thông báo được cập nhật |
| expired | Phiên hiển thị hết thời gian; khoản chuyển đến trễ vẫn được tiếp nhận đối soát |
| cancelled | Người giữ phiên xác nhận chưa chuyển và hủy; khoản chuyển đến trễ vẫn được kiểm tra |

Đã nhận một phần tiền thì không cho hủy phiên. QR mới trong phiên chỉ chứa số còn thiếu. Phần đã nhận và số còn thiếu hiển thị riêng; không yêu cầu cư dân trả lại toàn bộ hóa đơn.

## Ghi nhận giao dịch và tiền chuyển dư

Không thể ngăn ngân hàng nhận hai lần chuyển tiền từ hai thiết bị hoặc một QR đã lưu. Source giảm khả năng này bằng việc chỉ cấp QR cho một người, khóa khi người đó báo đã chuyển, kiểm tra trạng thái định kỳ và cảnh báo không chuyển lại.

Backend xử lý từng khoản nhận trong giao dịch SQLite có khóa ghi. Số được phân bổ cho hóa đơn luôn giới hạn ở số còn nợ; tiền chuyển dư được lưu riêng, không tạo biên nhận thu hóa đơn lần hai.

| Tình huống | Kết quả |
| --- | --- |
| Webhook gửi lại cùng giao dịch | Trả kết quả đã nhận, không cộng tiền lần nữa |
| Hai giao dịch thực tế khác nhau cho cùng hóa đơn | Lưu cả hai; chỉ phân bổ tối đa số còn thiếu |
| Chuyển thiếu | Giữ hóa đơn chưa trả đủ, lưu phần đã nhận; chủ phiên nhận QR số còn lại |
| Chuyển dư | Hóa đơn được ghi đủ; phần dư xuất hiện trong sổ đối soát BQL |
| Sai/thiếu mã hóa đơn | Lưu giao dịch chưa xác định để BQL kiểm tra; không tự đánh dấu hóa đơn đã trả |
| Khoản chuyển đến trễ hoặc sau khi đã thu đủ | Đối soát theo mã gốc; tiền không còn được phân bổ được giữ trong sổ xử lý |

Trong **Quản lý hóa đơn → Đối soát chuyển khoản**, BQL kiểm tra tham chiếu, tiền nhận, tiền đã phân bổ, phần cần xử lý và ghi chú. Các kết quả **Đã kiểm tra**, **Đã hoàn trả thực tế**, **Đã thống nhất giữ lại** chỉ là sổ theo dõi có người và thời điểm cập nhật. Chúng không gọi API hoàn tiền, không chuyển tiền và không tự gán tiền sang hóa đơn khác. Chỉ ghi đã hoàn trả sau khi BQL đã thực hiện hoàn và kiểm tra chứng từ.

## Nguồn xác nhận và an toàn

Webhook chỉ nhận JSON với Authorization dạng Apikey, dùng khóa bí mật riêng trong SEPAY_WEBHOOK_API_KEY. Backend kiểm tra ngân hàng, tài khoản nhận, chiều tiền vào, mã chuyển khoản và số tiền nguyên VND; đối chiếu định danh để chống gửi lặp. Chỉ request đã xác thực mới được xử lý. [Tài liệu webhook SePay](https://docs.sepay.vn/tich-hop-webhooks.html).

Nút **Kiểm tra trạng thái** gọi server. Nếu có đủ SEPAY_API_TOKEN và SEPAY_BANK_ACCOUNT_ID, server tra API giao dịch SePay để đối soát bổ sung; nếu chưa cấu hình cặp này, server chỉ đọc trạng thái đã nhận qua webhook và thông báo cần kiểm tra. Không lấy kết quả từ ảnh chuyển khoản, tham số URL hoặc lời xác nhận phía trình duyệt.

Cấu hình API v2 dùng UUID tài khoản và token đúng môi trường. API Test dùng userapi-sandbox.sepay.vn; Live dùng userapi.sepay.vn. Việc đọc API không tạo giao dịch ngân hàng.

Không gửi khóa webhook/token qua frontend, không commit .env, không sửa SQLite để ép trạng thái thành công. Các chứng từ và lệnh cũ được giữ để đối chiếu lịch sử; chúng không tiếp tục gọi MoMo.

## Hóa đơn quá hạn và thông báo

Hạn ngày được tính hết ngày đó theo giờ Việt Nam. Hết hạn mà chưa trả đủ thì hóa đơn quá hạn; vẫn cho phép thanh toán công nợ. Source không tự thêm phí phạt chậm trả.

Khi ghi nhận đủ tiền lần đầu, server tạo một biên nhận và một sự kiện thanh toán thành công gửi BQL, đồng thời thông báo cho căn hộ. Outbox gửi lại khi dịch vụ thông báo tạm gián đoạn; sự kiện lặp không tạo thông báo thành công trùng. Biên nhận Test có nhãn thử nghiệm, không chứng minh thu tiền thật và không phải hóa đơn thuế.
