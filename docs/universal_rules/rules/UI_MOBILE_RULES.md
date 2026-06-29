# UI & Mobile Rules

Áp dụng khi project có giao diện người dùng (web, mobile app, PWA).

## Mobile-First

- Thiết kế và test mobile trước, sau đó mở rộng ra desktop
- Breakpoints chuẩn: mobile < 768px, tablet 768–1024px, desktop > 1024px
- Font size tối thiểu: **14px** cho body text trên mobile (đảm bảo readability)
- Input fields: `font-size >= 16px` để tránh iOS auto-zoom khi focus (iOS trigger zoom ở < 16px, không phải < 14px)

## Fluid Typography & Spacing

Dùng `clamp()` thay media query để typography và spacing tự scale mượt từ mobile đến desktop:

```css
/* Typography */
font-size: clamp(1rem, 2.5vw, 1.25rem);       /* body */
font-size: clamp(2rem, 5vw, 3.4rem);           /* heading */
font-size: clamp(3.8rem, 14vw, 8.5rem);        /* hero — aggressive scale */

/* Spacing */
padding: clamp(1rem, 4vw, 3rem);
```

Format: `clamp(min-mobile, vw-fluid, max-desktop)`

## Touch Targets

- Kích thước tối thiểu: **44×44px** (Apple HIG) / **48×48dp** (Material)
- `minHeight: 44` cho mọi button/interactive element trên mobile
- Khoảng cách giữa các touch targets: ≥ 8px
- `touch-action: manipulation` cho button/link — bỏ 300ms tap delay trên mobile:

```css
button, a { touch-action: manipulation; }
```

## Layout & Scroll

- Dùng `100dvh` thay `100vh` trên mobile (tránh bị thanh địa chỉ browser che)
- Sticky elements: dùng `position: sticky` + `bottom: 0` cho bottom bar
- Horizontal scroll: `overflow-x: auto` + `scrollbar-width: none` cho filter chips
- Tránh `overflow: hidden` trên body khi có modal (gây scroll lock trên iOS)

## Responsive Grid & Spacing

Pattern chuẩn với Tailwind — 1 cột mobile, mở rộng dần:

```html
<!-- Grid -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">

<!-- Padding responsive -->
<div class="px-4 sm:px-6 lg:px-8">

<!-- Flex direction responsive -->
<div class="flex flex-col sm:flex-row gap-3">
```

## Mobile Menu

Pattern sidebar/menu ẩn hiện bằng `translate-x` — không dùng `display: none` (giật):

```html
<!-- Sidebar: ẩn trên mobile, translate ra khi open -->
<div class="fixed md:sticky transition-transform
            ${open ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}">

<!-- Backdrop khi sidebar open trên mobile -->
<div class="fixed inset-0 md:hidden ${open ? 'block' : 'hidden'}"
     onClick={() => setOpen(false)} />
```

Nhớ `setSidebarOpen(false)` khi navigate/tab change.

## Viewport & Zoom

Có 2 cách kiểm soát zoom trên mobile — khác nhau về mức độ và trade-off:

**Cách 1 — `maximumScale: 1`: chặn zoom toàn trang (đơn giản, nhưng ảnh hưởng accessibility)**
```typescript
// Next.js
export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,  // user không pinch-zoom được gì cả
}
```
_Dùng khi nào: app mà zoom sẽ phá layout (ví dụ game, canvas). Không nên dùng cho content site — người mắt kém không zoom được._

**Cách 2 — Inline script: chặn zoom chỗ không cần, cho phép zoom chỗ cần (thông minh hơn)**
```javascript
// Chạy trước React hydration (inline trong <head>)
// iOS tự zoom vào input khi focus nếu font-size < 16px
// Script này: khi focus input → cho phép zoom (maximumScale=5)
//             khi blur input  → chặn zoom lại (maximumScale=1)
const el = document.querySelector('meta[name=viewport]')
document.addEventListener('focusin', (e) => {
  if (['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName)) {
    el.content = 'width=device-width, initial-scale=1, maximum-scale=5'
  }
})
document.addEventListener('focusout', () => {
  el.content = 'width=device-width, initial-scale=1, maximum-scale=1'
})
```
_Dùng khi nào: app có form input mà muốn tránh iOS auto-zoom, nhưng vẫn muốn user có thể zoom thủ công khi cần._

**Tóm tắt:**
- Chỉ dùng `maximumScale: 1` → chặn tất cả zoom (xấu cho accessibility)
- Inline script → kiểm soát zoom thông minh theo từng element (recommended)

## Platform Detection

Dùng `userAgent` khi cần render khác nhau giữa iOS / Android / Desktop:

```typescript
const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent)
const isMobile = /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i
  .test(navigator.userAgent)
```

Ví dụ áp dụng:
- iOS không render PDF trong `<iframe>` ổn định → show card UI + share button
- Mobile browser → route đến trang viewer; desktop → download thẳng

Luôn wrap trong `useEffect` (chỉ chạy client-side).

## Hover

**Hover chỉ dùng làm decoration** (màu, shadow, lift) — không dùng để show/hide thông tin quan trọng vì mobile không có hover state:

```css
/* ✅ OK — decoration only */
.card:hover { box-shadow: ...; transform: translateY(-2px); }

/* ❌ Sai — thông tin bị ẩn trên mobile */
.tooltip { display: none; }
.btn:hover .tooltip { display: block; }
```

Thông tin quan trọng phải luôn visible hoặc dùng tap/click để toggle.

