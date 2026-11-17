-- FAQ v3: nội dung khớp nghiệp vụ AN CƯ hiện tại.
-- Chỉ sửa faq_knowledge_base; không sửa thông báo, địa điểm hay dữ liệu thanh toán.
-- Không xóa FAQ, không đặt lại ID, không yêu cầu UNIQUE trên question.
-- Bên gọi quản lý transaction. DB Browser: Execute SQL rồi Write Changes.
-- insert_new=0: sửa câu cũ nếu đã có; không chèn thêm biến thể trùng chủ đề.
-- Sao lưu trước khi áp dụng.

CREATE TEMP TABLE chatbot_faq_v3 (
    question TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    answer TEXT NOT NULL,
    insert_new INTEGER NOT NULL CHECK (insert_new IN (0, 1))
);

-- Năm câu chính sách gửi xe đã chốt trong ui_policy_content.sql.
INSERT INTO chatbot_faq_v3 (question, category, answer, insert_new) VALUES
('Làm sao để đăng ký gửi xe tháng?', 'Gửi xe',
 'Bạn gửi đơn đăng ký trên ứng dụng hoặc liên hệ Ban quản lý; đơn được xét duyệt trong vòng 48 giờ. Chung cư nhận xe máy, xe điện (gồm xe máy điện và xe đạp điện) và xe đạp thường, không nhận ô tô. Xe máy cần có biển số; xe điện chưa có biển số cần tạo mã xe theo số căn hộ; xe đạp thường chưa có biển số được cấp mã theo số căn hộ. Bạn cần đăng ký ít nhất 2 tháng và chỉ được hủy khi đã gửi đủ thời gian cam kết. Hết thời gian cam kết, xe vẫn được đăng ký cho đến khi bạn yêu cầu hủy. Phí xe đạp thường là 50.000 đồng/tháng; xe máy và xe điện là 100.000 đồng/tháng, thu mỗi 6 tháng cùng phí dịch vụ. Xe mới đóng thêm 100.000 đồng làm thẻ trong tháng đầu, chỉ thu một lần cho mỗi xe; xe đăng ký lại đã có thẻ không đóng lại phí này. Trong bãi xe, chạy tối đa 20 km/h. Cần hỗ trợ, gọi Ban quản lý: 0228913665.', 1),
('Phí gửi xe tháng và phí làm thẻ là bao nhiêu?', 'Gửi xe',
 'Xe đạp thường: 50.000 đồng/tháng. Xe máy và xe điện (gồm xe máy điện và xe đạp điện): 100.000 đồng/tháng. Xe mới đóng thêm 100.000 đồng làm thẻ trong tháng đầu, chỉ thu một lần cho mỗi xe. Xe đăng ký lại đã có thẻ không đóng lại phí này. Phí gửi xe được thu mỗi 6 tháng cùng phí dịch vụ.', 1),
('Chung cư nhận gửi những loại xe nào?', 'Gửi xe',
 'Chung cư nhận xe máy, xe điện (gồm xe máy điện và xe đạp điện) và xe đạp thường, không nhận ô tô. Xe máy cần có biển số. Nếu xe điện chưa có biển số, bạn cần tạo mã xe theo số căn hộ khi đăng ký. Xe đạp thường chưa có biển số được cấp mã theo số căn hộ.', 1),
('Đăng ký gửi xe tối thiểu bao nhiêu tháng?', 'Gửi xe',
 'Bạn cần đăng ký gửi xe ít nhất 2 tháng. Nếu đã cam kết lâu hơn, bạn cần gửi đủ thời gian đã chọn rồi mới được hủy. Hết thời gian cam kết, xe vẫn được đăng ký và tiếp tục tính phí cho đến khi bạn yêu cầu hủy.', 1),
('Phí gửi xe được thu khi nào?', 'Gửi xe',
 'Phí gửi xe được thu mỗi 6 tháng cùng phí dịch vụ chung cư. Bạn trả tiền cho các tháng có đăng ký gửi xe trong đợt thu đó: xe đạp thường 50.000 đồng/tháng; xe máy và xe điện (gồm xe máy điện và xe đạp điện) 100.000 đồng/tháng. Xe mới đóng thêm 100.000 đồng làm thẻ trong đợt thu có tháng bắt đầu đăng ký; các đợt sau không thu lại phí thẻ.', 1);

-- Hướng dẫn các chức năng đã có. Hạn và trạng thái từng hóa đơn lấy từ dữ liệu thực.
INSERT INTO chatbot_faq_v3 (question, category, answer, insert_new) VALUES
('Hoá đơn điện nước được phát hành khi nào?', 'Thanh toán',
 'Ban quản lý lập hóa đơn điện, nước theo từng tháng. Bạn vào Hóa đơn & thanh toán → Điện & nước hàng tháng để xem hóa đơn của căn hộ mình. Ngày lập và hạn thanh toán được ghi trên từng hóa đơn, không có một ngày chung cho tất cả hóa đơn.', 1),
