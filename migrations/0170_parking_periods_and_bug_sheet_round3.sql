-- Parking registrations now cover whole months up to the end of their six-month fee period.
-- A December registration covers December only, so the CHECK drops from 2 months to 1.
-- SQLite cannot change a CHECK, so the table is rebuilt; no table references vehicles.
DROP VIEW IF EXISTS vw_vehicle_summary_by_apartment;
CREATE TABLE vehicles_by_period (
    vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment_id INTEGER NOT NULL,
    plate_number TEXT,
    vehicle_type TEXT NOT NULL CHECK(vehicle_type IN ('bicycle','motorbike','electric_bike')),
    monthly_fee INTEGER NOT NULL CHECK(monthly_fee IN (50000,100000)),
    registered_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','cancelled')),
    registration_months INTEGER NOT NULL DEFAULT 2 CHECK(registration_months >= 1),
    cancelled_date TEXT,
    card_fee INTEGER NOT NULL DEFAULT 100000 CHECK(card_fee IN (0,100000)),
    created_at TEXT
);
INSERT INTO vehicles_by_period(vehicle_id,apartment_id,plate_number,vehicle_type,monthly_fee,registered_date,
                               status,registration_months,cancelled_date,card_fee,created_at)
SELECT vehicle_id,apartment_id,plate_number,vehicle_type,monthly_fee,registered_date,
       status,registration_months,cancelled_date,card_fee,created_at FROM vehicles;
-- Keep AUTOINCREMENT history even when the highest ID was deleted.
UPDATE sqlite_sequence SET seq=MAX(seq,COALESCE((SELECT seq FROM sqlite_sequence WHERE name='vehicles'),0))
WHERE name='vehicles_by_period';
DROP TABLE vehicles;
ALTER TABLE vehicles_by_period RENAME TO vehicles;
CREATE INDEX idx_domain_vehicle_apartment ON vehicles(apartment_id,status);
CREATE UNIQUE INDEX uq_active_vehicle_plate ON vehicles(UPPER(plate_number))
WHERE status='active' AND plate_number IS NOT NULL AND TRIM(plate_number)<>'';
CREATE VIEW vw_vehicle_summary_by_apartment AS
SELECT apartment_id,
       SUM(CASE WHEN vehicle_type IN ('motorbike','electric_bike') THEN 1 ELSE 0 END) AS so_xe_may,
       SUM(CASE WHEN vehicle_type='bicycle' THEN 1 ELSE 0 END) AS so_xe_dap,
       SUM(monthly_fee) AS tong_phi_thang
FROM vehicles WHERE status='active' GROUP BY apartment_id;

-- Residents have no "Phương tiện đăng ký" tab, so earlier approval notes point at Quản lý gửi xe only.
UPDATE complaints
SET response=REPLACE(response,'Xem tại Quản lý gửi xe › Phương tiện đăng ký.','Xem tại Quản lý gửi xe.')
WHERE response LIKE '%Quản lý gửi xe › Phương tiện đăng ký.%';
UPDATE notifications
SET content=REPLACE(content,'Xem tại Quản lý gửi xe › Phương tiện đăng ký.','Xem tại Quản lý gửi xe.')
WHERE content LIKE '%Quản lý gửi xe › Phương tiện đăng ký.%';

-- Chatbot parking answers: the new registration period rule, renewal, the extra parking invoice,
-- and less repetition. Only answers still as originally written are changed; edited ones are kept.
UPDATE faq_knowledge_base
SET answer='Bạn vào Quản lý gửi xe → Gửi đơn đăng ký, chọn loại xe, nhập biển số, ngày bắt đầu và số tháng gửi rồi gửi đơn. Ban quản lý xét duyệt trong vòng 48 giờ; khi đơn được duyệt, xe hiện trong Quản lý gửi xe và bạn nhận được thông báo. Trong bãi xe, chạy tối đa 20 km/h. Cần hỗ trợ, gọi Ban quản lý: 0228913665.'
WHERE question='Làm sao để đăng ký gửi xe tháng?' AND answer='Bạn gửi đơn đăng ký trên ứng dụng hoặc liên hệ Ban quản lý; đơn được xét duyệt trong vòng 48 giờ. Chung cư nhận xe máy, xe điện (gồm xe máy điện và xe đạp điện) và xe đạp thường, không nhận ô tô. Xe máy cần có biển số; xe điện chưa có biển số cần tạo mã xe theo số căn hộ; xe đạp thường chưa có biển số được cấp mã theo số căn hộ. Bạn cần đăng ký ít nhất 2 tháng và chỉ được hủy khi đã gửi đủ thời gian cam kết. Hết thời gian cam kết, xe vẫn được đăng ký cho đến khi bạn yêu cầu hủy. Phí xe đạp thường là 50.000 đồng/tháng; xe máy và xe điện là 100.000 đồng/tháng, thu mỗi 6 tháng cùng phí dịch vụ. Xe mới đóng thêm 100.000 đồng làm thẻ trong tháng đầu, chỉ thu một lần cho mỗi xe; xe đăng ký lại đã có thẻ không đóng lại phí này. Trong bãi xe, chạy tối đa 20 km/h. Cần hỗ trợ, gọi Ban quản lý: 0228913665.';

