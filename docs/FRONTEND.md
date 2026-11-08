# Giao diện An Cư và Tailwind CSS

Giao diện dùng HTML/JavaScript, Tailwind CSS v4 và font Be Vietnam Pro. Bảng màu chủ đạo gồm xanh rừng, trắng và mint; ảnh kiến trúc được lưu ngay trong dự án. Các trang tiếp tục lấy dữ liệu qua API hiện có.

Dashboard có bố cục ảnh ghép, nền gradient, thẻ tiện ích có ảnh và các nhóm số liệu với màu nhấn riêng. Trang đăng nhập dùng khung biểu mẫu trên nền mint; hồ sơ và bảng tin có phần giới thiệu bằng ảnh. Bốn ảnh trong dự án được cung cấp từ thư viện ảnh, không phải ảnh chung cư đang vận hành.

Chuyển động được viết bằng CSS trong `theme.css`: nội dung xuất hiện theo nhịp, mở hộp thoại, nâng thẻ và phóng nhẹ ảnh khi rê chuột. Hiệu ứng xuất hiện chạy một lần; hiệu ứng rê chuột chỉ áp dụng cho chuột/con trỏ chính xác. `prefers-reduced-motion: reduce` tắt animation và transition. Không cần thư viện animation hay JavaScript theo dõi cuộn trang.

## Sửa giao diện

Tại thư mục gốc dự án, cài Node.js LTS và chạy một lần:

```powershell
npm ci
```

Trong terminal riêng, giữ trình biên dịch chạy khi sửa giao diện:

```powershell
npm run watch:css
```

Sau khi lưu `frontend/app.js`, `frontend/theme.css` hoặc `frontend/tailwind.css`, Tailwind biên dịch lại `frontend/styles.css`. Tải lại **http://localhost:5000** để xem. Docker đang mount thư mục frontend của workspace nên không cần build lại image cho những thay đổi này.

Biên dịch một lần trước khi bàn giao/chạy trên máy khác:

```powershell
npm run build:css
```

Trong VS Code: **Terminal → Run Task → QLCC: Tailwind - watch CSS**. **Ctrl+Shift+B** biên dịch CSS rồi build/chạy Docker. Cần `npm ci` trước lần đầu. Khi chỉ chạy ứng dụng với `styles.css` đã biên dịch sẵn, Python/Docker không cần Node.js.

## Các tệp cần sửa

Các cập nhật theo yêu cầu ngày 25/10/2026: số điện thoại bắt buộc khi đăng ký và sửa hồ sơ; thương hiệu hiển thị `AN CƯ`; đơn gửi xe dùng ba loại xe và biểu phí cố định. Chọn **Đăng ký thủ tục** mở thẳng đơn gửi xe. Đóng nội quy bằng nút Đóng, Escape hoặc nền bên ngoài sẽ trở lại đơn và giữ nguyên dữ liệu đang nhập.

Khi chuyển trang hoặc tab, nội dung hiện tại được giữ đến khi API trả về rồi thay trong một lần; `aria-busy` thể hiện trạng thái tải. Hiệu ứng xuất hiện lại của nội dung dashboard đã bỏ để tránh nháy màn. Phí 6 tháng trong thống kê là dự kiến cho đủ kỳ, chưa gồm phí thẻ; hóa đơn thực tế lấy kết quả tính theo kỳ từ Parking Service.

| Tệp | Vai trò |
|---|---|
| `frontend/app.js` | Markup, utility classes Tailwind, điều hướng và gọi API |
| `frontend/tailwind.css` | Điểm vào Tailwind, nguồn quét class, bảng màu và font `@theme` |
| `frontend/theme.css` | Các thành phần dùng lại qua `@apply`; chi tiết ảnh, biểu đồ, responsive |
| `frontend/styles.css` | CSS đầu ra đã rút gọn; **không sửa trực tiếp** |
| `frontend/fonts.css` | Khai báo font cục bộ và unicode-range hỗ trợ tiếng Việt |
| `frontend/assets/images/` | Ảnh kiến trúc cho đăng nhập và Tổng quan |

Utility classes phải xuất hiện đầy đủ trong mã nguồn, ví dụ `bg-forest`, `text-forest-900`, `grid-cols-2`. Không ghép chuỗi dạng `bg-${color}` vì trình biên dịch không xác định được toàn bộ class. Nguồn quét được giới hạn rõ vào `app.js` và `index.html` theo [tài liệu Tailwind](https://tailwindcss.com/docs/detecting-classes-in-source-files).

Thiết lập dùng [Tailwind CLI chính thức](https://tailwindcss.com/docs/installation/tailwind-cli), không nạp trình biên dịch CSS trong trình duyệt. File CSS đầu ra được giữ trong dự án để các bản Python/Docker chạy ngay; `package-lock.json` cố định phiên bản build.

## Ảnh và font

Ảnh chụp từ thư viện ảnh không đại diện cho chung cư đang quản lý. Nguồn và quyền sử dụng: [IMAGE_CREDITS.md](../frontend/assets/IMAGE_CREDITS.md). Có thể thay bằng ảnh của đơn vị tại các tên tệp hiện tại; giữ bố cục dọc cho trang đăng nhập và ngang cho dashboard.

Font, giấy phép và dung lượng: [FONT_CREDITS.md](../frontend/assets/FONT_CREDITS.md). Ảnh và font đều phục vụ cùng gateway, không cần gọi máy chủ bên ngoài khi mở trang.
