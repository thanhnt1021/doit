# Design System — `docs/DESIGN.md` là nguồn sự thật UI-UX của project

> Phân biệt rõ:
> - `rules/UI_MOBILE_RULES.md` + `rules/MOBILE_APP_STRICT_RULES.md` = **CÁCH build UI** (kỹ thuật chung, mọi project: safe-area, touch target, z-index, chống auto-zoom...).
> - **`docs/DESIGN.md`** = **HỆ THIẾT KẾ CỦA project NÀY** (palette, typography, spacing, component spec, token) — nguồn sự thật để UI nhất quán, KHÔNG "mỗi trang một kiểu".

## Khi nào project CẦN `DESIGN.md`

Tạo khi project có **bất kỳ** dấu hiệu sau:
- Có file thiết kế nguồn (Figma / Canva / Sketch) cần code khớp pixel.
- Có ≥3 trang/màn dùng chung style → cần token (màu/chữ/spacing) thống nhất.
- Có design system / component library (shadcn, MUI, tự build...).
- Nhiều người (hoặc nhiều phiên AI) cùng đụng UI → dễ lệch nếu không có chuẩn.

KHÔNG cần: tool CLI, script, backend thuần, prototype 1 trang vứt đi.

## `DESIGN.md` sống Ở ĐÂU

- Đặt tại **`docs/DESIGN.md`** của project — **project-specific, NGOÀI `universal_rules/`** (không bị `sync uni` ghi đè).
- Tạo từ `docs/universal_rules/templates/DESIGN_TEMPLATE.md`.
- Trong `CLAUDE.md` thêm dòng trỏ: `> Design system: docs/DESIGN.md` (BẮT BUỘC đọc trước khi đụng UI).

## Quy tắc dùng

1. **Đọc `DESIGN.md` TRƯỚC khi sửa UI** — lấy token/spec từ đó, KHÔNG tự chế màu/spacing/size mới.
2. **Token là nguồn sự thật**: dùng biến/token đã định nghĩa, không hardcode giá trị rời rạc trùng lặp.
3. **Đổi nguyên tắc thiết kế** (palette, scale, đổi design system) = **`Constitution change`** → ghi `docs/CHANGELOG.md` (xem `CHANGELOG_RULES.md`), không đổi lén.
4. **Pixel-exact** (nếu project yêu cầu khớp Figma/Canva): đo bằng ink thật của glyph, không đo box/origin — ghi rõ phương pháp trong `DESIGN.md`.
5. UI mới phải **trace về token/component** trong `DESIGN.md`; thứ chưa có thì bổ sung vào `DESIGN.md` TRƯỚC rồi mới code (giống iron-rule roadmap).

> Map vào hệ source-of-truth: `DESIGN.md` đảm nhận phần **UX Consistency** của `constitution.md` — cùng `CLAUDE.md` tạo thành "hiến pháp" của project. Xem `CHANGELOG_RULES.md` mục mapping.