('Hạn thanh toán hoá đơn điện nước hằng tháng là ngày nào?', 'Thanh toán',
 'Bạn vào Hóa đơn & thanh toán → Chi tiết hóa đơn để xem hạn thanh toán do Ban quản lý ghi trên hóa đơn đó. Mỗi hóa đơn có thể có hạn khác nhau, không mặc định là ngày 10. Mình cần xem hóa đơn của bạn mới trả lời được ngày đến hạn cụ thể.', 1),
('Phí dịch vụ chung và phí gửi xe được thu như thế nào?', 'Thanh toán',
 'Phí dịch vụ chung và phí gửi xe được thu mỗi 6 tháng. Phí gửi xe chỉ tính cho các tháng có đăng ký trong đợt thu đó: xe đạp thường 50.000 đồng/tháng; xe máy và xe điện (gồm xe máy điện và xe đạp điện) 100.000 đồng/tháng. Đăng ký trong tháng nào thì tính đủ tiền tháng đó, kể cả gửi chưa hết tháng. Xe mới đóng thêm 100.000 đồng làm thẻ một lần vào đợt thu đầu tiên. Bạn xem số tiền và hạn thanh toán tại Hóa đơn & thanh toán → Dịch vụ 6 tháng.', 1),
('Có những hình thức thanh toán nào?', 'Thanh toán',
 'Bạn vào Hóa đơn & thanh toán, mở hóa đơn rồi chọn Thanh toán để chuyển khoản qua VietQR. Mỗi lần chỉ một thành viên trong căn hộ giữ phiên thanh toán. Kiểm tra đúng người nhận, số tiền còn lại và giữ nguyên nội dung chuyển khoản. Hóa đơn tự chuyển sang Đã thanh toán khi SePay báo đã nhận đủ tiền; nếu có lỗi, màn hình thanh toán sẽ báo cho bạn. Nếu người khác trong căn hộ đang thanh toán, hãy chờ và không chuyển thêm. Muốn nộp tiền mặt, liên hệ Ban quản lý.', 1),
('Nếu thanh toán quá hạn thì sao?', 'Thanh toán',
 'Nếu chưa thanh toán sau ngày đến hạn, hóa đơn của bạn sẽ được ghi là Quá hạn và dịch vụ có thể bị tạm ngưng. Bạn nên vào Hóa đơn & thanh toán để kiểm tra tất cả khoản còn nợ và liên hệ Ban quản lý để được hướng dẫn. Nếu dịch vụ đã bị ngưng, bạn cần thanh toán hết các khoản quá hạn và chờ kỹ thuật viên xử lý việc mở lại dịch vụ. Dịch vụ chưa được mở lại ngay khi bạn vừa trả xong một hóa đơn.', 1),
('Thanh toán thiếu tiền thì hoá đơn có được tính là đã thanh toán không?', 'Thanh toán',
 'Chưa. Nếu SePay xác nhận bạn đã chuyển thiếu, hóa đơn sẽ hiển thị số tiền đã nhận và số còn thiếu. Chỉ chuyển thêm đúng số còn thiếu theo hướng dẫn mới trên web, giữ nguyên nội dung chuyển khoản. Nếu khoản vừa chuyển chưa hiện, hãy chờ hệ thống tự cập nhật, không chuyển lại toàn bộ. Hóa đơn chỉ hiện Đã thanh toán sau khi hệ thống xác nhận tổng tiền đã nhận đủ.', 1),
('Làm sao để tra cứu lịch sử thanh toán?', 'Thanh toán',
 'Bạn đăng nhập, vào Hóa đơn & thanh toán → Lịch sử thanh toán để xem các khoản đã trả, ngày thanh toán, cách thanh toán và tải biên nhận. Bạn chỉ xem được thông tin của căn hộ gắn với tài khoản mình.', 1),
('Có xuất hoá đơn điện tử không?', 'Thanh toán',
 'Sau khi thanh toán được xác nhận, bạn vào Hóa đơn & thanh toán → Lịch sử thanh toán để tải giấy xác nhận đã thu tiền, gọi là biên nhận nội bộ. Giấy này không phải hóa đơn dùng cho kê khai thuế. Nếu cần hóa đơn thuế, hãy liên hệ Ban quản lý để được hướng dẫn.', 1),
('Đã thanh toán nhưng hoá đơn vẫn báo chưa thanh toán thì làm gì?', 'Thanh toán',
 'Hệ thống tự cập nhật hóa đơn khi SePay báo đã nhận tiền, có thể mất vài phút. Không chuyển khoản lại khi đang chờ. Nếu hóa đơn vẫn chưa cập nhật, vào Khiếu nại & đăng ký → Gửi yêu cầu → Góp ý / Khiếu nại, gửi mã hóa đơn, số tiền và mã giao dịch để Ban quản lý kiểm tra. Không gửi mã OTP, mật khẩu hoặc thông tin thẻ.', 1),
