# CLOUDFLARE_RULES — Pages + Functions + D1 (đúc kết từ doit)

> Áp dụng khi làm website tĩnh + API trên **Cloudflare Pages** (deploy Git tự động), có backend nhẹ bằng **Pages Functions** + **D1** (SQLite). Đọc cùng `ENV_RULES.md`, `SECURITY_CHECKLIST.md`, `GIT_WORKFLOW.md`.

## 0. Kiểm tra trước khi nói "không làm được" (BẮT BUỘC)
- Trước khi bảo "không có quyền / phải tự làm" → CHẠY `npx wrangler whoami`, `gh auth status`. Đã login + có scope (`d1 write`, `pages write`) thì **tự làm**: tạo D1, chạy schema, set secret, deploy.
- Account Cloudflare của hệ này: `hentaii.kidd@gmail.com` (zone `jst4.fun` ở đây). `wrangler` thường đã login sẵn.

### 0.1 Tạo Pages project Git-connected qua dashboard (UI tháng 6/2026 — đã verify thật)
Luồng CHÍNH XÁC (Cloudflare đã gộp Pages vào Workers, không còn tab "Pages" riêng):
1. Sidebar: **Build → Compute → Workers & Pages**.
2. Bấm nút xanh **Create application** (góc trên phải).
3. Màn mở ra tiêu đề **"Create a Worker"** — ĐỪNG đi tiếp luồng Worker. Nhìn **trên cùng** có dòng nhỏ **"Looking to deploy Pages? Get started"** → bấm **Get started**. (Project có thư mục `functions/` = Pages Functions BẮT BUỘC đi đường Pages; nếu lỡ tạo bằng Worker thì `functions/` không chạy.)
4. Vào màn **"Deploy a site from your account"** (3 bước: Select repository → Set up builds → Deploy site). Tab **GitHub**, chọn **GitHub account** đúng (vd `thanhnt1021`).
5. Gõ tên repo. Nếu **"No repositories matching ..."** → repo private/mới chưa được GitHub App nhìn thấy. Bấm link **"Cloudflare Pages"** trong câu *"configure repository access for the Cloudflare Pages app on GitHub"* (ngay dưới ô tìm) → sang GitHub → **Repository access** → **All repositories** (hoặc Only select + tick repo) → **Save**. Quay lại Cloudflare gõ lại tên repo → hiện ra → chọn → **Begin setup**.
6. Bước 2 (Set up builds): **Project name** (đúng tên muốn dùng cho domain) · **Production branch** `main` · **Framework preset** None · **Build command** để trống · **Build output directory** = thư mục asset (vd `public`). → **Save and Deploy**.
7. Thành công → preview tại `<project>.pages.dev`. Card **"Add custom domain"** ở màn này (hoặc project → **Custom domains**) để gắn domain — nhập `sub.zone`, cùng account thì Cloudflare tự tạo CNAME + activate.

**Quan trọng — cái gì CLI tự làm được, cái gì PHẢI dashboard:**
- ✅ `wrangler` TỰ làm: tạo D1, chạy schema, set secret (`wrangler pages secret put`), deploy trực tiếp (`wrangler pages deploy <dir> --project-name`), list/check (`wrangler pages project list`, `wrangler pages deployment list`).
- ❌ `wrangler` KHÔNG làm được (phải dashboard 1 lần): **Connect to Git** (OAuth authorize Cloudflare↔GitHub App), **cấp quyền repo cho GitHub App**, **thêm custom domain** (không có `wrangler pages domain`). OAuth token của wrangler (tự refresh khi chạy CLI) KHÔNG dùng được cho Cloudflare REST API trực tiếp (lỗi 9106) → đừng cố gọi API bằng token đó.

