-- Presentation spelling only: retain identifiers, dates, statuses and history.
UPDATE faq_knowledge_base SET
    category=REPLACE(REPLACE(category,'ban quản lý','Ban quản lý'),'Ban Quản Lý','Ban quản lý'),
    question=REPLACE(REPLACE(question,'ban quản lý','Ban quản lý'),'Ban Quản Lý','Ban quản lý'),
    answer=REPLACE(REPLACE(answer,'ban quản lý','Ban quản lý'),'Ban Quản Lý','Ban quản lý');
UPDATE locations SET
    name=REPLACE(REPLACE(name,'ban quản lý','Ban quản lý'),'Ban Quản Lý','Ban quản lý'),
    description=REPLACE(REPLACE(description,'ban quản lý','Ban quản lý'),'Ban Quản Lý','Ban quản lý');
UPDATE notifications SET
    title=REPLACE(REPLACE(title,'ban quản lý','Ban quản lý'),'Ban Quản Lý','Ban quản lý'),
    content=REPLACE(REPLACE(content,'ban quản lý','Ban quản lý'),'Ban Quản Lý','Ban quản lý');
UPDATE complaints SET
    category=REPLACE(REPLACE(category,'ban quản lý','Ban quản lý'),'Ban Quản Lý','Ban quản lý'),
    content=REPLACE(REPLACE(content,'ban quản lý','Ban quản lý'),'Ban Quản Lý','Ban quản lý'),
    response=REPLACE(REPLACE(response,'ban quản lý','Ban quản lý'),'Ban Quản Lý','Ban quản lý');
UPDATE maintenance_tickets SET
    description=REPLACE(REPLACE(description,'ban quản lý','Ban quản lý'),'Ban Quản Lý','Ban quản lý');

-- Match managed policy by question, since source and runtime IDs can differ.
-- This block is safe to reapply after a future source content refresh.
CREATE TEMP TABLE ui_parking_faq(question TEXT PRIMARY KEY,answer TEXT NOT NULL);
INSERT INTO ui_parking_faq(question,answer) VALUES
('Làm sao để đăng ký gửi xe tháng?',
 'Bạn gửi đơn đăng ký trên ứng dụng hoặc liên hệ Ban quản lý; đơn được xét duyệt trong vòng 48 giờ. Chung cư nhận xe máy, xe điện (gồm xe máy điện và xe đạp điện) và xe đạp thường, không nhận ô tô. Xe máy cần có biển số; xe điện chưa có biển số cần tạo mã xe theo số căn hộ; xe đạp thường chưa có biển số được cấp mã theo số căn hộ. Bạn cần đăng ký ít nhất 2 tháng và chỉ được hủy khi đã gửi đủ thời gian cam kết. Hết thời gian cam kết, xe vẫn được đăng ký cho đến khi bạn yêu cầu hủy. Phí xe đạp thường là 50.000 đồng/tháng; xe máy và xe điện là 100.000 đồng/tháng, thu mỗi 6 tháng cùng phí dịch vụ. Xe mới đóng thêm 100.000 đồng làm thẻ trong tháng đầu, chỉ thu một lần cho mỗi xe; xe đăng ký lại đã có thẻ không đóng lại phí này. Trong bãi xe, chạy tối đa 20 km/h. Cần hỗ trợ, gọi Ban quản lý: 0228913665.'),
('Phí gửi xe tháng và phí làm thẻ là bao nhiêu?',
 'Xe đạp thường: 50.000 đồng/tháng. Xe máy và xe điện (gồm xe máy điện và xe đạp điện): 100.000 đồng/tháng. Xe mới đóng thêm 100.000 đồng làm thẻ trong tháng đầu, chỉ thu một lần cho mỗi xe. Xe đăng ký lại đã có thẻ không đóng lại phí này. Phí gửi xe được thu mỗi 6 tháng cùng phí dịch vụ.'),
('Chung cư nhận gửi những loại xe nào?',
 'Chung cư nhận xe máy, xe điện (gồm xe máy điện và xe đạp điện) và xe đạp thường, không nhận ô tô. Xe máy cần có biển số. Nếu xe điện chưa có biển số, bạn cần tạo mã xe theo số căn hộ khi đăng ký. Xe đạp thường chưa có biển số được cấp mã theo số căn hộ.'),
('Đăng ký gửi xe tối thiểu bao nhiêu tháng?',
 'Bạn cần đăng ký gửi xe ít nhất 2 tháng. Nếu đã cam kết lâu hơn, bạn cần gửi đủ thời gian đã chọn rồi mới được hủy. Hết thời gian cam kết, xe vẫn được đăng ký và tiếp tục tính phí cho đến khi bạn yêu cầu hủy.'),
('Phí gửi xe được thu khi nào?',
 'Phí gửi xe được thu mỗi 6 tháng cùng phí dịch vụ chung cư. Bạn trả tiền cho các tháng có đăng ký gửi xe trong đợt thu đó: xe đạp thường 50.000 đồng/tháng; xe máy và xe điện (gồm xe máy điện và xe đạp điện) 100.000 đồng/tháng. Xe mới đóng thêm 100.000 đồng làm thẻ trong đợt thu có tháng bắt đầu đăng ký; các đợt sau không thu lại phí thẻ.');
UPDATE faq_knowledge_base SET answer=(
    SELECT answer FROM ui_parking_faq WHERE ui_parking_faq.question=faq_knowledge_base.question
) WHERE question IN (SELECT question FROM ui_parking_faq);
INSERT INTO faq_knowledge_base(category,question,answer)
SELECT 'Gửi xe',question,answer FROM ui_parking_faq
WHERE NOT EXISTS (SELECT 1 FROM faq_knowledge_base WHERE faq_knowledge_base.question=ui_parking_faq.question);
DROP TABLE ui_parking_faq;
