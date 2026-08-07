---
name: mobile-webapp
description: Kích hoạt khi làm web app mobile cảm giác native (giao diện điện thoại, mobile-first, responsive, bottom nav, PWA, chống zoom iOS, safe area, phone frame). Trigger vi: web app mobile, giao diện điện thoại, native feel, thanh điều hướng dưới, chống auto-zoom, vùng chạm. Trigger en: mobile web app, mobile-first, responsive, bottom navigation, native-like UI, PWA, prevent iOS auto-zoom, safe area insets, touch target.
---

# Mobile Web App — Quy tắc CSS/UX cho web app cảm giác native

> Skill self-contained. Mọi mã màu / class name / giá trị dưới đây là ví dụ generic — thay bằng token của project bạn.

## Khi nào dùng
- Xây/sửa web app mobile-first muốn cảm giác như native app (app-shell).
- Thêm/sửa: bottom nav, modal, input form, fixed element, overlay, toast, dropdown trên mobile.
- Fix bug: nav nhảy/lệch khi keyboard mở, input bị iOS zoom, content bị che, layout vỡ trên iPhone, dropdown bị cắt.
- Làm PWA / add-to-home-screen; xử lý notch / Dynamic Island / home indicator.

---

## 0. Viewport — 1 QUYẾT ĐỊNH DUY NHẤT (đọc trước tiên)

Đây là điểm hay mâu thuẫn nhất. Quy tắc chốt:

**MẶC ĐỊNH: KHÔNG khoá zoom. Accessibility thắng.**
Người mắt kém phải pinch-zoom được. Chống iOS auto-zoom bằng **font-size ≥ 16px trên input**, KHÔNG bằng `user-scalable=no`.

```html
<!-- Default cho hầu hết app: KHÔNG có maximum-scale / user-scalable -->
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```
```css
/* Đây mới là cách chống auto-zoom đúng — không hy sinh accessibility */
input, select, textarea { font-size: max(16px, 1rem); }
html { -webkit-text-size-adjust: 100%; }
```

**NGOẠI LỆ (chỉ khi có lý do rõ ràng): app dạng native-feel/app-shell mà zoom sẽ phá tương tác** — game, canvas vẽ, bản đồ kéo-thả, editor pixel. Khi đó mới cho:

```html
<meta name="viewport" content="width=device-width, initial-scale=1,
      maximum-scale=1, user-scalable=no, viewport-fit=cover">
<!-- LÝ DO (bắt buộc ghi vào comment/PR): vd "canvas pan/zoom tự xử lý, pinch của
     browser xung đột với gesture của app" -->
```

Quy tắc: dùng ngoại lệ → **phải ghi lý do**. Không có lý do cụ thể (game/canvas/map) → dùng default. `viewport-fit=cover` luôn cần (để safe-area hoạt động), độc lập với quyết định zoom.

> Vì sao vẫn cần `viewport-fit=cover` ở cả 2 nhánh: thiếu nó thì `env(safe-area-inset-*)` trả về `0` → app dính notch. Xem mục 4.

---

## 1. Bottom Navigation — cố định tuyệt đối

Bottom nav phải luôn dính đáy, không bị đẩy lên / che / biến mất.

```css
.bottom-nav {
  position: fixed; bottom: 0; left: 0; right: 0; width: 100%;
  z-index: 2000;                 /* modal thường để < 2000 */
  padding: 8px 0 calc(8px + var(--safe-bottom)) 0;
  background: rgba(255,255,255,0.97);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
}
```

Body chừa chỗ để content không bị nav che:
```css
body { padding-bottom: calc(var(--nav-height) + var(--safe-bottom) + 16px); }
/* --nav-height: chiều cao nav (vd 64px); +16px để phần cuối không sát nav */
```

Lỗi hay gặp:

