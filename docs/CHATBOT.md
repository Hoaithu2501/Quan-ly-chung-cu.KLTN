# Trợ lý cư dân An Cư

Chatbot tìm thông tin trong `faq_knowledge_base` và `locations` trước khi trả lời. Có thể bật LLM để diễn đạt lại những nguồn đã tìm thấy; không có cấu hình hoặc nhà cung cấp lỗi thì trả về nội dung gốc. Việc mở rộng FAQ và sửa cách tìm kiếm đều cần thiết: prompt không tự sửa được dữ liệu sai hoặc kết quả tìm kiếm sai.

## 1. Nội dung và cách trả lời

- Bộ [SQL FAQ v3](../scripts/sql/chatbot_faq_v3.sql) cập nhật các câu vận hành đã chốt, giữ ID và FAQ tự thêm. Cách INSERT, xem trước, sao lưu và cập nhật đúng DB Python/Docker nằm trong [CHATBOT_DATA.md](CHATBOT_DATA.md).
- Tìm kiếm hỗ trợ tiếng Việt không dấu và từ đồng nghĩa, phân biệt phí, hạn, lịch sử, phương thức thanh toán và hotline. Câu hỏi vị trí lấy danh bạ địa điểm. Những câu không đủ dữ liệu nhận phản hồi chưa có thông tin.
- Cư dân có thể hỏi tự nhiên như “gửi xe điện hết bao nhiêu tiền?” hoặc “xe đạp điện được để ở chung cư không?”. Tìm kiếm nhận diện ý hỏi giá và loại xe được nhận, không yêu cầu gõ đúng tiêu đề FAQ. Xe điện gồm xe máy điện và xe đạp điện; mức phí trong nguồn được phân biệt với xe đạp thường. Câu hỏi về sạc xe vẫn cần nguồn quy định riêng, không suy ra từ việc được gửi xe.
- “Tiền nhà” được hỏi lại là tiền thuê hay phí dịch vụ. Câu hỏi nhiều ý có thể dùng nhiều nguồn. Các câu hỏi khẩn cấp bỏ qua bước gọi LLM, trả nội dung quản lý đã có hoặc hướng dẫn liên hệ ứng cứu khi thiếu dữ liệu.
- Prompt thực tế là [system_prompt.txt](../chatbot-service/prompts/system_prompt.txt); file được đóng gói trong image chatbot. Câu hỏi và nguồn là dữ liệu JSON, không được ghép thành chỉ dẫn hệ thống.
- Chatbot chỉ hướng dẫn thao tác; thanh toán, phê duyệt và các trạng thái nghiệp vụ vẫn do service chuyên trách xác nhận.

## 2. Bật LLM tùy chọn

