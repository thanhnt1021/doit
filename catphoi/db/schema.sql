-- Kho tôn thừa (phôi cũ) của xưởng — Cloudflare D1 `catphoi-db`.
-- Nhiều máy trong công ty cùng mở link https://catphoi.jst4.fun và thấy CHUNG kho này.
-- Chạy:  npx wrangler d1 execute catphoi-db --remote --file=db/schema.sql
--
-- ⚠ File này chỉ TẠO MỚI bảng. Kho đang chạy production thì dùng file
--   db/migrate-2026-09-tam-nguyen-kho.sql để THÊM CỘT, tuyệt đối không DROP.

CREATE TABLE IF NOT EXISTS remnants (
  -- Mã tấm thừa, sinh phía Functions (crypto.randomUUID), không cho client tự đặt.
  id           TEXT PRIMARY KEY,

  -- Tên do người đặt, BẮT BUỘC, ví dụ "thừa lô sườn 15". Đây là thứ thợ tìm theo.
  name         TEXT NOT NULL,

  -- Kích thước KHUNG BAO của tấm thừa, đơn vị MILIMET (theo quy ước src/types.ts).
  -- width_mm chạy theo trục x, length_mm chạy theo trục y.
  -- Với tấm lưu theo kiểu MỚI, khung bao LUÔN bằng đúng khổ tấm gốc (2000×6000).
  width_mm     REAL NOT NULL,
  length_mm    REAL NOT NULL,

  -- ── VIỆC 3: tấm thừa giữ NGUYÊN KHỔ kèm phần đã cắt đi ────────────────────
  -- Founder: "tấm thừa nên là hình của thừa có cả phần cắt đi cơ, để dễ biết nó
  -- ở chỗ nào mà còn vẽ. bounding vẫn luôn phải là 2000x6000 chuẩn".
  --
  -- KHỔ TẤM GỐC lúc đem đi cắt, mm. NULL = dòng dữ liệu CŨ (lưu trước khi đổi
  -- cấu trúc) — khi đọc thì lấy tạm width_mm/length_mm và gắn cờ legacy.
  sheet_w_mm   REAL,
  sheet_h_mm   REAL,

  -- Các LỖ ĐÃ CẮT trên tấm gốc, JSON mảng các vòng kín, toạ độ mm trong hệ của
  -- TẤM GỐC (gốc (0,0) = góc dưới-trái tấm):
  --   [[{"x":100,"y":100},{"x":600,"y":100},...], [...lỗ nữa...]]
  -- NULL hoặc '[]' = tấm nguyên chưa cắt gì.
  cuts         TEXT,

  -- HÌNH ĐỂ VẼ: JSON mảng các vòng kín, vòng[0] là biên ngoài, vòng[1..] là lỗ.
  -- Tấm kiểu mới: vòng[0] chính là hình chữ nhật nguyên khổ 2000×6000.
  -- Giữ lại cột này để bản cũ của trình duyệt (đang mở sẵn ngoài xưởng) vẫn đọc được.
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
