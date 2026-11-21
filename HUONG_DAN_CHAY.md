# Hướng dẫn chạy An Cư (Quản lý chung cư)

Hướng dẫn cho người mới: cài và chạy hệ thống trên máy tính, mở trên điện thoại, bật các kết nối tùy chọn (thanh toán QR, thông báo đẩy, chatbot AI) và xử lý sự cố thường gặp.

**Mục lục**

1. [Chuẩn bị](#1-chuẩn-bị)
2. [Chạy trên máy tính](#2-chạy-trên-máy-tính)
3. [Đăng nhập và dùng thử](#3-đăng-nhập-và-dùng-thử)
4. [Mở trên điện thoại](#4-mở-trên-điện-thoại)
5. [Kết nối tùy chọn: thanh toán QR, thông báo đẩy, chatbot AI](#5-kết-nối-tùy-chọn)
6. [Dữ liệu và sao lưu](#6-dữ-liệu-và-sao-lưu)
7. [Dành cho người phát triển](#7-dành-cho-người-phát-triển)
8. [Xử lý sự cố](#8-xử-lý-sự-cố)

## 1. Chuẩn bị

| Cần có | Ghi chú |
| --- | --- |
| Máy tính Windows 10/11, macOS hoặc Linux | Nên có từ 8 GB RAM |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Cài xong, mở Docker Desktop và đợi trạng thái **Engine running** |
| Mã nguồn | Tải bằng Git hoặc tải file ZIP từ GitHub (bên dưới) |

Không cần cài Python, Node.js hay tạo file cấu hình để chạy thử: Docker lo toàn bộ.

**Tải mã nguồn.** Cách 1, có Git:

```powershell
git clone https://github.com/Hoaithu2501/Quan-ly-chung-cu.KLTN.git
cd Quan-ly-chung-cu.KLTN
```

Cách 2, không có Git: mở trang GitHub của dự án, bấm **Code → Download ZIP**, giải nén, rồi mở PowerShell (hoặc Terminal) trong thư mục vừa giải nén.

**Máy chỉ có 8 GB RAM (Windows):** nên giới hạn bộ nhớ của Docker để máy không bị treo. Tạo file `%UserProfile%\.wslconfig` với nội dung dưới, chạy `wsl --shutdown`, rồi mở lại Docker Desktop:

```ini
[wsl2]
memory=2GB
```

## 2. Chạy trên máy tính

Trong thư mục dự án, chạy:

```powershell
docker compose up --build -d
```

Lần đầu mất vài phút để tải và build. Kiểm tra trạng thái:

```powershell
docker compose ps
```

Khi các service hiện `healthy`, mở **http://localhost:5000** bằng trình duyệt.

Hệ thống gồm 8 service nghiệp vụ (mỗi service một container), một gateway phục vụ giao diện ở cổng 5000, một job khởi tạo database chạy xong rồi thoát, và một container sao lưu tự động.

| Việc cần làm | Lệnh |
| --- | --- |
| Xem trạng thái | `docker compose ps` |
| Xem nhật ký một service | `docker compose logs -f billing` (thay `billing` bằng tên service) |
| Dừng hệ thống (giữ dữ liệu) | `docker compose down` |
| Chạy lại | `docker compose up -d` |
| Cập nhật khi có mã nguồn mới | `git pull`, rồi `docker compose up --build -d` |

Các container tự chạy lại mỗi khi Docker Desktop khởi động. Để hệ thống tự chạy sau khi bật máy, vào Docker Desktop → **Settings → General**, bật **Start Docker Desktop when you sign in to your computer**.

Không thêm `-v` vào `docker compose down` nếu muốn giữ dữ liệu: `-v` xóa toàn bộ database (xem mục 6).

## 3. Đăng nhập và dùng thử

Lần chạy đầu tạo database mới có dữ liệu mẫu và ba tài khoản thử:

| Vai trò | Tài khoản | Mật khẩu |
| --- | --- | --- |
| Ban quản lý | `admin` | `Admin@12345` |
| Cư dân | `resident` | `Resident@12345` |
| Kỹ thuật viên | `technician` | `Tech@12345` |

Mật khẩu này công khai, chỉ dùng để thử trên máy của bạn. Trước khi mở hệ thống ra internet (mục 4), hãy đổi mật khẩu cả ba tài khoản tại **Thông tin cá nhân**. Mật khẩu mới dài từ 6 đến 30 ký tự. Hệ thống không có chức năng quên mật khẩu, nên hãy ghi nhớ mật khẩu mới.

**Cư dân mới tham gia:**

1. Ở trang đăng nhập, cư dân chọn **Đăng ký tài khoản**, điền thông tin và mã căn hộ, rồi bấm **Tạo tài khoản cư dân**.
2. Ban quản lý vào **Cư dân & hợp đồng**, tìm cư dân đó và chọn **Xác nhận căn hộ**.
3. Từ lúc này, cư dân xem được hóa đơn, gửi yêu cầu và nhận thông báo của căn hộ.

Mỗi tài khoản thuộc một căn hộ. Ban quản lý không tạo cư dân thủ công; hợp đồng chỉ lập cho cư dân đã có tài khoản.

**Gợi ý dùng thử theo vai trò:**

- **Ban quản lý:** quản lý căn hộ, xác nhận cư dân, lập hợp đồng, lập hóa đơn điện nước hằng tháng và dịch vụ 6 tháng, duyệt đơn đăng ký gửi xe, trả lời khiếu nại, gửi thông báo, xem báo cáo, đổi vai trò tài khoản, cập nhật câu trả lời cho chatbot.
- **Cư dân:** xem và thanh toán hóa đơn, gửi khiếu nại hoặc đơn đăng ký (kể cả đăng ký gửi xe), yêu cầu sửa chữa, đọc thông báo, hỏi chatbot qua nút **Trợ lý**.
- **Kỹ thuật viên:** nhận và cập nhật phiếu sửa chữa, ghi nhận cắt/cấp lại dịch vụ khi hóa đơn quá hạn, ghi doanh thu gửi xe vãng lai theo ngày, quản lý hóa đơn như Ban quản lý.

## 4. Mở trên điện thoại

An Cư là trang web, không có trên App Store hay CH Play. Điện thoại mở trang web của máy đang chạy hệ thống, và có thể thêm biểu tượng ra màn hình chính để dùng như một ứng dụng. Máy chạy hệ thống phải đang bật và Docker đang chạy.

Có hai cách mở:

| Cách | Địa chỉ trên điện thoại | Dùng ngoài nhà | Thông báo đẩy |
| --- | --- | --- | --- |
| A. Cùng mạng Wi-Fi | `http://<IP của máy>:5000` | Không | Không |
| B. Tailscale Funnel (HTTPS) | `https://<tên-máy>.<tên-mạng>.ts.net` | Có | Có |

### Cách A: cùng mạng Wi-Fi

1. Trên máy chạy hệ thống, mở PowerShell, chạy `ipconfig` và lấy dòng **IPv4 Address** của card Wi-Fi hoặc Ethernet, ví dụ `192.168.1.20`.
2. Điện thoại kết nối cùng mạng đó rồi mở `http://192.168.1.20:5000`.
3. Nếu Windows hỏi quyền tường lửa cho Docker Desktop, cho phép trên mạng **Riêng (Private)**. Mạng khách hoặc mạng có chế độ cách ly thiết bị sẽ chặn điện thoại.

Trình duyệt chỉ cho đăng ký thông báo đẩy trên HTTPS, nên cách này không có thông báo đẩy; thông báo vẫn hiện trong mục **Thông báo** của trang web.

### Cách B: Tailscale Funnel

Tailscale Funnel miễn phí, cho một địa chỉ HTTPS cố định (không đổi khi khởi động lại máy, Docker hay Tailscale) và mở được từ mọi nơi. Đây cũng là địa chỉ SePay dùng để báo tiền về (mục 5). Chỉ cần làm một lần:

1. Cài Tailscale: mở PowerShell bằng **Run as Administrator** và chạy `winget install --id Tailscale.Tailscale -e`, hoặc tải tại [tailscale.com/download](https://tailscale.com/download).
2. Mở Tailscale từ khay hệ thống, chọn **Log in** và đăng nhập bằng Google, Microsoft hoặc GitHub. Gói miễn phí là đủ.
3. Tùy chọn: đổi tên máy để địa chỉ dễ nhớ. Vào trang quản trị Tailscale → **Machines** → máy này → **Edit machine name**, ví dụ `ancu`. Phải đổi trước bước 4, vì đổi tên sau sẽ làm đổi địa chỉ.
4. Mở một cửa sổ PowerShell mới (không cần quyền Administrator) và chạy `tailscale funnel --bg 5000`. Lần đầu, lệnh in ra một đường link để bật HTTPS và Funnel; mở link, đồng ý, rồi chạy lại lệnh.
5. Chạy `tailscale funnel status` để xem địa chỉ, dạng `https://ancu.<tên-mạng>.ts.net`. Lần đầu có thể mất tới 10 phút mới truy cập được từ internet.

Với `--bg`, Funnel tự bật lại mỗi khi Tailscale chạy. Muốn tắt hẳn, chạy `tailscale funnel reset`.

Funnel đưa trang đăng nhập lên internet: ai có địa chỉ cũng thấy trang này. Hãy đổi mật khẩu các tài khoản thử trước khi bật (mục 3).

### Thêm An Cư ra màn hình chính

**iPhone, iPad** (dùng Safari):

1. Mở **Safari**, nhập địa chỉ của hệ thống.
2. Nhấn nút **Chia sẻ** (ô vuông có mũi tên hướng lên; trên iOS mới có thể nằm trong nút **•••**).
3. Chọn **Thêm vào MH chính**, giữ tên **An Cư**, bật **Mở dưới dạng ứng dụng web** nếu có, rồi nhấn **Thêm**.
4. Mở An Cư **từ biểu tượng trên màn hình chính** rồi đăng nhập. Biểu tượng lưu đăng nhập riêng, không dùng chung với tab Safari.

**Android** (dùng Chrome):

1. Mở **Chrome**, nhập địa chỉ của hệ thống.
2. Nhấn **⋮** ở góc trên bên phải, chọn **Cài đặt ứng dụng** hoặc **Thêm vào màn hình chính**, rồi xác nhận.
3. Mở An Cư từ biểu tượng trên màn hình chính.

Samsung Internet: nhấn **≡**, chọn **Thêm trang vào**, rồi **Màn hình chính**.

### Bật thông báo đẩy trên điện thoại

Cần: mở bằng địa chỉ HTTPS (cách B) và Firebase đã được cấu hình (mục 5). Trên iPhone cần iOS 16.4 trở lên và phải mở An Cư từ biểu tượng trên màn hình chính.

Vào **Thông báo**, nhấn **Bật thông báo trình duyệt**, chọn **Cho phép**. Android 13 trở lên hỏi thêm quyền thông báo của hệ thống; chọn **Cho phép**.

Mỗi điện thoại nhận thông báo đẩy cho một tài khoản tại một thời điểm; đăng nhập tài khoản khác thì thôi nhận của tài khoản cũ. Khi đổi địa chỉ (đổi tên máy trong Tailscale), biểu tượng cũ không mở được nữa: xóa biểu tượng, thêm lại từ địa chỉ mới và bật lại thông báo.

## 5. Kết nối tùy chọn

Không có các kết nối này, mọi chức năng khác vẫn hoạt động: nút thanh toán QR bị khóa kèm lý do, thông báo vẫn hiện trong trang web, chatbot trả lời bằng nội dung có sẵn.

Tạo file cấu hình từ mẫu (chỉ làm một lần), rồi điền các mục cần dùng. Mỗi dòng trong `.env.example` có chú thích.

```powershell
Copy-Item .env.example .env
```

Sau mỗi lần sửa `.env`, chạy `docker compose up -d` để áp dụng. Không đưa `.env` lên Git: file này chứa khóa bí mật.

### Thanh toán VietQR qua SePay

Luôn thử bằng **Test Mode** trước; Test Mode chỉ mô phỏng giao dịch, không chuyển tiền thật.

1. Trên [my.sepay.vn](https://my.sepay.vn/), bật **Test Mode** và tạo tài khoản ngân hàng Test.
2. Trong `.env`: đặt `SEPAY_ENV=test`, điền `SEPAY_BANK_CODE`, `SEPAY_BANK_NAME`, `SEPAY_ACCOUNT_NUMBER`, `SEPAY_ACCOUNT_NAME`, và tự đặt một chuỗi bí mật cho `SEPAY_WEBHOOK_API_KEY`.
3. Cần địa chỉ HTTPS công khai (Tailscale Funnel, mục 4). Đặt `SEPAY_WEBHOOK_URL=https://<địa chỉ Funnel>/api/billing/sepay/webhook`.
4. Trên SePay, tạo webhook trỏ tới đúng URL đó, kiểu xác thực **API Key** với đúng giá trị `SEPAY_WEBHOOK_API_KEY`.
5. Tùy chọn đối soát dự phòng: điền cả `SEPAY_API_TOKEN` và `SEPAY_BANK_ACCOUNT_ID` (UUID tài khoản trên SePay).
6. Chạy `docker compose up -d`.

**Thử một lần thanh toán:**

1. Ban quản lý lập một hóa đơn nhỏ cho căn hộ thử.
2. Cư dân của căn hộ đó mở hóa đơn, bấm **Thanh toán VietQR** và giữ nguyên hộp thoại.
3. Trên dashboard SePay (Test Mode), mô phỏng một giao dịch tiền vào với **đúng số tiền** và **đúng nội dung chuyển khoản** hiện trong hộp thoại.
4. Vài giây sau, hộp thoại báo đã thanh toán, hóa đơn chuyển **Đã thanh toán** và tải được biên nhận.

Không quét QR Test bằng ứng dụng ngân hàng thật. Chế độ `SEPAY_ENV=live` dùng tài khoản thật và tiền thật; khi đó hệ thống không tạo tài khoản thử và từ chối khởi động nếu tài khoản thử còn dùng mật khẩu công khai.

### Thông báo đẩy qua Firebase

1. Tạo một project trên [Firebase](https://console.firebase.google.com/), thêm Web app để lấy **Web config**, tạo **VAPID key** (Cloud Messaging → Web Push certificates) và tải **service account** (Project settings → Service accounts).
2. Lưu file service account thành `secrets/firebase-credentials.json`.
3. Trong `.env`, điền `FIREBASE_PROJECT_ID`, `FIREBASE_WEB_CONFIG` (JSON viết trên một dòng) và `FIREBASE_VAPID_KEY`, rồi chạy `docker compose up -d`.
4. Kiểm tra: `docker compose exec notification python scripts/check_firebase.py`.

### Chatbot AI (Gemini)

Chatbot luôn trả lời từ kho câu hỏi thường gặp và danh bạ địa điểm của chung cư. Nếu có khóa Gemini, chatbot diễn đạt câu trả lời tự nhiên hơn nhưng vẫn chỉ dựa trên nội dung tìm được. Lấy khóa tại [Google AI Studio](https://aistudio.google.com/apikey), điền vào `LLM_API_KEY` trong `.env`, rồi chạy `docker compose up -d`.

## 6. Dữ liệu và sao lưu

**Database nằm ở đâu.** Hệ thống dùng một file SQLite tên `QLCC.db` trong volume Docker `qlcc-data`, không nằm trong thư mục dự án. Lần chạy đầu, database được tạo từ dữ liệu mẫu `tests/fixtures/demo.sql` rồi áp dụng lần lượt các file trong `migrations/`. Những lần sau chỉ áp dụng migration mới, không ghi đè dữ liệu.

**Sao lưu tự động.** Container `backup` tạo mỗi ngày một bản đã kiểm tra tại `backups/QLCC-auto-*.db` và giữ 14 bản gần nhất. Sao lưu ngay khi cần (ví dụ trước khi cập nhật):

```powershell
docker compose exec -T backup python scripts/backup_db.py --output /backups
```

`backups/` chứa dữ liệu cá nhân và mật khẩu đã băm, không đưa lên Git.

**Xem dữ liệu.** Mở một file trong `backups/` bằng [DB Browser for SQLite](https://sqlitebrowser.org/) (chọn **Open Database Read Only**). Repo có sẵn `database/QLCC_an_danh.db`, bản sao dữ liệu thật đã ẩn danh để xem cấu trúc và dữ liệu (xem `database/README.md`).

**Khôi phục một bản sao lưu** (thay `TEN-BAN-SAO-LUU.db` bằng tên file trong `backups/`):

```powershell
docker compose stop
docker compose run --rm --no-deps -v "${PWD}/backups:/backups:ro" db-init python -c "import sqlite3; s=sqlite3.connect('/backups/TEN-BAN-SAO-LUU.db'); d=sqlite3.connect('/app/data/QLCC.db'); s.backup(d); d.close()"
docker compose up -d
```

**Làm lại từ dữ liệu mẫu.** Lệnh dưới **xóa toàn bộ dữ liệu**; hãy sao lưu trước:

```powershell
docker compose down -v
docker compose up --build -d
```

## 7. Dành cho người phát triển

**Tài liệu API.** Mỗi service có Swagger UI trên máy chạy hệ thống: Auth http://localhost:5001/docs, Resident 5002, Billing 5003, Parking 5004, Maintenance 5005, Notification 5006, Complaint 5007, Chatbot 5008. Bấm **Authorize** và dán JWT lấy từ `/api/auth/login`. Trạng thái các service: http://localhost:5000/api-status.

**Sửa giao diện.** Gateway đọc thẳng thư mục `frontend/`, nên chỉ cần tải lại trang sau khi lưu. Giao diện dùng Tailwind: cài Node.js, chạy `npm ci` một lần, rồi giữ `npm run watch:css` chạy trong lúc sửa. `frontend/styles.css` là file sinh ra; sửa `frontend/theme.css` và các class trong `frontend/app.js`. Sửa code Python thì chạy lại `docker compose up --build -d`.

**Chạy không dùng Docker** (Python 3.11 trở lên; dùng database riêng `data/QLCC.db`, không phải database của Docker):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/init_db.py --demo
.\.venv\Scripts\python.exe scripts/run.py
```

Sau dòng `Ready`, mở http://localhost:5000. Nhấn **Ctrl+C** để dừng. Không chạy cùng lúc với bản Docker vì trùng cổng.

**Kiểm thử.** Bộ test tự dựng database tạm, không đụng database đang chạy, không chuyển tiền và không gửi thông báo thật:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Test giao diện mở trình duyệt thật (Chrome hoặc Edge đã cài) và tốn nhiều RAM, nên được bỏ qua trong lệnh trên. GitHub Actions tự chạy toàn bộ test, kể cả test giao diện, mỗi lần push. Muốn chạy trên máy:

```powershell
$env:RUN_BROWSER_TESTS='1'
.\.venv\Scripts\python.exe -m pytest tests/test_browser.py tests/test_bug_sheet_browser.py -q
Remove-Item Env:RUN_BROWSER_TESTS
```

## 8. Xử lý sự cố

| Hiện tượng | Cách xử lý |
| --- | --- |
| `docker` báo không kết nối được, hoặc lỗi `500 Internal Server Error` | Docker Desktop chưa chạy hoặc bị treo. Thoát Docker Desktop từ khay hệ thống, mở lại, đợi **Engine running**, rồi chạy `docker compose up -d` |
| Trang `localhost:5000` tải mãi không xong | Máy thiếu RAM. Đóng bớt ứng dụng, đặt giới hạn bộ nhớ cho Docker (mục 1), rồi khởi động lại Docker Desktop |
| Báo cổng 5000 đang được dùng | Đang có một bản khác chạy (ví dụ bản Python). Dừng bản đó, hoặc `docker compose down` rồi chạy lại |
| Một service không `healthy` | Xem nhật ký: `docker compose logs <tên service>` |
| Điện thoại không mở được `http://<IP>:5000` | Kiểm tra cùng mạng Wi-Fi, đúng IP, tường lửa Windows cho phép Docker Desktop trên mạng Private, mạng không bật cách ly thiết bị |
| PowerShell không tìm thấy lệnh `tailscale` | Mở cửa sổ PowerShell mới sau khi cài, hoặc gọi đủ đường dẫn: `& "C:\Program Files\Tailscale\tailscale.exe" funnel status` |
| Địa chỉ Funnel chỉ hiện "Không tìm thấy trang." | `.env` đang có `TUNNEL_ACCESS=webhook`. Bỏ dòng đó hoặc đặt `all`, rồi chạy `docker compose up -d` |
| Biểu tượng trên điện thoại mở ra trang lỗi | Máy chạy hệ thống đang tắt, Docker chưa chạy hoặc Tailscale chưa đăng nhập. Kiểm tra bằng `tailscale funnel status` |
| "Trình duyệt này chưa hỗ trợ thông báo đẩy." trên iPhone | Chưa mở từ biểu tượng trên màn hình chính, hoặc iOS dưới 16.4 |
| "Hãy mở bằng localhost trên máy này hoặc địa chỉ HTTPS." | Đang mở bằng `http://<IP>:5000`. Dùng địa chỉ HTTPS của Funnel |
| "Bạn chưa cho phép thông báo…" | Quyền đã bị chặn. Bật lại trong cài đặt điện thoại (iPhone: Cài đặt → Thông báo → An Cư) hoặc cài đặt trang của Chrome |
| "Firebase chưa được cấu hình đầy đủ…" | Cấu hình Firebase theo mục 5 |
| Nút **Thanh toán VietQR** bị khóa | Thiếu cấu hình SePay. Điền đủ các mục ở mục 5 rồi chạy `docker compose up -d` |
| Đã mô phỏng giao dịch trên SePay nhưng hóa đơn chưa đổi | Xem nhật ký webhook trên SePay: lỗi 401/403 là sai API Key; 404/502 là sai địa chỉ hoặc Funnel đang tắt. Nội dung chuyển khoản và số tiền phải đúng như trong hộp thoại |
| Tài khoản bị khóa khi đăng nhập | Ban quản lý đã khóa tài khoản (thường do hợp đồng thuê đã hết hạn). Ban quản lý mở khóa tại **Cư dân & hợp đồng → Chi tiết** |
