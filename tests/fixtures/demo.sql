-- Synthetic demonstration and test fixture. No real credentials or personal contacts.
BEGIN TRANSACTION;
CREATE TABLE apartment_contracts (
    contract_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment_id    INTEGER NOT NULL REFERENCES apartments(apartment_id),
    resident_id     INTEGER NOT NULL REFERENCES residents(resident_id),
    contract_type   TEXT NOT NULL CHECK (contract_type IN ('ownership','rental')),
    start_date      TEXT NOT NULL,
    end_date        TEXT,
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','expired','terminated'))
);
INSERT INTO "apartment_contracts" VALUES(1,1,1,'ownership','2022-01-01',NULL,'active');
INSERT INTO "apartment_contracts" VALUES(2,2,2,'ownership','2021-06-15',NULL,'active');
INSERT INTO "apartment_contracts" VALUES(3,3,3,'rental','2025-01-01','2026-12-31','active');
INSERT INTO "apartment_contracts" VALUES(4,5,4,'ownership','2020-03-10',NULL,'active');
INSERT INTO "apartment_contracts" VALUES(5,6,5,'ownership','2019-09-01',NULL,'active');
INSERT INTO "apartment_contracts" VALUES(6,8,6,'rental','2024-05-01','2025-04-30','expired');
INSERT INTO "apartment_contracts" VALUES(7,11,7,'ownership','2023-02-14',NULL,'active');
INSERT INTO "apartment_contracts" VALUES(8,12,8,'ownership','2018-07-20',NULL,'active');
INSERT INTO "apartment_contracts" VALUES(9,13,9,'rental','2026-01-01','2026-12-31','active');
INSERT INTO "apartment_contracts" VALUES(10,14,10,'ownership','2022-11-11',NULL,'active');
INSERT INTO "apartment_contracts" VALUES(11,1,11,'rental','2026-03-01','2027-02-28','active');
INSERT INTO "apartment_contracts" VALUES(12,2,12,'rental','2025-08-01','2026-07-31','active');
INSERT INTO "apartment_contracts" VALUES(13,5,13,'ownership','2021-01-01',NULL,'active');
INSERT INTO "apartment_contracts" VALUES(14,6,14,'ownership','2020-10-05',NULL,'active');
INSERT INTO "apartment_contracts" VALUES(15,8,15,'rental','2024-01-01','2024-12-31','terminated');
CREATE TABLE apartments (
    apartment_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,
    block           TEXT,
    floor           INTEGER,
    status          TEXT NOT NULL DEFAULT 'vacant' CHECK (status IN ('vacant','occupied'))
);
INSERT INTO "apartments" VALUES(1,'A101','A',1,'occupied');
INSERT INTO "apartments" VALUES(2,'A102','A',1,'occupied');
INSERT INTO "apartments" VALUES(3,'A203','A',2,'occupied');
INSERT INTO "apartments" VALUES(4,'A204','A',2,'vacant');
INSERT INTO "apartments" VALUES(5,'A305','A',3,'occupied');
INSERT INTO "apartments" VALUES(6,'B101','B',1,'occupied');
INSERT INTO "apartments" VALUES(7,'B102','B',1,'occupied');
INSERT INTO "apartments" VALUES(8,'B203','B',2,'occupied');
INSERT INTO "apartments" VALUES(9,'B204','B',2,'vacant');
INSERT INTO "apartments" VALUES(10,'B305','B',3,'occupied');
INSERT INTO "apartments" VALUES(11,'C101','C',1,'occupied');
INSERT INTO "apartments" VALUES(12,'C102','C',1,'occupied');
INSERT INTO "apartments" VALUES(13,'C203','C',2,'occupied');
INSERT INTO "apartments" VALUES(14,'C204','C',2,'occupied');
INSERT INTO "apartments" VALUES(15,'C305','C',3,'vacant');
INSERT INTO "apartments" VALUES(18,'A103','A',1,'vacant');
INSERT INTO "apartments" VALUES(19,'A104','A',1,'vacant');
INSERT INTO "apartments" VALUES(20,'A105','A',1,'vacant');
INSERT INTO "apartments" VALUES(21,'A106','A',1,'vacant');
INSERT INTO "apartments" VALUES(22,'A107','A',1,'vacant');
INSERT INTO "apartments" VALUES(23,'A108','A',1,'vacant');
INSERT INTO "apartments" VALUES(24,'A109','A',1,'vacant');
INSERT INTO "apartments" VALUES(25,'A110','A',1,'vacant');
INSERT INTO "apartments" VALUES(26,'A201','A',2,'vacant');
INSERT INTO "apartments" VALUES(27,'A202','A',2,'vacant');
INSERT INTO "apartments" VALUES(30,'A205','A',2,'vacant');
INSERT INTO "apartments" VALUES(31,'A206','A',2,'vacant');
INSERT INTO "apartments" VALUES(32,'A207','A',2,'vacant');
INSERT INTO "apartments" VALUES(33,'A208','A',2,'vacant');
INSERT INTO "apartments" VALUES(34,'A209','A',2,'vacant');
INSERT INTO "apartments" VALUES(35,'A210','A',2,'vacant');
INSERT INTO "apartments" VALUES(36,'A301','A',3,'vacant');
INSERT INTO "apartments" VALUES(37,'A302','A',3,'vacant');
INSERT INTO "apartments" VALUES(38,'A303','A',3,'vacant');
INSERT INTO "apartments" VALUES(39,'A304','A',3,'vacant');
INSERT INTO "apartments" VALUES(41,'A306','A',3,'vacant');
INSERT INTO "apartments" VALUES(42,'A307','A',3,'vacant');
INSERT INTO "apartments" VALUES(43,'A308','A',3,'vacant');
INSERT INTO "apartments" VALUES(44,'A309','A',3,'vacant');
INSERT INTO "apartments" VALUES(45,'A310','A',3,'vacant');
INSERT INTO "apartments" VALUES(46,'A401','A',4,'vacant');
INSERT INTO "apartments" VALUES(47,'A402','A',4,'vacant');
INSERT INTO "apartments" VALUES(48,'A403','A',4,'vacant');
INSERT INTO "apartments" VALUES(49,'A404','A',4,'vacant');
INSERT INTO "apartments" VALUES(50,'A405','A',4,'vacant');
INSERT INTO "apartments" VALUES(51,'A406','A',4,'vacant');
INSERT INTO "apartments" VALUES(52,'A407','A',4,'vacant');
INSERT INTO "apartments" VALUES(53,'A408','A',4,'vacant');
INSERT INTO "apartments" VALUES(54,'A409','A',4,'vacant');
INSERT INTO "apartments" VALUES(55,'A410','A',4,'vacant');
INSERT INTO "apartments" VALUES(56,'A501','A',5,'vacant');
INSERT INTO "apartments" VALUES(57,'A502','A',5,'vacant');
INSERT INTO "apartments" VALUES(58,'A503','A',5,'vacant');
INSERT INTO "apartments" VALUES(59,'A504','A',5,'vacant');
INSERT INTO "apartments" VALUES(60,'A505','A',5,'vacant');
INSERT INTO "apartments" VALUES(61,'A506','A',5,'vacant');
INSERT INTO "apartments" VALUES(62,'A507','A',5,'vacant');
INSERT INTO "apartments" VALUES(63,'A508','A',5,'vacant');
INSERT INTO "apartments" VALUES(64,'A509','A',5,'vacant');
INSERT INTO "apartments" VALUES(65,'A510','A',5,'vacant');
INSERT INTO "apartments" VALUES(66,'A601','A',6,'vacant');
INSERT INTO "apartments" VALUES(67,'A602','A',6,'vacant');
INSERT INTO "apartments" VALUES(68,'A603','A',6,'vacant');
INSERT INTO "apartments" VALUES(69,'A604','A',6,'vacant');
INSERT INTO "apartments" VALUES(70,'A605','A',6,'vacant');
INSERT INTO "apartments" VALUES(71,'A606','A',6,'vacant');
INSERT INTO "apartments" VALUES(72,'A607','A',6,'vacant');
INSERT INTO "apartments" VALUES(73,'A608','A',6,'vacant');
INSERT INTO "apartments" VALUES(74,'A609','A',6,'vacant');
INSERT INTO "apartments" VALUES(75,'A610','A',6,'vacant');
INSERT INTO "apartments" VALUES(76,'A701','A',7,'vacant');
INSERT INTO "apartments" VALUES(77,'A702','A',7,'vacant');
INSERT INTO "apartments" VALUES(78,'A703','A',7,'vacant');
INSERT INTO "apartments" VALUES(79,'A704','A',7,'vacant');
INSERT INTO "apartments" VALUES(80,'A705','A',7,'vacant');
INSERT INTO "apartments" VALUES(81,'A706','A',7,'vacant');
INSERT INTO "apartments" VALUES(82,'A707','A',7,'vacant');
INSERT INTO "apartments" VALUES(83,'A708','A',7,'vacant');
INSERT INTO "apartments" VALUES(84,'A709','A',7,'vacant');
INSERT INTO "apartments" VALUES(85,'A710','A',7,'vacant');
INSERT INTO "apartments" VALUES(86,'A801','A',8,'vacant');
INSERT INTO "apartments" VALUES(87,'A802','A',8,'vacant');
INSERT INTO "apartments" VALUES(88,'A803','A',8,'vacant');
INSERT INTO "apartments" VALUES(89,'A804','A',8,'vacant');
INSERT INTO "apartments" VALUES(90,'A805','A',8,'vacant');
INSERT INTO "apartments" VALUES(91,'A806','A',8,'vacant');
INSERT INTO "apartments" VALUES(92,'A807','A',8,'vacant');
INSERT INTO "apartments" VALUES(93,'A808','A',8,'vacant');
INSERT INTO "apartments" VALUES(94,'A809','A',8,'vacant');
INSERT INTO "apartments" VALUES(95,'A810','A',8,'vacant');
INSERT INTO "apartments" VALUES(96,'A901','A',9,'vacant');
INSERT INTO "apartments" VALUES(97,'A902','A',9,'vacant');
INSERT INTO "apartments" VALUES(98,'A903','A',9,'vacant');
INSERT INTO "apartments" VALUES(99,'A904','A',9,'vacant');
INSERT INTO "apartments" VALUES(100,'A905','A',9,'vacant');
INSERT INTO "apartments" VALUES(101,'A906','A',9,'vacant');
INSERT INTO "apartments" VALUES(102,'A907','A',9,'vacant');
INSERT INTO "apartments" VALUES(103,'A908','A',9,'vacant');
INSERT INTO "apartments" VALUES(104,'A909','A',9,'vacant');
INSERT INTO "apartments" VALUES(105,'A910','A',9,'vacant');
INSERT INTO "apartments" VALUES(108,'B103','B',1,'vacant');
INSERT INTO "apartments" VALUES(109,'B104','B',1,'vacant');
INSERT INTO "apartments" VALUES(110,'B105','B',1,'vacant');
INSERT INTO "apartments" VALUES(111,'B106','B',1,'vacant');
INSERT INTO "apartments" VALUES(112,'B107','B',1,'vacant');
INSERT INTO "apartments" VALUES(113,'B108','B',1,'vacant');
INSERT INTO "apartments" VALUES(114,'B109','B',1,'vacant');
INSERT INTO "apartments" VALUES(115,'B110','B',1,'vacant');
INSERT INTO "apartments" VALUES(116,'B201','B',2,'vacant');
INSERT INTO "apartments" VALUES(117,'B202','B',2,'vacant');
INSERT INTO "apartments" VALUES(120,'B205','B',2,'vacant');
INSERT INTO "apartments" VALUES(121,'B206','B',2,'vacant');
INSERT INTO "apartments" VALUES(122,'B207','B',2,'vacant');
INSERT INTO "apartments" VALUES(123,'B208','B',2,'vacant');
INSERT INTO "apartments" VALUES(124,'B209','B',2,'vacant');
INSERT INTO "apartments" VALUES(125,'B210','B',2,'vacant');
INSERT INTO "apartments" VALUES(126,'B301','B',3,'vacant');
INSERT INTO "apartments" VALUES(127,'B302','B',3,'vacant');
INSERT INTO "apartments" VALUES(128,'B303','B',3,'vacant');
INSERT INTO "apartments" VALUES(129,'B304','B',3,'vacant');
INSERT INTO "apartments" VALUES(131,'B306','B',3,'vacant');
INSERT INTO "apartments" VALUES(132,'B307','B',3,'vacant');
INSERT INTO "apartments" VALUES(133,'B308','B',3,'vacant');
INSERT INTO "apartments" VALUES(134,'B309','B',3,'vacant');
INSERT INTO "apartments" VALUES(135,'B310','B',3,'vacant');
INSERT INTO "apartments" VALUES(136,'B401','B',4,'vacant');
INSERT INTO "apartments" VALUES(137,'B402','B',4,'vacant');
INSERT INTO "apartments" VALUES(138,'B403','B',4,'vacant');
INSERT INTO "apartments" VALUES(139,'B404','B',4,'vacant');
INSERT INTO "apartments" VALUES(140,'B405','B',4,'vacant');
INSERT INTO "apartments" VALUES(141,'B406','B',4,'vacant');
INSERT INTO "apartments" VALUES(142,'B407','B',4,'vacant');
INSERT INTO "apartments" VALUES(143,'B408','B',4,'vacant');
INSERT INTO "apartments" VALUES(144,'B409','B',4,'vacant');
INSERT INTO "apartments" VALUES(145,'B410','B',4,'vacant');
INSERT INTO "apartments" VALUES(146,'B501','B',5,'vacant');
INSERT INTO "apartments" VALUES(147,'B502','B',5,'vacant');
INSERT INTO "apartments" VALUES(148,'B503','B',5,'vacant');
INSERT INTO "apartments" VALUES(149,'B504','B',5,'vacant');
INSERT INTO "apartments" VALUES(150,'B505','B',5,'vacant');
INSERT INTO "apartments" VALUES(151,'B506','B',5,'vacant');
INSERT INTO "apartments" VALUES(152,'B507','B',5,'vacant');
INSERT INTO "apartments" VALUES(153,'B508','B',5,'vacant');
INSERT INTO "apartments" VALUES(154,'B509','B',5,'vacant');
INSERT INTO "apartments" VALUES(155,'B510','B',5,'vacant');
INSERT INTO "apartments" VALUES(156,'B601','B',6,'vacant');
INSERT INTO "apartments" VALUES(157,'B602','B',6,'vacant');
INSERT INTO "apartments" VALUES(158,'B603','B',6,'vacant');
INSERT INTO "apartments" VALUES(159,'B604','B',6,'vacant');
INSERT INTO "apartments" VALUES(160,'B605','B',6,'vacant');
INSERT INTO "apartments" VALUES(161,'B606','B',6,'vacant');
INSERT INTO "apartments" VALUES(162,'B607','B',6,'vacant');
INSERT INTO "apartments" VALUES(163,'B608','B',6,'vacant');
INSERT INTO "apartments" VALUES(164,'B609','B',6,'vacant');
INSERT INTO "apartments" VALUES(165,'B610','B',6,'vacant');
INSERT INTO "apartments" VALUES(166,'B701','B',7,'vacant');
INSERT INTO "apartments" VALUES(167,'B702','B',7,'vacant');
INSERT INTO "apartments" VALUES(168,'B703','B',7,'vacant');
INSERT INTO "apartments" VALUES(169,'B704','B',7,'vacant');
INSERT INTO "apartments" VALUES(170,'B705','B',7,'vacant');
INSERT INTO "apartments" VALUES(171,'B706','B',7,'vacant');
INSERT INTO "apartments" VALUES(172,'B707','B',7,'vacant');
INSERT INTO "apartments" VALUES(173,'B708','B',7,'vacant');
INSERT INTO "apartments" VALUES(174,'B709','B',7,'vacant');
INSERT INTO "apartments" VALUES(175,'B710','B',7,'vacant');
INSERT INTO "apartments" VALUES(176,'B801','B',8,'vacant');
INSERT INTO "apartments" VALUES(177,'B802','B',8,'vacant');
INSERT INTO "apartments" VALUES(178,'B803','B',8,'vacant');
INSERT INTO "apartments" VALUES(179,'B804','B',8,'vacant');
INSERT INTO "apartments" VALUES(180,'B805','B',8,'vacant');
INSERT INTO "apartments" VALUES(181,'B806','B',8,'vacant');
INSERT INTO "apartments" VALUES(182,'B807','B',8,'vacant');
INSERT INTO "apartments" VALUES(183,'B808','B',8,'vacant');
INSERT INTO "apartments" VALUES(184,'B809','B',8,'vacant');
INSERT INTO "apartments" VALUES(185,'B810','B',8,'vacant');
INSERT INTO "apartments" VALUES(186,'B901','B',9,'vacant');
INSERT INTO "apartments" VALUES(187,'B902','B',9,'vacant');
INSERT INTO "apartments" VALUES(188,'B903','B',9,'vacant');
INSERT INTO "apartments" VALUES(189,'B904','B',9,'vacant');
INSERT INTO "apartments" VALUES(190,'B905','B',9,'vacant');
INSERT INTO "apartments" VALUES(191,'B906','B',9,'vacant');
INSERT INTO "apartments" VALUES(192,'B907','B',9,'vacant');
INSERT INTO "apartments" VALUES(193,'B908','B',9,'vacant');
INSERT INTO "apartments" VALUES(194,'B909','B',9,'vacant');
INSERT INTO "apartments" VALUES(195,'B910','B',9,'vacant');
INSERT INTO "apartments" VALUES(198,'C103','C',1,'vacant');
INSERT INTO "apartments" VALUES(199,'C104','C',1,'vacant');
INSERT INTO "apartments" VALUES(200,'C105','C',1,'vacant');
INSERT INTO "apartments" VALUES(201,'C106','C',1,'vacant');
INSERT INTO "apartments" VALUES(202,'C107','C',1,'vacant');
INSERT INTO "apartments" VALUES(203,'C108','C',1,'vacant');
INSERT INTO "apartments" VALUES(204,'C109','C',1,'vacant');
INSERT INTO "apartments" VALUES(205,'C110','C',1,'vacant');
INSERT INTO "apartments" VALUES(206,'C201','C',2,'vacant');
INSERT INTO "apartments" VALUES(207,'C202','C',2,'vacant');
INSERT INTO "apartments" VALUES(210,'C205','C',2,'vacant');
INSERT INTO "apartments" VALUES(211,'C206','C',2,'vacant');
INSERT INTO "apartments" VALUES(212,'C207','C',2,'vacant');
INSERT INTO "apartments" VALUES(213,'C208','C',2,'vacant');
INSERT INTO "apartments" VALUES(214,'C209','C',2,'vacant');
INSERT INTO "apartments" VALUES(215,'C210','C',2,'vacant');
INSERT INTO "apartments" VALUES(216,'C301','C',3,'vacant');
INSERT INTO "apartments" VALUES(217,'C302','C',3,'vacant');
INSERT INTO "apartments" VALUES(218,'C303','C',3,'vacant');
INSERT INTO "apartments" VALUES(219,'C304','C',3,'vacant');
INSERT INTO "apartments" VALUES(221,'C306','C',3,'vacant');
INSERT INTO "apartments" VALUES(222,'C307','C',3,'vacant');
INSERT INTO "apartments" VALUES(223,'C308','C',3,'vacant');
INSERT INTO "apartments" VALUES(224,'C309','C',3,'vacant');
INSERT INTO "apartments" VALUES(225,'C310','C',3,'vacant');
INSERT INTO "apartments" VALUES(226,'C401','C',4,'vacant');
INSERT INTO "apartments" VALUES(227,'C402','C',4,'vacant');
INSERT INTO "apartments" VALUES(228,'C403','C',4,'vacant');
INSERT INTO "apartments" VALUES(229,'C404','C',4,'vacant');
INSERT INTO "apartments" VALUES(230,'C405','C',4,'vacant');
INSERT INTO "apartments" VALUES(231,'C406','C',4,'vacant');
INSERT INTO "apartments" VALUES(232,'C407','C',4,'vacant');
INSERT INTO "apartments" VALUES(233,'C408','C',4,'vacant');
INSERT INTO "apartments" VALUES(234,'C409','C',4,'vacant');
INSERT INTO "apartments" VALUES(235,'C410','C',4,'vacant');
INSERT INTO "apartments" VALUES(236,'C501','C',5,'vacant');
INSERT INTO "apartments" VALUES(237,'C502','C',5,'vacant');
INSERT INTO "apartments" VALUES(238,'C503','C',5,'vacant');
INSERT INTO "apartments" VALUES(239,'C504','C',5,'vacant');
INSERT INTO "apartments" VALUES(240,'C505','C',5,'vacant');
INSERT INTO "apartments" VALUES(241,'C506','C',5,'vacant');
INSERT INTO "apartments" VALUES(242,'C507','C',5,'vacant');
INSERT INTO "apartments" VALUES(243,'C508','C',5,'vacant');
INSERT INTO "apartments" VALUES(244,'C509','C',5,'vacant');
INSERT INTO "apartments" VALUES(245,'C510','C',5,'vacant');
INSERT INTO "apartments" VALUES(246,'C601','C',6,'vacant');
INSERT INTO "apartments" VALUES(247,'C602','C',6,'vacant');
INSERT INTO "apartments" VALUES(248,'C603','C',6,'vacant');
INSERT INTO "apartments" VALUES(249,'C604','C',6,'vacant');
INSERT INTO "apartments" VALUES(250,'C605','C',6,'vacant');
INSERT INTO "apartments" VALUES(251,'C606','C',6,'vacant');
INSERT INTO "apartments" VALUES(252,'C607','C',6,'vacant');
INSERT INTO "apartments" VALUES(253,'C608','C',6,'vacant');
INSERT INTO "apartments" VALUES(254,'C609','C',6,'vacant');
INSERT INTO "apartments" VALUES(255,'C610','C',6,'vacant');
INSERT INTO "apartments" VALUES(256,'C701','C',7,'vacant');
INSERT INTO "apartments" VALUES(257,'C702','C',7,'vacant');
INSERT INTO "apartments" VALUES(258,'C703','C',7,'vacant');
INSERT INTO "apartments" VALUES(259,'C704','C',7,'vacant');
INSERT INTO "apartments" VALUES(260,'C705','C',7,'vacant');
INSERT INTO "apartments" VALUES(261,'C706','C',7,'vacant');
INSERT INTO "apartments" VALUES(262,'C707','C',7,'vacant');
INSERT INTO "apartments" VALUES(263,'C708','C',7,'vacant');
INSERT INTO "apartments" VALUES(264,'C709','C',7,'vacant');
INSERT INTO "apartments" VALUES(265,'C710','C',7,'vacant');
INSERT INTO "apartments" VALUES(266,'C801','C',8,'vacant');
INSERT INTO "apartments" VALUES(267,'C802','C',8,'vacant');
INSERT INTO "apartments" VALUES(268,'C803','C',8,'vacant');
INSERT INTO "apartments" VALUES(269,'C804','C',8,'vacant');
INSERT INTO "apartments" VALUES(270,'C805','C',8,'vacant');
INSERT INTO "apartments" VALUES(271,'C806','C',8,'vacant');
INSERT INTO "apartments" VALUES(272,'C807','C',8,'vacant');
INSERT INTO "apartments" VALUES(273,'C808','C',8,'vacant');
INSERT INTO "apartments" VALUES(274,'C809','C',8,'vacant');
INSERT INTO "apartments" VALUES(275,'C810','C',8,'vacant');
INSERT INTO "apartments" VALUES(276,'C901','C',9,'vacant');
INSERT INTO "apartments" VALUES(277,'C902','C',9,'vacant');
INSERT INTO "apartments" VALUES(278,'C903','C',9,'vacant');
INSERT INTO "apartments" VALUES(279,'C904','C',9,'vacant');
INSERT INTO "apartments" VALUES(280,'C905','C',9,'vacant');
INSERT INTO "apartments" VALUES(281,'C906','C',9,'vacant');
INSERT INTO "apartments" VALUES(282,'C907','C',9,'vacant');
INSERT INTO "apartments" VALUES(283,'C908','C',9,'vacant');
INSERT INTO "apartments" VALUES(284,'C909','C',9,'vacant');
INSERT INTO "apartments" VALUES(285,'C910','C',9,'vacant');
CREATE TABLE complaints (
    complaint_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id      INTEGER NOT NULL,
    type             TEXT NOT NULL CHECK (type IN ('complaint','registration')),
    category         TEXT,
    content          TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','resolved','rejected')),
    response         TEXT,
    created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at      TEXT
);
INSERT INTO "complaints" VALUES(1,1,'complaint','Yeu cau mau','Noi dung mau 1','resolved','Phan hoi mau','2026-10-03 04:47:26','2026-08-03 10:00:00');
INSERT INTO "complaints" VALUES(2,2,'registration','Yeu cau mau','Noi dung mau 2','resolved','Phan hoi mau','2026-10-03 04:47:26','2026-08-04 09:00:00');
INSERT INTO "complaints" VALUES(3,3,'complaint','Yeu cau mau','Noi dung mau 3','processing',NULL,'2026-10-03 04:47:26',NULL);
INSERT INTO "complaints" VALUES(4,4,'complaint','Yeu cau mau','Noi dung mau 4','resolved','Phan hoi mau','2026-10-03 04:47:26','2026-08-06 15:00:00');
INSERT INTO "complaints" VALUES(5,5,'registration','Yeu cau mau','Noi dung mau 5','resolved','Phan hoi mau','2026-10-03 04:47:26','2026-08-02 11:00:00');
INSERT INTO "complaints" VALUES(6,6,'complaint','Yeu cau mau','Noi dung mau 6','pending',NULL,'2026-10-03 04:47:26',NULL);
INSERT INTO "complaints" VALUES(7,7,'complaint','Yeu cau mau','Noi dung mau 7','processing',NULL,'2026-10-03 04:47:26',NULL);
INSERT INTO "complaints" VALUES(8,8,'registration','Yeu cau mau','Noi dung mau 8','resolved','Phan hoi mau','2026-10-03 04:47:26','2026-08-07 16:00:00');
INSERT INTO "complaints" VALUES(9,9,'complaint','Yeu cau mau','Noi dung mau 9','processing',NULL,'2026-10-03 04:47:26',NULL);
INSERT INTO "complaints" VALUES(10,10,'complaint','Yeu cau mau','Noi dung mau 10','resolved','Phan hoi mau','2026-10-03 04:47:26','2026-08-08 14:00:00');
INSERT INTO "complaints" VALUES(11,11,'registration','Yeu cau mau','Noi dung mau 11','pending',NULL,'2026-10-03 04:47:26',NULL);
INSERT INTO "complaints" VALUES(12,12,'complaint','Yeu cau mau','Noi dung mau 12','processing',NULL,'2026-10-03 04:47:26',NULL);
INSERT INTO "complaints" VALUES(13,13,'complaint','Yeu cau mau','Noi dung mau 13','resolved','Phan hoi mau','2026-10-03 04:47:26','2026-08-10 09:30:00');
INSERT INTO "complaints" VALUES(14,14,'registration','Yeu cau mau','Noi dung mau 14','pending',NULL,'2026-10-03 04:47:26',NULL);
INSERT INTO "complaints" VALUES(15,15,'complaint','Yeu cau mau','Noi dung mau 15','rejected','Phan hoi mau','2026-10-03 04:47:26','2026-08-11 13:00:00');
CREATE TABLE faq_knowledge_base (
    faq_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category        TEXT,
    question        TEXT NOT NULL,
    answer          TEXT NOT NULL
);
INSERT INTO "faq_knowledge_base" VALUES(1,'chính sách','Giờ giấc ra vào chung cư như thế nào?','Cư dân ra vào tự do 24/7, khách cần đăng ký tại quầy bảo vệ');
INSERT INTO "faq_knowledge_base" VALUES(2,'chính sách','Có được nuôi thú cưng trong chung cư không?','Được phép nuôi thú cưng nhỏ, phải đăng ký với ban quản lý');
INSERT INTO "faq_knowledge_base" VALUES(3,'chính sách','Có chỗ đậu xe cho khách không?','Có khu vực gửi xe vãng lai tại tầng hầm B1');
INSERT INTO "faq_knowledge_base" VALUES(4,'chính sách','Giờ hoạt động của phòng sinh hoạt cộng đồng?','Từ 7h đến 22h hàng ngày');
INSERT INTO "faq_knowledge_base" VALUES(5,'điều khoản','Quy định về sửa chữa, cải tạo căn hộ?','Phải đăng ký với ban quản lý trước khi thi công, không thi công sau 19h');
INSERT INTO "faq_knowledge_base" VALUES(6,'chính sách','Làm sao để đăng ký gửi xe tháng?','Đăng ký qua web hoặc trực tiếp tại văn phòng ban quản lý');
INSERT INTO "faq_knowledge_base" VALUES(7,'chính sách','Có wifi miễn phí khu vực sảnh không?','Có wifi miễn phí tại sảnh chính và phòng sinh hoạt cộng đồng');
INSERT INTO "faq_knowledge_base" VALUES(8,'điều khoản','Quy định về việc phơi đồ ngoài ban công?','Không được phơi đồ ra mặt ngoài ban công gây mất mỹ quan');
INSERT INTO "faq_knowledge_base" VALUES(9,'chính sách','Chung cư có hỗ trợ chuyển đồ khi dọn vào/ra không?','Không, cư dân tự túc');
INSERT INTO "faq_knowledge_base" VALUES(10,'điều khoản','Mức phạt nếu vi phạm nội quy gửi xe?','Phạt theo quy định nội bộ, mức phạt được niêm yết tại bảng tin');
INSERT INTO "faq_knowledge_base" VALUES(11,'điều khoản','Chính sách xử lý khiếu nại mất bao lâu?','Trong vòng 3-5 ngày làm việc kể từ khi tiếp nhận');
CREATE TABLE guest_parking_daily (
    record_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    parking_date     TEXT NOT NULL UNIQUE,
    daily_revenue    INTEGER NOT NULL
);
INSERT INTO "guest_parking_daily" VALUES(1,'2026-08-01',210000);
INSERT INTO "guest_parking_daily" VALUES(2,'2026-08-02',240000);
INSERT INTO "guest_parking_daily" VALUES(3,'2026-08-03',150000);
INSERT INTO "guest_parking_daily" VALUES(4,'2026-08-04',215000);
INSERT INTO "guest_parking_daily" VALUES(5,'2026-08-05',210000);
INSERT INTO "guest_parking_daily" VALUES(6,'2026-08-06',275000);
INSERT INTO "guest_parking_daily" VALUES(7,'2026-08-07',160000);
INSERT INTO "guest_parking_daily" VALUES(8,'2026-08-08',190000);
INSERT INTO "guest_parking_daily" VALUES(9,'2026-08-09',200000);
INSERT INTO "guest_parking_daily" VALUES(10,'2026-08-10',185000);
INSERT INTO "guest_parking_daily" VALUES(11,'2026-08-11',165000);
INSERT INTO "guest_parking_daily" VALUES(12,'2026-08-12',230000);
INSERT INTO "guest_parking_daily" VALUES(13,'2026-08-13',195000);
INSERT INTO "guest_parking_daily" VALUES(14,'2026-08-14',250000);
INSERT INTO "guest_parking_daily" VALUES(15,'2026-08-15',140000);
CREATE TABLE locations (
    location_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    block           TEXT,
    floor           TEXT,
    description     TEXT
);
INSERT INTO "locations" VALUES(1,'Phòng camera an ninh','A','1','Phòng giám sát camera trung tâm, cạnh sảnh chính toà A');
INSERT INTO "locations" VALUES(2,'Hiệu thuốc','A','1','Hiệu thuốc tiện lợi tại tầng trệt toà A');
INSERT INTO "locations" VALUES(3,'Phòng sinh hoạt cộng đồng','B','1','Khu vực sinh hoạt chung, tổ chức họp cư dân');
INSERT INTO "locations" VALUES(4,'Phòng kỹ thuật điện','A','B1','Phòng kỹ thuật điện tổng, tầng hầm B1');
INSERT INTO "locations" VALUES(5,'Phòng kỹ thuật nước','A','B1','Phòng kỹ thuật hệ thống cấp thoát nước, tầng hầm B1');
INSERT INTO "locations" VALUES(6,'Bãi gửi xe máy','B','B1','Khu vực gửi xe máy cư dân, tầng hầm B1');
INSERT INTO "locations" VALUES(7,'Quầy bảo vệ chính','A','1','Quầy trực bảo vệ 24/7 tại sảnh chính');
INSERT INTO "locations" VALUES(8,'Khu vui chơi trẻ em','C','1','Sân chơi ngoài trời dành cho trẻ em, cạnh toà C');
INSERT INTO "locations" VALUES(9,'Phòng gym','B','1','Phòng tập gym cơ bản cho cư dân');
INSERT INTO "locations" VALUES(10,'Cửa hàng tiện lợi','C','1','Cửa hàng tạp hoá, tầng trệt toà C');
INSERT INTO "locations" VALUES(11,'Văn phòng ban quản lý','A','1','Nơi tiếp nhận khiếu nại, đăng ký dịch vụ');
INSERT INTO "locations" VALUES(12,'Trạm sạc xe điện','B','B1','Khu vực sạc xe máy điện, tầng hầm B1');
INSERT INTO "locations" VALUES(13,'Phòng rác kỹ thuật','C','B1','Khu tập kết rác thải, tầng hầm B1 toà C');
INSERT INTO "locations" VALUES(14,'Sân vườn trung tâm','A','1','Không gian xanh giữa 3 toà A, B, C');
CREATE TABLE maintenance_tickets (
    ticket_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment_id     INTEGER,
    technician_id    INTEGER REFERENCES technicians(technician_id),
    type             TEXT NOT NULL CHECK (type IN ('repair','cut_service','restore_service','maintenance')),
    description      TEXT,
    priority         TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high')),
    status           TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','in_progress','completed')),
    created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at     TEXT
);
INSERT INTO "maintenance_tickets" VALUES(1,3,2,'cut_service','Yeu cau sua chua mau 1','high','completed','2026-10-03 04:47:26','2026-08-11 10:00:00');
INSERT INTO "maintenance_tickets" VALUES(2,13,2,'cut_service','Yeu cau sua chua mau 2','high','in_progress','2026-10-03 04:47:26',NULL);
INSERT INTO "maintenance_tickets" VALUES(3,NULL,3,'maintenance','Yeu cau sua chua mau 3','medium','completed','2026-10-03 04:47:26','2026-08-05 15:00:00');
INSERT INTO "maintenance_tickets" VALUES(4,NULL,3,'maintenance','Yeu cau sua chua mau 4','high','completed','2026-10-03 04:47:26','2026-08-06 16:00:00');
INSERT INTO "maintenance_tickets" VALUES(5,1,1,'repair','Yeu cau sua chua mau 5','high','completed','2026-10-03 04:47:26','2026-08-02 11:00:00');
INSERT INTO "maintenance_tickets" VALUES(6,6,1,'repair','Yeu cau sua chua mau 6','low','completed','2026-10-03 04:47:26','2026-08-03 09:30:00');
INSERT INTO "maintenance_tickets" VALUES(7,8,5,'repair','Yeu cau sua chua mau 7','medium','in_progress','2026-10-03 04:47:26',NULL);
INSERT INTO "maintenance_tickets" VALUES(8,11,5,'repair','Yeu cau sua chua mau 8','medium','completed','2026-10-03 04:47:26','2026-08-07 14:00:00');
INSERT INTO "maintenance_tickets" VALUES(9,14,4,'repair','Yeu cau sua chua mau 9','low','pending','2026-10-03 04:47:26',NULL);
INSERT INTO "maintenance_tickets" VALUES(10,NULL,6,'maintenance','Yeu cau sua chua mau 10','medium','completed','2026-10-03 04:47:26','2026-08-09 08:00:00');
INSERT INTO "maintenance_tickets" VALUES(11,2,4,'repair','Yeu cau sua chua mau 11','high','in_progress','2026-10-03 04:47:26',NULL);
INSERT INTO "maintenance_tickets" VALUES(12,3,2,'restore_service','Yeu cau sua chua mau 12','high','pending','2026-10-03 04:47:26',NULL);
INSERT INTO "maintenance_tickets" VALUES(13,5,8,'repair','Yeu cau sua chua mau 13','medium','completed','2026-10-03 04:47:26','2026-08-13 10:30:00');
INSERT INTO "maintenance_tickets" VALUES(14,12,7,'repair','Yeu cau sua chua mau 14','low','pending','2026-10-03 04:47:26',NULL);
INSERT INTO "maintenance_tickets" VALUES(15,NULL,9,'maintenance','Yeu cau sua chua mau 15','medium','completed','2026-10-03 04:47:26','2026-08-14 17:00:00');
CREATE TABLE monthly_invoices (
    invoice_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment_id    INTEGER NOT NULL,
    period          TEXT NOT NULL,
    electricity_fee INTEGER NOT NULL DEFAULT 0,
    water_fee       INTEGER NOT NULL DEFAULT 0,
    total_amount    INTEGER NOT NULL DEFAULT 0,
    due_date        TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'unpaid' CHECK (status IN ('unpaid','paid','overdue')),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_monthly_invoice UNIQUE (apartment_id, period)
);
INSERT INTO "monthly_invoices" VALUES(1,1,'2026-07',350000,120000,470000,'2026-08-10','paid','2026-10-03 04:47:26');
INSERT INTO "monthly_invoices" VALUES(2,2,'2026-07',420000,150000,570000,'2026-08-10','paid','2026-10-03 04:47:26');
INSERT INTO "monthly_invoices" VALUES(3,3,'2026-07',280000,100000,380000,'2026-08-10','overdue','2026-10-03 04:47:26');
INSERT INTO "monthly_invoices" VALUES(4,5,'2026-07',300000,110000,410000,'2026-08-10','paid','2026-10-03 04:47:26');
INSERT INTO "monthly_invoices" VALUES(5,6,'2026-07',500000,200000,700000,'2026-08-10','paid','2026-10-03 04:47:26');
INSERT INTO "monthly_invoices" VALUES(6,8,'2026-07',260000,90000,350000,'2026-08-10','unpaid','2026-10-03 04:47:26');
INSERT INTO "monthly_invoices" VALUES(7,11,'2026-07',240000,80000,320000,'2026-08-10','paid','2026-10-03 04:47:26');
INSERT INTO "monthly_invoices" VALUES(8,12,'2026-07',250000,85000,335000,'2026-08-10','paid','2026-10-03 04:47:26');
INSERT INTO "monthly_invoices" VALUES(9,13,'2026-07',320000,130000,450000,'2026-08-10','overdue','2026-10-03 04:47:26');
INSERT INTO "monthly_invoices" VALUES(10,14,'2026-07',310000,125000,435000,'2026-08-10','paid','2026-10-03 04:47:26');
INSERT INTO "monthly_invoices" VALUES(11,1,'2026-08',360000,125000,485000,'2026-09-10','unpaid','2026-10-03 04:47:26');
INSERT INTO "monthly_invoices" VALUES(12,2,'2026-08',400000,140000,540000,'2026-09-10','paid','2026-10-03 04:47:26');
INSERT INTO "monthly_invoices" VALUES(13,5,'2026-08',310000,115000,425000,'2026-09-10','paid','2026-10-03 04:47:26');
INSERT INTO "monthly_invoices" VALUES(14,6,'2026-08',480000,190000,670000,'2026-09-10','paid','2026-10-03 04:47:26');
INSERT INTO "monthly_invoices" VALUES(15,11,'2026-08',230000,78000,308000,'2026-09-10','paid','2026-10-03 04:47:26');
CREATE TABLE monthly_payments (
    payment_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id       INTEGER NOT NULL REFERENCES monthly_invoices(invoice_id),
    amount           INTEGER NOT NULL,
    payment_method   TEXT NOT NULL CHECK (payment_method IN ('QR','cash','bank_transfer')),
    transaction_code TEXT,
    paid_at          TEXT,
    status           TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('success','failed','pending'))
);
INSERT INTO "monthly_payments" VALUES(1,1,470000,'QR','DEMO-monthly_payments-1','2026-08-08 09:15:00','success');
INSERT INTO "monthly_payments" VALUES(2,2,570000,'QR','DEMO-monthly_payments-2','2026-08-08 10:02:00','success');
INSERT INTO "monthly_payments" VALUES(3,4,410000,'bank_transfer','DEMO-monthly_payments-3','2026-08-07 14:30:00','success');
INSERT INTO "monthly_payments" VALUES(4,5,700000,'QR','DEMO-monthly_payments-4','2026-08-06 08:45:00','success');
INSERT INTO "monthly_payments" VALUES(5,7,320000,'cash','DEMO-monthly_payments-5','2026-08-05 16:00:00','success');
INSERT INTO "monthly_payments" VALUES(6,8,335000,'QR','DEMO-monthly_payments-6','2026-08-05 17:20:00','success');
INSERT INTO "monthly_payments" VALUES(7,10,435000,'QR','DEMO-monthly_payments-7','2026-08-04 11:10:00','success');
INSERT INTO "monthly_payments" VALUES(8,14,670000,'bank_transfer','DEMO-monthly_payments-8','2026-08-03 13:25:00','success');
INSERT INTO "monthly_payments" VALUES(9,3,380000,'QR','DEMO-monthly_payments-9',NULL,'failed');
INSERT INTO "monthly_payments" VALUES(10,9,450000,'QR','DEMO-monthly_payments-10',NULL,'failed');
INSERT INTO "monthly_payments" VALUES(11,6,200000,'QR','DEMO-monthly_payments-11','2026-08-12 09:00:00','pending');
INSERT INTO "monthly_payments" VALUES(12,11,200000,'QR','DEMO-monthly_payments-12',NULL,'pending');
INSERT INTO "monthly_payments" VALUES(13,12,540000,'QR','DEMO-monthly_payments-13','2026-09-02 10:30:00','success');
INSERT INTO "monthly_payments" VALUES(14,13,425000,'cash','DEMO-monthly_payments-14','2026-09-03 15:45:00','success');
INSERT INTO "monthly_payments" VALUES(15,15,308000,'QR','DEMO-monthly_payments-15','2026-09-04 08:50:00','success');
CREATE TABLE notification_logs (
    log_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_id  INTEGER NOT NULL REFERENCES notifications(notification_id),
    resident_id      INTEGER NOT NULL,
    is_read          INTEGER NOT NULL DEFAULT 0,
    sent_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO "notification_logs" VALUES(6,3,3,1,'2026-08-05 10:00:00');
INSERT INTO "notification_logs" VALUES(7,4,9,0,'2026-08-05 10:05:00');
INSERT INTO "notification_logs" VALUES(10,7,4,1,'2026-08-02 11:35:00');
INSERT INTO "notification_logs" VALUES(12,9,1,1,'2026-08-03 10:35:00');
INSERT INTO "notification_logs" VALUES(14,11,3,1,'2026-08-11 09:05:00');
INSERT INTO "notification_logs" VALUES(15,13,10,0,'2026-08-13 16:05:00');
CREATE TABLE notifications (
    notification_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    type                 TEXT NOT NULL CHECK (type IN ('general','private')),
    title                TEXT NOT NULL,
    content              TEXT,
    target_apartment_id  INTEGER,
    created_by           INTEGER,
    created_at           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO "notifications" VALUES(3,'private','Thong bao mau 3','Noi dung thong bao mau de kiem thu.',3,2,'2026-08-05 10:00:00');
INSERT INTO "notifications" VALUES(4,'private','Thong bao mau 4','Noi dung thong bao mau de kiem thu.',13,2,'2026-08-05 10:05:00');
INSERT INTO "notifications" VALUES(7,'private','Thong bao mau 7','Noi dung thong bao mau de kiem thu.',5,1,'2026-08-02 11:30:00');
INSERT INTO "notifications" VALUES(9,'private','Thong bao mau 9','Noi dung thong bao mau de kiem thu.',1,1,'2026-08-03 10:30:00');
INSERT INTO "notifications" VALUES(11,'private','Thong bao mau 11','Noi dung thong bao mau de kiem thu.',3,2,'2026-08-11 09:00:00');
INSERT INTO "notifications" VALUES(13,'private','Thong bao mau 13','Noi dung thong bao mau de kiem thu.',9,3,'2026-08-13 16:00:00');
INSERT INTO "notifications" VALUES(15,'private','Thong bao mau 15','Noi dung thong bao mau de kiem thu.',6,2,'2026-08-06 09:00:00');
INSERT INTO "notifications" VALUES(16,'general','Thong bao mau 16','Noi dung thong bao mau de kiem thu.',NULL,1,'2026-10-01 08:00:00');
INSERT INTO "notifications" VALUES(17,'general','Thong bao mau 17','Noi dung thong bao mau de kiem thu.',NULL,1,'2026-10-01 09:30:00');
INSERT INTO "notifications" VALUES(18,'general','Thong bao mau 18','Noi dung thong bao mau de kiem thu.',NULL,2,'2026-10-02 08:00:00');
INSERT INTO "notifications" VALUES(19,'general','Thong bao mau 19','Noi dung thong bao mau de kiem thu.',NULL,2,'2026-10-02 10:15:00');
INSERT INTO "notifications" VALUES(20,'general','Thong bao mau 20','Noi dung thong bao mau de kiem thu.',NULL,1,'2026-10-03 08:30:00');
INSERT INTO "notifications" VALUES(21,'general','Thong bao mau 21','Noi dung thong bao mau de kiem thu.',NULL,1,'2026-10-03 14:00:00');
INSERT INTO "notifications" VALUES(22,'general','Thong bao mau 22','Noi dung thong bao mau de kiem thu.',NULL,2,'2026-10-04 08:00:00');
INSERT INTO "notifications" VALUES(23,'general','Thong bao mau 23','Noi dung thong bao mau de kiem thu.',NULL,2,'2026-10-04 09:00:00');
INSERT INTO "notifications" VALUES(24,'general','Thong bao mau 24','Noi dung thong bao mau de kiem thu.',NULL,1,'2026-10-05 08:00:00');
INSERT INTO "notifications" VALUES(25,'general','Thong bao mau 25','Noi dung thong bao mau de kiem thu.',NULL,1,'2026-10-05 10:30:00');
INSERT INTO "notifications" VALUES(26,'general','Thong bao mau 26','Noi dung thong bao mau de kiem thu.',NULL,2,'2026-10-06 08:00:00');
INSERT INTO "notifications" VALUES(27,'general','Thong bao mau 27','Noi dung thong bao mau de kiem thu.',NULL,1,'2026-10-06 10:00:00');
INSERT INTO "notifications" VALUES(28,'general','Thong bao mau 28','Noi dung thong bao mau de kiem thu.',NULL,2,'2026-10-07 07:30:00');
INSERT INTO "notifications" VALUES(29,'general','Thong bao mau 29','Noi dung thong bao mau de kiem thu.',NULL,2,'2026-10-07 09:00:00');
INSERT INTO "notifications" VALUES(30,'general','Thong bao mau 30','Noi dung thong bao mau de kiem thu.',NULL,1,'2026-10-08 08:00:00');
INSERT INTO "notifications" VALUES(31,'general','Thong bao mau 31','Noi dung thong bao mau de kiem thu.',NULL,1,'2026-10-08 10:00:00');
INSERT INTO "notifications" VALUES(32,'general','Thong bao mau 32','Noi dung thong bao mau de kiem thu.',NULL,2,'2026-10-09 08:30:00');
INSERT INTO "notifications" VALUES(33,'general','Thong bao mau 33','Noi dung thong bao mau de kiem thu.',NULL,2,'2026-10-09 10:00:00');
INSERT INTO "notifications" VALUES(34,'general','Thong bao mau 34','Noi dung thong bao mau de kiem thu.',NULL,1,'2026-10-10 08:00:00');
INSERT INTO "notifications" VALUES(35,'general','Thong bao mau 35','Noi dung thong bao mau de kiem thu.',NULL,1,'2026-10-10 10:00:00');
INSERT INTO "notifications" VALUES(36,'general','Thong bao mau 36','Noi dung thong bao mau de kiem thu.',NULL,2,'2026-10-11 08:30:00');
INSERT INTO "notifications" VALUES(37,'general','Thong bao mau 37','Noi dung thong bao mau de kiem thu.',NULL,2,'2026-10-11 15:00:00');
INSERT INTO "notifications" VALUES(38,'general','Thong bao mau 38','Noi dung thong bao mau de kiem thu.',NULL,1,'2026-10-12 08:00:00');
INSERT INTO "notifications" VALUES(39,'general','Thong bao mau 39','Noi dung thong bao mau de kiem thu.',NULL,1,'2026-10-12 10:00:00');
INSERT INTO "notifications" VALUES(40,'general','Thong bao mau 40','Noi dung thong bao mau de kiem thu.',NULL,2,'2026-10-13 08:00:00');
INSERT INTO "notifications" VALUES(41,'general','Thong bao mau 41','Noi dung thong bao mau de kiem thu.',NULL,2,'2026-10-13 10:30:00');
INSERT INTO "notifications" VALUES(42,'general','Thong bao mau 42','Noi dung thong bao mau de kiem thu.',NULL,1,'2026-10-14 08:00:00');
INSERT INTO "notifications" VALUES(43,'general','Thong bao mau 43','Noi dung thong bao mau de kiem thu.',NULL,1,'2026-10-14 10:00:00');
INSERT INTO "notifications" VALUES(44,'general','Thong bao mau 44','Noi dung thong bao mau de kiem thu.',NULL,2,'2026-10-15 08:00:00');
INSERT INTO "notifications" VALUES(45,'general','Thong bao mau 45','Noi dung thong bao mau de kiem thu.',NULL,2,'2026-10-16 08:00:00');
CREATE TABLE residents (
    resident_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER,
    full_name       TEXT NOT NULL,
    id_card         TEXT,
    phone           TEXT,
    relation_type   TEXT NOT NULL CHECK (relation_type IN ('owner','tenant'))
);
INSERT INTO "residents" VALUES(1,3,'Cu dan mau 1',NULL,NULL,'owner');
INSERT INTO "residents" VALUES(2,4,'Cu dan mau 2',NULL,NULL,'owner');
INSERT INTO "residents" VALUES(3,5,'Cu dan mau 3',NULL,NULL,'tenant');
INSERT INTO "residents" VALUES(4,6,'Cu dan mau 4',NULL,NULL,'owner');
INSERT INTO "residents" VALUES(5,7,'Cu dan mau 5',NULL,NULL,'owner');
INSERT INTO "residents" VALUES(6,8,'Cu dan mau 6',NULL,NULL,'tenant');
INSERT INTO "residents" VALUES(7,9,'Cu dan mau 7',NULL,NULL,'owner');
INSERT INTO "residents" VALUES(8,10,'Cu dan mau 8',NULL,NULL,'owner');
INSERT INTO "residents" VALUES(9,14,'Cu dan mau 9',NULL,NULL,'tenant');
INSERT INTO "residents" VALUES(10,15,'Cu dan mau 10',NULL,NULL,'owner');
INSERT INTO "residents" VALUES(11,3,'Cu dan mau 11',NULL,NULL,'tenant');
INSERT INTO "residents" VALUES(12,4,'Cu dan mau 12',NULL,NULL,'tenant');
INSERT INTO "residents" VALUES(13,5,'Cu dan mau 13',NULL,NULL,'owner');
INSERT INTO "residents" VALUES(14,6,'Cu dan mau 14',NULL,NULL,'owner');
INSERT INTO "residents" VALUES(15,7,'Cu dan mau 15',NULL,NULL,'tenant');
CREATE TABLE semiannual_invoices (
    invoice_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment_id    INTEGER NOT NULL,
    period          TEXT NOT NULL,
    service_fee     INTEGER NOT NULL DEFAULT 0,
    parking_fee     INTEGER NOT NULL DEFAULT 0,
    total_amount    INTEGER NOT NULL DEFAULT 0,
    due_date        TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'unpaid' CHECK (status IN ('unpaid','paid','overdue')),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_semiannual_invoice UNIQUE (apartment_id, period)
);
INSERT INTO "semiannual_invoices" VALUES(1,1,'2026-H1',3000000,780000,3780000,'2026-07-10','paid','2026-10-03 04:47:26');
INSERT INTO "semiannual_invoices" VALUES(2,2,'2026-H1',3000000,600000,3600000,'2026-07-10','paid','2026-10-03 04:47:26');
INSERT INTO "semiannual_invoices" VALUES(3,3,'2026-H1',3000000,600000,3600000,'2026-07-10','overdue','2026-10-03 04:47:26');
INSERT INTO "semiannual_invoices" VALUES(4,5,'2026-H1',3000000,960000,3960000,'2026-07-10','paid','2026-10-03 04:47:26');
INSERT INTO "semiannual_invoices" VALUES(5,6,'2026-H1',4200000,1200000,5400000,'2026-07-10','paid','2026-10-03 04:47:26');
INSERT INTO "semiannual_invoices" VALUES(6,8,'2026-H1',3000000,0,3000000,'2026-07-10','unpaid','2026-10-03 04:47:26');
INSERT INTO "semiannual_invoices" VALUES(7,11,'2026-H1',2700000,780000,3480000,'2026-07-10','paid','2026-10-03 04:47:26');
INSERT INTO "semiannual_invoices" VALUES(8,12,'2026-H1',2700000,600000,3300000,'2026-07-10','paid','2026-10-03 04:47:26');
INSERT INTO "semiannual_invoices" VALUES(9,13,'2026-H1',3600000,600000,4200000,'2026-07-10','overdue','2026-10-03 04:47:26');
INSERT INTO "semiannual_invoices" VALUES(10,14,'2026-H1',3600000,600000,4200000,'2026-07-10','paid','2026-10-03 04:47:26');
INSERT INTO "semiannual_invoices" VALUES(11,1,'2025-H2',3000000,780000,3780000,'2026-01-10','paid','2026-10-03 04:47:26');
INSERT INTO "semiannual_invoices" VALUES(12,2,'2025-H2',3000000,600000,3600000,'2026-01-10','paid','2026-10-03 04:47:26');
INSERT INTO "semiannual_invoices" VALUES(13,5,'2025-H2',3000000,960000,3960000,'2026-01-10','paid','2026-10-03 04:47:26');
INSERT INTO "semiannual_invoices" VALUES(14,6,'2025-H2',4200000,1200000,5400000,'2026-01-10','paid','2026-10-03 04:47:26');
INSERT INTO "semiannual_invoices" VALUES(15,11,'2025-H2',2700000,780000,3480000,'2026-01-10','paid','2026-10-03 04:47:26');
CREATE TABLE semiannual_payments (
    payment_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id       INTEGER NOT NULL REFERENCES semiannual_invoices(invoice_id),
    amount           INTEGER NOT NULL,
    payment_method   TEXT NOT NULL CHECK (payment_method IN ('QR','cash','bank_transfer')),
    transaction_code TEXT,
    paid_at          TEXT,
    status           TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('success','failed','pending'))
);
INSERT INTO "semiannual_payments" VALUES(1,1,3780000,'QR','DEMO-semiannual_payments-1','2026-07-08 09:00:00','success');
INSERT INTO "semiannual_payments" VALUES(2,2,3600000,'QR','DEMO-semiannual_payments-2','2026-07-08 09:30:00','success');
INSERT INTO "semiannual_payments" VALUES(3,4,3960000,'bank_transfer','DEMO-semiannual_payments-3','2026-07-07 10:00:00','success');
INSERT INTO "semiannual_payments" VALUES(4,5,5400000,'QR','DEMO-semiannual_payments-4','2026-07-06 11:00:00','success');
INSERT INTO "semiannual_payments" VALUES(5,7,3480000,'cash','DEMO-semiannual_payments-5','2026-07-05 14:00:00','success');
INSERT INTO "semiannual_payments" VALUES(6,8,3300000,'QR','DEMO-semiannual_payments-6','2026-07-05 15:00:00','success');
INSERT INTO "semiannual_payments" VALUES(7,10,4200000,'QR','DEMO-semiannual_payments-7','2026-07-04 16:00:00','success');
INSERT INTO "semiannual_payments" VALUES(8,3,3600000,'QR','DEMO-semiannual_payments-8',NULL,'failed');
INSERT INTO "semiannual_payments" VALUES(9,9,4200000,'QR','DEMO-semiannual_payments-9',NULL,'failed');
INSERT INTO "semiannual_payments" VALUES(10,6,3000000,'QR','DEMO-semiannual_payments-10',NULL,'pending');
INSERT INTO "semiannual_payments" VALUES(11,11,3780000,'QR','DEMO-semiannual_payments-11','2026-01-08 09:00:00','success');
INSERT INTO "semiannual_payments" VALUES(12,12,3600000,'QR','DEMO-semiannual_payments-12','2026-01-08 09:30:00','success');
INSERT INTO "semiannual_payments" VALUES(13,13,3960000,'bank_transfer','DEMO-semiannual_payments-13','2026-01-07 10:00:00','success');
INSERT INTO "semiannual_payments" VALUES(14,14,5400000,'QR','DEMO-semiannual_payments-14','2026-01-06 11:00:00','success');
INSERT INTO "semiannual_payments" VALUES(15,15,3480000,'cash','DEMO-semiannual_payments-15','2026-01-05 14:00:00','success');
CREATE TABLE technicians (
    technician_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER,
    full_name        TEXT NOT NULL,
    specialty        TEXT CHECK (specialty IN ('parking','payment','general'))
);
INSERT INTO "technicians" VALUES(1,11,'Ky thuat vien mau 1','parking');
INSERT INTO "technicians" VALUES(2,12,'Ky thuat vien mau 2','general');
INSERT INTO "technicians" VALUES(3,13,'Ky thuat vien mau 3','general');
INSERT INTO "technicians" VALUES(4,11,'Ky thuat vien mau 4','general');
INSERT INTO "technicians" VALUES(5,12,'Ky thuat vien mau 5','general');
INSERT INTO "technicians" VALUES(6,13,'Ky thuat vien mau 6','general');
INSERT INTO "technicians" VALUES(7,11,'Ky thuat vien mau 7','general');
INSERT INTO "technicians" VALUES(8,12,'Ky thuat vien mau 8','general');
INSERT INTO "technicians" VALUES(9,13,'Ky thuat vien mau 9','general');
INSERT INTO "technicians" VALUES(10,11,'Ky thuat vien mau 10','general');
INSERT INTO "technicians" VALUES(11,12,'Ky thuat vien mau 11','parking');
INSERT INTO "technicians" VALUES(12,13,'Ky thuat vien mau 12','general');
INSERT INTO "technicians" VALUES(13,11,'Ky thuat vien mau 13','payment');
INSERT INTO "technicians" VALUES(14,12,'Ky thuat vien mau 14','payment');
INSERT INTO "technicians" VALUES(15,13,'Ky thuat vien mau 15','general');
CREATE TABLE users (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    email           TEXT UNIQUE,
    phone           TEXT,
    role            TEXT NOT NULL CHECK (role IN ('admin','resident','technician')),
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','locked')),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO "users" VALUES(1,'admin01','!disabled-synthetic-account','admin01@example.invalid',NULL,'admin','active','2026-10-03 04:47:25');
INSERT INTO "users" VALUES(2,'admin02','!disabled-synthetic-account','admin02@example.invalid',NULL,'admin','active','2026-10-03 04:47:25');
INSERT INTO "users" VALUES(3,'resident03','!disabled-synthetic-account','resident03@example.invalid',NULL,'resident','active','2026-10-03 04:47:25');
INSERT INTO "users" VALUES(4,'resident04','!disabled-synthetic-account','resident04@example.invalid',NULL,'resident','active','2026-10-03 04:47:25');
INSERT INTO "users" VALUES(5,'resident05','!disabled-synthetic-account','resident05@example.invalid',NULL,'resident','active','2026-10-03 04:47:25');
INSERT INTO "users" VALUES(6,'resident06','!disabled-synthetic-account','resident06@example.invalid',NULL,'resident','active','2026-10-03 04:47:25');
INSERT INTO "users" VALUES(7,'resident07','!disabled-synthetic-account','resident07@example.invalid',NULL,'resident','active','2026-10-03 04:47:25');
INSERT INTO "users" VALUES(8,'resident08','!disabled-synthetic-account','resident08@example.invalid',NULL,'resident','active','2026-10-03 04:47:25');
INSERT INTO "users" VALUES(9,'resident09','!disabled-synthetic-account','resident09@example.invalid',NULL,'resident','locked','2026-10-03 04:47:25');
INSERT INTO "users" VALUES(10,'resident10','!disabled-synthetic-account','resident10@example.invalid',NULL,'resident','active','2026-10-03 04:47:25');
INSERT INTO "users" VALUES(11,'technician11','!disabled-synthetic-account','technician11@example.invalid',NULL,'technician','active','2026-10-03 04:47:25');
INSERT INTO "users" VALUES(12,'technician12','!disabled-synthetic-account','technician12@example.invalid',NULL,'technician','active','2026-10-03 04:47:25');
INSERT INTO "users" VALUES(13,'technician13','!disabled-synthetic-account','technician13@example.invalid',NULL,'technician','active','2026-10-03 04:47:25');
INSERT INTO "users" VALUES(14,'resident14','!disabled-synthetic-account','resident14@example.invalid',NULL,'resident','active','2026-10-03 04:47:25');
INSERT INTO "users" VALUES(15,'resident15','!disabled-synthetic-account','resident15@example.invalid',NULL,'resident','active','2026-10-03 04:47:25');
CREATE TABLE vehicles (
    vehicle_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment_id     INTEGER NOT NULL,
    plate_number     TEXT,
    vehicle_type     TEXT NOT NULL CHECK (vehicle_type IN ('bicycle','motorbike')),
    monthly_fee      INTEGER NOT NULL,
    registered_date  TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','cancelled'))
);
INSERT INTO "vehicles" VALUES(1,1,'DEMO-0001','motorbike',100000,'2022-01-05','active');
INSERT INTO "vehicles" VALUES(2,1,'DEMO-0002','bicycle',50000,'2022-01-05','active');
INSERT INTO "vehicles" VALUES(3,2,'DEMO-0003','motorbike',100000,'2021-06-20','active');
INSERT INTO "vehicles" VALUES(4,3,'DEMO-0004','motorbike',100000,'2025-01-05','active');
INSERT INTO "vehicles" VALUES(5,5,'DEMO-0005','motorbike',100000,'2020-03-15','active');
INSERT INTO "vehicles" VALUES(6,5,'DEMO-0006','bicycle',50000,'2020-03-15','active');
INSERT INTO "vehicles" VALUES(7,5,'DEMO-0007','bicycle',50000,'2020-06-01','active');
INSERT INTO "vehicles" VALUES(8,6,'DEMO-0008','motorbike',100000,'2019-09-05','active');
INSERT INTO "vehicles" VALUES(9,6,'DEMO-0009','motorbike',100000,'2020-10-10','active');
INSERT INTO "vehicles" VALUES(10,8,'DEMO-0010','motorbike',100000,'2024-05-05','cancelled');
INSERT INTO "vehicles" VALUES(11,11,'DEMO-0011','motorbike',100000,'2023-02-20','active');
INSERT INTO "vehicles" VALUES(12,11,'DEMO-0012','bicycle',50000,'2023-02-20','active');
INSERT INTO "vehicles" VALUES(13,12,'DEMO-0013','motorbike',100000,'2018-07-25','active');
INSERT INTO "vehicles" VALUES(14,13,'DEMO-0014','motorbike',100000,'2026-01-05','active');
INSERT INTO "vehicles" VALUES(15,14,'DEMO-0015','motorbike',100000,'2022-11-15','active');
CREATE VIEW vw_apartment_overview AS
SELECT
    a.apartment_id,
    a.code,
    a.block,
    a.floor,
    a.status            AS apartment_status,
    r.full_name         AS current_resident,
    r.relation_type,
    c.contract_type,
    c.start_date,
    c.end_date,
    c.status            AS contract_status
FROM apartments a
LEFT JOIN apartment_contracts c ON c.apartment_id = a.apartment_id AND c.status = 'active'
LEFT JOIN residents r ON r.resident_id = c.resident_id;
CREATE VIEW vw_overdue_invoices AS
SELECT 'monthly' AS invoice_type, invoice_id, apartment_id, period, total_amount, due_date, status
FROM monthly_invoices
WHERE status = 'overdue'
UNION ALL
SELECT 'semiannual' AS invoice_type, invoice_id, apartment_id, period, total_amount, due_date, status
FROM semiannual_invoices
WHERE status = 'overdue';
CREATE VIEW vw_vehicle_summary_by_apartment AS
SELECT
    apartment_id,
    SUM(CASE WHEN vehicle_type = 'motorbike' THEN 1 ELSE 0 END) AS so_xe_may,
    SUM(CASE WHEN vehicle_type = 'bicycle' THEN 1 ELSE 0 END)   AS so_xe_dap,
    SUM(monthly_fee)                                             AS tong_phi_thang
FROM vehicles
WHERE status = 'active'
GROUP BY apartment_id;
CREATE VIEW vw_monthly_revenue_report AS
SELECT
    period,
    SUM(electricity_fee)                               AS tong_tien_dien,
    SUM(water_fee)                                      AS tong_tien_nuoc,
    SUM(total_amount)                                   AS tong_doanh_thu,
    COUNT(*)                                            AS so_hoa_don,
    SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END)    AS so_da_thanh_toan
FROM monthly_invoices
GROUP BY period;
CREATE VIEW vw_guest_parking_monthly AS
SELECT
    strftime('%Y-%m', parking_date) AS period,
    SUM(daily_revenue)              AS tong_doanh_thu_vang_lai
FROM guest_parking_daily
GROUP BY strftime('%Y-%m', parking_date);
CREATE TRIGGER trg_calc_monthly_total_ins
AFTER INSERT ON monthly_invoices
BEGIN
    UPDATE monthly_invoices
    SET total_amount = NEW.electricity_fee + NEW.water_fee
    WHERE invoice_id = NEW.invoice_id;
END;
CREATE TRIGGER trg_calc_monthly_total_upd
AFTER UPDATE ON monthly_invoices
BEGIN
    UPDATE monthly_invoices
    SET total_amount = NEW.electricity_fee + NEW.water_fee
    WHERE invoice_id = NEW.invoice_id;
END;
CREATE TRIGGER trg_calc_semiannual_total_ins
AFTER INSERT ON semiannual_invoices
BEGIN
    UPDATE semiannual_invoices
    SET total_amount = NEW.service_fee + NEW.parking_fee
    WHERE invoice_id = NEW.invoice_id;
END;
CREATE TRIGGER trg_calc_semiannual_total_upd
AFTER UPDATE ON semiannual_invoices
BEGIN
    UPDATE semiannual_invoices
    SET total_amount = NEW.service_fee + NEW.parking_fee
    WHERE invoice_id = NEW.invoice_id;
END;
CREATE TRIGGER trg_update_monthly_invoice_status_ins
AFTER INSERT ON monthly_payments
WHEN NEW.status = 'success'
BEGIN
    UPDATE monthly_invoices
    SET status = 'paid'
    WHERE invoice_id = NEW.invoice_id
      AND NEW.amount >= total_amount;
END;
CREATE TRIGGER trg_update_monthly_invoice_status_upd
AFTER UPDATE ON monthly_payments
WHEN NEW.status = 'success'
BEGIN
    UPDATE monthly_invoices
    SET status = 'paid'
    WHERE invoice_id = NEW.invoice_id
      AND NEW.amount >= total_amount;
END;
CREATE TRIGGER trg_update_semiannual_invoice_status_ins
AFTER INSERT ON semiannual_payments
WHEN NEW.status = 'success'
BEGIN
    UPDATE semiannual_invoices
    SET status = 'paid'
    WHERE invoice_id = NEW.invoice_id
      AND NEW.amount >= total_amount;
END;
CREATE TRIGGER trg_update_semiannual_invoice_status_upd
AFTER UPDATE ON semiannual_payments
WHEN NEW.status = 'success'
BEGIN
    UPDATE semiannual_invoices
    SET status = 'paid'
    WHERE invoice_id = NEW.invoice_id
      AND NEW.amount >= total_amount;
END;
CREATE TRIGGER trg_auto_ticket_monthly_overdue
AFTER UPDATE ON monthly_invoices
WHEN NEW.status = 'overdue' AND OLD.status <> 'overdue'
BEGIN
    INSERT INTO maintenance_tickets (apartment_id, type, description, priority, status)
    VALUES (NEW.apartment_id, 'cut_service',
            'Tự động tạo: hoá đơn điện/nước kỳ ' || NEW.period || ' quá hạn thanh toán',
            'high', 'pending');
END;
CREATE TRIGGER trg_auto_ticket_semiannual_overdue
AFTER UPDATE ON semiannual_invoices
WHEN NEW.status = 'overdue' AND OLD.status <> 'overdue'
BEGIN
    INSERT INTO maintenance_tickets (apartment_id, type, description, priority, status)
    VALUES (NEW.apartment_id, 'cut_service',
            'Tự động tạo: hoá đơn dịch vụ/gửi xe kỳ ' || NEW.period || ' quá hạn thanh toán',
            'high', 'pending');
END;
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('users',15);
INSERT INTO "sqlite_sequence" VALUES('apartments',285);
INSERT INTO "sqlite_sequence" VALUES('residents',15);
INSERT INTO "sqlite_sequence" VALUES('apartment_contracts',15);
INSERT INTO "sqlite_sequence" VALUES('vehicles',15);
INSERT INTO "sqlite_sequence" VALUES('guest_parking_daily',15);
INSERT INTO "sqlite_sequence" VALUES('monthly_invoices',15);
INSERT INTO "sqlite_sequence" VALUES('monthly_payments',15);
INSERT INTO "sqlite_sequence" VALUES('semiannual_invoices',15);
INSERT INTO "sqlite_sequence" VALUES('semiannual_payments',15);
INSERT INTO "sqlite_sequence" VALUES('technicians',15);
INSERT INTO "sqlite_sequence" VALUES('maintenance_tickets',15);
INSERT INTO "sqlite_sequence" VALUES('complaints',15);
INSERT INTO "sqlite_sequence" VALUES('notifications',45);
INSERT INTO "sqlite_sequence" VALUES('notification_logs',15);
INSERT INTO "sqlite_sequence" VALUES('faq_knowledge_base',11);
INSERT INTO "sqlite_sequence" VALUES('locations',14);
COMMIT;
