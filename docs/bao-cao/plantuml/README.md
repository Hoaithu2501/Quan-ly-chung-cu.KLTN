# Mã PlantUML cho báo cáo khóa luận

Mỗi file `.puml` là một hình trong Chương 3, tên file trùng số hình trong báo cáo (ví dụ `H3_05_...` là Hình 3.5). Các file dùng chung `_style.iuml` (font Times New Roman, nền trắng).

Sinh ảnh PNG/SVG:

```bash
java -jar plantuml.jar -tpng -charset UTF-8 docs/bao-cao/plantuml/*.puml
```

Hoặc dán từng file (kèm nội dung `_style.iuml` thay cho dòng `!include`) vào https://www.plantuml.com/plantuml hoặc extension PlantUML của VS Code. Dòng `title` có thể xóa nếu chú thích hình đã nằm dưới ảnh trong báo cáo.
