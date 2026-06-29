---
name: mobile-webapp
description: Kích hoạt khi làm web app mobile cảm giác native (mobile-first, responsive, PWA, giao diện điện thoại / phone frame). Trigger vi: làm web app mobile, giao diện điện thoại, UI mobile, bottom nav, thanh điều hướng dưới, chống auto-zoom, safe area, vùng chạm, native feel. Trigger en: mobile web app, mobile-first, responsive, bottom navigation, prevent iOS auto-zoom, safe area insets, touch target, native-like UI, PWA.
---

# Mobile Web App — Quy tắc CSS/UX nghiêm ngặt

> Skill ngữ cảnh tự kích hoạt. Chi tiết đầy đủ: `docs/universal_rules/rules/MOBILE_APP_STRICT_RULES.md` + `docs/universal_rules/rules/UI_MOBILE_RULES.md`. CSS var values / class names dưới đây là reference — chỉnh theo project.

## Khi nào dùng skill này
- Xây/sửa web app mobile-first muốn cảm giác như native app.
- Thêm/sửa: bottom nav, modal, input form, fixed element, overlay, toast trên mobile.
- Fix bug: nav nhảy/lệch khi keyboard mở, input bị iOS zoom, content bị che, layout vỡ trên iPhone.
- Làm PWA / add-to-home-screen, xử lý notch / Dynamic Island / home indicator.

## Checklist cốt lõi (bắt buộc)
- [ ] **Bottom nav** `position: fixed; bottom/left/right:0; width:100%; z-index:2000`; padding-bottom `calc(8px + var(--safe-bottom))`. Modal z-index < 2000.
- [ ] **KHÔNG đổi `bottom` khi keyboard mở**; KHÔNG `animation-fill-mode: both` + `transform` trên parent của fixed (tạo stacking context → fixed bị anchor sai). Page enter chỉ dùng `opacity`, KHÔNG `transform`.
- [ ] **Chống auto-zoom 3 lớp**: (1) viewport `maximum-scale=1.0, user-scalable=no, viewport-fit=cover`; (2) `input,select,textarea { font-size: max(16px, inherit) }`; (3) `html { -webkit-text-size-adjust: 100% }`. KHÔNG bao giờ input < 16px.
- [ ] **Phone frame**: content trong `.container` max-width ~600px mobile / 480px @≥640 / 500px @≥768. Desktop nền gradient xám + box-shadow.
- [ ] **Mọi `position: fixed` mới**: @≥640px thêm `max-width:480px; left:50%; transform:translateX(-50%); width:100%`; @≥768px `max-width:500px`. (Hoặc class `.mobile-contained-fixed` / `.mobile-contained-overlay`.)
- [ ] **Safe-area insets**: `:root` định nghĩa `--safe-top/bottom/left/right: env(safe-area-inset-*, 0px)`. `body` padding-top `--safe-top`, padding-bottom `calc(var(--nav-height) + var(--safe-bottom) + 16px)`. Bắt buộc `viewport-fit=cover`.
- [ ] **Touch target ≥ 44×44px**: button `min-height:44px`; nav item `min-width:64px`; input login `min-height:52px`; icon btn `44×44`. Khoảng cách giữa target ≥ 8px.
- [ ] **`:active` ONLY, NO `:hover`** cho thay đổi UI quan trọng. Tap feedback: `.btn:active { transform: scale(0.97) }`. Hover chỉ làm decoration, KHÔNG ẩn/hiện info. Thêm `-webkit-tap-highlight-color: transparent`, `touch-action: manipulation`, `user-select: none` cho interactive.
- [ ] **Dùng `dvh` KHÔNG `vh`** (`100vh` không trừ address bar → content bị che). `100dvh` cho body/modal fullscreen.
- [ ] **Scroll**: `html,body { overflow-x: hidden }`; `body { overscroll-behavior-y: contain }` (chặn pull-to-refresh).
- [ ] **Typography/spacing qua CSS vars** (`--primary`, `--radius-lg:16px`, `--transition-*`...), KHÔNG hardcode. Font stack `-apple-system,...`. Cân nhắc `clamp(min,vw,max)` cho fluid type/spacing.
- [ ] **Prevent double-submit**: xử lý toàn cục ở `base.html` (disable btn + spinner, flag `submitted`), KHÔNG thêm JS riêng cho từng form.
- [ ] **PWA meta**: `apple-mobile-web-app-capable=yes`, `theme-color`, `format-detection: telephone=no`.

## Cạm bẫy / lỗi hay gặp
- `transform` (kể cả `translateX/Y(0)`) hoặc `filter` trên parent → `position: fixed` con bị anchor vào parent thay vì viewport → nav/modal/dropdown lệch.
- Input `0.875rem`/`0.75rem` (14/12px) → iOS auto-zoom khi focus. Phải `1rem` = 16px.
- Quên `viewport-fit=cover` → `env(safe-area-inset-*)` trả về 0, app dính notch.
- Dùng `100vh` → content bị thanh địa chỉ che trên mobile.
- Tooltip/info hiện bằng `:hover` → mất hẳn trên mobile (không có hover).
- Dropdown `position:absolute` bị `overflow-y:auto` của modal cha cắt → dùng `position:fixed` + `getBoundingClientRect()` (lưu ý edge case parent có transform).
- Modal/fixed quên constrain @≥640px → tràn full-width trên desktop, vỡ phone frame.
- `overflow:hidden` trên body khi mở modal → scroll-lock lỗi trên iOS.

## Verify trước khi báo xong
- [ ] Test ở 375px (iPhone SE): không horizontal scroll, không vỡ layout.
- [ ] Mở keyboard: bottom-nav KHÔNG bị đẩy lên / biến mất.
- [ ] Focus input: KHÔNG bị iOS zoom (mọi input ≥ 16px).
- [ ] Mọi fixed/modal centered trong phone frame ở mọi breakpoint (≥640, ≥768).
- [ ] Safe area top/bottom đúng trên thiết bị có notch; content không bị nav che.
- [ ] Tap feedback chỉ qua `:active`; không có info ẩn sau hover.
- [ ] Text tiếng Việt CÓ DẤU; colors/spacing dùng CSS vars; dùng `dvh`.
