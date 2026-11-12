-- Answers that described screens which have since changed. Edits made by management are left alone.
UPDATE faq_knowledge_base
SET answer='Bạn vào Quản lý gửi xe → Gửi đơn đăng ký, điền thông tin xe rồi gửi Ban quản lý xét duyệt trong vòng 48 giờ. Khi đơn được duyệt, xe xuất hiện trong mục Phương tiện đăng ký cùng biển số hoặc mã xe (ví dụ A101-XD-1) và bạn nhận được thông báo. Muốn đổi thông tin hoặc hủy xe, hãy liên hệ Ban quản lý. Bạn chỉ được hủy khi đã gửi đủ thời gian cam kết, ít nhất 2 tháng. Phí tính theo các tháng có đăng ký trong đợt thu; hóa đơn đã lập không tự thay đổi khi bạn thêm hoặc sửa đăng ký xe.'
WHERE question='Đăng ký thêm, huỷ hoặc thay đổi xe đã đăng ký như thế nào?' AND answer LIKE '%Đăng ký thủ tục, điền đơn gửi xe%';

UPDATE faq_knowledge_base
SET answer='Bạn vào Sửa chữa & bảo trì → Tạo yêu cầu, chọn Sửa chữa hoặc Bảo trì rồi mô tả chỗ bị hỏng. Tài khoản cần được Ban quản lý xác nhận liên kết căn hộ trước khi gửi yêu cầu. Bạn có thể xem người phụ trách và tiến độ xử lý ngay trong mục này. Nếu cần hỗ trợ gấp, gọi Ban quản lý: 0228913665.'
WHERE question='Căn hộ bị hỏng điện nước thì báo ở đâu?' AND answer LIKE 'Bạn vào Sửa chữa & bảo trì → Tạo yêu cầu, chọn Sửa chữa hoặc Bảo trì rồi mô tả chỗ bị hỏng. Bạn có thể xem%';
