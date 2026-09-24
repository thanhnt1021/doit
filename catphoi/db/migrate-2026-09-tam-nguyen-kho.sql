-- ĐỔI CẤU TRÚC KHO TÔN THỪA — VIỆC 3 "tấm thừa giữ nguyên khổ kèm phần đã cắt".
--
-- Chạy MỘT LẦN trên kho đang chạy thật:
--   npx wrangler d1 execute catphoi-db --remote --file=db/migrate-2026-09-tam-nguyen-kho.sql
-- Thử trước ở máy:
--   npx wrangler d1 execute catphoi-db --local  --file=db/migrate-2026-09-tam-nguyen-kho.sql
--
-- ⚠ CHỈ THÊM CỘT. Không DROP, không UPDATE, không xoá một dòng nào.
--   Dữ liệu tấm thừa cũ đang có trong kho giữ nguyên si; 3 cột mới để NULL và
--   API tự hiểu đó là "tấm kiểu cũ" (xem rowToRemnant trong
--   functions/api/remnants/_lib.js và src/remnant/normalize.ts).
--
-- SQLite không có "ADD COLUMN IF NOT EXISTS": chạy lại lần hai sẽ báo
-- "duplicate column name" — đó là bình thường, nghĩa là đã chạy rồi.

ALTER TABLE remnants ADD COLUMN sheet_w_mm REAL;
ALTER TABLE remnants ADD COLUMN sheet_h_mm REAL;
ALTER TABLE remnants ADD COLUMN cuts TEXT;
