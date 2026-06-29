# DoIt — Weekly Life Dashboard

## Ngôn ngữ
Luôn giao tiếp bằng tiếng Việt có dấu.

## ⚠️ Luật BẮT BUỘC: phải thử chạy thật, không được tự nhận "không làm được"
- **Trước khi nói "tôi không có quyền / không vào được / bạn phải tự làm" → PHẢI kiểm tra credentials/tool thật trước.** Ví dụ: `npx wrangler whoami`, `gh auth status`, thử gọi API. Đã kết nối sẵn thì làm luôn, đừng đẩy việc về cho user.
- **Đã build/connect thì PHẢI chạy thử end-to-end** (curl API, `wrangler pages dev`, mở app) rồi mới báo xong. Cấm báo "xong" chỉ dựa vào đọc code.
- Account Cloudflare `wrangler` đang login: `hentaii.kidd@gmail.com` (có quyền `d1 write` + `pages write`) — tạo D1, chạy schema, deploy được trực tiếp.
- **Sửa xong là COMMIT + PUSH luôn lên `main`, KHÔNG hỏi "xem lại không".** User cần thấy nó chạy thật trên site. Push xong thì chờ Cloudflare deploy rồi check live (`curl`/mở app) — không dừng ở "đã push".

## Database (Cloudflare D1)
- DB `doit-db` đã tạo · `database_id` trong `wrangler.toml` (binding `DB`).
- API: `functions/api/state.js` (GET đọc theo ngày) · `functions/api/save.js` (POST ghi). Schema: `db/schema.sql`.
- Bind production qua `wrangler.toml` (Pages đọc khi build Git). Chi tiết: `db/DATABASE_SETUP.md`.

## Git Config
- **Account**: thanhnt1021
- **Repo**: https://github.com/thanhnt1021/doit
- **Identity**: `thanhnt1021 <thanhnt1021@users.noreply.github.com>`
- **gh account**: phải switch sang `thanhnt1021` trước khi push

```bash
gh auth switch --user thanhnt1021
git push
```

Nếu push bị lỗi "repository not found":
```bash
git remote set-url origin https://thanhnt1021:$(gh auth token)@github.com/thanhnt1021/doit.git
git push
git remote set-url origin https://github.com/thanhnt1021/doit.git  # reset lại
```

## Deploy
- **Domain**: doit.jst4.fun
- **Platform**: Cloudflare Pages (auto-deploy từ GitHub main)
- **Build command**: `npm run build`
- **Build output**: `dist`

## Tech Stack
- Vite + React (JSX)
- Inline styles (dark theme, mobile-first)
- Google Fonts: Crimson Pro, JetBrains Mono

> Đọc docs/universal_rules/INDEX.md để áp dụng universal workflow rules.
