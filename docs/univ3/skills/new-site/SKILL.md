---
name: new-site
description: >-
  Kích hoạt khi user muốn tạo một trang/web mới trên Cloudflare + GitHub chỉ bằng một câu chat —
  "tạo trang mới", "dựng site mới", "làm cho tao trang X", "new site X", "spin up a site".
  Tự động hoá trọn gói headless: scaffold code, tạo repo GitHub private, tạo D1, deploy Cloudflare
  Pages (direct-upload), gắn custom domain <tên>.jst4.fun + DNS CNAME — không đụng dashboard.
  Credential đọc từ file local, KHÔNG nằm trong skill.
---

# new-site — tạo trang mới trên Cloudflare + GitHub bằng 1 lệnh

## Khi nào dùng
User nói muốn có một trang/web/app mới và muốn nó tự lên sóng. Không dùng cho việc sửa site đã có.

## Yêu cầu 1 lần (đã setup thì bỏ qua)
1. File credential `~/.claude/cloudflare-deploy.env` (chmod 600) có:
   `CF_API_TOKEN` (quyền Pages:Edit + DNS:Edit + D1:Edit + **Workers AI**), `CF_ACCOUNT_ID`, `CF_ZONE_NAME`, `CF_ZONE_ID`, `GH_OWNER`.
   → File này **không bao giờ** commit / không đưa vào univ3.
   → Đây là **KHOÁ CLOUDFLARE CHUNG của mọi dự án**: việc nào cần gọi Cloudflare (kể cả Workers AI — whisper, dịch `@cf/…`)
     thì đọc khoá ở đây TRƯỚC, đừng dùng khoá riêng của dự án rồi báo «thiếu khoá». Máy chủ khác (hosting, VPS) không đọc được
     tệp này → chép khoá sang `.env` của máy đó (quyền 600), không in khoá ra màn hình. Kiểm khoá gọi được AI:
     `curl -s https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/ai/run/@cf/meta/m2m100-1.2b -H "Authorization: Bearer $CF_API_TOKEN" -d '{"text":"Hello","source_lang":"en","target_lang":"vi"}'`.
2. `wrangler`, `gh` (đã đăng nhập `GH_OWNER`), `python3` có sẵn.

## Cách chạy
```bash
bash ~/.claude/skills/new-site/new-site.sh <tên> [--no-d1] [--domain <fqdn>] [--dir <path>]
```
- `<tên>` → tên project, repo, D1, và domain mặc định `<tên>.jst4.fun`.
- `--no-d1`: bỏ tạo D1. `--domain`: đổi domain. `--dir`: đổi thư mục (mặc định `~/PycharmProjects/<tên>`).

## Skill làm gì (headless, không dashboard)
1. Scaffold: `wrangler.toml`, `public/index.html` (đủ meta OG + twitter card + favicon), `functions/api/health.js`, `db/schema.sql`, `package.json`, `.gitignore`.
   - `gen-assets.sh` sinh **favicon.svg** (chữ cái + màu brand), **og.png 1200×630** (có tên site + domain), **apple-touch-icon.png** — offline bằng qlmanage+sips (built-in macOS), đúng luật seo-geo.
2. Tạo D1 `<tên>-db` + áp schema (trừ `--no-d1`).
3. `git init` + tạo repo private `GH_OWNER/<tên>` + push.
4. Tạo Pages project + `wrangler pages deploy` (dùng token, không OAuth).
5. Gắn custom domain + DNS CNAME `<tên> → <subdomain Pages thật>` (proxied) qua Cloudflare API — đọc `result.subdomain` từ API, KHÔNG tự ghép `<tên>.pages.dev` (tên trùng thì Cloudflare cấp kiểu `oha-65v.pages.dev`).
6. Ghi `CLOUDFLARE_PAGES_SETUP.md` vào project.

Kết quả: `https://<tên>.jst4.fun` sống (SSL mất ~1-2 phút) + `https://<subdomain Pages thật>` chạy ngay.

## Bảo mật
Skill chỉ chứa logic. Token nằm ở file local ngoài repo → đẩy skill lên SSOT univ3 (private) vẫn không lộ credential.

## Deploy lại sau này
Trong project: `pnpm run deploy` (hoặc thêm GitHub Actions dùng cùng token nếu muốn auto-deploy khi push).
