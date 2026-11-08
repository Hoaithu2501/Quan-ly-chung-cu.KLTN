# Kết quả nghiệm thu cục bộ

## Lưu trữ các database cũ và xuất một bản đầy đủ — 08/11/2026

- Xuất database Docker đang chạy thành `data/QLCC.snapshot.db` bằng SQLite backup; nguồn mở chỉ đọc. Bản xuất gồm 37 bảng, `integrity_check=ok`, 0 lỗi khóa ngoại và SHA-256 khớp bản được tạo trong container. Bản xuất không cần file WAL/SHM bên cạnh.
- Gói `backups/database-archive-20261108-075353.zip` chứa 9 snapshot: 7 bản cũ trên Windows, file nguồn ở gốc và bản xuất Docker đầy đủ. Đã giải nén kiểm tra tất cả snapshot, xác minh SHA-256, toàn vẹn SQLite và khóa ngoại. `manifest.json` ghi đường dẫn gốc và số dòng các bảng.
- `data/QLCC.db` ban đầu đang mở trong DB Browser nên được giữ lại. Sau khi người dùng xác nhận đã lưu/đóng, đối chiếu cả schema và nội dung các bảng với snapshot trong gói: khớp. Sau đó kiểm tra quyền truy cập độc quyền, đường dẫn và mã băm trước khi dọn nốt.
- Đã dọn 7 file DB cũ cùng sidecar liên quan sau khi xác minh sao lưu. `data/` chỉ còn một file DB là `QLCC.snapshot.db`. `QLCC.db` ở gốc được giữ vì Dockerfile khởi tạo và fixture kiểm thử cần nó. Không xóa hay nhập đè vào database/backup trong volume Docker.
- Bỏ cấu hình Compose trỏ tới `QLCC.docker-seed.db` cũ. Volume mới dùng file nguồn; volume đã có DB tiếp tục giữ dữ liệu hiện tại. Đã kiểm tra bản nguồn khi chép riêng vào image vẫn có cùng số dòng từng bảng và toàn vẹn tốt.
- Bổ sung `scripts/export_database.py`: không ghi đè bản xuất có sẵn, kiểm tra trước khi hoàn tất. Loại `backups/` và `.runtime/` khỏi Docker build context.
- Kiểm thử: **6 passed** cho audit/export và **7 passed** cho database refresh. Compose config hợp lệ. Kiểm tra Docker sau dọn: tất cả service vẫn dùng chung database, 37 bảng, không lỗi toàn vẹn hay khóa ngoại; không restart service hoặc thực hiện giao dịch thanh toán.

## Xác định database chính — 08/11/2026

- Kiểm tra trực tiếp 10 container Compose: gateway, 8 service nghiệp vụ và `db-init` cùng mount volume `qlcc_qlcc-data`, cùng `DATABASE_PATH=/app/data/QLCC.db`. Các service đang chạy; `db-init` đã thoát sau khởi tạo.
- SQLite Docker có 37 bảng ứng dụng, `integrity_check=ok`, `foreign_key_check` không có lỗi. Tại thời điểm kiểm tra có 19 hóa đơn tháng, 18 bản ghi thanh toán tháng, 2 giao dịch ngân hàng và 4 token push.
- So sánh 8 file DB trên Windows theo khóa chính và các cột chung: không thấy khóa chỉ có ở bản cũ mà thiếu trong bản Docker. Có khác biệt nội dung ở một số bản ghi cùng khóa; không nhập đè hay gộp giao dịch. Giữ dữ liệu nguồn, seed và bản sao lưu nguyên trạng.
- `start.ps1` mặc định chạy Docker; chế độ Python phải chọn rõ `-Mode Python`. README và các hướng dẫn được sửa để phân biệt database chính với `data/QLCC.db` trên Windows.
- Bổ sung `scripts/check_database.py` kiểm tra chỉ đọc volume/đường dẫn và toàn vẹn dữ liệu. Đã chạy `--inventory` trên Docker: cùng database `OK`, toàn vẹn `ok`, 0 lỗi khóa ngoại. Công cụ không in dữ liệu cá nhân, mật khẩu hay token.
- `tests/test_database_audit.py`: **4 passed**; kiểm tra phát hiện khác volume/file mount, thiếu service, đọc dữ liệu đã commit trong WAL mà không ghi DB, không tạo DB khi sai đường dẫn và phát hiện lỗi khóa ngoại. Cú pháp `start.ps1` và JSON tác vụ VS Code đều hợp lệ. Không chạy lại launcher thật vì hệ thống đang hoạt động.
- Chi tiết các file và lệnh kiểm tra: [DATABASE.md](DATABASE.md).

## Người dùng xác nhận kiểm thử Firebase trên điện thoại hoàn tất — 07/11/2026

- Sau hướng dẫn thêm An Cư vào Màn hình chính trên iPhone, người dùng báo “tôi đã test done”. Trước đó người dùng đã xác nhận thấy thông báo trên trình duyệt desktop.
- Ghi nhận luồng nhận thông báo thực tế đã được người dùng kiểm thử thành công trên desktop và iPhone. Đây là xác nhận của người dùng, không phải lần kiểm thử thiết bị do agent trực tiếp quan sát.
- Chưa có kết quả riêng cho từng ca âm như căn hộ khác, đổi tài khoản hoặc đăng xuất; giữ các ca này trong checklist nghiệm thu tổng thể. SePay Live đã có giao dịch và thông báo thành công được xác nhận ở các mục trước.
- Các mốc phía dưới là lịch sử chuẩn bị và kiểm tra trước khi người dùng hoàn tất thử trên thiết bị.