## Share / Download (Web)

- Nút share: dùng **Web Share API** (`navigator.share`) — hỗ trợ iOS 15+, Android Chrome 75+
- Share file PDF: `navigator.canShare({ files })` trước khi share
- Fallback: share URL nếu không share được file; copy clipboard nếu không có `navigator.share`
- iOS không render PDF trong `<iframe>` / `<embed>` ổn định → dùng card UI + share button thay thế
- Android Chrome: render PDF trong iframe OK

## Forms

- Tránh `position: fixed` cho elements khi keyboard mở trên mobile (bị đẩy lên)
- Dùng `inputmode` attribute đúng loại: `numeric`, `email`, `tel`, `url`
- Autocomplete attributes: `name`, `email`, `current-password`, `new-password`

### Dropdown trong modal có `overflow-y: auto`

`position: absolute` dropdown bị cắt bởi `overflow-y: auto` của container cha — đây là browser behavior chuẩn, không phải bug.

**Fix đơn giản (chấp nhận scroll nhẹ):** Thêm `paddingBottom` (60–80px) ở cuối modal body → user scroll thêm một chút là thấy dropdown:

```tsx
// Modal body
<div className="px-6 py-5 space-y-4" style={{ paddingBottom: '60px' }}>
```

**Fix triệt để (không cần scroll):** Dùng `position: fixed` + `getBoundingClientRect()` để tính tọa độ thực. `fixed` không bị `overflow: auto` của parent cắt:

```tsx
const addrRef = useRef<HTMLDivElement>(null)
const [dropPos, setDropPos] = useState({ top: 0, left: 0, width: 0 })

useEffect(() => {
  if (open && results.length > 0 && addrRef.current) {
    const r = addrRef.current.getBoundingClientRect()
    setDropPos({ top: r.bottom + 4, left: r.left, width: r.width })
  }
}, [open, results])

// Dropdown:
<div style={{ position: 'fixed', top: dropPos.top, left: dropPos.left, width: dropPos.width, zIndex: 9999 }}>
```

_⚠️ Edge case của fixed approach: nếu parent có `transform`/`filter` → fixed sẽ bị anchor vào parent thay vì viewport. Kiểm tra trước khi dùng._

### Email validation — `emailTouched` pattern

Chỉ hiện lỗi validation SAU khi user đã focus vào field ít nhất 1 lần. Tránh UX xấu khi vừa vào trang đã thấy lỗi đỏ, hoặc khi email được pre-fill từ server.

```tsx
const [emailTouched, setEmailTouched] = useState(false)
const isValidEmail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)
const emailInvalid = emailTouched && email.length > 0 && !isValidEmail(email)
const canSubmit = email.trim() !== '' && isValidEmail(email)

<input
  type="email"
  value={email}
  onChange={e => setEmail(e.target.value)}
  onFocus={() => setEmailTouched(true)}  // ← bật flag khi lần đầu focus
/>
{emailInvalid && (
  <p style={{ color: '#c8410a', fontSize: '0.75rem' }}>
    📧 Vui lòng nhập đúng định dạng email
  </p>
)}
<button disabled={!canSubmit}>Submit</button>
```

**Rules:**
- `emailTouched` chỉ bật khi `onFocus`, không bao giờ tắt lại
- Lỗi hiện khi: touched AND có text AND format sai
- Button disable khi: email rỗng OR (có text AND format sai)
- KHÔNG dùng `type="email"` browser validation thay thế — UX không nhất quán giữa các browser

### Auth-conditional UI elements

Nút/tính năng chỉ có nghĩa với user đã đăng nhập (lịch sử, hủy, profile...) → **ẩn hoàn toàn** cho guest, không disabled.

_Lý do: disabled button gây bối rối — guest không hiểu tại sao không bấm được, không có CTA rõ để đăng nhập. Ẩn hẳn + thay bằng text giải thích rõ hơn._

```tsx
const { user } = useAuth()
const isGuest = !user

// ✅ Đúng — ẩn hoàn toàn
{!isGuest && (
  <button onClick={() => router.push('/profile?tab=history')}>
    Về lịch sử →
  </button>
)}

// Thay bằng text phù hợp cho guest
{isGuest && (
  <p>Báo cáo sẽ tự gửi vào email khi hoàn thành.</p>
)}

// ❌ Sai — disabled nhưng không giải thích
<button disabled={isGuest}>Về lịch sử →</button>
```

**Các trường hợp thường gặp cần ẩn cho guest:**
- "Về lịch sử / My orders"
- "Hủy báo cáo / Cancel" (guest đã trả tiền → cancel = mất tiền, không nên để bấm)
- "Lưu hồ sơ" — hiện nhưng cần redirect login
- Settings, profile, subscription buttons

## Performance

- Lazy load images, ưu tiên `next/image` (Next.js) hoặc tương đương
- Tránh re-render không cần thiết — memo/callback khi component nặng
- Bundle size: kiểm tra khi thêm dependency lớn (> 50KB)

## Testing Checklist (trước khi deploy)

- [ ] Test trên phone thật (không chỉ DevTools)
- [ ] Kiểm tra portrait + landscape
- [ ] Kiểm tra keyboard không che content quan trọng
- [ ] Nút/link đủ lớn để tap dễ
- [ ] Share/download hoạt động trên iOS và Android
- [ ] Hover effects không ẩn thông tin quan trọng
- [ ] Tap delay không bị (touch-action: manipulation)
