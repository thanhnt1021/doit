# Mobile Web App — Strict Rules & Conditions

Tài liệu tổng hợp **tất cả quy tắc bắt buộc** để webapp hoạt động như native mobile app.
Áp dụng cho mọi project dạng mobile-first web app. Mọi thay đổi UI/CSS/JS **phải tuân thủ** file này. Vi phạm = bug.
CSS variable values và class names cụ thể bên dưới là ví dụ reference — điều chỉnh theo project.

---

## 1. Bottom Navigation Bar — Cố định tuyệt đối

Bottom navbar **PHẢI luôn cố định ở đáy màn hình**, không bao giờ bị đẩy lên, che khuất, hay biến mất.

### CSS bắt buộc

```css
.bottom-nav {
    position: fixed !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    width: 100% !important;
    z-index: 2000 !important;
    background: rgba(255, 255, 255, 0.97) !important;
    -webkit-backdrop-filter: saturate(180%) blur(20px);
    backdrop-filter: saturate(180%) blur(20px);
    padding: 8px 0 calc(8px + var(--safe-bottom)) 0 !important;
}
```

### Các lỗi thường gặp khiến bottom-nav bị lệch

| Lỗi | Nguyên nhân | Cách phòng |
|-----|-------------|------------|
| Nav bị đẩy lên khi keyboard mở | Không dùng `position: fixed` cho nav, hoặc JS resize listener sai | Luôn dùng `position: fixed` + **KHÔNG** thay đổi `bottom` khi keyboard mở |
| Nav biến mất sau animation | `animation: ... both` với `transform` tạo new stacking context | **KHÔNG** dùng `animation-fill-mode: both` với transform trên parent của nav |
| Nav nhảy vị trí trên desktop | Thiếu `max-width` + `left:50%` + `translateX(-50%)` | Xem mục 3 (Container Constraints) |
| Nav bị che bởi modal | Modal z-index cao hơn nav | Nav `z-index: 2000`, modal `z-index < 2000` hoặc modal fullscreen che nav có chủ đích |

### Quy tắc animation liên quan bottom-nav

```css
/* Page enter animation CHỈ dùng opacity, KHÔNG dùng transform */
@keyframes pageEnter {
    from { opacity: 0; }
    to { opacity: 1; }
}

/* Forms chứa modal KHÔNG ĐƯỢC có animation/transform */
.container.py-3 > form {
    animation: none !important;
    transform: none !important;
}
```

**Lý do:** `transform` (kể cả `translateY(0)`) tạo new stacking context → `position: fixed` bên trong bị anchor vào parent thay vì viewport → bottom-nav và modal bị lệch.

### Body padding-bottom

Body **phải** có `padding-bottom` đủ để content không bị bottom-nav che:

```css
body {
    padding-bottom: calc(var(--nav-height) + var(--safe-bottom) + 16px) !important;
}
```

`--nav-height: 64px` — chiều cao navbar. `16px` thêm để content cuối cùng không sát nav.

---

## 2. Chống Auto-Zoom khi nhập text (iOS)

iOS Safari **tự động zoom vào input** khi focus nếu `font-size < 16px`. Đây là hành vi mặc định của Safari, không phải bug — nhưng phá vỡ trải nghiệm native app.

### Giải pháp đang dùng (3 lớp bảo vệ)

**Lớp 1 — Viewport meta tag** (chặn zoom toàn trang):

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0,
      maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
