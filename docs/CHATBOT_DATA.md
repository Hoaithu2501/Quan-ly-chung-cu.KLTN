# Bổ sung FAQ cho chatbot AN CƯ

Dùng [`scripts/sql/chatbot_faq_v3.sql`](../scripts/sql/chatbot_faq_v3.sql) thay cho phần nhập FAQ trong `faq_seed_v2.sql`. File v3 đã sửa nội dung theo chức năng hiện có, giữ ID và các FAQ khác do Ban quản lý tự nhập. Việc cập nhật source không tự chạy SQL này; dùng runner bên dưới để xem trước và áp dụng trên đúng DB. Trạng thái các lần áp dụng đã thực hiện được ghi trong [VERIFICATION.md](VERIFICATION.md).

## Chọn đúng cơ sở dữ liệu

| Cách chạy ứng dụng | DB đang phục vụ web |
|---|---|
| Python trên máy | `DATABASE_PATH` trong môi trường; mặc định `data/QLCC.db` |
| Docker Compose | `/app/data/QLCC.db` trong volume `qlcc_qlcc-data` |
| File `QLCC.db` ở gốc dự án | Dữ liệu nguồn, không phải DB đang phục vụ web |

Sửa `QLCC.db` ở gốc hoặc `data/QLCC.db` trên Windows không tự cập nhật DB trong Docker. Runner bên dưới từ chối ghi vào file nguồn ở gốc và file chỉ định bằng `DATABASE_SEED_PATH`. Không thay cả DB ứng dụng chỉ để thêm FAQ.

## Cách sửa INSERT

Bảng hiện tại có `faq_id`, `category`, `question`, `answer`. Chưa có ràng buộc `UNIQUE(question)`, nên `ON CONFLICT(question)` không sử dụng được. Cách phù hợp là cập nhật đúng câu hỏi đã biết, rồi chỉ thêm nếu chưa tồn tại. Không tự gán `faq_id`, không `DELETE WHERE faq_id > ...`, không đặt lại `sqlite_sequence`, không dùng `INSERT OR REPLACE` để thay FAQ.

Ví dụ dưới đây có thể chạy lại mà không tạo thêm cùng một câu hỏi:

```sql
UPDATE faq_knowledge_base
SET category = 'Liên hệ',
    answer = 'Số điện thoại hỗ trợ của Ban quản lý là 0228913665.'
WHERE question = 'Số hotline của chung cư là gì?';

INSERT INTO faq_knowledge_base (category, question, answer)
SELECT 'Liên hệ',
       'Số hotline của chung cư là gì?',
       'Số điện thoại hỗ trợ của Ban quản lý là 0228913665.'
WHERE NOT EXISTS (
    SELECT 1 FROM faq_knowledge_base
    WHERE question = 'Số hotline của chung cư là gì?'
);
```

Giữ nguyên câu hỏi khi sửa nội dung một FAQ đã có. Đổi cách viết câu hỏi rồi chạy `INSERT` sẽ tạo một FAQ khác. Nếu chỉ muốn sửa một dòng cụ thể trong các câu hỏi trùng, dùng `UPDATE ... WHERE faq_id = ...` sau khi kiểm tra ID. Dấu nháy đơn trong nội dung SQL phải viết hai lần, ví dụ `''`.

File v3 dùng một bảng `TEMP` để áp dụng cùng mẫu trên cho nhiều câu. `insert_new = 1` nghĩa là thêm câu còn thiếu; `insert_new = 0` chỉ sửa câu v2 đã tồn tại. Những câu nằm trong danh sách v3 sẽ được cập nhật khi chạy lại, kể cả khi Ban quản lý đã sửa câu trả lời đó; hãy xem phần `previous_answer` trong preview. Các câu hỏi ngoài danh sách không bị đổi. Nếu DB đã có hai dòng cùng câu hỏi, cả hai giữ nguyên ID và được cập nhật; runner báo `duplicate_questions` để bạn chủ động rà soát, không tự xóa.

## Nội dung đã sửa