## Chuẩn bị kiểm thử Firebase trên iPhone — 07/11/2026

- Người dùng xác nhận đã thấy thông báo trên trình duyệt desktop; chưa có xác nhận nhận trên iPhone.
- Bổ sung `frontend/manifest.webmanifest` (`display: standalone`, `scope: /`, `start_url: /`) và metadata Apple trong `index.html` để thêm An Cư vào Màn hình chính. Hướng dẫn iOS ở mục 7.1 của [FIREBASE_PUSH.md](FIREBASE_PUSH.md).
- Tunnel cũ đã dừng. Đã mở tunnel riêng cho lần kiểm thử điện thoại; trang chủ và manifest trả HTTP 200 qua HTTPS. Manifest có MIME `application/manifest+json`, chế độ standalone; tài nguyên icon trả HTTP 200 ở gateway. Không đổi cấu hình SePay.
- Đây là kiểm tra tài nguyên và truy cập HTTPS, chưa phải nghiệm thu push trên thiết bị iOS. Cần thử cấp quyền trong web app, nhận ở nền/màn hình khóa và đúng người nhận trên iPhone thật.

## Firebase đã cấu hình và xác thực với Google — 07/11/2026

- Sau khi người dùng lưu cấu hình, đã sửa `FIREBASE_WEB_CONFIG` thành JSON một dòng và bỏ ký tự `3` thừa trước dấu `:` của `appId`. Các biến ngoài Firebase được giữ nguyên.
- Web app, `FIREBASE_PROJECT_ID` và service account khớp project; app ID khớp sender ID. Khóa VAPID giải mã hợp lệ thành public key P-256. Kiểm tra này chưa chứng minh VAPID được đăng ký đúng với Firebase; cần thử lấy token trên trình duyệt.
- Google OAuth xác thực thành công với khóa server. Đã recreate riêng notification-service để nạp `.env`, container healthy; kiểm tra cấu hình và OAuth bên trong container đều OK.
- FCM HTTP v1 trả **HTTP 200** cho yêu cầu `validate_only: true` dùng topic kiểm tra. Chế độ này kiểm tra quyền/API mà không phát thông báo: [tài liệu Firebase](https://firebase.google.com/docs/reference/fcm/rest/v1/projects.messages/send). Không ghi database hoặc gửi tới cư dân/BQL.
- Database Docker có **0 token trình duyệt** tại thời điểm kiểm tra. **Chưa nghiệm thu nhận push thật**: cần mỗi tài khoản bật quyền trên trình duyệt, sau đó thử foreground/background và thông báo riêng theo bước 7–8 trong [FIREBASE_PUSH.md](FIREBASE_PUSH.md).

## Hoàn tất bước 6 và 7 đối soát SePay — 07/11/2026

- Chạy lại `scripts/check_sepay.py --probe --check-api`: Gateway OK, Webhook OK, API OK, mã thoát 0. Dòng webhook từ chối yêu cầu không có API Key là kết quả bảo mật mong đợi, không phải lỗi. Trong lần chạy này không tái hiện lỗi terminal mới.
- So khớp các biến thanh toán của container billing với `.env`: đều khớp, không in token/khóa. Billing và gateway healthy. Scheduler Live đã có lần kiểm tra mới, `last_error` rỗng.
- Lệnh `python -m pytest tests/test_billing.py tests/test_sepay_check.py -q` đạt **101 passed in 32.38s**, không failed/error. Bao gồm phục hồi webhook bị mất qua API, API tới trước/webhook tới sau, webhook gửi lặp, tiền thiếu cộng dồn, tiền dư/chuyển lần hai, hai thành viên mở đồng thời, API lỗi mạng và kiểm tra cấu hình.
- Bộ test dùng SQLite tạm và SePay giả lập, không chuyển tiền thật hoặc ghi vào database Docker. Sau kiểm tra, #HD0019 vẫn đúng một payment thành công 10.000đ; sổ ngân hàng Live vẫn một giao dịch matched, tiền chưa phân bổ bằng 0. Hai sự kiện thanh toán cho cư dân/BQL vẫn được tiếp nhận thành công.
- Bước 6 cấu hình/kiểm tra kết nối và bước 7 kiểm thử tự động trong [SEPAY_DOI_SOAT_DU_PHONG.md](SEPAY_DOI_SOAT_DU_PHONG.md) đã đạt. Kết quả này không phải một lần gửi webhook mới từ dashboard SePay hoặc nghiệm thu các ca thiếu/dư bằng tiền thật.

## Đối soát API Live và sửa công cụ kiểm tra — 07/11/2026

- Đã cấu hình token API Live và UUID tài khoản MB. API trả HTTP 200, UUID/số tài khoản/tên người nhận/ngân hàng đều khớp. Phản hồi thực tế có `active` dạng chuỗi `"1"`; script kiểm tra cũ chỉ nhận số 1/boolean nên báo sai “tài khoản không khớp”. Đã hỗ trợ chuỗi `"1"` và vẫn từ chối 0, `"0"`, false, null.
- `tests/test_sepay_check.py`: **20 passed**, gồm trạng thái hoạt động dạng boolean/số/chuỗi, tài khoản không khớp hoặc không hoạt động, không xuất khóa và không gửi giao dịch trong kiểm tra.
- API danh sách giao dịch đọc được đúng một giao dịch TTHD 10.000đ thuộc tài khoản đã cấu hình. Billing đã nạp token/UUID; phiên Live của hóa đơn #HD0019 có lần đối soát thành công, không lỗi. Sổ ngân hàng vẫn một giao dịch matched; hai định danh API/webhook cùng trỏ một giao dịch; hóa đơn vẫn đúng một khoản thu thành công 10.000đ.
- Tunnel `moves-done-parameter-studying.trycloudflare.com` đã dừng trong lúc kiểm tra. Đã mở tunnel nền mới `green-poet-directions-titled.trycloudflare.com`, cập nhật `.env` và tạo lại billing, chờ healthy. `scripts/check_sepay.py --probe --check-api` đạt đủ Gateway OK, Webhook OK, API OK.
- **Cần người dùng cập nhật URL webhook QLCC Live trên SePay** thành `https://green-poet-directions-titled.trycloudflare.com/api/billing/sepay/webhook`. Lần kiểm tra này xác nhận endpoint công khai và API hoạt động, chưa xác nhận người dùng đã lưu URL mới trên dashboard SePay. Không tạo chuyển khoản mới hoặc chỉnh sửa lịch sử thanh toán.

## Nghiệm thu thanh toán SePay Live — 07/11/2026

- Người dùng xác nhận chuyển tiền thật thành công, cư dân và BQL đều nhận thông báo; ảnh chụp thể hiện hóa đơn #HD0019, căn hộ A101, kỳ 2026-06, tổng 10.000đ, hạn 21/11/2026.
- Đối chiếu chỉ đọc database Docker: hóa đơn #19 `paid`, lập lúc 09:19:51 ngày 07/11/2026 theo giờ Việt Nam. Phiên VietQR có `environment=live`, `status=success`; giao dịch ngân hàng `matched`, nhận/phân bổ đủ 10.000đ, tiền chưa phân bổ bằng 0.
- Có đúng một khoản thu thành công cho hóa đơn: payment #18, phương thức `bank_transfer`, 10.000đ, `paid_at=2026-11-07T09:22:55+07:00`. Không có hóa đơn tháng/sáu tháng nào có nhiều hơn một payment thành công trong lần kiểm tra này.
- Hai sự kiện `billing:paid:monthly:19` và `billing:paid-admin:monthly:19` đã chuyển tới Notification, mỗi sự kiện một lần thử, không có lỗi; thời điểm tiếp nhận 09:22:56 theo giờ Việt Nam. Người dùng đã xác nhận hiển thị thông báo cho cả hai vai trò.
- Tất cả 9 container phục vụ web (gateway và 8 service nghiệp vụ) đang running/healthy tại thời điểm kiểm tra. Không phát sinh thêm giao dịch hay chỉnh dữ liệu tài chính trong lần đối chiếu.
- Luồng chính tạo hóa đơn → QR → chuyển khoản thật → webhook → ghi nhận một lần → thông báo hai bên đã được nghiệm thu. API đối soát dự phòng chưa cấu hình; chưa nghiệm thu Firebase push trên trình duyệt. Đây là kết quả luồng Live thành công, không phải tuyên bố đã kiểm thử toàn bộ hệ thống hoặc mọi tình huống sự cố.
- Các bước hoàn thiện tiếp theo: [HOAN_THIEN_PROJECT.md](HOAN_THIEN_PROJECT.md).

## Cấu hình MB và SePay Live — 07/11/2026

- Sau khi người dùng tạo webhook QLCC Live, đã đổi `.env` sang `SEPAY_ENV=live`, dùng tài khoản MB chính đuôi 7720, tên TRAN HOAI THU theo ảnh người dùng cung cấp; không cần VA. Tạo lại riêng container billing để nạp cấu hình. `.env.example` giữ tài khoản/khóa trống và môi trường Test mặc định cho máy mới.
- Đã dùng tunnel hiện hành `moves-done-parameter-studying.trycloudflare.com`. Tên miền `cakes-citizenship-societies-lobby.trycloudflare.com` cũ không còn bản ghi DNS và log báo `Tunnel not found`; không dùng lại URL cũ khi tạo webhook.
- Gateway/billing healthy. `scripts/check_sepay.py --probe` đạt ở Live; webhook công khai trả 403 khi thiếu API Key, trả 400 khi có khóa đúng nhưng payload rỗng. Đây là kiểm tra đường nhận, cấu hình và xác thực của ứng dụng, chưa chứng minh khóa đã điền trên SePay khớp hoặc có giao dịch tiền thật được nhận.
- Kiểm tra database chỉ đọc: không có phiên Test đang chờ; vẫn chỉ có một giao dịch Test matched 15.000đ, không có tiền dư. Hóa đơn #HD0018 giữ trạng thái paid; chưa tạo hóa đơn, phiên QR hay giao dịch Live trong lần cấu hình này.
- API đối soát dự phòng chưa bật vì chưa có token/UUID Live. Cần tạo hóa đơn thử mới và chuyển một khoản nhỏ bằng ngân hàng để nghiệm thu đầu cuối. Xem phần **MB Live: không cần thêm tài khoản ảo** trong [SEPAY_VIETQR.md](SEPAY_VIETQR.md).

## Tính điện/nước, thời gian và căn hộ trong thông báo — 07/11/2026

- Biểu mẫu lập hóa đơn tháng nhập lượng tiêu thụ kWh/m³ và đơn giá từng loại, xem trước tổng tiền. Backend dùng Decimal tính mỗi khoản, làm tròn đến đồng; lưu đủ lượng dùng/đơn giá và hiển thị cách tính trong chi tiết/biên nhận. Hóa đơn cũ giữ phí gốc và các trường lượng dùng/đơn giá là NULL.
- Chi tiết hóa đơn, lịch sử thanh toán, thông báo và biên nhận hiển thị thời gian đến giây theo giờ Việt Nam. Thời gian lập từ SQLite UTC được đổi đúng múi giờ, kể cả qua ngày; thời gian thanh toán lấy từ lần ghi nhận đủ tiền. Danh sách/chi tiết hóa đơn và thông báo kiểm tra cập nhật mỗi 5 giây khi tab hiển thị, không thay biểu mẫu đang nhập.
- Thông báo BQL có căn hộ liên quan, thời gian lập và thanh toán; căn hộ mô tả hóa đơn không thay đổi đối tượng nhận. Migration bổ sung thông tin cho 6 thông báo cũ mà không gửi lại hay sửa trạng thái đọc.
- Đã kiểm tra database Docker: `integrity_check=ok`, không lỗi khóa ngoại, không có hóa đơn sai tổng hoặc hai bản ghi thanh toán thành công cho cùng hóa đơn. Database vốn có UNIQUE căn hộ/kỳ và trigger cộng tổng. Bổ sung CHECK lượng dùng/đơn giá, trigger kiểm tra công thức/đầu vào và UNIQUE một payment thành công cho mỗi hóa đơn tháng/sáu tháng. Phần dư từ các giao dịch ngân hàng khác nhau vẫn nằm trong sổ đối soát.
- Kiểm thử: 93 ca Billing/HTTP/domain/database đạt trước bổ sung ràng buộc cuối; sau bổ sung, 85 ca Billing/HTTP/database đạt, gồm thử ghi SQL sai công thức và thanh toán trùng. 3 ca trình duyệt đạt cho lập hóa đơn theo lượng dùng → thanh toán → biên nhận, cập nhật không tải lại ở cả hai vai trò, giữ dữ liệu đang nhập, múi giờ khác Việt Nam và căn hộ trong thông báo. 9 ca thanh toán SePay trình duyệt đã đạt trước thay biểu mẫu; cú pháp JavaScript đạt. Không tạo giao dịch thử trên database đang phục vụ web.
- Backup trước bổ sung thời gian: `/app/data/backups/QLCC-before-billing-times-20261106T151512Z.db`; trước công thức/ràng buộc: `/app/data/backups/QLCC-before-utility-calculation-20261107T011735Z.db`. Đối chiếu toàn bộ cột cũ của hóa đơn, thanh toán, bank_transactions, bank_payment_intents, notifications và notification_logs: giữ nguyên.
- Đã build/nạp Docker Billing, Notification và gateway, giữ tên mặc định. API chạy thực xác nhận 8 dịch vụ nghiệp vụ `ok`; hóa đơn #HD0018 A101 vẫn paid 15.000đ, lập lúc **21:39:37 ngày 06/11/2026**, thanh toán **21:41:27 cùng ngày** theo giờ Việt Nam. Thông báo BQL trả `related_apartment_code=A101`, `target_role=admin`, không đặt `target_apartment_id`; SePay Test vẫn ready.
- Cách dùng và quy tắc: [PAYMENTS.md](PAYMENTS.md), [TEST_THANH_TOAN_HOA_DON.md](TEST_THANH_TOAN_HOA_DON.md).

## Chuyển sang VietQR và SePay Test — 06/11/2026

- Đồng bộ tiền tố mới TTHD trong .env và Billing. Nhận diện vẫn giữ các tiền tố của phiên đã phát hành, để webhook/API đến trễ hoặc gửi lặp với mã QLCC cũ không mất đối soát. Bộ Billing/HTTP/CLI liên quan đạt **81 ca**, gồm 3 ca mới về đổi tiền tố và mã mơ hồ.
- Đã xác minh luồng SePay Test đầu cuối ngày 06/11/2026: người dùng mô phỏng 15.000đ với mã `TTHD39D79F724429`, webhook qua tunnel thành công và hóa đơn #HD0018 của A101 (kỳ 2026-09) chuyển sang `paid`. Database có đúng một khoản thanh toán 15.000đ lúc 21:41:27 +07:00; giao dịch ngân hàng `matched`, phân bổ đủ 15.000đ, không có tiền thừa. Hai sự kiện thông báo cho cư dân và BQL đã được dịch vụ thông báo tiếp nhận; người dùng xác nhận hiển thị trên web bằng ảnh. Đây là giao dịch Test, không chuyển tiền thật.

- Đã thay luồng thanh toán mới bằng SePay: webhook API Key, đọc API v2 dự phòng, QR theo số còn nợ và phân quyền thành viên căn hộ. API MoMo/simulate, cấu hình và công cụ kiểm tra cũ đã gỡ; bảng giao dịch cũ vẫn giữ để đối chiếu.
- 286 kiểm thử backend đạt; thêm 1 ca đối soát định kỳ không có người đăng nhập đạt. Các ca dùng database tạm và phản hồi SePay giả lập, không chuyển tiền thật.
- JavaScript kiểm tra cú pháp đạt; CSS đã build lại. Kiểm thử trình duyệt thanh toán đã đạt 9 ca ở lần kiểm tra chức năng này.
- Đã sao lưu SQLite trước nâng cấp tại `/app/data/backups/QLCC-before-sepay-20261106T113511Z.db`, kiểm tra toàn vẹn `ok`.
- Đã build và tạo lại Billing/gateway trên Docker; migration đã áp dụng. Sau nâng cấp, SQLite `integrity_check=ok`, không lỗi khóa ngoại; đối chiếu toàn bộ dòng users, residents, apartment_contracts, hóa đơn tháng/sáu tháng, thanh toán tháng/sáu tháng và payment_orders với backup đều giữ nguyên.
- API đang chạy trả mode SePay, môi trường Test; không còn endpoint MoMo/simulate hoặc biến MOMO trong Billing. Kiểm tra quyền trước giao dịch Test xác nhận cư dân ID 24 (A101) đọc được các hóa đơn 17, 16, 11, 1.
- Cấu hình local chọn `PAYMENT_MODE=sepay`, `SEPAY_ENV=test`. Đã điền MBBank Test theo ảnh người dùng, tạo khóa webhook và cập nhật tunnel HTTPS. `check_sepay.py --probe` đạt: gateway OK, webhook từ chối yêu cầu không có API Key. Luồng webhook Test đã xác minh như trên; chưa có token/UUID API dự phòng và chưa nghiệm thu Live.
- Theo yêu cầu giữ tên cũ, đã bỏ container_name có số cổng khỏi Compose; qlcc-billing-1 và qlcc-gateway-1 đang healthy. Tài khoản và cấu hình thanh toán được giữ nguyên khi tạo lại container.
- Chạy lại 2 ca trình duyệt sau khi build CSS: lập hóa đơn/thanh toán/biên nhận và QR cập nhật phần còn thiếu đều đạt. Không lưu ảnh hoặc chuyển tiền thật.
- Thiết lập tiếp theo: [SEPAY_VIETQR.md](SEPAY_VIETQR.md); kịch bản thử: [TEST_THANH_TOAN_HOA_DON.md](TEST_THANH_TOAN_HOA_DON.md).

Các mục phía dưới là lịch sử nghiệm thu phiên bản cũ, không phải hướng dẫn chạy thanh toán hiện tại. Công cụ và ca kiểm thử MoMo được nhắc ở lịch sử đã gỡ khi chuyển sang SePay.

## Lời chatbot và phản hồi khiếu nại — 05/11/2026

- Đã viết lại FAQ và hướng dẫn trong prompt theo cách nói dễ hiểu cho cư dân. Các giá trị phí, cam kết, thời hạn và hotline được giữ nguyên; 5 FAQ gửi xe trong seed và quy tắc cập nhật nội dung đồng bộ. Câu hỏi thanh toán không còn hướng dẫn bằng IPN/API Query; câu khiếu nại mô tả chức năng phản hồi và thông báo riêng mới.
- Ban quản lý có thể phản hồi hoặc sửa phản hồi, kể cả yêu cầu đã đóng mà không đổi trạng thái/ngày hoàn tất. Phản hồi mới hoặc thay đổi được lưu cùng sự kiện thông báo; gửi lại nguyên nội dung không tạo thông báo trùng. Khi gửi thông báo lỗi, phản hồi vẫn lưu và hàng đợi tự thử lại mỗi 30 giây.
- Thông báo nhắm tới đúng cư dân gửi yêu cầu qua `notification_resident_audience`; cư dân khác cùng căn hộ không xem hoặc đánh dấu đã đọc được. Bộ lọc push cũng dùng người nhận này; chưa gửi thử Firebase vào tài khoản thật.
- Toàn bộ backend: **239 passed, 12 skipped** trong 64,52 giây. Ca trình duyệt Edge mới: **1 passed**, kiểm tra gửi đơn, phản hồi/đổi phản hồi đã đóng, thông báo riêng và cư dân khác không xem được. Không lưu ảnh hoặc báo cáo test lâu dài.
- Đã build và cập nhật Docker `chatbot`, `complaint`, `notification`; nạp migration `notifications_resident_replies.sql`. Cả 9 service đều running/healthy. Đã áp FAQ trên volume Docker: thêm 16, sửa 5, tổng 31 FAQ; rà soát câu trả lời không có các từ IPN/API/JWT/SQLite/database.
- Backup trước cập nhật đã được xuất về `backups/QLCC-before-chatbot-faq-20261104T172145505073Z.db`. Đối chiếu toàn bộ dòng tài khoản, cư dân, kỹ thuật viên, hợp đồng, hóa đơn, thanh toán, lệnh thanh toán, phương tiện và khiếu nại với backup: giữ nguyên. SQLite `integrity_check=ok`, không có lỗi khóa ngoại. Không tạo khiếu nại/thông báo thử trên dữ liệu đang phục vụ web.
- Thao tác trên web và cách nâng cấp: [COMPLAINTS.md](COMPLAINTS.md).

## Chatbot, prompt và dữ liệu FAQ — 04/11/2026

- Đã nối truy xuất FAQ/địa điểm vào `/api/chatbot/ask`, có nguồn, nhiều ý hỏi, hỏi lại câu mơ hồ và ưu tiên sự cố khẩn cấp. Bộ xếp hạng phân biệt phí, hạn, lịch sử, phương thức và hotline; bỏ cơ chế cho điểm bằng nhau chỉ vì chung chủ đề.
- LLM tùy chọn dùng prompt đóng gói trong source, tối đa 5 nguồn và một lần gọi có timeout. Thiếu cấu hình, lỗi HTTP/JSON, nguồn không tồn tại hoặc số liệu mới không thuộc nguồn trích dẫn đều quay về nội dung gốc. Chưa gọi nhà cung cấp LLM thật hoặc xác minh API key/model.
- Tra cứu hóa đơn cá nhân có cấu hình bật riêng, dùng JWT của cư dân và trả lời trực tiếp từ Billing; không gửi hóa đơn/JWT tới LLM. Kiểm thử HTTP thực xác nhận dữ liệu vẫn theo phạm vi căn hộ do Billing/Resident quyết định.
- SQL `scripts/sql/chatbot_faq_v3.sql` giữ FAQ tự thêm và ID; chỉ cập nhật các câu đã liệt kê, thêm câu còn thiếu. Runner có preview, backup SQLite gồm WAL và transaction/rollback. Chưa áp dụng vào DB thật. Preview `data/QLCC.db`: thêm 20, sửa 1, giữ 10, tổng dự kiến 31; đây là DB Python trên máy, không phải volume Docker.
- **97 kiểm thử liên quan đạt**: 35 truy xuất, 53 hợp đồng API/LLM/quyền riêng tư, 7 seed/backup/rollback, 1 HTTP tra cứu hóa đơn và 1 kiểm thử tương thích chatbot cũ. Không gọi LLM thật và không lưu ảnh chụp hoặc kết quả kiểm thử lâu dài.
- Hướng dẫn SQL và DB Browser/Docker: [CHATBOT_DATA.md](CHATBOT_DATA.md). Cấu hình AI và giới hạn kiểm chứng: [CHATBOT.md](CHATBOT.md).

## Kiểm tra MoMo Sandbox — 27/10/2026

- **Đã xác nhận một giao dịch ATM Sandbox thành công qua API Query** sau khi người dùng thanh toán bằng thẻ test: `orderId=QLCC-TEST-a716b6c5c9374e079cc665cf3b1f6f1b`, số tiền 10.000 VND, HTTP 200, `resultCode=0`, `transId=4876805567`. Kết quả khớp màn hình NAPAS báo thành công. Đã kiểm chứng luồng Create → thanh toán ATM Test → Query; đây là lệnh độc lập, chưa chứng minh luồng cập nhật hóa đơn/IPN của QLCC thành công.
- Người dùng cho phép tạo giao dịch thử. Đã gọi MoMo Test với khóa từ `.env`, lệnh độc lập 10.000 VND, `captureWallet`: HTTP 200, `resultCode=0`, nhận `payUrl` hợp lệ và phản hồi khớp mã lệnh/số tiền. Query tiếp theo trả HTTP 200, `resultCode=1000`, `transId=0`: đang chờ xác nhận thanh toán. Chưa xác nhận thanh toán thành công hoặc nghiệm thu luồng hóa đơn/IPN đầu cuối.
- Lệnh thử khi đó không thay đổi hóa đơn trong QLCC. Công cụ `scripts/check_momo.py` của phiên bản cũ đã được gỡ trong lần chuyển sang SePay.
- Cả 9 dịch vụ Docker đã được kiểm tra chạy và healthy. URL Cloudflare cũ mất DNS: đã khởi động lại đúng quick tunnel trỏ gateway 5000, cập nhật `MOMO_IPN_URL` trong `.env` và tạo lại billing. Probe lại đạt: gateway OK, IPN HTTPS nhận POST và trả 400 cho nội dung thiếu chữ ký. Query dự phòng tại trang redirect được giữ.
- Sau phản ánh quét QR bằng MoMo thường/TPBank, Query lệnh ví vẫn trả `1000` (chờ xác nhận). Đã tạo thêm lệnh độc lập 10.000 VND bằng `payWithATM`, HTTP 200 / `resultCode=0`, để thử trên trình duyệt với thẻ ATM Sandbox. Hai lệnh chưa được xác nhận đã thanh toán. Hướng dẫn phân biệt ứng dụng MoMo Test và thông tin thẻ test được bổ sung vào tài liệu.
- Kiểm thử CLI bổ sung: `python -m pytest tests/test_momo_check.py -q --tb=short` — **34 passed**. Kiểm tra chữ ký, chặn môi trường sai, phản hồi sai mã/số tiền/URL, che khóa, lỗi HTTP và timeout không tự gửi lại; các test không gọi mạng hoặc DB thật.

## Yêu cầu lần 2 — 25–26/10/2026

- Đối chiếu [tài liệu yêu cầu, tab lần 2](https://docs.google.com/document/d/1L5WDmtex38o1qpn2NP9LE5NuWhiLh1-Ny_iXgc6nQc4/edit?tab=t.4o5jrfw4q3hj): điện thoại bắt buộc, thương hiệu `AN CƯ`, thống nhất `Ban quản lý`, bỏ nhãn chú thích ảnh trên giao diện.
- Gửi xe chỉ gồm xe máy, xe điện, xe đạp; phí tháng lần lượt 100.000/100.000/50.000 đồng. Cam kết tối thiểu 2 tháng, thu theo kỳ 6 tháng cùng dịch vụ và phí thẻ lần đầu 100.000 đồng. Biển số bắt buộc với xe máy/xe điện; xe điện chưa có biển dùng biển nhận dạng theo căn hộ. Nội quy ghi tốc độ 20 km/h, duyệt trong 48h và hotline 0228913665.
- Đóng nội quy trở lại đúng đơn và giữ dữ liệu; chọn Đăng ký thủ tục mở ngay đơn gửi xe. Đổi trang/tab giữ nội dung đến khi API hoàn tất; bỏ hiệu ứng xuất hiện lại gây nháy. Chặn phản hồi chậm mở lại đơn đã đóng hoặc ghi đè dữ liệu xuất báo cáo mới.
- `node --check frontend/app.js` và `npm run build:css`: đạt. Bộ backend: **102 passed, 10 skipped** (browser chạy riêng). Sau chỉnh snapshot/migration nội dung: bộ refresh **7 passed**, migration chính sách **1 passed**.
- **11 ca trình duyệt đã đạt qua các lần chạy đầy đủ và chạy lại có chọn lọc.** Chrome có lúc kẹt khi tải trang/thao tác; các ca còn lại được kiểm tra bằng Edge. Bao gồm cả ba vai trò, điện thoại bắt buộc, giữ đơn khi đóng nội quy, chuyển loại yêu cầu, phản hồi chậm sau đóng đơn, chuyển tab và xuất CSV đúng năm sau khi phản hồi đến sai thứ tự. Không lưu ảnh hoặc thư mục kết quả lâu dài; thanh toán trong test dùng phản hồi giả lập.
- Đã nạp dữ liệu nguồn vào volume Docker: **270 căn hộ, 24 tài khoản, 21 cư dân, 50 thông báo, 15 phương tiện**. Đối chiếu toàn bộ hàng dữ liệu tài khoản, cư dân, kỹ thuật viên, hợp đồng, hóa đơn, thanh toán và lệnh thanh toán với bản sao lưu: giữ nguyên. SQLite `integrity_check=ok`, không có lỗi khóa ngoại.
- Bản sao lưu trước cập nhật: `backups/QLCC-before-refresh-20261025T140158398034Z.db`. File nguồn `QLCC.db` giữ nguyên. Lệnh đồng bộ có preview, tự sao lưu, ánh xạ ID thông báo và giữ dữ liệu nghiệp vụ; xem [DATABASE_REFRESH.md](DATABASE_REFRESH.md).
- Bộ khóa MoMo Sandbox và URL IPN Cloudflare do người dùng cung cấp đã được đặt trong `.env`, được Git bỏ qua. Đã tạo lại container billing để nạp cấu hình. `scripts/check_momo.py --probe` đạt: cấu hình đầy đủ, gateway hoạt động, callback HTTPS nhận POST và từ chối nội dung thiếu chữ ký với HTTP 400. Luồng `captureWallet` và API Query dự phòng tại trang redirect được giữ. Chưa tạo giao dịch hoặc xác minh khóa với nhà cung cấp.

## Bổ sung bố cục, gradient và chuyển động — 17/10/2026

- Hero dashboard đổi sang gradient xanh rừng với ảnh ghép; các thẻ tiện ích có ảnh và mở chức năng thật. Bổ sung ảnh nội thất, lối dạo xanh, banner hồ sơ/bảng tin và khung đăng nhập trên nền mint.
- Animation xuất hiện theo nhịp, mở hộp thoại và hiệu ứng rê chuột bằng CSS. Kiểm tra `prefers-reduced-motion` xác nhận animation tắt khi người dùng yêu cầu giảm chuyển động.
- `npm run build:css` và `node --check frontend/app.js`: đạt. Toàn bộ `tests/test_browser.py`: **7 passed** trong 153,65 giây, dùng dữ liệu tạm và API MoMo giả lập.
- Kiểm tra bổ sung trên stack HTTP cô lập: **42 lượt đạt** cho đăng nhập/đăng ký, tổng quan, hóa đơn, bảng tin và hồ sơ tại 320/390/900/1440 px; ảnh tải đủ, font tiếng Việt sẵn sàng, không tràn ngang, không lỗi JavaScript/HTTP. Sáu thẻ tiện ích của quản trị/cư dân mở đúng trang bằng phím Enter.
- Khi rà menu di động, đã sửa trường hợp chọn lại trang đang mở nhưng menu chưa đóng. Kiểm tra bổ sung đạt sau sửa.
- Không lưu ảnh chụp hoặc tạo `test-results`; kết quả kiểm thử được ghi bằng văn bản.
- Hạn chế bản chạy: Docker Engine cục bộ trả HTTP 500 ở cả API danh sách container và `/_ping`; `docker compose up -d` chưa khởi động lại được stack. Đã thử `docker desktop restart --timeout 90`, nhưng Docker Desktop/WSL không dừng trong thời hạn. `localhost:5000` chưa phản hồi tại lần kiểm tra cuối. Các kết quả 7 + 42 ở trên được xác nhận bằng stack HTTP cô lập; cần khôi phục Docker Desktop rồi chạy `docker compose up -d` để xem trên bản Docker.

## Giao diện Tailwind CSS — 17/10/2026

- `npm run build:css`: thành công với Tailwind CSS 4.3.3; `node --check frontend/app.js`: đạt. CSS được biên dịch cục bộ bằng Node.js, không dùng trình biên dịch CDN.
- Kiểm thử trình duyệt: **7 ca đạt**. Lần chạy toàn bộ có 6 ca đạt và 1 assertion cũ kiểm tra số căn hộ trong ô họ tên; sửa selector để kiểm tra họ tên và căn hộ riêng biệt, rồi chạy lại ca đăng ký/hồ sơ/đổi mật khẩu thành công. Ba vai trò, menu di động, tạo căn hộ/hoá đơn, thanh toán mô phỏng, tải biên nhận và hai luồng MoMo giả lập đều đạt.
- Bản Docker tại `http://localhost:5000`: **83 lượt kiểm tra** đăng nhập/đăng ký, các trang của quản trị và cư dân, cùng hộp thoại hoá đơn; chiều rộng 320, 390, 900, 1440 px. Không có tràn ngang toàn trang, ảnh hỏng, lỗi JavaScript, lỗi HTTP hoặc ô báo lỗi dữ liệu.
- Giao diện đã được xem trực tiếp qua trình duyệt: trang đăng nhập với ảnh kiến trúc, dashboard xanh lá–trắng–mint, bảng hoá đơn, hồ sơ và hộp thoại trên máy tính/điện thoại. Ảnh và font tiếng Việt phục vụ từ thư mục frontend trong dự án.
- Bổ sung kiểm tra sau tinh chỉnh: chữ phụ có độ tương phản cao hơn; nhãn tiện ích trên trang đăng nhập ẩn ở màn hình nhỏ; biểu tượng SVG nằm cùng dòng chữ. HTML, JS, CSS và khai báo font của gateway khớp workspace.
- Theo yêu cầu người dùng, đã xoá thư mục `test-results` và bỏ thao tác lưu ảnh/tạo thư mục đó trong browser tests. Kết quả được ghi bằng văn bản tại đây.

Hướng dẫn sửa và biên dịch giao diện: [FRONTEND.md](FRONTEND.md). Các ca MoMo vẫn sử dụng phản hồi giả lập; cần bộ khoá Sandbox và IPN HTTPS để nghiệm thu giao dịch với nhà cung cấp thật.

## Kết quả đã chạy ngày 16/10/2026

- Backend: **85 passed** qua hai lần chạy: `tests/test_billing.py tests/test_billing_http.py` — 53 ca; `tests/test_auth_resident.py tests/test_domains.py tests/test_database_health.py` — 32 ca.
- Trình duyệt: `RUN_BROWSER_TESTS=1 python -m pytest tests/test_browser.py -k 'momo or admin_creation_and_resident_payment' -q` — **3 passed, 4 deselected**. Bao gồm tạo hoá đơn/thanh toán mô phỏng/biên nhận, quay về từ MoMo không tin `resultCode` trên URL, đăng nhập/tải lại để tiếp tục đơn, lấy lại liên kết, đối soát và biên nhận. Những phản hồi MoMo trong các ca này là giả lập.
- JavaScript: `node --check frontend/app.js` — đạt. Python: compileall cho Billing, gateway và scripts — đạt.
- Docker: `docker compose config --quiet` và `docker compose up --build -d` thành công. Job `db-init` thoát thành công trước khi 8 service nghiệp vụ và gateway khởi động. `/api-status` xác nhận cả tám service `ok`.
- Bản đang chạy tại `http://localhost:5000`: HTML, JS, CSS khớp từng byte với workspace; trình duyệt đăng nhập quản trị, mở dashboard/hoá đơn không có lỗi JavaScript.
- Cấu hình thực tế: `PAYMENT_MODE=sandbox`, `ready=false`, thiếu Partner Code, Access Key, Secret Key và IPN URL. UI hiện đúng thông báo sandbox chưa sẵn sàng. Chưa phát sinh giao dịch MoMo thật.
- Đã sao lưu nhất quán SQLite tại `/app/data/QLCC.pre-momo-20261016-e8edeee4.db` trong volume Docker. Sau nâng cấp: `integrity_check=ok`, migration `billing_momo_reconciliation.sql` đã áp dụng, số bản ghi users/hoá đơn/thanh toán/payment_orders khớp bản sao lưu.
- File `QLCC.db` gốc giữ nguyên; migration, demo accounts và các thay đổi nghiệp vụ chỉ nằm trong bản sao. Kiểm thử tích hợp dùng DB tạm riêng.

## Phạm vi chứng minh

Các ca backend kiểm tra quyền từng vai trò/phạm vi căn hộ, đăng ký và tạo hồ sơ qua HTTP, khóa tài khoản, hiệu lực hợp đồng, tính phí gửi xe sáu tháng, hóa đơn trùng kỳ, thanh toán đồng thời, callback giả/chữ ký sai, outbox retry, quá hạn/khôi phục, thông báo riêng, nhân sự kỹ thuật và chatbot.

Các test nghiệp vụ dùng DB riêng; browser tests MoMo chặn phản hồi API thanh toán để mô phỏng các tình huống xác định. Kiểm tra bản Docker thực tế dùng API đang chạy và chỉ đăng nhập/đọc dữ liệu. Kiểm thử giao diện tắt chuyển động bằng thiết lập reduced motion để thao tác tự động ổn định. Không lưu ảnh chụp màn hình theo yêu cầu của người dùng.

## Chưa kiểm chứng với nhà cung cấp thật

MoMo Sandbox cần credentials và callback HTTPS công khai; Firebase cần service account/Web config/VAPID và người dùng cho phép nhận push. Bộ test hiện tại xác minh cách ký/xác thực giao dịch bằng phản hồi giả lập, không chứng minh đã phát sinh giao dịch Sandbox hoặc push Firebase thật. SQLite dùng chung và các giới hạn demo được mô tả trong [GETTING_STARTED.md](GETTING_STARTED.md).
# Firebase push — cập nhật ngày 07/11/2026

- Bổ sung volume credentials chỉ đọc cho notification-service, kiểm tra Web config/VAPID/project/service account, và lệnh `scripts/check_firebase.py` (không gửi push).
- Gửi theo tài khoản đang hoạt động và liên kết căn hộ hiện hành; thông báo phản hồi khiếu nại chỉ đến người gửi đơn. Thông báo riêng trên hệ điều hành dùng lời nhắc chung, chi tiết vẫn yêu cầu đăng nhập.
- Frontend có bật/tắt push, khôi phục khi tải lại trang, gỡ token lúc đăng xuất; service worker kiểm tra người nhận trước khi hiển thị.
- Backend: **25 passed** (`tests/test_firebase_push.py`, `tests/test_complaint_notifications.py`, `tests/test_domains.py`). Trình duyệt: **2 passed** (`tests/test_browser.py -k firebase`). Service worker: **2 passed** (`node --test tests/test_firebase_worker.cjs`). Firebase được giả lập, database tạm; không gửi tới thiết bị thật và không đổi lịch sử SePay.
- **Chưa nghiệm thu FCM thật:** người dùng chưa tạo Firebase project tại thời điểm thực hiện; thiếu cấu hình Web, VAPID và file service account. Hoàn thành theo [FIREBASE_PUSH.md](FIREBASE_PUSH.md), kiểm tra foreground/background và đúng người nhận trên trình duyệt thật.
- Docker `qlcc-notification-1` đã build/recreate và healthy; gateway trả HTTP 200 với `push.js` và worker mới. Lệnh kiểm tra trong container báo đúng các cấu hình Firebase còn thiếu, không gửi push. Không restart dịch vụ thanh toán.