('Mỗi căn hộ được đăng ký tối đa bao nhiêu xe?', 'Gửi xe',
 'Hiện không giới hạn số xe mỗi căn hộ. Bạn có thể đăng ký xe máy, xe điện (gồm xe máy điện và xe đạp điện) và xe đạp thường; mỗi xe đều cần đăng ký và đóng phí theo quy định gửi xe.', 1),
('Đăng ký thêm, huỷ hoặc thay đổi xe đã đăng ký như thế nào?', 'Gửi xe',
 'Bạn vào Quản lý gửi xe → Gửi đơn đăng ký, điền thông tin xe rồi gửi Ban quản lý xét duyệt trong vòng 48 giờ. Khi đơn được duyệt, xe xuất hiện trong mục Phương tiện đăng ký cùng biển số hoặc mã xe (ví dụ A101-XD-1) và bạn nhận được thông báo. Muốn đổi thông tin hoặc hủy xe, hãy liên hệ Ban quản lý. Bạn chỉ được hủy khi đã gửi đủ thời gian cam kết, ít nhất 2 tháng. Phí tính theo các tháng có đăng ký trong đợt thu; hóa đơn đã lập không tự thay đổi khi bạn thêm hoặc sửa đăng ký xe.', 1),
('Căn hộ bị hỏng điện nước thì báo ở đâu?', 'Sửa chữa',
 'Bạn vào Sửa chữa & bảo trì → Tạo yêu cầu, chọn Sửa chữa hoặc Bảo trì rồi mô tả chỗ bị hỏng. Tài khoản cần được Ban quản lý xác nhận liên kết căn hộ trước khi gửi yêu cầu. Bạn có thể xem người phụ trách và tiến độ xử lý ngay trong mục này. Nếu cần hỗ trợ gấp, gọi Ban quản lý: 0228913665.', 1),
('Yêu cầu sửa chữa được xử lý trong bao lâu?', 'Sửa chữa',
 'Bạn vào Sửa chữa & bảo trì để xem yêu cầu đang Chờ xử lý, Đang thực hiện hay Đã hoàn thành. Thời gian sửa tùy mức độ hư hỏng và lịch của người phụ trách; hiện chưa có thời hạn chung cho mọi yêu cầu. Nếu cần hỗ trợ gấp, gọi Ban quản lý: 0228913665.', 1),
('Gửi khiếu nại như thế nào?', 'Khiếu nại',
 'Bạn vào Khiếu nại & đăng ký → Gửi yêu cầu → Góp ý / Khiếu nại, chọn loại vấn đề rồi viết nội dung cần phản ánh. Ban quản lý có thể trả lời ngay trong Khiếu nại & đăng ký. Khi có phản hồi, bạn nhận được thông báo riêng trong mục Thông báo; bạn cũng có thể mở lại khiếu nại để xem câu trả lời và tiến độ xử lý.', 1),
('Số hotline của chung cư là gì?', 'Liên hệ',
 'Bạn gọi Ban quản lý qua số 0228913665 để được hỗ trợ. Mình chưa có số riêng của bảo vệ hoặc kỹ thuật viên đã được xác nhận.', 1),
('Xem thông báo của Ban quản lý ở đâu?', 'Thông báo',
 'Bạn vào mục Thông báo để xem thông báo chung của chung cư và thông báo riêng gửi cho mình, gồm phản hồi khiếu nại từ Ban quản lý. Nếu muốn nhận thông báo bật lên trên thiết bị, bạn cần cho phép trình duyệt gửi thông báo và tính năng này cần được bật cho ứng dụng. Dù chưa nhận được thông báo bật lên, bạn vẫn có thể vào mục Thông báo để kiểm tra.', 1);

-- Câu v2 bị lệch hoặc mô tả chức năng chưa có: chỉ sửa nếu đã nhập trước đó.
-- Không đổi câu hỏi/ID để tránh mất liên kết hoặc ghi đè FAQ khác cùng chủ đề.
INSERT INTO chatbot_faq_v3 (question, category, answer, insert_new) VALUES
('Giá vé gửi xe tháng là bao nhiêu?', 'Gửi xe',
 'Xe đạp thường: 50.000 đồng/tháng. Xe máy và xe điện (gồm xe máy điện và xe đạp điện): 100.000 đồng/tháng. Phí được thu mỗi 6 tháng, chỉ tính cho các tháng có đăng ký gửi xe trong đợt thu đó. Xe mới đóng thêm 100.000 đồng làm thẻ một lần vào đợt thu có tháng bắt đầu đăng ký.', 0),
