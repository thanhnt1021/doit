-- VIỆC 2 — MÃ TỰ SINH + NGUỒN GỐC cho tấm tôn thừa mới.
--
-- Founder: *"sao lại lưu đè, phải đặt mã mới chứ. auto đặt tên mã theo batch cắt
-- + số thứ tự + ngày tháng"*. Mã nằm ngay trong cột `name` (LO-2026-09-25-01)
-- nên không cần cột mới cho mã. Hai cột dưới đây ghi NGUỒN GỐC: tấm thừa mới
-- này được cắt ra từ tấm thừa cũ nào — để ngoài xưởng lần ngược lại được.
--
-- Chạy MỘT LẦN trên kho đang chạy thật:
--   npx wrangler d1 execute catphoi-db --remote --file=db/migrate-2026-09-nguon-goc-tam-thua.sql
-- Thử trước ở máy:
--   npx wrangler d1 execute catphoi-db --local  --file=db/migrate-2026-09-nguon-goc-tam-thua.sql
--
-- ⚠ CHỈ THÊM CỘT. Không DROP, không UPDATE, không xoá một dòng nào.
--   Dòng cũ để NULL = "không biết cắt ra từ đâu" (tấm mới nguyên khổ, hoặc tấm
--   lưu trước khi có tính năng này). API vẫn đọc bình thường.
--
-- SQLite không có "ADD COLUMN IF NOT EXISTS": chạy lại lần hai sẽ báo
-- "duplicate column name" — đó là bình thường, nghĩa là đã chạy rồi.
--
-- API cũng CHẠY ĐƯỢC KHI CHƯA CHẠY FILE NÀY: functions/api/remnants/_lib.js có
-- đường lui, thấy thiếu cột thì tự quay về bộ cột cũ (xem SELECT_COLS_LEGACY).

ALTER TABLE remnants ADD COLUMN source_id TEXT;
ALTER TABLE remnants ADD COLUMN source_name TEXT;
