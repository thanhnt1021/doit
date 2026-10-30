# Bộ «dữ liệu khó nhất» — khuôn chung mọi dự án (univ3 · học từ 13 kho — ĐX3, chốt 28/10/2026)

> Màn đẹp với dữ liệu mẫu gọn gàng chưa phải màn đẹp. Trước khi báo xong một màn danh sách / chi tiết, bật bộ dữ liệu khó lên **DB thử**, soi (`may-soi`) + chụp (`may-chup`) rồi dọn sạch.

## 1. Sáu loại dữ liệu bắt buộc có
| Loại | Ví dụ | Màn hay vỡ ở đâu |
|---|---|---|
| Tên / chữ RẤT dài | tên 120 ký tự, không dấu cách | tràn khung, đẩy cột, nút bị đẩy khỏi màn |
| 0 dòng | cửa hàng / nhóm không có bản ghi nào | trạng thái rỗng thiếu, bảng trơ khung |
| Đúng 1 dòng / 1 món | | số nhiều sai («1 items»), khung co lệch |
| Hàng nghìn dòng | ≥ 1.000 bản ghi một nhóm | phân trang, tải chậm, đếm sai |
| Số âm / số rất lớn | −45,99 · 1.234.567,89 · số lượng 9.999 | dấu trừ mất, số xuống dòng, sai định dạng tiền |
| Ô trống | null, chuỗi rỗng, 0 món | chữ «undefined»/«null», ô lệch, lỗi trang |
| (thêm) Emoji / đa ngữ | 🎄 · 日本語 · العربية | lệch dòng, vỡ font |

## 2. Luật an toàn — không thương lượng
- **Chỉ DB thử** (dev). Công cụ tự kiểm tên DB đang nối (`current_database()` hoặc tương đương) — khác tên DB thử thì **thoát mã lỗi, không ghi gì**. Cấm suy ra DB từ tệp `.env` rồi tin.
- **Đánh dấu riêng** mọi bản ghi tạo ra (tiền tố mã như `ZK…`, dải mã riêng `99000…`) để không lẫn dữ liệu thật.
- **Sổ id**: ghi ngay id của từng bản ghi vừa tạo vào 2 nơi (tệp nháp bị gitignore trong dự án + `/tmp/`).
- **Dọn = xoá theo id đích danh** đọc từ sổ, kiểm lại từng id còn mang dấu đánh dấu rồi mới xoá, trong một giao dịch, con trước cha sau. **Cấm xoá theo dải / theo điều kiện LIKE.**
- Ghi **theo lô** (một câu chèn nhiều dòng / `unnest`), không chèn từng dòng — qua đường hầm, nghìn câu lẻ mất cả chục phút và giữ giao dịch treo.
- Không bật song song hai lần: lệnh bật thấy sổ còn id → từ chối, bảo chạy dọn trước.

## 3. Lệnh mẫu (mỗi dự án tự viết lớp gọi riêng theo khuôn)
```bash
node scripts/don-kho/don-kho.mjs bat    # tạo bộ dữ liệu khó, in mã bản ghi để mở màn
node scripts/don-kho/don-kho.mjs xem    # in sổ: đang bật gì, mã nào
node scripts/don-kho/don-kho.mjs tat    # xoá đúng id trong sổ, in số đã xoá
```
Sau `bat`: chạy web dev trỏ DB thử → `may-soi` + `may-chup` từng màn (danh sách nhóm nghìn dòng, nhóm 0 dòng, chi tiết bản ghi tên dài / số âm / ô trống / nhiều món) → `tat`.

- **Bản ghi giả phải đủ các ô mà màn ĐỌC**, không chỉ ô muốn thử: màn chi tiết thường rơi về nhánh dự phòng khi thiếu ô đi kèm (vd tên người nhận chỉ hiện khi đơn có địa chỉ giao — đơn giả thiếu địa chỉ thì ô Tên ra «—», tên 120 ký tự không bao giờ lên màn). Đọc hàm dựng dữ liệu của màn trước khi viết bộ bật.
- Máy dev (Next dev) biên dịch từng màn khi mở lần đầu, soi + chụp hàng chục màn liên tiếp làm tiến trình dev phình bộ nhớ và tự khởi động lại giữa chừng (đo 28/10: trần 3 GB khởi động lại 8 lần) — chạy dev với trần bộ nhớ lớn hơn (`--max-old-space-size=8192`) hoặc soi trên bản dựng (`build` + `start`).

## 4. Đạt khi
- Không màn nào lỗi trang, không hiện «undefined/null/NaN».
- `may-soi` không tụt điểm so với dữ liệu thường; mục Tràn không có lỗi mới từ ô tên dài; dòng «Dữ liệu hiển thị» 0 chữ rác, 0 cột ô trống 2 kiểu.
- Sổ id rỗng sau `tat`, đếm lại DB thử không còn bản ghi mang dấu.