Cấu hình demo của dự án dùng **[Google Gemini 3.5 Flash-Lite](https://aistudio.google.com/docs/models/gemini-3.5-flash-lite)**, dùng chung cho mọi tài khoản. Model do backend đọc từ `.env`; giao diện chỉ có phần hỏi đáp và không có bộ chọn model. API hỏi đáp chỉ nhận `question`, không cho client ghi đè model hoặc khóa API.

Điền trong file `.env` **ở thư mục gốc dự án**, giữ nguyên các cấu hình khác:

```dotenv
LLM_API_URL=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
LLM_API_KEY=KHOA_API_CUA_BAN
LLM_MODEL=gemini-3.5-flash-lite
LLM_TIMEOUT_SECONDS=15
LLM_REASONING_EFFORT=minimal
```

Tạo khóa tại [Google AI Studio](https://aistudio.google.com/api-keys), rồi thay `KHOA_API_CUA_BAN` bằng khóa thật. Chỉ lưu khóa trong `.env` ở backend, không đưa vào JavaScript frontend hoặc tài liệu. Thiếu khóa thì chatbot tiếp tục trả lời từ kho kiến thức. URL trên dùng [API tương thích Chat Completions của Google](https://ai.google.dev/gemini-api/docs/openai).

Để demo miễn phí, giữ dự án Google ở **Free Tier**, chọn model được hỗ trợ và dùng trong [hạn mức của tài khoản](https://ai.google.dev/gemini-api/docs/rate-limits). Chạy trên `localhost` vẫn cần Internet và vẫn tiêu thụ hạn mức API. Code không bật Billing hay chuyển dự án sang trả phí. Kiểm tra gói và model trên [bảng giá Google](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite); nếu API từ chối do hết hạn mức, chatbot trả lời từ FAQ dự phòng.

Nhà cung cấp nhận câu hỏi và tối đa năm nguồn FAQ/địa điểm được chọn. Ở Free Tier, Google có thể sử dụng nội dung gửi và nhận để cải thiện sản phẩm theo [điều khoản Gemini API](https://ai.google.dev/gemini-api/terms). Mã tài khoản, JWT và dữ liệu hóa đơn cá nhân không được tự động thêm vào payload này; nội dung người dùng tự nhập trong câu hỏi vẫn được gửi đi.

Đặt `LLM_REASONING_EFFORT=minimal` cho tác vụ diễn đạt FAQ ngắn. Nếu quản trị viên đổi model hoặc nhà cung cấp sau này, kiểm tra khả năng hỗ trợ `response_format: {"type":"json_object"}`, `max_completion_tokens` và message `system`/`user`. `LLM_REASONING_EFFORT` phụ thuộc model; để trống thì không gửi tham số này. URL/key/model phải có đủ; không dùng khóa webhook SePay, JWT hoặc token nội bộ làm khóa LLM.

Sau khi đổi cấu hình Docker:

```powershell
docker compose up -d --build --no-deps --force-recreate chatbot
```

Nếu lệnh báo lỗi `500 Internal Server Error` tại `dockerDesktopLinuxEngine/_ping`, Docker Engine chưa phản hồi bình thường. Mở Docker Desktop, chờ Engine hoạt động; nếu lỗi còn tiếp diễn thì khởi động lại Docker Desktop và chạy lại lệnh trên. Không cần xóa volume hoặc tạo lại database để đổi cấu hình model.

Nếu chạy Python, khởi động lại runner. File prompt được đọc từ source mỗi lần gọi LLM trong bản Python; với Docker cần build image để nhận file đã sửa.

Kiểm tra trên web bằng câu hỏi “Phí gửi xe điện bao nhiêu?”. Trong trình duyệt, mở F12 → Network → yêu cầu `ask` → Response: `engine: "llm"` xác nhận lượt đó đã dùng AI; `engine: "knowledge_base"` là trả lời trực tiếp từ kho kiến thức. Nếu đã điền khóa nhưng vẫn nhận `knowledge_base`, kiểm tra hạn mức API, quyền truy cập model và việc tạo lại container. Việc tra cứu hóa đơn cá nhân ở phần 3 có cấu hình riêng và trả `resident_data`, không dùng LLM.

Mỗi lượt chỉ gọi LLM một lần, không tự retry. Thời gian chờ đọc mặc định 8 giây, cấu hình trong khoảng 1–15 giây, ngoài thời gian kết nối tối đa 3 giây. Lỗi HTTP, timeout, JSON sai, câu bị cắt, trích nguồn không tồn tại, URL/HTML hoặc số liệu không có trong nguồn được trích đều quay về câu trả lời gốc. Đây là lớp giảm sai sót; nó không chứng minh mọi câu diễn đạt của LLM đều đúng ngữ nghĩa. Cần kiểm tra bộ câu hỏi nghiệp vụ với model thực tế trước khi dùng rộng rãi.

## 3. Tra cứu hóa đơn của chính cư dân

Mặc định tắt. Có thể bật bằng `CHATBOT_RESIDENT_CONTEXT_ENABLED=true` và tạo lại container chatbot. Câu hỏi rõ là dữ liệu của mình, ví dụ “Hóa đơn của tôi còn nợ bao nhiêu?”, được tra cứu qua Billing bằng JWT đang đăng nhập. Billing quyết định phạm vi căn hộ; chatbot không dùng token nội bộ và không nhận `resident_context`, `resident_id` hoặc `apartment_id` do client gửi.

Kết quả là nội dung dựng trực tiếp từ hóa đơn của tài khoản, không qua LLM. Chatbot không xác nhận đã chuyển tiền chỉ dựa trên lời người dùng. Khi Billing lỗi, trả lời chưa lấy được dữ liệu thay vì báo không có nợ. Ban quản lý tra cứu các căn hộ trong mục Hóa đơn & thanh toán bằng quyền quản lý như trước.

## 4. Kiểm thử và phản hồi API

`POST /api/chatbot/ask` giữ body `{"question":"Phí gửi xe bao nhiêu?"}` và yêu cầu JWT. Kết quả giữ các trường `answer`, `matched`, `source`, `source_id`, `source_title`, `confidence`; bổ sung `sources` và `engine` (`knowledge_base`, `llm`, `resident_data`). Nguồn và confidence mô tả truy xuất, không phải xác suất câu trả lời đúng.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_chatbot_retrieval.py tests/test_chatbot_assistant.py tests/test_chatbot_seed.py tests/test_chatbot_integration.py -q
```

Các test nhà cung cấp dùng phản hồi giả lập. Chúng kiểm tra giới hạn và fallback, không xác nhận khóa/model thực tế có thể gọi được. Nạp FAQ vào đúng DB đang phục vụ web rồi thử ít nhất: giá gửi xe; ngày đến hạn; thanh toán quá hạn; lịch sử thanh toán; hotline; địa điểm có/không có trong danh bạ; câu nhiều ý; câu thiếu thông tin.
