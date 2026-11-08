# Các bước hoàn thiện project An Cư

Cập nhật ngày 07/11/2026, dựa trên mã nguồn, tài liệu trong repository và lần đối chiếu database Docker. Danh sách này dành cho bản demo/khóa luận; không có nghĩa mọi mục dưới đây đều đang lỗi hoặc chưa được lập trình.

## Đã xác nhận

- SePay Test đã thanh toán hóa đơn #HD0018, 15.000đ.
- SePay Live đã thanh toán hóa đơn #HD0019, A101, 10.000đ; ghi nhận đúng một khoản thu lúc 09:22:55 ngày 07/11/2026, không có tiền dư. Cư dân và BQL đều nhận thông báo có căn hộ, thời gian lập và thanh toán.
- Firebase: người dùng đã xác nhận nhận thông báo desktop và hoàn tất kiểm thử iPhone ngày 07/11/2026. Các ca phân quyền/đăng xuất vẫn cần được ghi kết quả cụ thể khi nghiệm thu tổng thể.
- Gateway và 8 service nghiệp vụ đang healthy tại thời điểm kiểm tra.
- Mã nguồn đã có kiểm thử nghiệp vụ, phân quyền và HTTP liên dịch vụ; xem [TESTING.md](TESTING.md). Lần rà soát này không chạy lại toàn bộ bộ test.

Bằng chứng và giới hạn kiểm chứng: [VERIFICATION.md](VERIFICATION.md).

## 1. Hoàn thiện độ ổn định của thanh toán

Các thao tác cụ thể nằm trong [SEPAY_DOI_SOAT_DU_PHONG.md](SEPAY_DOI_SOAT_DU_PHONG.md).

- [x] Bổ sung token SePay **Live** và UUID ngân hàng tương ứng. Ngày 07/11/2026 đã đọc thành công tài khoản và giao dịch 10.000đ qua API; scheduler có lần đối soát thành công và hóa đơn #HD0019 vẫn chỉ một khoản thu. Chi tiết tại [VERIFICATION.md](VERIFICATION.md). URL webhook trên SePay cần khớp tunnel hiện hành khi tunnel đổi.
- [x] Kiểm thử tự động webhook chậm/gửi lại, tiền thiếu/dư và hai thành viên cùng thanh toán trên database tạm với SePay giả lập: **101 ca Billing/kiểm tra cấu hình đạt ngày 07/11/2026**. Không chuyển tiền thật; thử các ca này qua dashboard SePay Test là một bước nghiệm thu bên ngoài riêng nếu cần.
- [ ] Giữ tunnel hoạt động khi demo; kiểm tra URL và `--probe` trước buổi trình bày. Nếu cần địa chỉ ổn định, chuẩn bị tunnel có tên miền cố định hoặc môi trường triển khai riêng.
- [ ] Đối chiếu danh sách hóa đơn, biên nhận, sổ chuyển khoản và báo cáo thu theo kỳ; phân biệt các khoản thử nghiệm với tiền thực nhận khi trình bày số liệu.

Đạt khi luồng thành công và các trường hợp chậm/lặp/tiền dư đều có kết quả đúng, giải thích được cách xử lý. Hướng dẫn cấu hình: [SEPAY_VIETQR.md](SEPAY_VIETQR.md). Không cần thêm VA cho cấu hình MB hiện tại.

## 2. Nghiệm thu toàn bộ nghiệp vụ theo ba vai trò

| Luồng | Kết quả cần kiểm tra |
| --- | --- |
| BQL xác nhận cư dân/căn hộ/hợp đồng | Cư dân có quyền với đúng căn hộ; dữ liệu căn hộ khác không bị lộ |
| Lập hóa đơn tháng và sáu tháng | Công thức điện/nước đúng; phí xe/dịch vụ đúng kỳ; không lập trùng căn hộ/kỳ |
| Hai thành viên trong cùng căn hộ thanh toán | Đều có quyền thanh toán; hóa đơn chỉ cần trả một lần; người còn lại thấy trạng thái cập nhật |
| Cư dân gửi khiếu nại → BQL phản hồi | Đúng cư dân nhận thông báo riêng, người khác không xem được phản hồi riêng |
| Sửa chữa → phân công → kỹ thuật viên xử lý | Chỉ kỹ thuật viên được giao cập nhật; chuyển trạng thái đúng thứ tự |
| Đăng ký xe → phê duyệt → tính phí | Thông tin xe và phí được phản ánh đúng; không trùng biển số đang hoạt động |
| Quá hạn → xử lý nghiệp vụ → thanh toán | Không tạo lặp yêu cầu; trả đủ nợ cập nhật đúng các phiếu liên quan |
| Báo cáo BQL và biên nhận cư dân | Tổng thu/nợ và thời điểm khớp dữ liệu thanh toán; đúng phạm vi quyền |

