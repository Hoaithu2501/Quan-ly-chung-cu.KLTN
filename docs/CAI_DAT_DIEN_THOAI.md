# Cài An Cư trên iPhone và Android

An Cư là trang web, không có bản trên App Store hay CH Play. "Cài đặt" ở đây là thêm biểu tượng An Cư ra màn hình chính. Từ biểu tượng đó, trang mở toàn màn hình như một ứng dụng và dùng chung dữ liệu với máy tính.

Mục 1 dành cho người chạy hệ thống. Mục 2 và 3 dành cho người dùng điện thoại.

## 1. Chuẩn bị trên máy chạy hệ thống

Hệ thống phải đang chạy (`docker compose up -d`). Điện thoại mở An Cư theo một trong hai cách:

| Cách mở | Địa chỉ trên điện thoại | Thông báo đẩy |
| --- | --- | --- |
| Qua Tailscale Funnel (nên dùng) | `https://<tên-máy>.<tên-mạng>.ts.net` | Có |
| Cùng mạng Wi-Fi | `http://<IP máy chạy hệ thống>:5000` | Không, vì trình duyệt chỉ cho đăng ký thông báo trên HTTPS |

**Qua Tailscale Funnel**

Tailscale Funnel miễn phí và cho một địa chỉ HTTPS **cố định**. Địa chỉ này không đổi khi khởi động lại máy, Docker hay Tailscale. Đây cũng là địa chỉ SePay dùng để gọi webhook. Chỉ cần làm một lần:

1. Cài Tailscale cho Windows: mở PowerShell bằng **Run as Administrator** và chạy `winget install --id Tailscale.Tailscale -e`, hoặc tải bộ cài tại [tailscale.com/download/windows](https://tailscale.com/download/windows).
2. Mở Tailscale từ khay hệ thống, chọn **Log in** và đăng nhập bằng tài khoản Google, Microsoft hoặc GitHub. Gói miễn phí là đủ.
3. Tùy chọn: đổi tên máy để địa chỉ dễ nhớ. Vào trang quản trị Tailscale → **Machines** → máy này → **Edit machine name**, ví dụ `ancu`. Phải đổi trước bước 4, vì đổi tên sau sẽ làm đổi địa chỉ.
4. Mở một cửa sổ PowerShell mới (không cần quyền Administrator) và chạy `tailscale funnel --bg 5000`. Lần đầu, lệnh in ra đường link để bật HTTPS và Funnel cho mạng Tailscale của bạn. Mở link, đồng ý, rồi chạy lại lệnh.
5. Chạy `tailscale funnel status` để xem địa chỉ, dạng `https://ancu.<tên-mạng>.ts.net`. Gửi cho người dùng **địa chỉ gốc** này, không kèm `/api/...`. Lần đầu, địa chỉ có thể mất tới 10 phút mới truy cập được từ internet.
6. Trong `.env`, đặt `SEPAY_WEBHOOK_URL=https://<địa chỉ ở bước 5>/api/billing/sepay/webhook`. Sửa webhook trên SePay trỏ tới đúng địa chỉ đó, rồi chạy `docker compose up -d`.

Có `--bg` thì Funnel tự bật lại mỗi khi Tailscale chạy, không cần mở cửa sổ nào. Muốn tắt hẳn, chạy `tailscale funnel reset`. Funnel đang ở giai đoạn thử nghiệm (beta) và có giới hạn băng thông, nhưng đủ cho chung cư dùng và cho demo.

Trong `.env` không đặt `TUNNEL_ACCESS=webhook`. Giá trị đó chỉ cho Funnel (và Cloudflare Tunnel) chuyển webhook ngân hàng, điện thoại sẽ chỉ thấy dòng "Không tìm thấy trang.". Nếu không có dòng này, mặc định là `all`.

Khi Funnel mở cả trang web, ai có địa chỉ cũng thấy trang đăng nhập. Hãy dùng mật khẩu mạnh. Khi không cần dùng điện thoại, đặt `TUNNEL_ACCESS=webhook`.

Cloudflare quick tunnel (`cloudflared tunnel --url http://localhost:5000 --protocol http2`) vẫn dùng được thay cho Funnel, nhưng đổi địa chỉ mỗi lần chạy lại. Khi đó phải cài lại biểu tượng trên điện thoại và sửa webhook SePay.

**Cùng mạng Wi-Fi**

1. Trên máy chạy hệ thống, mở PowerShell, chạy `ipconfig` và lấy dòng `IPv4 Address` của card Wi-Fi hoặc Ethernet, ví dụ `192.168.1.20`.
2. Điện thoại kết nối cùng mạng đó rồi mở `http://192.168.1.20:5000`.
3. Nếu Windows hỏi quyền tường lửa cho Docker Desktop, chọn cho phép trên mạng **Riêng (Private)**. Mạng khách hoặc mạng có chế độ cách ly thiết bị sẽ chặn điện thoại.

**Thông báo đẩy** chỉ hoạt động khi đã cấu hình Firebase ([GETTING_STARTED.md](GETTING_STARTED.md), mục 6). Khi chưa cấu hình, thông báo vẫn hiện trong mục **Thông báo** của trang web.

## 2. iPhone và iPad

Cần iOS hoặc iPadOS 16.4 trở lên để nhận thông báo đẩy. Hãy dùng Safari.

1. Mở **Safari** và nhập địa chỉ HTTPS mà người chạy hệ thống gửi.
2. Nhấn nút **Chia sẻ** (ô vuông có mũi tên hướng lên). Trên iOS bản mới, nút này có thể nằm trong nút **•••** ở thanh dưới.
3. Kéo xuống, chọn **Thêm vào MH chính**.
4. Giữ tên **An Cư**. Nếu có tùy chọn **Mở dưới dạng ứng dụng web**, để bật. Nhấn **Thêm**.
5. Mở An Cư **từ biểu tượng trên màn hình chính**, rồi đăng nhập. Biểu tượng lưu đăng nhập riêng, không dùng chung với tab Safari.
6. Bật thông báo: vào **Thông báo**, nhấn **Bật thông báo trình duyệt**, chọn **Cho phép**.

Trên iPhone, thông báo đẩy chỉ bật được khi mở từ biểu tượng. Nếu mở trong tab Safari, trang báo "Trình duyệt này chưa hỗ trợ thông báo đẩy.".

## 3. Android

Nên dùng **Chrome** bản mới.

1. Mở **Chrome** và nhập địa chỉ HTTPS mà người chạy hệ thống gửi.
2. Nhấn **⋮** ở góc trên bên phải, chọn **Cài đặt ứng dụng** hoặc **Thêm vào màn hình chính** (tên mục tùy phiên bản Chrome), rồi xác nhận.
3. Mở An Cư từ biểu tượng trên màn hình chính, đăng nhập nếu được hỏi.
4. Bật thông báo: vào **Thông báo**, nhấn **Bật thông báo trình duyệt**, chọn **Cho phép**. Android 13 trở lên sẽ hỏi thêm quyền thông báo của hệ thống; hãy chọn **Cho phép**.

Samsung Internet cũng làm được: nhấn **≡**, chọn **Thêm trang vào**, rồi **Màn hình chính**.

## 4. Đổi địa chỉ, tắt thông báo, gỡ cài đặt

- **Khi đổi địa chỉ** (đổi tên máy trong Tailscale, hoặc chuyển giữa Cloudflare và Funnel): biểu tượng cũ không mở được nữa. Xóa biểu tượng cũ, cài lại từ địa chỉ mới theo mục 2 hoặc 3, rồi bật lại thông báo.
- **Tắt thông báo:** vào **Thông báo**, nhấn **Tắt thông báo trình duyệt**. Bạn cũng có thể tắt trong cài đặt điện thoại: trên iPhone vào Cài đặt → Thông báo → An Cư; trên Android nhấn giữ biểu tượng, chọn Thông tin ứng dụng → Thông báo.
- **Gỡ cài đặt:** nhấn giữ biểu tượng An Cư và chọn xóa hoặc gỡ cài đặt. Dữ liệu trên hệ thống không bị ảnh hưởng.
- Mỗi điện thoại chỉ nhận thông báo đẩy cho **một tài khoản** tại một thời điểm. Khi đăng nhập tài khoản khác, điện thoại thôi nhận thông báo của tài khoản cũ.

## 5. Xử lý sự cố

| Hiện tượng | Cách xử lý |
| --- | --- |
| Điện thoại không mở được `http://<IP>:5000` | Kiểm tra cùng mạng Wi-Fi, đúng IP, tường lửa Windows cho phép Docker Desktop, mạng không bật cách ly thiết bị |
| PowerShell báo không tìm thấy lệnh `tailscale` | Mở cửa sổ PowerShell mới sau khi cài, hoặc gọi đủ đường dẫn: `& "C:\Program Files\Tailscale\tailscale.exe" funnel status` |
| Trang qua Funnel chỉ hiện "Không tìm thấy trang." | `.env` đang có `TUNNEL_ACCESS=webhook`. Bỏ dòng đó hoặc đặt `all`, rồi chạy `docker compose up -d` |
| Biểu tượng mở ra trang lỗi | Máy chạy hệ thống đang tắt, Docker chưa chạy, hoặc Tailscale chưa đăng nhập. Kiểm tra bằng `tailscale funnel status` trên máy đó |
| "Hãy mở bằng localhost trên máy này hoặc địa chỉ HTTPS." | Đang mở bằng `http://<IP>:5000`. Dùng địa chỉ HTTPS của Funnel để bật thông báo |
| "Trình duyệt này chưa hỗ trợ thông báo đẩy." trên iPhone | Chưa mở từ biểu tượng màn hình chính, hoặc iOS dưới 16.4 |
| "Bạn chưa cho phép thông báo…" | Quyền đã bị chặn. Bật lại trong cài đặt điện thoại (mục 4) hoặc trong cài đặt trang của Chrome, rồi nhấn lại **Bật thông báo trình duyệt** |
| "Firebase chưa được cấu hình đầy đủ…" | Người chạy hệ thống cần cấu hình Firebase theo [GETTING_STARTED.md](GETTING_STARTED.md), mục 6 |
| Thông báo đến chậm khi khóa màn hình | Chế độ tiết kiệm pin hoặc chế độ Tập trung đang hạn chế thông báo. Cho phép An Cư trong các chế độ đó |
| Biểu tượng trên màn hình chính không đúng logo | Điện thoại lưu biểu tượng lúc cài. Nếu đã cài trước khi web có ảnh logo PNG, xóa biểu tượng và cài lại |