### 0.2 Pages (Git) vs Worker (CLI deploy) — chọn đúng kiểu
- **Pages + Git** (`pages_build_output_dir`, thư mục `functions/`): push `main` → Cloudflare auto-build. Cần 1 lần Connect-to-Git trên dashboard. Hợp khi muốn auto-deploy + có Pages Functions.
- **Worker + assets** (`main = "src/index.js"`, `[assets] directory`): deploy bằng `wrangler deploy` từ máy, KHÔNG cần dashboard, KHÔNG cần Git. Nhanh, nhưng push git không tự deploy. (Đây là lý do project kiểu này "tạo chẳng phải làm gì" — vì deploy thẳng CLI.)
- KHÔNG trộn: project `functions/` (Pages Functions) mà tạo bằng Worker thì API không chạy.

## 1. Kiến trúc chuẩn
```
project/
├── public/            # asset tĩnh (Vite build ra dist/) — Pages serve
├── functions/         # Pages Functions = API. File-based routing.
│   ├── _auth.js       # file _ đầu = KHÔNG thành route, chỉ import
│   └── api/
│       ├── state.js   # GET  /api/state   (export onRequestGet)
│       └── save.js    # POST /api/save    (export onRequestPost)
├── db/
│   ├── schema.sql     # CREATE TABLE IF NOT EXISTS ...
│   └── DATABASE_SETUP.md
├── wrangler.toml      # name + pages_build_output_dir + [[d1_databases]]
└── .dev.vars          # secret cho local (GITIGNORE!)
```
- Functions chạy trên Workers runtime: có `crypto.subtle`, `Date.now()`, `fetch`, `Request/Response`. KHÔNG có Node API (`fs`, `crypto` module).
- `context.env.DB` = binding D1; `context.env.TÊN_SECRET` = biến môi trường/secret.

## 2. D1 — tạo & bind
```bash
npx wrangler d1 create <db-name>              # in ra database_id
npx wrangler d1 execute <db-name> --remote --file=db/schema.sql   # tạo bảng (remote)
npx wrangler d1 execute <db-name> --local  --file=db/schema.sql   # cho local dev
```
Bind cho Pages (deploy Git): để trong `wrangler.toml` — Pages đọc khi build:
```toml
name = "<project>"
compatibility_date = "2025-06-01"
pages_build_output_dir = "dist"

[[d1_databases]]
binding = "DB"
database_name = "<db-name>"
database_id = "<id thật>"
```
> ⚠️ Đừng commit `wrangler.toml` với `database_id` giả/placeholder rồi push — build Git có thể fail. Tạo D1 thật TRƯỚC, điền id thật, rồi mới push. Khi chưa có DB, Functions nên trả 503 và frontend tự fallback localStorage để site không chết.
- Cách khác: bind ở Dashboard → project → Settings → Functions → D1 bindings (không đụng repo). Nhưng `wrangler.toml` tiện hơn cho Git deploy.

## 3. Pattern code Functions
```js
// functions/api/state.js
function json(o,s){return new Response(JSON.stringify(o),{status:s||200,
  headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});}
export async function onRequestGet(context){
  const {request, env} = context;
  if(!env.DB) return json({error:'no-db'}, 503);   // fallback-friendly
  const date = new URL(request.url).searchParams.get('date') || '';
  const rows = await env.DB.prepare("SELECT k,v FROM settings").all();   // .all() .first() .run() .batch()
  return json({ ... });
}
```
- D1 API: `.prepare(sql).bind(...args).all()|.first()|.run()`; nhiều câu → `env.DB.batch([stmt,...])`.
- Upsert: `INSERT ... ON CONFLICT(key) DO UPDATE SET v=excluded.v`.