| Lỗi | Nguyên nhân | Phòng |
|-----|-------------|-------|
| Nav bị đẩy lên khi keyboard mở | JS đổi `bottom` khi keyboard, hoặc không `position: fixed` | Luôn `fixed`, **KHÔNG** đổi `bottom` khi keyboard mở |
| Nav biến mất sau animation | `animation ... both` + `transform` trên parent → tạo stacking context mới | KHÔNG dùng `animation-fill-mode: both` + `transform` trên parent của nav |
| Nav nhảy trên desktop | Thiếu constrain phone frame | Xem mục 3 |
| Nav bị modal che | Modal z-index ≥ nav | Nav `z-index: 2000`, modal thấp hơn (trừ modal fullscreen cố ý che) |

---

## 2. ⭐ BÀI HỌC ĐẮT NHẤT: `transform` phá `position: fixed`

**`transform` (KỂ CẢ `translateX/Y(0)`), `filter`, `perspective`, hay `will-change: transform` trên phần tử CHA sẽ tạo một stacking/containing context mới → mọi `position: fixed` bên trong bị anchor vào CHA đó thay vì viewport.** Kết quả: bottom-nav, modal, dropdown, action bar bị lệch/nhảy chỗ — cực khó debug vì CSS "trông đúng".

Hệ quả trực tiếp: **page-enter animation KHÔNG được dùng `transform`** nếu trong page có phần tử `fixed`.

```css
/* ✅ Page enter chỉ opacity — an toàn với fixed */
@keyframes pageEnter { from { opacity: 0; } to { opacity: 1; } }
.page > * { animation: pageEnter 0.3s cubic-bezier(0.4,0,0.2,1) both; }

/* ❌ Nếu form/parent chứa modal-fixed, cấm transform */
.page > form { animation: none; transform: none; }
```

Checklist khi thấy fixed element lệch: grep parent chain tìm `transform`, `filter`, `will-change`, `animation ... both`, `perspective`, `contain: paint/layout`.

---

## 3. Phone frame — constrain trên desktop

Trên desktop, app hiển thị dạng "khung điện thoại" giữa nền xám. Mọi UI nằm trong container max-width; mọi `position: fixed` cũng phải constrain (nếu không sẽ tràn full-width, vỡ frame).

```css
.app-container { max-width: 600px; margin-inline: auto; }         /* mobile ~full */
@media (min-width: 640px) { .app-container { max-width: 480px; } } /* tablet */
@media (min-width: 768px) { .app-container { max-width: 500px; } } /* desktop */

/* Nền desktop + shadow tạo cảm giác phone frame (đổi màu theo theme) */
@media (min-width: 640px) {
  body { background: linear-gradient(180deg, #f0f2f5, #e8eaed); }
  .app-container { min-height: 100dvh; box-shadow: 0 0 40px rgba(0,0,0,0.06); }
}

/* Template BẮT BUỘC cho mọi position:fixed mới (nav, FAB, action bar, overlay) */
@media (min-width: 640px) {
  .my-fixed { max-width: 480px; left: 50%; transform: translateX(-50%); width: 100%; }
}
@media (min-width: 768px) { .my-fixed { max-width: 500px; } }
```

> Lưu ý: `transform: translateX(-50%)` ở đây nằm TRÊN chính phần tử fixed — không phải trên cha nó — nên an toàn (xem mục 2).

---

## 4. Safe-area insets (notch, Dynamic Island, home indicator)

```css
:root {
  --safe-top: env(safe-area-inset-top, 0px);
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  --safe-left: env(safe-area-inset-left, 0px);
  --safe-right: env(safe-area-inset-right, 0px);
}
```

| Thành phần | Rule |
|-----------|------|
| `body` padding-top | `var(--safe-top)` |
| `body` padding-bottom | `calc(var(--nav-height) + var(--safe-bottom) + 16px)` |
| Bottom nav padding-bottom | `calc(8px + var(--safe-bottom))` |
| Toast/header top | `calc(12px + var(--safe-top))` |
| `body` padding L/R | `var(--safe-left)` / `var(--safe-right)` |

Bắt buộc `viewport-fit=cover` trong meta viewport (mục 0), nếu không `env()` trả về `0`.

---

## 5. Touch target ≥ 44×44px

Apple HIG 44×44px / Material 48×48dp. Khoảng cách giữa các target ≥ 8px.

