# Bật thông báo trình duyệt bằng Firebase

Hướng dẫn cho An Cư chạy Docker tại `http://localhost:5000`. Hộp thông báo trong web vẫn hoạt động khi chưa cấu hình Firebase. Push bổ sung lời nhắc khi người dùng đang xem trang khác hoặc để trang ở nền.

## 1. Tạo Firebase project

1. Mở [Firebase Console](https://console.firebase.google.com/), đăng nhập Google.
2. Chọn **Create a project / Add project**. Đặt tên, ví dụ `An Cu QLCC`. Nếu có màn hình giới thiệu AI, có thể bỏ qua tùy chọn đó.
3. Google Analytics là tùy chọn, có thể tắt cho project này. Chọn **Create project** rồi **Continue**.
4. Vào biểu tượng bánh răng → **Project settings → General**. Ghi lại **Project ID**, không dùng tên hiển thị thay cho ID.

Không cần chuyển database của An Cư lên Firebase. SQLite, tài khoản đăng nhập và SePay tiếp tục dùng cấu hình hiện tại.

## 2. Đăng ký ứng dụng Web

1. Tại **Project overview**, chọn biểu tượng **Web `</>`**. Nếu không thấy: **Project settings → General → Your apps → Add app → Web**.
2. Đặt App nickname là `An Cu Web`. Chưa cần chọn Firebase Hosting. Bấm **Register app**.
3. Trong phần cấu hình SDK, tìm object `firebaseConfig`. Lấy các giá trị `apiKey`, `authDomain`, `projectId`, `storageBucket`, `messagingSenderId`, `appId`.
4. Chưa cần cài npm hoặc dán đoạn SDK vào HTML: source đã tích hợp SDK. Chọn **Continue to console**.

Đây là cấu hình Web công khai. Nó khác với private key của server ở bước 4. Hướng dẫn chính thức: [thêm Firebase cho Web](https://firebase.google.com/docs/web/setup).

## 3. Lấy khóa Web Push (VAPID)

1. Mở **Project settings → Cloud Messaging**.
2. Tìm **Web configuration → Web Push certificates**.
3. Bấm **Generate key pair**.
4. Sao chép **public key** vào biến `FIREBASE_VAPID_KEY` ở bước 5.
5. Kiểm tra **Firebase Cloud Messaging API (V1)** đã bật. Nếu chưa, mở liên kết quản lý API trong Google Cloud Console, chọn đúng project và bật API. Không cần bật API Legacy.

Nguồn: [Firebase Web Push certificates](https://firebase.google.com/docs/cloud-messaging/web/get-started).

## 4. Tải file xác thực cho backend

1. **Project settings → Service accounts → Firebase Admin SDK**.
2. Chọn **Generate new private key → Generate key** để tải file JSON.
3. Lưu/đổi tên file thành:

   ```text
   D:\Downloads_new\QLCC\secrets\firebase-credentials.json
   ```

4. Không dán nội dung file này vào chat, frontend hoặc README. Thư mục `secrets` đã được loại khỏi Git và Docker build context; Docker chỉ gắn nó dạng chỉ đọc vào service thông báo.

File phải thuộc **cùng project** với Web app ở bước 2. Nguồn: [tạo service account key](https://firebase.google.com/docs/admin/setup#initialize_the_sdk_in_non-google_environments).

## 5. Điền `.env`

Sửa các dòng Firebase trong `.env` thật ở thư mục project, không chỉ sửa `.env.example`. Thay giá trị trong dấu `<...>` bằng dữ liệu vừa lấy:

```dotenv
GOOGLE_APPLICATION_CREDENTIALS=secrets/firebase-credentials.json
FIREBASE_PROJECT_ID=<project-id>
FIREBASE_WEB_CONFIG='{"apiKey":"<web-api-key>","authDomain":"<project-id>.firebaseapp.com","projectId":"<project-id>","storageBucket":"<storage-bucket-từ-console>","messagingSenderId":"<sender-id>","appId":"<app-id>"}'
FIREBASE_VAPID_KEY=<public-vapid-key>
```

`FIREBASE_WEB_CONFIG` phải nằm **trên một dòng**, tên trường và giá trị đều dùng dấu nháy kép JSON. Không đưa `const firebaseConfig =`, dấu chấm phẩy hoặc dấu phẩy cuối vào biến này. Không thay các biến SePay, JWT, Gemini đang hoạt động.

## 6. Nạp cấu hình Docker và kiểm tra

Trong PowerShell ở `D:\Downloads_new\QLCC`:

```powershell
docker compose up -d --build --no-deps --wait notification
docker compose exec notification python -X utf8 scripts/check_firebase.py --check-auth
```

Phải có:

```text
Firebase: cấu hình Web, VAPID và service account cùng project: OK
Google OAuth: OK (chưa kiểm tra quyền gửi FCM hoặc việc nhận trên thiết bị).
```

Lệnh này không gửi push và không sửa database. Nó xác nhận cấu hình và Google chấp nhận khóa server; bước 8 mới kiểm chứng việc gửi/nhận thực tế. Chỉ `docker compose restart` sẽ không nạp giá trị `.env` mới; dùng lệnh `up` ở trên.

Nếu muốn kiểm tra trên Windows trước, chạy:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/check_firebase.py --check-auth
```

Gateway Docker đang gắn trực tiếp thư mục `frontend`; dùng **Ctrl+F5** để nhận giao diện mới. Nếu chạy một image không gắn frontend, build lại gateway bằng `docker compose up -d --build --no-deps --wait gateway`.

## 7. Bật quyền trên từng trình duyệt

1. Mở Chrome hoặc Edge tại `http://localhost:5000` trên máy chạy Docker.
2. Đăng nhập → **Thông báo → Bật thông báo trình duyệt**.
3. Chọn **Allow / Cho phép** khi trình duyệt hỏi. Nút đổi thành **Tắt thông báo trình duyệt** là đăng ký thành công.
4. Cho phép ứng dụng Chrome/Edge gửi thông báo trong **Windows Settings → System → Notifications**; tắt **Do not disturb** lúc kiểm thử.
5. Để kiểm tra BQL và cư dân cùng lúc, dùng hai trình duyệt hoặc hai profile riêng, ví dụ BQL trên Edge, cư dân trên Chrome. Mỗi bên đều phải bấm bật.

Đăng ký thuộc trình duyệt, profile và địa chỉ trang đang dùng. Hai tab trong cùng profile chia sẻ một đăng ký; tài khoản bật sau cùng là người nhận. `localhost`, `127.0.0.1` và URL tunnel là các địa chỉ khác nhau, phải bật lại riêng.

Trên điện thoại, dùng **HTTPS** trỏ về gateway. `localhost` trên điện thoại là điện thoại, không phải máy tính; `http://192.168...:5000` không phải secure context. Máy tính có thể dùng localhost theo [quy tắc secure context của trình duyệt](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Secure_Contexts). Nếu tunnel đổi tên miền, đăng nhập và bật thông báo tại tên miền mới. Nên nghiệm thu desktop trước.

### 7.1. iPhone: mở từ Màn hình chính

Web Push cần **iOS 16.4 trở lên** và web app được thêm vào Màn hình chính. Source đã có `manifest.webmanifest` với `display: standalone` và metadata Apple để mở An Cư theo chế độ này. Đây không phải ứng dụng phải phát hành lên App Store. [Yêu cầu của WebKit](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/).

1. Giữ máy tính chạy Docker và tunnel HTTPS; máy tính không được ngủ trong lúc thử. iPhone cần kết nối Internet, có thể dùng Wi-Fi hoặc 4G/5G.
2. Trong **Safari**, mở **URL gốc HTTPS của tunnel đang chạy**, ví dụ `https://<ten-tunnel-hien-tai>.trycloudflare.com/`. Không dùng `localhost` hay đường dẫn `/api/billing/sepay/webhook` trên điện thoại.
3. Bấm **Chia sẻ** (ô vuông có mũi tên lên) → **Thêm vào MH chính / Add to Home Screen**. Nếu phiên bản iOS có lựa chọn **Open as Web App / Mở dưới dạng ứng dụng web**, hãy bật nó. Đặt tên **An Cư** → **Thêm**.
4. Trở về Màn hình chính, **bấm biểu tượng An Cư vừa thêm**, rồi đăng nhập cư dân. Nếu bấm biểu tượng mà vẫn mở trong tab Safari, tải lại trang trong Safari và thêm lại biểu tượng bằng bản source mới.
5. Vào **Thông báo → Bật thông báo trình duyệt → Cho phép**. Quyền đã bật trên máy tính không tự chuyển sang iPhone. Nếu đã đăng nhập ở Safari, có thể vẫn phải đăng nhập lại trong An Cư trên Màn hình chính.
6. Mở **Cài đặt → Thông báo → An Cư**: bật **Cho phép thông báo**, **Màn hình khóa**, **Trung tâm thông báo**, **Biểu ngữ**. Trong Trung tâm điều khiển, tắt **Tập trung / Không làm phiền (Focus / Do Not Disturb)** lúc kiểm thử.
7. Giữ cư dân đăng nhập trên iPhone. BQL dùng máy tính gửi thông báo mới theo bảng bên dưới.

| Lần thử | Trạng thái iPhone | Thao tác của BQL trên máy tính | Kết quả cần thấy |
| --- | --- | --- | --- |
| 1 | Đang mở An Cư | Tạo thông báo riêng đúng căn hộ cư dân | Lời nhắc và nội dung mới trong web; không bắt buộc hiện biểu ngữ iOS khi app đang ở trước |
| 2 | Vuốt về Màn hình chính, để An Cư ở nền | Tạo thông báo khác, tiêu đề khác | iPhone hiện thông báo iOS. Bấm thông báo mở An Cư tại bảng tin |
| 3 | Khóa màn hình, giữ kết nối Internet | Tạo thêm thông báo mới | Thông báo hiện trên màn hình khóa hoặc trong Trung tâm thông báo tùy cài đặt |
| 4 | Cư dân A101 vẫn đăng nhập | Tạo thông báo riêng một căn hộ khác | iPhone của cư dân A101 không nhận push đó, nếu không được xác nhận thuộc căn hộ kia |
| 5 | Tắt push hoặc đăng xuất An Cư | Gửi thông báo mới cho tài khoản/căn hộ cũ | Không nhận push của tài khoản cũ trên thiết bị đó |

Khi thử ở nền, chỉ chuyển về Màn hình chính, chưa vuốt buộc đóng An Cư. Không cam kết nhận tức thời trong mọi điều kiện mạng/tiết kiệm pin. Thông báo riêng chỉ hiện lời nhắc chung; mở An Cư để xem chi tiết.

Nếu không thấy **An Cư** trong Cài đặt → Thông báo, hãy mở đúng biểu tượng trên Màn hình chính và bấm bật quyền trong web trước. Nếu báo chưa hỗ trợ push, kiểm tra phiên bản iOS và đang mở đúng chế độ web app. [Thao tác thêm web app trên iPhone theo Apple](https://support.apple.com/guide/iphone/turn-a-website-into-an-app-iphea86e5236/ios).

**Tunnel đổi tên miền:** biểu tượng cũ vẫn trỏ tới địa chỉ cũ. Thêm lại An Cư từ địa chỉ mới và đăng ký push lại; cấu hình Firebase không phải tạo lại. URL này phải đang hoạt động, không chỉ có trong `.env`. Nếu đồng thời kiểm thử thanh toán SePay, URL webhook trên dashboard SePay phải khớp tunnel hiện hành.

### 7.2. Test desktop và iPhone cùng lúc

Hai thiết bị dùng cùng backend và [database Docker](DATABASE.md); chỉ cần **một webhook SePay cho môi trường đang test**, không chia webhook theo thiết bị.

| Thiết bị | Địa chỉ | Tài khoản khi test hai vai trò |
| --- | --- | --- |
| Desktop chạy Docker | `http://localhost:5000` hoặc cùng URL HTTPS với iPhone | Ban quản lý |
| iPhone | An Cư trên Màn hình chính, được thêm từ URL HTTPS của tunnel hiện hành | Cư dân |

1. Giữ Docker và tunnel cùng chạy trên máy tính; tunnel trỏ về gateway cổng 5000.
2. Bật thông báo trên từng thiết bị. BQL tạo thông báo riêng đúng căn hộ rồi kiểm tra iPhone khi đang mở và khi ở nền.
3. Để thử nhận cùng một thông báo trên cả desktop và iPhone, có thể đăng nhập cùng một cư dân trên hai thiết bị, bật push ở cả hai; BQL gửi từ một trình duyệt/profile khác.
4. Khi kiểm tra thanh toán, cư dân chỉ thanh toán hóa đơn một lần. BQL theo dõi trạng thái và thông báo thanh toán; thành viên khác trong căn hộ thấy cùng hóa đơn đã được thanh toán. Không chuyển tiền lần hai chỉ để thử trên thiết bị còn lại.
5. URL webhook trong dashboard SePay và `SEPAY_WEBHOOK_URL` phải là `https://<tunnel-hien-hanh>/api/billing/sepay/webhook`. Đây là URL backend nhận kết quả; trên điện thoại mở URL gốc, không mở đường dẫn webhook.

Quyền Firebase cần bật riêng trên từng thiết bị và từng địa chỉ trang. Khi tunnel đổi tên miền, cập nhật URL webhook, thêm lại web app trên iPhone và bật push ở địa chỉ mới. Không phải tạo thêm webhook cho desktop.

## 8. Kiểm thử gửi/nhận

Chuẩn bị một BQL, một cư dân A101 và một cư dân căn hộ khác trên các profile riêng.

| Ca kiểm thử | Thao tác | Kết quả mong đợi |
| --- | --- | --- |
| Trang đang mở | BQL soạn thông báo chung có tiêu đề dễ nhận biết | Cư dân thấy lời nhắc trong web, bảng tin cập nhật |
| Trang ở nền | Cư dân chuyển sang tab khác; BQL tạo thông báo mới | Chrome/Edge hiện thông báo hệ điều hành; bấm vào mở bảng tin An Cư |
| Riêng căn hộ | BQL gửi thông báo riêng A101 | Các thành viên đã được xác nhận của A101 và đã bật push nhận; căn hộ khác không nhận push |
| Riêng cá nhân | Cư dân gửi khiếu nại, BQL phản hồi | Chỉ cư dân gửi khiếu nại nhận push phản hồi; người cùng căn hộ cũng không nhận thay |
| Tải lại trang | Cư dân F5, vẫn đăng nhập, tạo thông báo mới từ BQL | Tự khôi phục đăng ký, không hỏi quyền lại |
| Tắt / đăng xuất | Cư dân tắt push hoặc đăng xuất, rồi BQL tạo thông báo mới | Trình duyệt đó không hiện push cho tài khoản cũ |
| Đổi tài khoản | Đăng nhập tài khoản căn hộ khác trong trình duyệt vừa dùng | Không hiện thông báo riêng của người trước; người mới bấm bật nếu muốn nhận |

Thông báo riêng trên màn hình khóa chỉ có lời nhắc “Bạn có thông báo mới”. Chi tiết hóa đơn/khiếu nại chỉ xem sau khi đăng nhập. BQL vẫn xem thông báo căn hộ trong web theo quyền quản lý; không có nghĩa mọi thông báo riêng đều đẩy tới thiết bị BQL. Sự kiện thanh toán đã có hai nhóm nhận riêng: căn hộ và BQL.

Không cần chuyển tiền Live thêm chỉ để thử Firebase. Có thể nghiệm thu push bằng thông báo mới hoặc phản hồi khiếu nại; luồng thanh toán dùng cùng service thông báo.

## 9. Nếu chưa nhận được

| Hiện tượng | Kiểm tra |
| --- | --- |
| Firebase chưa cấu hình | Chạy `check_firebase.py` trong container; sửa đủ Web config, VAPID, project và đường dẫn file |
| Không đọc được service account | File đúng tên trong `secrets`, chưa bị lưu thành `.json.txt`; đã recreate service với volume mới |
| Google OAuth lỗi | Đúng file JSON service account, khóa chưa bị thu hồi; kiểm tra mạng và giờ máy |
| Không tạo được token | Web app, VAPID cùng project; FCM Registration API đã bật; mạng không chặn `gstatic.com`/Firebase; không dùng chế độ ẩn danh để nghiệm thu |
| Có thông báo trong web nhưng không có popup | Đã bật trên đúng profile/địa chỉ chưa; thử để tab ở nền; kiểm tra quyền trang và Notifications/Do not disturb của Windows |
| Firebase báo delivery failures | Xem `docker compose logs --tail 50 notification`; kiểm tra API V1 và quyền gửi Cloud Messaging của service account trong project |
| Máy/ngân hàng hoạt động nhưng không có push lúc mất Internet | Push cần Internet cả phía backend và thiết bị; đọc lại thông báo đã lưu trong web khi kết nối trở lại |

Push là lời nhắc bổ sung, không phải bằng chứng thanh toán. Source giữ thông báo trong database trước khi gọi Firebase; push không có hàng đợi retry riêng khi Google lỗi. Google chấp nhận gửi cũng chưa đảm bảo hệ điều hành hiện popup. Tin push chờ quá 5 phút sẽ hết hạn; thông báo trong web vẫn còn. Khi đóng hẳn trình duyệt hoặc hệ điều hành hạn chế chạy nền, không cam kết thời gian nhận.

## Kiểm thử tự động cho source

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_firebase_push.py tests/test_complaint_notifications.py tests/test_domains.py -q
node --test tests/test_firebase_worker.cjs
$env:RUN_BROWSER_TESTS='1'
.\.venv\Scripts\python.exe -m pytest tests/test_browser.py -k firebase -q
```

Các ca này dùng database tạm và giả lập Firebase, không gửi ra thiết bị thật. Hoàn tất chức năng thực tế khi bước 6 và 8 cùng đạt với project của bạn.