```

**Lớp 2 — CSS font-size tối thiểu 16px** cho mọi input:

```css
input, select, textarea {
    font-size: max(16px, inherit);
}
```

**Lớp 3 — `-webkit-text-size-adjust`** ngăn Safari tự scale text:

```css
html {
    -webkit-text-size-adjust: 100%;
}
```

### Quy tắc khi tạo input mới

- **KHÔNG BAO GIỜ** set `font-size` nhỏ hơn `16px` cho bất kỳ `<input>`, `<select>`, `<textarea>` nào
- Nếu cần input nhỏ (inline edit, filter chip...): dùng `font-size: 1rem` (= 16px), **KHÔNG** dùng `0.875rem` (14px) hay `0.75rem` (12px)
- `form-control-lg` dùng `font-size: 1rem !important` + `min-height: 52px` cho trang login/register/settings
- `.borderless-input` dùng `font-size: 1.1rem !important` cho expense form

### Lưu ý accessibility

`maximum-scale=1.0, user-scalable=no` chặn người dùng pinch-zoom. Đây là trade-off có chủ đích cho app feel, nhưng ảnh hưởng người khiếm thị. Nếu sau này cần hỗ trợ accessibility tốt hơn → chuyển sang giải pháp inline script (xem `docs/universal_rules/rules/UI_MOBILE_RULES.md` mục Viewport & Zoom Cách 2).

---

## 3. Container Max-Width — Giả lập phone frame

Mọi thành phần UI **phải** nằm trong max-width container. Trên desktop, app hiển thị dạng "phone frame" centered trên nền xám.

### Breakpoints

| Màn hình | Container max-width | Bottom-nav max-width | Modal max-width |
|----------|--------------------|--------------------|----------------|
| < 640px (mobile) | 600px (gần full-width) | 100% | 100% |
| ≥ 640px (tablet) | 480px | 480px | 420px (centered), 480px (fullscreen) |
| ≥ 768px (desktop) | 500px | 500px | 420px (centered), 500px (fullscreen) |

### CSS cho element fixed mới (template bắt buộc)

Khi tạo bất kỳ element `position: fixed` nào (action bar, floating button, overlay...):

```css
/* Mobile: full-width, không cần gì thêm */

/* Tablet: constrain trong phone frame */
@media (min-width: 640px) {
    .my-fixed-element {
        max-width: 480px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: 100% !important;
    }
}