| Thành phần | Tối thiểu |
|-----------|-----------|
| Button standalone | `min-height: 44px` |
| Nav item | `min-width: 64px; min-height: 44px` |
| Input (login/settings) | `min-height: 52px` |
| Icon button (close/action) | `width: 44px; height: 44px` |
| FAB | `min-height: 48px` |
| List item tappable | `padding: 14px 16px` |

```css
button, a { touch-action: manipulation; } /* bỏ 300ms tap delay */
```

---

## 6. Interaction — native feel, KHÔNG hover

Mobile không có hover. **Hover chỉ dùng làm decoration** (màu/shadow/lift), KHÔNG bao giờ dùng để show/hide thông tin — info đó sẽ biến mất trên mobile.

```css
/* ✅ decoration only */
.card:hover { box-shadow: var(--shadow-card); }

/* ❌ info bị ẩn trên mobile */
.tooltip { display: none; } .btn:hover .tooltip { display: block; }
```

Tap feedback dùng `:active`:
```css
.btn:active { transform: scale(0.97); opacity: 0.9; }
.nav-item:active { transform: scale(0.92); }
```
Thêm cho interactive elements:
```css
.btn, .nav-item, .chip {
  -webkit-tap-highlight-color: transparent;
  -webkit-user-select: none; user-select: none;
}
```
Thông tin quan trọng: luôn visible, hoặc toggle bằng tap/click — không bao giờ chỉ có trên hover.

---

## 7. Height units — `dvh` KHÔNG `vh`

`100vh` không trừ thanh địa chỉ browser → content bị che dưới đáy. Dùng `100dvh` (dynamic viewport height) tự điều chỉnh.

```css
body { min-height: 100dvh; }
.modal-fullscreen .dialog { height: 100dvh; }
```

---

## 8. Scroll behavior

```css
html, body { overflow-x: hidden; }               /* chặn horizontal scroll do element tràn */
body { overscroll-behavior-y: contain; }          /* chặn pull-to-refresh của browser */
html { scroll-behavior: smooth; }
.scrollable { -webkit-overflow-scrolling: touch; } /* smooth scroll iOS */
```
Filter chips scroll ngang: `overflow-x: auto; scrollbar-width: none;`.
Tránh `overflow: hidden` trên `body` khi mở modal → scroll-lock lỗi trên iOS.

---

## 9. Modal — constrained trong phone frame

Centered modal `max-width` (vd 420px) trên desktop; fullscreen modal `height: 100dvh; border-radius: 0`, và @≥640px vẫn phải constrain max-width + center (nếu không tràn full-width desktop).

```css
@media (min-width: 640px) {
  .modal-fullscreen .dialog { max-width: 480px; margin-inline: auto; }
}
```

### Dropdown bên trong modal có `overflow-y: auto` (bug hay gặp)
`position: absolute` dropdown bị `overflow-y: auto` của container cha **cắt** — đây là hành vi chuẩn của browser, không phải bug.

- Fix nhẹ: thêm `padding-bottom: 60–80px` cuối modal body → scroll thêm chút là thấy.
- Fix triệt để: dropdown dùng `position: fixed` + `getBoundingClientRect()` để tính toạ độ thực (`fixed` không bị `overflow` cha cắt).

```tsx
const r = anchorRef.current.getBoundingClientRect();
setPos({ top: r.bottom + 4, left: r.left, width: r.width });
// <div style={{ position:'fixed', top:pos.top, left:pos.left, width:pos.width, zIndex:9999 }}>
```
⚠️ Edge case: nếu parent có `transform`/`filter`, `fixed` bị anchor vào parent (mục 2) → tính sai. Kiểm tra parent chain trước khi dùng.

---

## 10. Forms & inputs

- Input font-size ≥ 16px (mục 0) — vd `1rem`, KHÔNG `0.875rem`/`0.75rem`.
- `inputmode` đúng loại: `numeric`, `email`, `tel`, `url`.
- `autocomplete`: `name`, `email`, `current-password`, `new-password`.
- Tránh `position: fixed` cho element khi keyboard mở (bị đẩy).
- Validation "touched": chỉ hiện lỗi SAU khi user focus field ≥ 1 lần (tránh lỗi đỏ ngay khi vừa vào / khi field pre-fill).
- Prevent double-submit: disable button + spinner + flag `submitted` khi submit; nên xử lý toàn cục (event delegation) thay vì JS riêng từng form.

