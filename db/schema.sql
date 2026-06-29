-- DoIt — D1 schema cho Lịch Tuần (/7days)
-- Chạy: npx wrangler d1 execute doit-db --remote --file=db/schema.sql

-- Mỗi ngày, mỗi bài tập: đã đánh dấu xong chưa + làm ở bậc nào
CREATE TABLE IF NOT EXISTS done_log (
  date     TEXT NOT NULL,            -- 'YYYY-MM-DD'
  exercise TEXT NOT NULL,            -- key bài: pushH, pullH, squat, hinge, pushV, pullV
  done     INTEGER NOT NULL DEFAULT 0,
  level    INTEGER,                  -- bậc đang tập lúc đánh dấu (lưu lịch sử)
  updated_at TEXT,
  PRIMARY KEY (date, exercise)
);

-- Cài đặt toàn cục (không theo ngày): bậc tiến trình + chế độ dụng cụ
CREATE TABLE IF NOT EXISTS settings (
  k TEXT PRIMARY KEY,               -- 'levels' (JSON) | 'noequip' ('0'/'1')
  v TEXT NOT NULL
);
