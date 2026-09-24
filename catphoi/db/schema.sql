-- Kho tôn thừa (phôi cũ) của xưởng — Cloudflare D1 `catphoi-db`.
-- Nhiều máy trong công ty cùng mở link https://catphoi.jst4.fun và thấy CHUNG kho này.
-- Chạy:  npx wrangler d1 execute catphoi-db --remote --file=db/schema.sql

CREATE TABLE IF NOT EXISTS remnants (
  -- Mã tấm thừa, sinh phía Functions (crypto.randomUUID), không cho client tự đặt.
  id           TEXT PRIMARY KEY,

  -- Tên do người đặt, BẮT BUỘC, ví dụ "thừa lô sườn 15". Đây là thứ thợ tìm theo.
  name         TEXT NOT NULL,

  -- Kích thước khung bao của tấm thừa, đơn vị MILIMET (theo quy ước src/types.ts).
  -- width_mm chạy theo trục x, length_mm chạy theo trục y.
  width_mm     REAL NOT NULL,
  length_mm    REAL NOT NULL,

  -- HÌNH DẠNG THẬT của phần còn lại sau khi cắt — KHÔNG phải hình chữ nhật.
  -- JSON: mảng các vòng kín, vòng[0] là biên ngoài, vòng[1..] là lỗ thủng.
  --   [[{"x":0,"y":0},{"x":1200,"y":0},...], [...lỗ...]]
  -- Toạ độ mm, gốc (0,0) ở góc dưới-trái khung bao.
  polygon      TEXT NOT NULL,

  -- Ghi chú tự do (mác thép, độ dày, để ở giá nào...). Có thể rỗng.
  note         TEXT NOT NULL DEFAULT '',

  -- 'available' = còn dùng được · 'used' = đã xài hết.
  status       TEXT NOT NULL DEFAULT 'available'
               CHECK (status IN ('available', 'used')),

  -- Thời điểm, epoch milisecond (UTC).
  created_at   INTEGER NOT NULL,
  updated_at   INTEGER NOT NULL
);

-- Truy vấn chính của panel: lấy tấm còn dùng được, mới nhất lên trước.
CREATE INDEX IF NOT EXISTS idx_remnants_status_created
  ON remnants (status, created_at DESC);