## 4. Auth 1 tài khoản (single-user) — pattern doit
Dùng khi: "chỉ chủ thao tác, khách chỉ xem". KHÔNG có đăng ký, chỉ 1 user.
- **Bảng** `auth(username PK, salt, hash, updated_at)`. Mật khẩu = **PBKDF2-SHA256 100k vòng + salt** (Web Crypto `crypto.subtle.deriveBits`). KHÔNG lưu thô.
- **Session** = cookie `HttpOnly; Secure; SameSite=Lax` chứa token `payload.HMAC` ký bằng secret `SESSION_SECRET` (HMAC-SHA256). Verify bằng cách ký lại + so + check `exp`.
- **Routes**: `/api/login` (POST → set cookie), `/api/logout`, `/api/me` (GET → {user}), `/api/password` (đổi mật khẩu, phải đang đăng nhập). Mọi route GHI (`/api/save`...) gọi `getSessionUser()` → null thì 401.
- **Frontend**: `fetch(..., {credentials:'same-origin'})` (cookie tự gửi cùng origin). Đọc công khai; ghi cần đăng nhập → 401 thì báo "vào /admin". Trang `/admin` = form login + đổi mật khẩu + đăng xuất.
- Helper dùng chung để ở `functions/_auth.js` (import `../_auth.js`). Bộ kit này generic — copy nguyên từ doit dùng lại được.
- Set secret production: `echo "$(openssl rand -hex 32)" | npx wrangler pages secret put SESSION_SECRET --project-name <project>`. Local: ghi `SESSION_SECRET=...` vào `.dev.vars` (GITIGNORE).
- Seed user: tính `pbkdf2(password, salt)` (Node `crypto.pbkdf2Sync(pw, Buffer.from(salt,'hex'),100000,32,'sha256')` — KHỚP tham số Worker) → `INSERT OR IGNORE INTO auth ...`.

## 5. Secret & env
- Production: `wrangler pages secret put NAME --project-name <project>` (nhập value qua stdin). Hoặc Dashboard → Settings → Environment variables.
- Local dev: `.dev.vars` (KEY=VALUE). **Thêm `.dev.vars` vào `.gitignore`**. KHÔNG commit secret.

## 6. Local dev & test thật
```bash
npx wrangler d1 execute <db> --local --file=db/schema.sql
npm run build && npx wrangler pages dev dist --port 8788
# rồi curl http://127.0.0.1:8788/api/... để test end-to-end (login, ghi, đọc)
```
- Test bằng mock D1 (Node) cho logic, NHƯNG phải có 1 lần test thật qua `pages dev` (routing + binding + SQL).

## 7. Deploy & VERIFY LIVE — bài học quan trọng nhất
- Deploy = **push lên `main`** → Cloudflare auto-build (~1-3 phút). Build đọc `wrangler.toml`.
- **Sau push PHẢI verify LIVE**, không chỉ đọc code: `curl https://<domain>/api/...`.
- **ROLLOUT PROPAGATION**: bản mới KHÔNG bật cùng lúc trên mọi edge. Trong ~1-3 phút, request có thể trúng bản CŨ hoặc MỚI → kết quả lẫn lộn (vd ghi anon lúc 200 lúc 401). ⇒ **Đừng kết luận đúng/sai/bảo mật từ vài request.** Poll tới khi **N lần liên tiếp nhất quán** (vd 25 lần 401) mới chắc đã lan hết.
- `/api/*` POST không bị cache (`cf-cache-status: DYNAMIC`). HTML: `cache-control: max-age=0, must-revalidate` (không cache gắt) — đổi HTML hiện gần như ngay sau khi lan xong.
- Dọn sạch dữ liệu test ghi vào DB thật sau khi verify.

## 8. localStorage vs D1 — quyết định theo từng tính năng
- **localStorage** = riêng từng trình duyệt/máy, KHÔNG đồng bộ. Chỉ nên dùng làm **cache offline**.
- **D1 (server)** = đồng bộ mọi thiết bị. Cái gì cần "mở máy khác vẫn thấy" (đăng ký chế độ, đánh dấu, cài đặt) → phải lưu D1, fallback localStorage khi offline/chưa login.
- Bug kinh điển: lưu cấu hình ở localStorage rồi tưởng nó đồng bộ → đổi máy mất hết.

## 9. Lệnh hay dùng
```bash
npx wrangler whoami
npx wrangler d1 list
npx wrangler d1 execute <db> --remote --command "SELECT * FROM <table> LIMIT 20"
npx wrangler pages deployment list --project-name <project>
npx wrangler pages secret put NAME --project-name <project>
```