- Gửi xe gồm xe máy, xe điện (xe máy điện và xe đạp điện) và xe đạp thường; phí lần lượt 100.000, 100.000 và 50.000 đồng/tháng. Xe đạp điện thuộc nhóm xe điện, không dùng mức phí xe đạp thường. Thẻ mới 100.000 đồng một lần, cam kết ít nhất 2 tháng. Thu cùng phí dịch vụ theo kỳ 6 tháng, tính các tháng có đăng ký trong kỳ. Giữ 5 FAQ chính sách đã chốt, thời gian xét duyệt 48 giờ và tốc độ tối đa 20 km/h.
- Ngày phát hành và hạn hóa đơn theo thông tin Ban quản lý nhập; không áp ngày 10 cho mọi hóa đơn. Thanh toán đủ tổng tiền, chưa hỗ trợ trả từng phần. Tải biên nhận nội bộ; chưa có chức năng phát hành hóa đơn điện tử thuế.
- Luồng online hiện là VietQR/SePay. Test Mode chỉ mô phỏng giao dịch trên dashboard SePay; không hướng cư dân quét bằng ứng dụng ngân hàng thật để thử. Live là chuyển tiền thật. Hóa đơn chỉ được ghi đã thanh toán sau khi server đối soát đủ tiền; Tôi đã chuyển khoản chỉ báo đang chờ xác nhận.
- Sửa chữa đi qua **Sửa chữa & bảo trì → Tạo yêu cầu**. Đăng ký thủ tục hiện mở form gửi xe. Không hướng dẫn đặt phòng, sự kiện, cấp thẻ hoặc trích xuất camera bằng form chưa tồn tại.
- Hotline đã xác nhận là **0228913665**. Không đưa các số mẫu trong v2 vào chatbot.
- Khiếu nại theo dõi tại **Khiếu nại & đăng ký**. Ban quản lý có thể phản hồi hoặc sửa phản hồi; cư dân đã gửi đơn nhận thông báo riêng khi có nội dung mới. Thông báo đẩy bật lên trên thiết bị còn phụ thuộc cấu hình và quyền trình duyệt.

V3 không sửa `notifications`, `locations` hoặc dữ liệu giao dịch. Các quy định chưa được chốt như giờ yên tĩnh, giờ gym/phòng sinh hoạt, thời hạn đăng ký sự kiện, mức phạt, phí sửa chữa và phí cấp lại thẻ không được tự thêm như chính sách mới. Nếu đã nhập v2 trước đây, cần rà soát riêng các câu này: v3 không tự hoàn tác mọi nội dung của v2 và không sửa lại thông báo đã phát hành. Đặc biệt không dùng khung nghỉ trưa 12:00–13:30 của v2 thay cho 12:00–14:00 trong thông báo nguồn khi chưa được xác nhận.

## Xem trước và áp dụng bằng runner

[`scripts/apply_chatbot_faq.py`](../scripts/apply_chatbot_faq.py) mặc định đọc DB, sao chép vào bộ nhớ và mô phỏng SQL. Preview không tạo bản sao trên đĩa và không ghi FAQ. Kết quả có đường dẫn DB, số dòng thêm/sửa/giữ nguyên, câu trả lời cũ/mới và danh sách câu hỏi trùng.

Trong kết quả preview, `inserted` là số câu sẽ thêm; `updated` là số câu sẽ sửa. Mở `changes` để đọc `previous_answer` (câu trả lời cũ) và `answer` (câu trả lời mới). Các câu trả lời mới dùng lời ngắn, dễ hiểu cho cư dân. Ví dụ, thay vì nói “đối soát qua IPN/API Query”, câu trả lời hướng dẫn bạn quay lại xem hóa đơn và liên hệ Ban quản lý nếu chưa được cập nhật. Preview vẫn chưa ghi thay đổi; `--apply` mới lưu các câu trả lời này.

Với bản Python, chạy từ thư mục dự án:

```powershell
.\.venv\Scripts\python.exe scripts/apply_chatbot_faq.py
```

Sau khi kiểm tra đúng DB và nội dung preview, lệnh ghi dữ liệu là:

```powershell
.\.venv\Scripts\python.exe scripts/apply_chatbot_faq.py --apply
```

Có thể chỉ rõ DB bằng `--database data/QLCC.db` và nơi lưu backup bằng `--backup-dir backups`. Lệnh từ chối tạo DB mới nếu đường dẫn sai hoặc file chưa tồn tại.

Với bản Docker, đưa script mới vào image `db-init`, rồi xem trước trên DB volume:

```powershell
docker compose build db-init
docker compose run --rm --no-deps db-init python scripts/apply_chatbot_faq.py
```

Sau khi xem preview, áp dụng trên cùng DB:

```powershell
docker compose run --rm --no-deps db-init python scripts/apply_chatbot_faq.py --apply
```