---

## 11. Typography & spacing (dùng CSS vars, KHÔNG hardcode)

```css
:root {
  /* Ví dụ generic — thay bằng brand token của bạn */
  --primary: #2563eb; --danger: #ef4444; --success: #22c55e;
  --text: #1a1a2e; --muted: #6b7280; --bg-page: #f8f9fb; --bg-card: #fff;
  --radius-md: 12px; --radius-lg: 16px; --radius-xl: 20px;
  --transition-base: 250ms cubic-bezier(0.4,0,0.2,1);
}
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased; line-height: 1.5;
}
h1,h2,h3 { font-weight: 700; letter-spacing: -0.02em; }
```

Fluid type/spacing bằng `clamp(min-mobile, vw, max-desktop)` thay vì nhiều media query:
```css
font-size: clamp(1rem, 2.5vw, 1.25rem);
padding: clamp(1rem, 4vw, 3rem);
```
Body text mobile tối thiểu 14px; input tối thiểu 16px (mục 0).

---

## 12. PWA / home-screen meta

```html
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#2563eb">          <!-- màu theo brand -->
<meta name="format-detection" content="telephone=no"> <!-- chặn Safari auto-link số ĐT -->
```

---

## 13. Platform detection & share

```ts
const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent); // wrap trong useEffect (client only)
```
- iOS render PDF trong `<iframe>`/`<embed>` không ổn định → dùng card UI + share button; Android Chrome iframe OK.
- Share: `navigator.share`; share file kiểm tra `navigator.canShare({ files })` trước; fallback share URL / copy clipboard.

## 14. OG share card — BẮT BUỘC MỌI WEBSITE (không riêng web app)
> Bài học thật: dựng web xong quên OG → gửi link vào Zalo/FB/Slack ra card trống, mất chuyên nghiệp. **Cứ là website là PHẢI có**, không đợi nhắc. Chi tiết ở skill **seo-geo** §2 (nguồn canonical).
- Bắt buộc: `og:image` (1200×630, **URL tuyệt đối** canonical host — KHÔNG relative/SVG) + `og:title` + `og:description` + `og:type=website` + `og:url` + `twitter:card=summary_large_image`.
- Không có tool tạo PNG? Next.js: `app/opengraph-image.tsx` (next/og `ImageResponse`) sinh PNG lúc build; nếu runtime (Workers/OpenNext) không phục vụ route động → copy `.next/server/app/opengraph-image.body` vào `public/og.png`, trỏ `og:image=/og.png`. Verify: `curl -I <og-url>` → 200 + `image/*`.

---

## Verify trước khi báo xong
- [ ] **Viewport theo mục 0**: default KHÔNG khoá zoom; nếu khoá thì đã ghi lý do (game/canvas/map).
- [ ] Test ở 375px (iPhone SE): không horizontal scroll, không vỡ layout.
- [ ] Mở keyboard: bottom-nav KHÔNG bị đẩy lên / biến mất.
- [ ] Focus input: KHÔNG bị iOS auto-zoom (mọi input ≥ 16px).
- [ ] Grep parent chain của mọi fixed element: không có `transform`/`filter`/`animation…both` gây lệch.
- [ ] Mọi fixed/modal centered trong phone frame ở ≥640px và ≥768px.
- [ ] Safe-area top/bottom đúng trên máy có notch; content không bị nav che (`viewport-fit=cover`).
- [ ] Tap feedback chỉ qua `:active`; không info nào ẩn sau hover.
- [ ] Dùng `dvh` (không `vh`); colors/spacing qua CSS vars; text tiếng Việt CÓ DẤU.
- [ ] **OG share card (§14)**: `curl -s <trang> | grep og:image` có URL tuyệt đối; `curl -I <og-url>` → 200 + `image/*`. Gửi link ra card có ảnh + tiêu đề.