UPDATE faq_knowledge_base
SET answer='Xe đạp thường: 50.000 đồng/tháng. Xe máy và xe điện (gồm xe máy điện và xe đạp điện): 100.000 đồng/tháng. Xe mới đóng thêm 100.000 đồng làm thẻ, chỉ thu một lần cho mỗi xe; xe từng đăng ký và đã có thẻ không đóng lại phí này. Phí gửi xe được thu cùng hóa đơn dịch vụ 6 tháng. Nếu hóa đơn dịch vụ của kỳ đã lập trước khi bạn đăng ký xe, Ban quản lý sẽ lập riêng một hóa đơn gửi xe bổ sung cho xe đó.'
WHERE question='Phí gửi xe tháng và phí làm thẻ là bao nhiêu?' AND answer='Xe đạp thường: 50.000 đồng/tháng. Xe máy và xe điện (gồm xe máy điện và xe đạp điện): 100.000 đồng/tháng. Xe mới đóng thêm 100.000 đồng làm thẻ trong tháng đầu, chỉ thu một lần cho mỗi xe. Xe đăng ký lại đã có thẻ không đóng lại phí này. Phí gửi xe được thu mỗi 6 tháng cùng phí dịch vụ';

UPDATE faq_knowledge_base
SET answer='Mỗi lần đăng ký ít nhất 2 tháng, tính cả tháng bắt đầu, và tối đa đến hết kỳ thu phí đang đăng ký (tháng 1–6 hoặc tháng 7–12). Ví dụ: đăng ký tháng 1 được gửi tối đa đến hết tháng 6; tháng 6 là tháng cuối kỳ nên được gửi đến hết tháng 12. Đăng ký tháng 12 chỉ gửi được tháng 12, vì không đăng ký sang năm sau. Hết thời gian đăng ký, xe không được gửi tiếp nếu chưa gia hạn: bạn gửi lại đơn đăng ký với đúng biển số hoặc mã xe cũ để Ban quản lý gia hạn.'
WHERE question='Đăng ký gửi xe tối thiểu bao nhiêu tháng?' AND answer='Bạn cần đăng ký gửi xe ít nhất 2 tháng. Nếu đã cam kết lâu hơn, bạn cần gửi đủ thời gian đã chọn rồi mới được hủy. Hết thời gian cam kết, xe vẫn được đăng ký và tiếp tục tính phí cho đến khi bạn yêu cầu hủy.';

-- Repeated "Phí dịch vụ chung và phí gửi xe được thu như thế nào?" almost word for word.
DELETE FROM faq_knowledge_base
WHERE question='Phí gửi xe được thu khi nào?' AND answer='Phí gửi xe được thu mỗi 6 tháng cùng phí dịch vụ chung cư. Bạn trả tiền cho các tháng có đăng ký gửi xe trong đợt thu đó: xe đạp thường 50.000 đồng/tháng; xe máy và xe điện (gồm xe máy điện và xe đạp điện) 100.000 đồng/tháng. Xe mới đóng thêm 100.000 đồng làm thẻ trong đợt thu có tháng bắt đầu đăng ký; các đợt sau không thu lại phí thẻ.';

UPDATE faq_knowledge_base
SET answer='Phí dịch vụ chung và phí gửi xe được thu theo kỳ 6 tháng (tháng 1–6 và tháng 7–12). Phí gửi xe chỉ tính các tháng xe có đăng ký trong kỳ; đăng ký trong tháng nào thì tính đủ tiền tháng đó. Bạn xem số tiền và hạn thanh toán tại Hóa đơn & thanh toán → Dịch vụ 6 tháng.'
WHERE question='Phí dịch vụ chung và phí gửi xe được thu như thế nào?' AND answer='Phí dịch vụ chung và phí gửi xe được thu mỗi 6 tháng. Phí gửi xe chỉ tính cho các tháng có đăng ký trong đợt thu đó: xe đạp thường 50.000 đồng/tháng; xe máy và xe điện (gồm xe máy điện và xe đạp điện) 100.000 đồng/tháng. Đăng ký trong tháng nào thì tính đủ tiền tháng đó, kể cả gửi chưa hết tháng. Xe mới đóng thêm 100.000 đồng làm thẻ một lần vào đợt thu đầu tiên. Bạn xem số tiền và hạn thanh toán tại Hóa đơn & thanh toán → Dịch vụ 6 tháng.';

UPDATE faq_knowledge_base
SET answer='Đăng ký thêm xe hoặc gia hạn xe sắp hết thời gian đăng ký: vào Quản lý gửi xe → Gửi đơn đăng ký; khi gia hạn, ghi đúng biển số hoặc mã xe cũ (ví dụ A101-XD-1). Muốn đổi thông tin xe, hãy liên hệ Ban quản lý. Xe đã đăng ký phải gửi hết thời gian đã chọn; hết thời gian mà không gia hạn thì xe không còn được gửi. Hóa đơn đã lập không tự thay đổi khi bạn thêm hoặc sửa đăng ký xe.'
WHERE question='Đăng ký thêm, huỷ hoặc thay đổi xe đã đăng ký như thế nào?' AND answer='Bạn vào Quản lý gửi xe → Gửi đơn đăng ký, điền thông tin xe rồi gửi Ban quản lý xét duyệt trong vòng 48 giờ. Khi đơn được duyệt, xe xuất hiện trong mục Phương tiện đăng ký cùng biển số hoặc mã xe (ví dụ A101-XD-1) và bạn nhận được thông báo. Muốn đổi thông tin hoặc hủy xe, hãy liên hệ Ban quản lý. Bạn chỉ được hủy khi đã gửi đủ thời gian cam kết, ít nhất 2 tháng. Phí tính theo các tháng có đăng ký trong đợt thu; hóa đơn đã lập không tự thay đổi khi bạn thêm hoặc sửa đăng ký xe.';