/* Desktop: wider phone frame */
@media (min-width: 768px) {
    .my-fixed-element {
        max-width: 500px !important;
    }
}
```

### Utility classes có sẵn

- **`.mobile-contained-overlay`** — cho overlay, loading screen, action sheet
- **`.mobile-contained-fixed`** — cho fixed action bar, save bar

### Desktop background

```css
@media (min-width: 640px) {
    body {
        background: linear-gradient(180deg, #f0f2f5, #e8eaed);
    }
    .container.py-3 {
        background: var(--bg-page);
        min-height: 100dvh;
        box-shadow: 0 0 40px rgba(0,0,0,0.06);
    }
}
```

---

## 4. Safe Area Insets (Notch, Dynamic Island, Home Indicator)

iPhone có notch/Dynamic Island (trên) và home indicator (dưới) chiếm không gian màn hình. App **phải** tính các vùng này.

### CSS Variables

```css
:root {
    --safe-top: env(safe-area-inset-top, 0px);
    --safe-bottom: env(safe-area-inset-bottom, 0px);
    --safe-left: env(safe-area-inset-left, 0px);
    --safe-right: env(safe-area-inset-right, 0px);
}
```

### Áp dụng

| Thành phần | Rule |
|-----------|------|
| `body` padding-top | `var(--safe-top)` |
| `body` padding-bottom | `calc(var(--nav-height) + var(--safe-bottom) + 16px)` |
| Bottom nav padding-bottom | `calc(8px + var(--safe-bottom))` |
| Toast container top | `calc(12px + var(--safe-top))` |
| `body` padding-left/right | `var(--safe-left)` / `var(--safe-right)` |

### Viewport meta bắt buộc

```html
<meta name="viewport" content="..., viewport-fit=cover">
```

`viewport-fit=cover` cho phép app vẽ vào vùng safe area → app tự quản lý padding. Nếu không có `viewport-fit=cover`, `env(safe-area-inset-*)` trả về `0`.

---

## 5. Touch Targets — Tối thiểu 44×44px

Mọi phần tử tương tác **phải** có vùng chạm tối thiểu **44×44 pixels** (Apple Human Interface Guidelines).

### Kích thước cụ thể

| Thành phần | Kích thước tối thiểu |
|-----------|---------------------|
| Standalone button | `min-height: 44px` |
| Nav item | `min-width: 64px; min-height: 44px` |
| List item (tappable) | `padding: 14px 16px` |
| Form input (login/register) | `min-height: 52px` |
| Split header link/button | `min-width: 44px; min-height: 44px` |
| FAB (floating action button) | `min-height: 48px` |
| Icon button (close, action) | `width: 44px; height: 44px` (dùng class `.icon-container-44`) |

### Utility classes

```css
.icon-container-44 { width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; }
.icon-container-45 { width: 45px; height: 45px; ... }
.icon-container-50 { width: 50px; height: 50px; ... }
.icon-container-56 { width: 56px; height: 56px; ... }
.touch-icon-btn { min-width: 44px; min-height: 44px; ... }
```

---

## 6. Interaction States — Native Feel, Không Hover

### Quy tắc cứng

- **KHÔNG dùng `:hover`** cho bất kỳ thay đổi UI quan trọng nào (mobile không có hover)
- **CHỈ dùng `:active`** cho tap feedback
- **KHÔNG** ẩn/hiện thông tin bằng hover (tooltip hover = bug trên mobile)

### Tap feedback patterns

```css
/* Buttons */
.btn:active { transform: scale(0.97); opacity: 0.9; }

/* Cards (chỉ khi nằm trong <a>) */
a > .card:active { transform: scale(0.985); }

/* Nav items */
.nav-item-link:active { transform: scale(0.92); }

/* List items */
.list-group-item-action:active { background: var(--bg-input) !important; }

/* Split chips */
.split-chip:active { background: var(--bg-input); }
```

### Disable hover effects

```css
.btn:hover { transform: none; }
.list-group-item-action:hover { background: transparent; }
.hover-shadow:hover { box-shadow: var(--shadow-card) !important; }
```

### No text selection trên interactive elements

```css
.nav-item-link, .btn, .split-chip, .split-tab, .select-list-item {
    -webkit-user-select: none;
    user-select: none;
}
```

### Tap highlight

```css
.btn, .nav-item-link, .split-chip, .select-list-item, .list-group-item {
    -webkit-tap-highlight-color: transparent;
}
```

### Touch action (loại bỏ 300ms delay)

```css
.btn { touch-action: manipulation; }
```

---

## 7. Overscroll & Scroll Behavior

```css
html { scroll-behavior: smooth; overflow-x: hidden; }
body { overflow-x: hidden; overscroll-behavior-y: contain; }
```

- `overscroll-behavior-y: contain` — ngăn pull-to-refresh của browser (giữ native app feel)
- `overflow-x: hidden` — ngăn horizontal scroll (thường do element vượt viewport)
- `-webkit-overflow-scrolling: touch` — smooth scroll trên iOS cho scrollable containers

---

## 8. Typography & Spacing

### Font stack

```css
body {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text',
                 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    line-height: 1.5;
}
```

### Headings

```css
h1, h2, h3, h4, h5, h6 {
    font-weight: 700;
    letter-spacing: -0.02em;
}
```

### Spacing chuẩn

| Thành phần | Giá trị |
|-----------|--------|
| Container padding LR | 16px |
| Card padding | 16px |
| Card border-radius | `var(--radius-lg)` = 16px |
| Modal border-radius (centered) | `var(--radius-xl)` = 20px |
| List item padding | 14px 16px |
| Page header padding | 1.25rem 1rem |

### CSS Custom Properties (LUÔN dùng, KHÔNG hardcode)

```css
:root {
    --primary: #00cc99;
    --primary-dark: #00b386;
    --primary-light: #e6fff7;
    --danger: #ff4757;
    --danger-light: #fff0f1;
    --success: #2ecc71;
    --warning: #f39c12;
    --dark-text: #1a1a2e;
    --secondary-text: #6b7280;
    --muted-text: #9ca3af;
    --border-soft: #f0f0f0;
    --bg-page: #f8f9fb;
    --bg-card: #ffffff;
    --bg-input: #f3f4f6;
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 20px;
    --radius-full: 9999px;
    --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
    --transition-base: 250ms cubic-bezier(0.4, 0, 0.2, 1);
    --transition-spring: 300ms cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

---

## 9. Modals — Constrained trong phone frame

### Centered modals

```css
.modal-dialog-centered .modal-content {
    border-radius: var(--radius-xl) !important;  /* 20px */
}
.modal-dialog { max-width: 420px; }  /* trên desktop */
```

### Fullscreen modals (expense add, payer picker...)

```css
.modal-full-mobile .modal-dialog {
    margin: 0;
    max-width: 100%;
    height: 100dvh;
}
.modal-full-mobile .modal-content {
    height: 100%;
    border-radius: 0 !important;
}
```

Trên desktop ≥640px, fullscreen modal **phải** constrain:

```css
@media (min-width: 640px) {
    .modal-full-mobile .modal-dialog {
        max-width: 480px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
}
```

---

## 10. Toast Notifications — Centered, trên safe area

```css
#liveToastContainer {
    position: fixed;
    top: calc(12px + var(--safe-top));
    left: 50%;
    transform: translateX(-50%);
    z-index: 9999;
    width: 92%;
    max-width: 380px;
}
```

Toast tự fade-out sau 5s (8s cho error). iOS-style với backdrop blur + border-radius 16px.

---

## 11. Animations — Subtile, không phá layout

### Transition timing chuẩn

| Tên | Giá trị | Dùng cho |
|-----|--------|---------|
| Fast | 150ms cubic-bezier(0.4, 0, 0.2, 1) | Tap feedback, color change |
| Base | 250ms cubic-bezier(0.4, 0, 0.2, 1) | Fade in/out, slide |
| Spring | 300ms cubic-bezier(0.34, 1.56, 0.64, 1) | Bounce, scale |

### Page enter animation

```css
.container.py-3 > * {
    animation: pageEnter 0.3s cubic-bezier(0.4, 0, 0.2, 1) both;
}
/* Staggered delay: 0s, 0.04s, 0.08s, 0.12s, 0.16s */
```

**QUAN TRỌNG:** `pageEnter` chỉ dùng opacity, **KHÔNG** dùng transform. Xem lý do ở mục 1.

---

## 12. PWA / Home Screen Meta Tags

```html
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#00cc99">
<meta name="format-detection" content="telephone=no">
```

- `apple-mobile-web-app-capable` — cho phép add to home screen trên iOS
- `format-detection: telephone=no` — ngăn Safari tự biến số điện thoại thành link (phá layout)
- `theme-color` — màu thanh status bar trên Android Chrome

---

## 13. Prevent Double-Submit

Mọi form submit đều được bảo vệ khỏi double-tap bằng JS trong `base.html`:

```javascript
// Khi submit → disable button + show spinner
// Sau 5s → auto-enable lại (fallback)
form.dataset.submitted = 'true';  // flag ngăn submit lại
btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Đang xử lý...';
btn.disabled = true;
```

**Quy tắc:** Khi tạo form mới, **KHÔNG** cần thêm JS double-submit riêng — `base.html` đã handle toàn cục qua event delegation.

---

## 14. CSRF Protection

```html
<meta name="csrf-token" content="{{ csrf_token() }}">
```

- Mọi form `method="POST"` được tự động inject `csrf_token` hidden input (JS trong `base.html`)
- API calls (`/api/*`) exempt khỏi CSRF (dùng JWT thay thế)
- AJAX/fetch calls gửi token qua header `X-CSRFToken`

---

## 15. Height Units — `dvh` thay `vh`

```css
body { min-height: 100dvh; }
.modal-full-mobile .modal-dialog { height: 100dvh; }
```

**KHÔNG dùng `100vh`** trên mobile — `vh` không trừ thanh address bar của browser → content bị che. `dvh` (dynamic viewport height) tự điều chỉnh.

---

## Checklist khi tạo trang/component mới

- [ ] Content trong `<div class="container py-3">`?
- [ ] Mọi modal constrained trong max-width container ở mọi breakpoint?
- [ ] Mọi `position: fixed` element có `max-width` + centered trên desktop?
- [ ] Bottom nav vẫn cố định sau khi thêm component mới?
- [ ] Touch targets ≥ 44×44px?
- [ ] Input `font-size` ≥ 16px (không gây auto-zoom)?
- [ ] Safe area insets cho top/bottom?
- [ ] Chỉ dùng `:active` (không `:hover`) cho tap feedback?
- [ ] Animation không dùng `transform` trên parent chứa fixed elements?
- [ ] Text tiếng Việt có dấu?
- [ ] Dùng CSS custom properties cho colors/spacing?
- [ ] Dùng `dvh` thay `vh`?
- [ ] Test trên 375px width (iPhone SE)?
- [ ] Test keyboard mở không đẩy bottom-nav lên?

---

_File này là source of truth cho mọi quy tắc UI/UX của mobile web app. CSS variable values và class names cụ thể cần điều chỉnh theo project._
_Reference: `docs/universal_rules/rules/UI_MOBILE_RULES.md`_