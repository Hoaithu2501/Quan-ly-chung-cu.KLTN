-- Update only obsolete payment instructions; keep FAQ IDs and custom policies.
UPDATE faq_knowledge_base
SET answer='Bạn vào Hóa đơn & thanh toán, mở hóa đơn rồi chọn Thanh toán. Mỗi lần chỉ một thành viên trong căn hộ giữ phiên thanh toán. Nếu màn hình ghi SePay Test, chỉ mô phỏng giao dịch trên trang SePay, không dùng ứng dụng ngân hàng thật để quét mã. Nếu màn hình ghi Live, kiểm tra đúng người nhận, số tiền còn lại và nội dung trước khi chuyển khoản qua VietQR. Hệ thống xác nhận sau khi SePay báo nhận tiền; nút Tôi đã chuyển khoản không xác nhận hóa đơn đã thanh toán. Nếu người khác trong căn hộ đang thanh toán, hãy chờ và không chuyển thêm. Muốn nộp tiền mặt, liên hệ Ban quản lý.'
WHERE question='Có những hình thức thanh toán nào?' AND answer LIKE '%MoMo%';

UPDATE faq_knowledge_base
SET answer='Bạn quay về Hóa đơn & thanh toán và bấm Kiểm tra trạng thái. Có thể hệ thống chưa nhận được xác nhận từ ngân hàng qua SePay. Không chuyển khoản lại khi đang chờ. Nếu hóa đơn vẫn chưa cập nhật, vào Khiếu nại & đăng ký → Gửi yêu cầu → Góp ý / Khiếu nại, gửi mã hóa đơn, số tiền và mã giao dịch để Ban quản lý kiểm tra. Không gửi mã OTP, mật khẩu hoặc thông tin thẻ.'
WHERE question='Đã thanh toán nhưng hoá đơn vẫn báo chưa thanh toán thì làm gì?' AND answer LIKE '%MoMo%';

UPDATE faq_knowledge_base
SET answer='Chưa. Nếu SePay xác nhận bạn đã chuyển thiếu, hóa đơn sẽ hiển thị số tiền đã nhận và số còn thiếu. Chỉ chuyển thêm đúng số còn thiếu theo hướng dẫn mới trên web, giữ nguyên nội dung chuyển khoản. Nếu khoản vừa chuyển chưa hiện, hãy bấm Kiểm tra trạng thái và chờ đối soát, không chuyển lại toàn bộ. Hóa đơn chỉ hiện Đã thanh toán sau khi hệ thống xác nhận tổng tiền đã nhận đủ.'
WHERE question='Thanh toán thiếu tiền thì hoá đơn có được tính là đã thanh toán không?' AND answer LIKE '%chưa thể chia nhỏ%';
