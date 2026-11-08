# CI/CD với GitHub Actions

Repository: [Hoaithu2501/Quan-ly-chung-cu.KLTN](https://github.com/Hoaithu2501/Quan-ly-chung-cu.KLTN).

## Pipeline

| Thời điểm | Workflow | Công việc |
|---|---|---|
| Push nhánh, mở/cập nhật Pull Request, hoặc Run workflow | CI | Kiểm tra file nhạy cảm, tạo DB mẫu, build CSS, kiểm tra JavaScript/Firebase worker, chạy pytest backend và browser, build 10 image và thử khởi động cả hệ thống. |
| Publish GitHub Release có tag v1.0.0 hoặc v1.0.0-rc.1 | Release Docker images | Chạy lại CI trên commit phát hành, build và kiểm tra chính các image sẽ đưa lên GHCR, chỉ push khi đạt. |

Đây là **Continuous Integration + Continuous Delivery**: phát hành image có phiên bản để tải và chạy. Chưa có máy chủ triển khai cố định nên workflow không tự deploy, không restart Docker trên máy cá nhân và không đổi webhook SePay.

Kiểm thử tự động dùng dữ liệu mẫu và phản hồi nhà cung cấp giả lập. CI không chuyển tiền, không gọi SePay Live, không gửi Firebase push thật và không gọi Gemini. Việc này bổ sung cho các lần kiểm thử Live đã làm thủ công.

## 1. Bật và xem CI

1. Vào repository → **Settings → Actions → General**. Cho phép Actions và các action chính thức `actions/*`, `docker/*` được workflow sử dụng.
2. Mở **Actions → CI**. Push code sẽ tự chạy; hoặc chọn **Run workflow → main → Run workflow**.
3. Cần có ba job xanh: **Backend and browser tests**, **Docker build and smoke test**, **CI required**.
4. Nếu lỗi, mở step đỏ. JUnit report nằm tại **Artifacts → test-reports**; lỗi Docker có `docker-diagnostics`. Artifact không chứa database/credentials.
5. Nếu gói GitHub/repository hỗ trợ, đặt ruleset cho `main`: yêu cầu Pull Request và check **CI required** trước khi merge. Check chỉ hiện sau lần CI đầu tiên. Nếu gói không hỗ trợ bảo vệ nhánh, vẫn chờ CI xanh trước khi merge.

Workflow có quyền đọc source; riêng job phát hành có thêm `packages: write`. Nó dùng `GITHUB_TOKEN` tự cấp cho mỗi lần chạy. Không thêm khóa SePay, Firebase, Gemini vào Actions secrets; không cần PAT để phát hành.

## 2. Phát hành image

1. Chờ CI của commit cần phát hành xanh.
2. Chọn **Releases → Draft a new release → Choose a tag**, tạo `v1.0.0` trỏ đúng commit hoặc nhánh `main`.
3. Điền tên/mô tả rồi **Publish release**. Chỉ push tag hoặc lưu Draft chưa kích hoạt CD.
4. Theo dõi **Actions → Release Docker images** đến khi **Publish verified images to GHCR** xanh.
5. Xem danh sách image tại **Summary** của workflow hoặc **Packages** trên GitHub.

Image có dạng `ghcr.io/hoaithu2501/quan-ly-chung-cu.kltn/gateway:v1.0.0`.
Đủ 10 image: gateway, auth, resident, billing, parking, maintenance, notification, complaint, chatbot, db-init.
Mỗi image còn có tag `sha-<commit đầy đủ>`. Bản sau dùng tag mới (`v1.0.1`…); không tái sử dụng tag cũ. Workflow không ghi đè `latest`.

Nếu push gián đoạn, một phần image có thể đã lên registry; chỉ dùng bản phát hành khi toàn bộ workflow xanh. Sau khi sửa lỗi mạng/quyền, có thể **Re-run failed jobs**. Image hiện dành cho Linux amd64, phù hợp Docker Desktop Linux containers trên Windows x64.

## 3. Chạy thử image mà không tác động bản Live

PowerShell tại thư mục project:

```powershell
python scripts/ci/write_test_env.py --output .runtime/release-demo.env
$env:APP_ENV_FILE = '.runtime/release-demo.env'
$env:IMAGE_PREFIX = 'ghcr.io/hoaithu2501/quan-ly-chung-cu.kltn'
$env:IMAGE_TAG = 'v1.0.0'
$env:GATEWAY_PORT = '15000'
docker compose -p qlcc-release-demo -f docker-compose.release.yml pull
docker compose -p qlcc-release-demo -f docker-compose.release.yml up --no-build -d --wait --wait-timeout 180
```

Nếu file env thử đã tồn tại, giữ nguyên và bỏ lệnh tạo đầu tiên; script từ chối ghi đè.
Mở `http://localhost:15000`, dùng `admin / Admin@12345`, `resident / Resident@12345`, `technician / Tech@12345`.

Package private cần `docker login ghcr.io` bằng tài khoản có quyền đọc package trước khi pull (token tối thiểu `read:packages`). Không lưu token trong lệnh được commit. Repository và package có thiết lập công khai riêng.

Dừng bản thử, giữ volume:

```powershell
docker compose -p qlcc-release-demo -f docker-compose.release.yml down
```

Database thử nằm trong volume của `qlcc-release-demo`. Project Live `qlcc` dùng `docker-compose.yml` không bị tác động. Không dùng `down -v` với project Live.

## 4. Dữ liệu và bí mật

- Git loại .db, WAL/SHM, snapshot, backup, .env, secrets, log và môi trường Python/Node. Database nguồn đang có trên máy giữ nguyên.
- `tests/fixtures/demo.sql` chứa dữ liệu mẫu, không có hash đăng nhập thật. CI tạo QLCC.db từ SQL; script từ chối ghi đè file đã có.
- Image db-init cũng dùng fixture. Với volume đã có DB, bootstrap giữ dữ liệu và chỉ áp dụng migration thiếu. Bản clone Python mới chưa có .db tự tạo nguồn mẫu khi bootstrap.
- Compose release không mount frontend từ máy; gateway tự build CSS khi build image. Smoke test kiểm tra giao diện đã đóng gói.
- Tài khoản demo chỉ dùng kiểm thử. Khi chạy dữ liệu thật không bật INIT_DEMO trên DB mới và không dùng mật khẩu demo.
- Trước nâng cấp Live, sao lưu DB. Không rollback bằng cách chép DB mẫu đè DB Live; cần xem tương thích migration với phiên bản cũ.

## 5. Trước khi push

```powershell
git status --short
git add .
python scripts/ci/check_repository.py
git diff --cached --stat
git commit -m "Describe the change"
git push
```

Script từ chối file runtime, credentials và private key trong Git. Vẫn xem nội dung diff vì kiểm tra tự động không nhận diện được mọi dạng secret.
Repo phải có root là thư mục QLCC, không phải toàn bộ D:\Downloads_new; kiểm tra bằng `git rev-parse --show-toplevel`.

Tài liệu chính thức: [GitHub Actions](https://docs.github.com/en/actions/get-started/understand-github-actions), [phát hành Docker image](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images).
