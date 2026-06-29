# DB "Đánh dấu xong" (Cloudflare D1) — TRẠNG THÁI

App `/7days` + `/kegel` lưu trạng thái đánh dấu xong **theo từng ngày** vào D1. Trước khi binding có hiệu lực trên production, app **tự fallback localStorage** (vẫn sống sót F5, chỉ trên 1 máy).

## ✅ Đã làm sẵn (qua wrangler, account `hentaii.kidd@gmail.com`)
- [x] Tạo D1 `doit-db` — `database_id: 6fab28d9-665f-4fe4-9edb-45c58f6213ef`
- [x] Tạo bảng (`done_log`, `settings`) trên **remote** D1
- [x] `wrangler.toml` có binding `DB` → Pages tự bind khi build từ Git
- [x] Test end-to-end (`wrangler pages dev`): POST/GET `/api`, tách theo ngày, key Kegel `keg:` — PASS

## ⏳ Còn lại: deploy để binding có hiệu lực
Binding chỉ áp dụng sau khi Pages build lại với `wrangler.toml`:
```bash
gh auth switch --user thanhnt1021
git add -A && git commit -m "feat: D1 mark-done + Kegel timer + sửa bài tập" && git push
```
Sau khi Cloudflare auto-deploy xong → kiểm tra:
- `GET https://doit.jst4.fun/api/state?date=2026-06-29` trả JSON `{levels,noequip,done}` (KHÔNG phải 503).
- Bấm "Đánh dấu" → F5 → vẫn xanh. Mở máy khác → cũng xanh.

> Nếu sau deploy vẫn 503: vào Dashboard → doit → Settings → Functions → D1 bindings, đảm bảo có `DB = doit-db`. (Thường wrangler.toml đã đủ, không cần bước này.)

## (Tuỳ chọn) Khoá ghi bằng PIN
Không đăng nhập nên ai cũng ghi được. Muốn khoá: Dashboard → doit → Settings → Environment variables → thêm `APP_PIN` = mã tự đặt. Lần đầu bấm đánh dấu, web hỏi PIN và nhớ trên máy đó.

## Sửa/đọc DB thủ công
```bash
npx wrangler d1 execute doit-db --remote --command "SELECT * FROM done_log ORDER BY date DESC LIMIT 20"
npx wrangler d1 execute doit-db --remote --file=db/schema.sql   # chạy lại schema (idempotent)
```
