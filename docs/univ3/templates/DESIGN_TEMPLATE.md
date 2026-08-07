# DESIGN — Hệ thiết kế <Tên Project>

> Nguồn sự thật UI-UX của project này. Đọc TRƯỚC khi đụng giao diện. Quy tắc: `docs/universal_rules/rules/DESIGN_SYSTEM.md`.
> Đổi nguyên tắc ở đây = `Constitution change` → ghi `docs/CHANGELOG.md`.

## Nguồn thiết kế
- **File gốc**: <link Figma / Canva / Sketch, hoặc "tự thiết kế">
- **Phương pháp khớp**: <pixel-exact theo ink glyph / tương đối / tự do>
- **Design system nền**: <shadcn-ui / MUI / Tailwind thuần / tự build>

## Design Tokens

### Màu (palette)
| Token | Giá trị | Dùng cho |
|---|---|---|
| `--color-primary` | `#______` | nút chính, link, nhấn |
| `--color-bg` | `#______` | nền |
| `--color-text` | `#______` | chữ chính |
| `--color-muted` | `#______` | chữ phụ, border |
| `--color-danger` / `--color-success` | `#______` | trạng thái |

### Typography
| Token | Font / Size / Weight / Line-height | Dùng cho |
|---|---|---|
| `--font-display` | <font>, 32px, 700, 1.2 | tiêu đề lớn |
| `--font-h2` | <font>, 24px, 600, 1.3 | tiêu đề mục |
| `--font-body` | <font>, 16px, 400, 1.5 | nội dung (≥16px chống auto-zoom iOS) |
| `--font-caption` | <font>, 13px, 400, 1.4 | chú thích |

### Spacing scale
`4 · 8 · 12 · 16 · 24 · 32 · 48 · 64` (px) — chỉ dùng các bậc này, không số lẻ.

### Bo góc / Shadow / Breakpoint
- Radius: `sm 4px · md 8px · lg 16px · full 9999px`
- Shadow: `sm <...> · md <...> · lg <...>`
- Breakpoint: `mobile <640 · tablet 640-1024 · desktop >1024`

## Components (spec)
Mỗi component: trạng thái (default/hover/active/disabled), padding, size, token dùng.

| Component | Spec ngắn |
|---|---|
| Button | height 44px (touch), padding 12/24, radius md, primary dùng `--color-primary` |
| Input | height 44px, font ≥16px, border `--color-muted`, focus `--color-primary` |
| Card | padding 16, radius lg, shadow sm |
| <thêm...> | |

## Layout & Grid
- Container max-width: <px>. Cột: <12-col / flex>. Gutter: <px>.
- Safe-area (mobile): `env(safe-area-inset-*)`. Bottom-nav nếu có: chiều cao <px>.

## Iconography & Motion
- Icon set: <lucide / heroicons / ...>, size mặc định <px>, stroke <px>.
- Motion: duration <ms>, easing <cubic-bezier>. Hạn chế animation gây layout shift.

## Accessibility
- Tương phản ≥ WCAG AA (4.5:1 text). Touch target ≥ 44px. Focus visible. Alt cho ảnh.

## Do / Don't
- ✅ Dùng token; ✅ chữ tiếng Việt có dấu; ✅ ≥16px input.
- ❌ Hardcode màu/spacing rời; ❌ tự chế size ngoài scale; ❌ đổi palette không ghi CHANGELOG.

## Pixel-exact (nếu áp dụng)
- Đo **ink thật của glyph** (canvas pixel-scan mép chữ), CẤM đo box/origin (`range.left` đã gồm side-bearing → lệch).
- Mỗi màn so với <Figma/Canva trang N>; sai số cho phép: <±Npx>.
