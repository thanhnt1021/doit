# Cloudflare Pages Setup — doit.jst4.fun

## Thông tin project

| Field | Giá trị |
|-------|---------|
| Cloudflare account | Hentaii.kidd@gmail.com |
| Pages project name | `doit` |
| Pages default URL | `doit-65z.pages.dev` |
| Custom domain | `doit.jst4.fun` |
| GitHub repo | `thanhnt1021/doit` |
| Production branch | `main` |
| Framework | React (Vite) |
| Build command | `npm run build` |
| Build output | `dist` |

---

## Quy trình setup từ đầu (đã làm)

### 1. Tạo Pages project trên Cloudflare

1. Vào [Cloudflare Dashboard → Workers & Pages](https://dash.cloudflare.com/?to=/:account/workers-and-pages)
2. Bấm **"Create application"**
3. Ở màn hình tiếp, bấm link **"Looking to deploy Pages? Get started"** ở cuối trang
   > ⚠️ KHÔNG chọn "Continue with GitHub" ở mục Worker — đó tạo Worker, không phải Pages!
4. Chọn **"Connect to Git"** → chọn GitHub → chọn repo **thanhnt1021/doit**
5. Cấu hình build:
   - Project name: `doit`
   - Production branch: `main`
   - Framework preset: **React (Vite)**
   - Build command: `npm run build`
   - Build output directory: `dist`
6. Bấm **"Save and Deploy"**

### 2. Cấp quyền GitHub cho Cloudflare

Cloudflare cần access vào repo trên GitHub để auto-deploy.

1. Vào [GitHub → Settings → Installations → Cloudflare Workers and Pages](https://github.com/settings/installations)
2. Bấm **"Configure"** bên cạnh "Cloudflare Workers and Pages"
3. Ở mục **Repository access**:
   - Chọn **"Only select repositories"**
   - Thêm repo **doit** (giữ nguyên các repo khác như `lophochongxiem`)
4. Bấm **"Save"**

> Nếu không làm bước này, Cloudflare sẽ hiện banner vàng "This project is disconnected from your Git account" và auto-deploy sẽ không hoạt động.

### 3. Thêm custom domain

1. Vào [Cloudflare Dashboard → Workers & Pages → doit → Custom domains](https://dash.cloudflare.com/?to=/:account/workers-and-pages/doit/custom-domains)
2. Bấm **"Set up a custom domain"**
3. Nhập: `doit.jst4.fun`
4. Cloudflare sẽ yêu cầu thêm CNAME record

### 4. Thêm DNS record

1. Vào [Cloudflare Dashboard → Domains → jst4.fun → DNS Records](https://dash.cloudflare.com/?to=/:account/:zone/dns/records)
2. Bấm **"Add record"**:
   - Type: **CNAME**
   - Name: `doit`
   - Target: `doit-65z.pages.dev`
   - Proxy status: **Proxied** (cam)
   - TTL: Auto
3. Bấm **Save**
4. Quay lại Custom domains của project doit → đợi status chuyển thành **Active** + **SSL enabled**

---

## Deploy workflow

### Auto-deploy (bình thường)
Push lên `main` → Cloudflare tự build + deploy → live trên `doit.jst4.fun`

```bash
gh auth switch --user thanhnt1021
git add [files]
git commit -m "message"
git push
```

### Manual deploy (nếu cần)
1. Vào [Cloudflare → Workers & Pages → doit → Deployments](https://dash.cloudflare.com/?to=/:account/workers-and-pages/doit)
2. Bấm **"New deployment"** → chọn branch `main` → Deploy

### Kiểm tra deploy status
- Vào tab **Deployments** để xem build log
- Hoặc truy cập `https://doit.jst4.fun` trực tiếp

---

## Troubleshooting

### "This project is disconnected from your Git account"
→ Làm lại bước 2 (cấp quyền GitHub)

### Domain hiện "Verification is in undefined status"
→ Kiểm tra DNS record CNAME `doit` → `doit-65z.pages.dev` có tồn tại không

### Push bị lỗi "repository not found"
→ Token git credential cache sai account:
```bash
gh auth switch --user thanhnt1021
git remote set-url origin https://thanhnt1021:$(gh auth token)@github.com/thanhnt1021/doit.git
git push
git remote set-url origin https://github.com/thanhnt1021/doit.git  # reset lại
```