Chạy lại bộ test backend và các ca trình duyệt trên database tạm theo [TESTING.md](TESTING.md). Ghi kết quả từng ca, lỗi và bằng chứng sửa; không dùng thao tác trực tiếp database để làm giao diện trông như đã xử lý đúng.

## 3. Nghiệm thu chatbot bằng câu hỏi của cư dân

- [ ] Thử nhiều cách diễn đạt cùng ý: “phí gửi xe điện bao nhiêu?”, “gửi xe máy điện hết bao nhiêu tiền?”, “xe đạp điện được để ở chung cư không?”.
- [ ] Kiểm tra câu không dấu, câu nhiều ý, câu hỏi vị trí và câu thiếu thông tin cần hỏi lại.
- [ ] Đối chiếu câu trả lời với FAQ và địa điểm đã được BQL xác nhận; không tự suy ra phí, quy định hoặc nội dung chưa có nguồn.
- [ ] Kiểm tra câu hỏi về hóa đơn chỉ trả dữ liệu đúng tài khoản/căn hộ.
- [ ] Xác nhận lần gọi LLM thật và khả năng trả lời từ kho kiến thức khi nhà cung cấp lỗi/hết hạn mức. Có khóa trong `.env` chưa đủ để kết luận API đang hoạt động.

Cấu hình hiện có `LLM_API_KEY`; lần rà soát này chỉ kiểm tra sự có mặt của khóa, không gọi nhà cung cấp hoặc xuất khóa. Hướng dẫn: [CHATBOT.md](CHATBOT.md), [CHATBOT_DATA.md](CHATBOT_DATA.md).

## 4. Hoàn thiện thông báo ngoài trang web nếu giữ yêu cầu Firebase

Thông báo trong ứng dụng đã hoạt động. Ngày 07/11/2026 đã cấu hình Firebase, xác thực Google OAuth và kiểm tra FCM `validate_only` HTTP 200. Sau đó người dùng xác nhận nhận thông báo desktop và hoàn tất thử trên iPhone; xem lịch sử trong [VERIFICATION.md](VERIFICATION.md).

Source có volume credentials Docker, kiểm tra cấu hình, khôi phục đăng ký khi F5, tắt push/đăng xuất và kiểm tra người nhận ở service worker. Mục 7–8 trong [FIREBASE_PUSH.md](FIREBASE_PUSH.md) hướng dẫn lặp lại các ca thử desktop/iPhone.

- [x] Cấu hình credentials server, Web config và VAPID; kiểm tra backend/API đạt.
- [x] Nhận thông báo thực tế trên desktop và iPhone, theo xác nhận của người dùng.
- [ ] Kiểm tra hai tài khoản trên hai trình duyệt: thông báo chung, thông báo riêng, khi đang mở trang và khi trang ở nền.
- [ ] Kiểm tra đăng xuất/đổi tài khoản không nhận nhầm thông báo riêng.

Ca cần nghiệm thu là FCM-01 trong [TESTING.md](TESTING.md). Nếu chỉ dùng hộp thông báo trong web, tài liệu phải mô tả đúng phạm vi đó.

## 5. Chốt dữ liệu, tài liệu và kịch bản demo

- [ ] Rà soát các tài khoản mẫu, liên kết căn hộ/hợp đồng, lượng điện nước, phí và FAQ để nội dung demo nhất quán; giữ lại lịch sử giao dịch Live đã nghiệm thu.
- [ ] Sao lưu database Docker bằng cơ chế SQLite backup và thử phục hồi vào môi trường riêng. Ghi rõ database Docker khác bản `data/QLCC.db` khi chạy Python trực tiếp.
- [ ] Đối chiếu yêu cầu → Use Case/quy tắc nghiệp vụ → API/màn hình → ca kiểm thử. Cập nhật sơ đồ kiến trúc, dữ liệu và sequence thanh toán/khiếu nại theo source cuối cùng.
- [ ] Thống nhất thuật ngữ: hiện source xuất **biên nhận HTML nội bộ**, chưa tích hợp nhà cung cấp hóa đơn điện tử. Làm rõ phạm vi nếu tài liệu yêu cầu “hóa đơn điện tử”.
- [ ] Chuẩn bị tài khoản cho BQL, cư dân, kỹ thuật viên; diễn tập một vòng demo; quay video giao dịch Live thành công làm bằng chứng khi kết nối ngoài gặp sự cố.
- [ ] Kiểm tra khởi động lại Docker vẫn giữ dữ liệu, dịch vụ healthy, URL webhook đang hoạt động và hướng dẫn chạy đầy đủ.

Với bản demo local, chưa cần mở rộng sang nhiều database/replica hoặc triển khai Internet toàn bộ ứng dụng. Các giới hạn vận hành được ghi ở [GETTING_STARTED.md](GETTING_STARTED.md) và [ARCHITECTURE.md](ARCHITECTURE.md).