Kiểm tra từng lệnh thành công trước khi chạy bước tiếp theo. Khi `--apply`, runner giữ khóa ghi ngắn, tạo bản sao SQLite nhất quán gồm dữ liệu đã commit trong WAL, rồi cập nhật FAQ trong một transaction. Backup mặc định ở `<thư mục DB>/backups/QLCC-before-chatbot-faq-<thời điểm UTC>.db`; kết quả in đường dẫn thực tế. Có thể xuất backup Docker về máy bằng `docker compose cp chatbot:/app/data/backups/<ten-file>.db backups/` sau khi tạo thư mục `backups` trên máy. Không xóa volume.

Không cần restart chatbot chỉ để nạp FAQ, vì mỗi truy vấn đọc dữ liệu trong DB. **Bước 6 — bật AI:** dùng cấu hình Gemini 3.5 Flash-Lite chung cho mọi tài khoản, thêm API key Google AI Studio vào `.env`, rồi build/recreate theo [hướng dẫn bật LLM](CHATBOT.md#2-bật-llm-tùy-chọn). Với bản demo, giữ dự án Google ở Free Tier và dùng trong hạn mức model; hết hạn mức thì chatbot trả lời từ FAQ dự phòng. Nếu sau này dùng `refresh_db.py` để nhập lại danh mục từ nguồn cũ, hãy chạy preview FAQ v3 lại để kiểm tra nguồn có đưa câu trả lời cũ trở lại hay không.

## Dùng DB Browser for SQLite

Ưu tiên runner ở trên khi web chạy Docker. DB Browser không tự mở được DB trong named volume bằng đường dẫn `data/QLCC.db` trên Windows.

Với DB Python hoặc một bản làm việc độc lập:

1. Dừng tiến trình Python đang dùng DB, đóng các công cụ đang sửa DB và tạo bản sao nhất quán bằng chức năng backup SQLite. Không chép riêng file `.db` khi vẫn có thay đổi trong WAL.
2. Mở đúng file trong DB Browser. Lưu hoặc hoàn tác các chỉnh sửa cũ trước khi chạy script.
3. Mở tab **Execute SQL**, nạp toàn bộ `scripts/sql/chatbot_faq_v3.sql`, thực thi rồi kiểm tra các câu trả lời. File không chứa `BEGIN`/`COMMIT` để DB Browser quản lý transaction.
4. Chọn **Write Changes** khi kết quả đúng. Nếu báo lỗi, chọn **Revert Changes**, đóng/mở lại DB rồi kiểm tra lỗi trước khi thử lại; không lưu phần script chạy dở.

Các câu kiểm tra:

```sql
SELECT faq_id, category, question, answer
FROM faq_knowledge_base
ORDER BY faq_id;

SELECT question, COUNT(*) AS so_dong
FROM faq_knowledge_base
GROUP BY question
HAVING COUNT(*) > 1;

PRAGMA integrity_check;
```

## Lỗi và khôi phục

Nếu runner báo lỗi, transaction FAQ được hoàn tác; backup đã tạo vẫn giữ lại. Lỗi `database is locked` thường do DB Browser chưa lưu giao dịch hoặc có tiến trình khác giữ khóa: đóng giao dịch đó rồi chạy preview lại. Lỗi thiếu bảng/cột hoặc file không tồn tại cần kiểm tra đường dẫn, không tạo bảng tạm thay cho schema ứng dụng.

Nếu đã commit nhưng muốn phục hồi, dừng các service ghi DB và kiểm tra backup trước. Khôi phục toàn bộ backup sẽ đưa cả tài khoản/hóa đơn về thời điểm backup, nên không làm nếu đã có giao dịch mới. Khi chỉ cần sửa FAQ, đối chiếu FAQ của backup và cập nhật lại các dòng cần sửa theo `faq_id`. Nếu cần phục hồi toàn DB, dùng SQLite backup vào DB ứng dụng khi đã dừng service; không chép đè file `.db` đang hoạt động hoặc bỏ qua WAL.

Sau khi áp dụng, thử các câu “Phí gửi xe bao nhiêu?”, “gửi xe điện hết bao nhiêu tiền?”, “xe đạp điện được để ở chung cư không?”, “xe máy điện gửi tháng giá sao?”, “Hóa đơn quá hạn thì sao?”, “Hotline?” và “Báo hỏng điện nước ở đâu?”. Cả cách hỏi tự nhiên và câu không dấu đều cần nhận đúng ý hỏi giá hoặc loại xe được nhận. Đối chiếu cả câu trả lời lẫn nguồn FAQ; không dùng câu trả lời cho phép gửi xe để kết luận được sạc xe. Nội dung FAQ là dữ kiện để chatbot trả lời; không lưu API key, dữ liệu cư dân, chỉ dẫn hệ thống hoặc quy tắc phân quyền vào bảng này.