('Chung cư có nhận gửi ô tô không?', 'Gửi xe',
 'Chung cư chỉ nhận xe máy, xe điện (gồm xe máy điện và xe đạp điện) và xe đạp thường; không nhận ô tô. Liên hệ Ban quản lý nếu cần hướng dẫn thêm.', 0),
('Mất thẻ gửi xe thì phải làm gì?', 'Gửi xe',
 'Bạn báo mất thẻ cho Ban quản lý qua 0228913665 để được hướng dẫn. Mình chưa có thông tin về phí làm lại thẻ; bạn cần hỏi Ban quản lý trước khi nộp. Phí làm thẻ lần đầu là 100.000 đồng, chưa thể dùng mức này để trả lời phí làm lại thẻ.', 0),
('Có được sạc xe điện dưới hầm không?', 'Gửi xe',
 'Bạn hỏi Ban quản lý để biết nơi nào được sạc xe điện và cần tuân theo quy định gì. Xe điện gồm xe máy điện và xe đạp điện; được đăng ký gửi xe điện chưa có nghĩa là được sạc ngay tại chỗ đỗ xe.', 0),
('Có được tổ chức tiệc, sự kiện ở khu vực chung không?', 'Dịch vụ',
 'Bạn liên hệ Ban quản lý để hỏi lịch trống, điều kiện tổ chức và cần đăng ký trước bao lâu. Hiện chưa thể đặt sự kiện trên ứng dụng; mục Đăng ký thủ tục đang dùng để đăng ký gửi xe.', 0),
('Thẻ ra vào cư dân được cấp như thế nào?', 'Dịch vụ',
 'Bạn liên hệ Ban quản lý để được hướng dẫn làm thẻ ra vào hoặc làm lại thẻ bị mất. Hiện chưa thể đăng ký thẻ ra vào trên ứng dụng. Hãy hỏi Ban quản lý về chi phí vì phí thẻ ra vào có thể khác phí thẻ gửi xe.', 0),
('Muốn xem hoặc trích xuất camera an ninh thì làm thế nào?', 'Dịch vụ',
 'Bạn liên hệ Ban quản lý, nói rõ thời gian, khu vực và lý do cần xem camera. Ban quản lý sẽ kiểm tra yêu cầu và cho biết có thể cung cấp hình ảnh hay không theo quy định. Hiện bạn chưa thể tự xem hoặc tải hình camera trên ứng dụng.', 0),
('Sửa chữa trong căn hộ có mất phí không?', 'Sửa chữa',
 'Bạn hỏi Ban quản lý hoặc người phụ trách sửa chữa về công việc cần làm và chi phí trước khi đồng ý sửa. Mình chưa có bảng giá để trả lời chính xác việc sửa nào được miễn phí hay phải trả tiền.', 0),
('Đặt phòng sinh hoạt cộng đồng như thế nào?', 'Dịch vụ',
 'Bạn liên hệ Ban quản lý để hỏi lịch trống và cách đăng ký phòng sinh hoạt cộng đồng. Hiện chưa thể đặt phòng trên ứng dụng; mục Đăng ký thủ tục đang dùng để đăng ký gửi xe. Bạn xem thêm mục Thông báo để biết giờ sử dụng và lịch đóng cửa mới nhất.', 0),
('Xem thông báo của ban quản lý ở đâu?', 'Thông báo',
 'Bạn vào mục Thông báo để xem thông báo chung của chung cư và thông báo riêng gửi cho mình, gồm phản hồi khiếu nại từ Ban quản lý. Nếu muốn nhận thông báo bật lên trên thiết bị, bạn cần cho phép trình duyệt gửi thông báo và tính năng này cần được bật cho ứng dụng. Dù chưa nhận được thông báo bật lên, bạn vẫn có thể vào mục Thông báo để kiểm tra.', 0);

-- Các câu khác của v2 (giờ giấc, nội quy, tiện ích, xử phạt...) chưa được bổ sung
-- ở đây. Nếu từng nhập v2, cần rà soát riêng các câu đó.

UPDATE faq_knowledge_base
SET category = (SELECT category FROM chatbot_faq_v3 WHERE question = faq_knowledge_base.question),
    answer = (SELECT answer FROM chatbot_faq_v3 WHERE question = faq_knowledge_base.question)
WHERE question IN (SELECT question FROM chatbot_faq_v3);

INSERT INTO faq_knowledge_base (category, question, answer)
SELECT category, question, answer FROM chatbot_faq_v3
WHERE insert_new = 1
  AND NOT EXISTS (
      SELECT 1 FROM faq_knowledge_base
      WHERE faq_knowledge_base.question = chatbot_faq_v3.question
  );

DROP TABLE chatbot_faq_v3;
