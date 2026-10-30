# Luật hiệu ứng — áp MỌI trang của MỌI dự án (chốt 28/10/2026)

> Chủ nhà chọn «áp dụng tất cả các trang không bỏ gì cả»: web vận hành, trang landing, trang tarot / chiêm tinh / portfolio / trang HTML đơn lẻ — **không trang nào được miễn**.
> Học bản nhẹ từ 6 kho hiệu ứng (gsap-skills · react-bits · canvas-ui · scroll-world · hallmark · emil): giữ cái hay, bỏ phần nặng. Không cài nguyên kho, không chép mã kho ngoài.

## 1. Một hiệu ứng chính / trang
- Mỗi trang **tối đa 1 hiệu ứng chính** (nền chuyển động, thẻ bài lật, sao rơi, cuộn kể chuyện…). Còn lại chỉ là chuyển cảnh nhỏ (hover, mở hộp) ≤ 250ms.
- Web vận hành (bảng, form, dashboard): hiệu ứng chính = **0**; chỉ chuyển cảnh nhỏ ≤ 1–2 phần tử/màn (kiem-duyet mục 11).
- Chỉ animate `transform` và `opacity` (trượt, mờ dần, phóng nhẹ). **Cấm** animate `width/height/top/left/margin/box-shadow/filter` lớn — gây giật, ăn pin.

## 2. Bản dự phòng — BẮT BUỘC có, viết cùng lúc với hiệu ứng
Hiệu ứng chính phải có **bản tĩnh đẹp** (ảnh tĩnh / gradient đứng yên / thẻ đã lật sẵn) và tự lùi về bản đó khi:
| Điều kiện | Cách phát hiện |
|---|---|
| Người xem bật giảm chuyển động | `@media (prefers-reduced-motion: reduce)` (CSS) + `matchMedia('(prefers-reduced-motion: reduce)')` (JS) |
| Máy yếu | `navigator.hardwareConcurrency <= 4` · `navigator.deviceMemory <= 4` · `navigator.connection?.saveData` · đo khung hình 1 giây đầu < 45 fps |
| Tab ẩn / hiệu ứng ra khỏi màn | `document.visibilityState === 'hidden'` · `IntersectionObserver` → **dừng hẳn** vòng lặp, không chỉ ẩn |
| Lỗi WebGL / canvas | `try/catch` khi tạo context → bản tĩnh |

Khuôn tối thiểu:
```js
const giam = matchMedia('(prefers-reduced-motion: reduce)').matches
const yeu = (navigator.hardwareConcurrency ?? 8) <= 4 || (navigator.deviceMemory ?? 8) <= 4 || navigator.connection?.saveData
if (giam || yeu) document.documentElement.classList.add('tinh')   // CSS .tinh → bản tĩnh
else batHieuUng()                                                  // nhớ dừng khi khuất màn / tab ẩn
```
```css
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; scroll-behavior: auto !important; } }
```

## 3. Chữ vẫn là chữ
- Hiệu ứng nằm ở **lớp nền** (`pointer-events: none`, sau nội dung): chữ trên trang **vẫn chọn/copy được**, đọc được bằng máy đọc màn; không vẽ chữ chính vào canvas.
- Tương phản chữ trên nền động vẫn ≥ 4.5:1 ở khung hình TỆ nhất — không đạt thì thêm lớp phủ mờ sau chữ.
- Không chặn cuộn, không cướp phím; nội dung chính hiện ngay, không chờ hiệu ứng chạy xong (≤ 400ms thấy nội dung).

## 4. Chi phí
- Hiệu ứng dùng dịch vụ tốn tiền (dựng video/ảnh bằng AI, cảnh 3D thuê ngoài) → **báo giá trước** cho chủ nhà (vd «~27 đô / 6 cảnh»), có đồng ý mới làm.
- Thư viện hiệu ứng: ưu tiên CSS thuần / Web Animations API; thêm thư viện nặng (> 30 KB nén) phải nêu lý do trong phiếu.

## 5. Kiểm trước khi báo xong
- `may-soi` dòng «Hiệu ứng: N chuyển động lặp còn chạy khi bật giảm chuyển động» phải = **0**.
- Chụp 2 ảnh bằng `may-chup`: bản có hiệu ứng + bản dự phòng (giả lập giảm chuyển động) — cả hai phải đẹp, không vỡ.
- Trang có hiệu ứng chính mới → dựng `ba-ban-thu` (3 kiểu hiệu ứng) cho chủ nhà chọn.
