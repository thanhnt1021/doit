---
name: may-soi
description: Kích hoạt TRƯỚC KHI BÁO XONG mọi việc đổi giao diện web (màn mới, sửa màn, nút, bảng, form, bản điện thoại, trang landing/hiệu ứng) — máy mở trang ở 3 cỡ màn, đo chữ tràn · chữ quá nhỏ · nút bé · chữ mờ, chấm điểm /20, ra ảnh khoanh chỗ lỗi; và khi cần thử màn bằng DỮ LIỆU KHÓ NHẤT (tên rất dài, 0 dòng, 1 món, hàng nghìn dòng, số âm, ô trống). Trigger vi: soi giao diện, chấm điểm giao diện, kiểm màn trước khi báo xong, chữ tràn, chữ mờ, nút bé, vỡ khung, đơn khó, dữ liệu xấu nhất. Trigger en: UI audit, visual QA, overflow, contrast check, tap target, responsive check, edge-case data, stress data.
---

# Máy soi giao diện /20 (univ3 · học từ 13 kho — ĐX2 + ĐX3, chốt 28/10/2026)

> Như thợ kiểm xe trước khi giao: máy mở trang ở **3 cỡ màn**, đo 4 thứ, chấm **/20**. Tin báo xong mang dòng «Soi giao diện 18/20» — người nhận biết màn đã được soi, khỏi tự dò.
> Ngưỡng lấy đúng bảng «Số đo bắt buộc» của skill **ui-ux** — skill này là máy đo, ui-ux là luật.

## Lệnh
```bash
# chạy từ GỐC dự án; dùng chung cấu hình đăng nhập + che PII với máy chụp (docs/may-chup.json)
node ~/.claude/skills/may-soi/may-soi.mjs --url /orders [--vai seller] [--co 390,768,1440] \
  [--anh /tmp/soi] [--json /tmp/soi.json] [--dat 16] [--cho 4000] [--khong-dang-nhap]
```
- 3 cỡ màn + lượt «giảm chuyển động» chạy **song song**, phiên đăng nhập dùng chung với máy chụp (30 phút) — ~9 giây/màn trên bản thật (bản tuần tự cũ ~37–45 giây).
- In bảng điểm từng mục theo từng cỡ màn + tối đa 3 lỗi/mục/cỡ (tên thẻ + chữ) + dòng `Soi giao diện X/20` (kèm số giây).
- **Khung chung**: trang có `<main>` thì lỗi NGOÀI `<main>` (thanh bên, đầu/đáy trang) lặp y hệt ở mọi màn → gom lại báo **một dòng**, không trừ điểm màn đang soi. Việc đang sửa chính khung đó → `--ca-khung`.
- **Trang lỗi** (mã ≥ 400 / chữ «404 · not found · không tìm thấy trang» / trang trắng) → `0/20`, mã thoát `3`, không có dòng báo xong.
- `--anh`: mỗi cỡ màn 1 ảnh, chỗ lỗi đóng khung màu (đỏ tràn · cam chữ nhỏ · tím nút bé · xanh chữ mờ), dữ liệu khách đã che bằng bộ che của máy chụp.
- Mã thoát: `0` ≥ `--dat` (mặc định 16) · `1` dưới mức hoặc có chữ rác · `2` mở trang / đăng nhập hỏng · `3` trang lỗi.

## 4 mục × 5 điểm (điểm theo cỡ màn TỆ NHẤT: 0 lỗi 5 · 1–2 → 4 · 3–5 → 3 · 6–10 → 2 · 11–20 → 1 · > 20 → 0)
| Mục | Đo gì | Miễn |
|---|---|---|
| Tràn chữ | chữ bị cắt cụt không có «…» · phần tử thò ra mép màn > 4px · **cả trang cuộn ngang → mục này tối đa 2** | vùng cuộn ngang có chủ ý (`overflow-x: auto`), có `text-overflow: ellipsis` / line-clamp |
| Chữ nhỏ | chữ thật < 11px | — |
| Nút bé | vùng chạm < 44×44 (điện thoại < 600px) · < 24×24 (máy tính) | liên kết giữa câu · ô tích nằm trong nhãn · máy tính: ô 24 đặt giữa không chạm đích khác (WCAG 2.5.8) |
| Chữ mờ | tương phản < 4.5:1 (chữ lớn ≥ 24px / ≥ 18.66px đậm: < 3:1); đọc được màu oklch/lab | nền ảnh/gradient (không đo được → bỏ, không đoán) · phần tử vô hiệu |

Phần tử ẩn cho máy đọc màn (sr-only) không chấm. Các dòng **không tính điểm**:
- **Hiệu ứng lúc chạy**: chuyển động lặp còn chạy khi bật «giảm chuyển động», ghi **suốt lúc tải** (mỗi 150ms) — vòng quay / khung nhấp nháy chờ tải chỉ hiện vài trăm mili-giây cũng bị bắt.
- **Hiệu ứng trong MÃ** (quét tĩnh `--quet-ma src`, mặc định `src/`): lớp `animate-spin/ping/pulse/bounce` thiếu `motion-safe:`/`motion-reduce:`, CSS `infinite` mà bộ chọn không được nhắc lại trong khối `prefers-reduced-motion` — in `tệp:dòng`. Có luật chặn chung (`@media (prefers-reduced-motion: reduce) { * { animation… } }`) thì báo đạt.
- **Dấu hiệu kỹ thuật** (học từ impeccable bản `5e745ac`, 29/10/2026): **ảnh vỡ** (src trống / tải hỏng) · **lỗi JS chưa bắt lúc tải** (ghi ở lượt 1440) · **tiêu đề nhảy bậc** (h1 → h3) · **viền màu ≥ 3px một bên** trên khối (dấu hiệu máy dựng — vạch xám mảnh ở dòng thời gian không tính). Ảnh vỡ + lỗi JS được nối vào dòng báo xong (`· ⚠ 2 ảnh vỡ · 1 lỗi JS`); không đổi mã thoát. Lỗi ngoài `<main>` gom theo khung chung như 4 mục điểm.
- **Dữ liệu hiển thị**: cột bảng có ô trống hiện **2 kiểu** («—» lẫn để trắng) → ⚠; **chữ rác** lọt ra màn (`undefined` · `NaN` · `[object Object]` · `Invalid Date` · `null` đứng một mình) → ⛔ mã thoát 1 dù điểm cao.

## Luật dùng
- Việc đổi giao diện: **soi trước khi báo xong**; dưới 16/20 thì sửa mục điểm thấp trước, hoặc ghi rõ trong tin vì sao chấp nhận (vd lỗi có sẵn từ trước, không thuộc việc này — so với lượt soi TRƯỚC khi sửa).
- Sửa màn cũ: soi **TRƯỚC và SAU** cùng `--url` — tin báo xong ghi `Soi giao diện 12 → 17/20`.
- Điểm là máy đo, không thay mắt người: soi xong vẫn chụp ảnh bằng `may-chup` và nhìn lại.

## Thử bằng dữ liệu khó nhất (ĐX3) — xem `references/du-lieu-kho.md`
Màn hiển thị danh sách/đơn/số tiền: trước khi báo xong, bật **bộ dữ liệu khó** trên DB thử (tên rất dài · 0 dòng · đúng 1 món · hàng nghìn dòng · số âm · ô trống) rồi soi + chụp lại xem có vỡ khung không. Khuôn dựng + dọn an toàn ở tệp tham chiếu.
