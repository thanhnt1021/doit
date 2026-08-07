---
name: new-project-setup
description: Kích hoạt khi khởi tạo/thiết lập dự án mới hoặc chạy lệnh "check requirements". Trigger vi+en - setup project mới, khởi tạo dự án, "check requirements", scaffold project, bootstrap repo, kiểm tra + tạo file còn thiếu (CLAUDE.md/README/GOAL), detect project type, apply rule/skill phù hợp. KHÔNG overwrite file đã có.
---

# New Project Setup

> Skill ngữ cảnh tự kích hoạt & self-contained.
> Chạy lệnh `check requirements` → Claude: (1) kiểm tra từng mục dưới, (2) tạo file placeholder còn thiếu, (3) hỏi user input cho phần cần cấu hình thủ công, (4) thêm dòng reference vào `CLAUDE.md` nếu chưa có.

## Checklist Tự Động (Claude tự kiểm tra + tạo)

### Files bắt buộc
- [ ] `CLAUDE.md` ở root — chưa có: tạo template cơ bản, hỏi user điền thông tin project. **KHÔNG overwrite nếu đã có** (chứa context project-specific).
- [ ] Dòng reference trong `CLAUDE.md` trỏ tới bộ rule (vd `> Chi tiết: docs/univ3/INDEX.md`) — chưa có: **append**. KHÔNG sửa nội dung khác.
- [ ] Block **Available Commands** trong `CLAUDE.md` — chưa có: thêm sau dòng reference:
  ```
  ## Available Commands
  | Lệnh | Hành động |
  |---|---|
  | `read context` | Đọc toàn bộ docs + GOAL.md → báo "Đã hiểu, sẵn sàng nhận lệnh." |
  | `report context` | Đọc docs → output structured summary |
  | `feature: [tên]` | Tạo branch → Q&A → implement → quick deploy → DỪNG |
  | `quick deploy` / `test demo` | Build + deploy demo, KHÔNG commit |
  | `commit` | Commit + push nhánh hiện tại |
  | `merge main` / `lên production` | Merge vào main + deploy production |
  | `full update` | One-shot: update MD → commit → push → merge main → restart service → report |
  | `check requirements` | Kiểm tra + setup mọi thứ còn thiếu |
  | `check goal` | Show GOAL.md + tiến độ + đề xuất |
  | `update goal` | Update GOAL.md dựa trên việc vừa làm |
  | `docs project` | Tạo/update tài liệu dự án |
  ```
- [ ] `docs/MD_FILES_TO_UPDATE.md` — chưa có: tạo với template trống (xem dưới).
- [ ] `docs/REQUIREMENTS_CHECK.md` — chưa có: tạo template, hỏi user điền thông tin server.
- [ ] `README.md` ở root — chưa có: copy từ template README, hỏi user điền. **KHÔNG overwrite nếu đã có.**
- [ ] `docs/GOAL.md` — chưa có: copy từ template GOAL và hỏi user điền 3 câu (mục tiêu / thành công / không làm gì). **KHÔNG overwrite nếu đã có.**
- [ ] `docs/SESSION_SPINE.md` — spine RIÊNG cho project (luật luôn-nạp, univ3 KHÔNG ghi đè). Chưa có: **SINH bằng cách ĐỌC REPO THẬT** (xem `## Sinh docs/SESSION_SPINE.md` dưới). Đây là artifact ROI cao nhất của skill này — đừng bỏ. **KHÔNG overwrite nếu đã có** (chỉ append gotchas mới).

### Auto-detect project type → apply skill/rule tương ứng
Khi `check requirements`, Claude scan codebase, detect signal, rồi **hỏi user confirm** trước khi thêm reference vào `CLAUDE.md`.

> **Cấu trúc univ3:** `rules/` chỉ còn phần lõi luôn-đúng (SPINE + WORKFLOWS + GIT + DOCS + ASK-BACK + AGENTS-ORCH + GATES). Mọi rule chuyên biệt đã được **skill-hoá** — kích hoạt theo ngữ cảnh, không nhồi vào rules/. Bảng dưới map signal → **skill**. Nếu không chắc rule/skill nào còn tồn tại, **đọc `INDEX.md` (hoặc `_meta/manifest`) của bộ rule** để biết danh sách hiện có rồi map.

| Detect signal | Áp dụng (skill) |
|---|---|
| `package.json` có `next`/`react` + UI mobile-first, viewport meta, bottom-nav, hoặc user nói "webapp" | skill `mobile-webapp` |
| Google OAuth / NextAuth config | skill `google-oauth` |
| SePay / payment / QR chuyển khoản | skill `sepay-payment` |
| Có auth / payment / file-upload / sensitive data | skill `app-security` |
| `python-telegram-bot` / Discord / bot framework | skill `bot-commands` |
| Cần pipeline build/test/deploy (`.github/workflows`, SSH/VPS deploy) | skill `ci-cd` |
| Cần dựng/vận hành hạ tầng tự host (server, systemd, docker, nginx, SSL, deploy an toàn) | skill `infra` |
| SEO / GEO / canonical / sitemap / og / index Google | skill `seo-geo` |
| Cần tạo/update tài liệu dự án | skill `project-docs` |
| Phân tích sản phẩm / growth / QA nhiều lượt (TDK) | skill `tdk-master` (điều phối → `product-growth` / `qa-multipass` / `infra`) |

**Quy trình:**
1. Claude scan codebase (package.json, config files, templates).
2. Detect signal → list skill cần apply.
3. Output: "Phát hiện project type: [X]. Đề xuất apply: [list skill]. OK?"
4. User confirm → Claude thêm reference lines vào `CLAUDE.md`.

## Sinh `docs/SESSION_SPINE.md` (spine RIÊNG cho project — ROI cao nhất)

> Cơ sở (số liệu, không phải cảm giác): context file **chỉ có giá trị ở phần project-specific mà agent KHÔNG tự grep ra** — lệnh verify được, "đừng đụng", "thao tác tốn kém", gotchas. Phần overview/cây thư mục/mô tả kiến trúc đo được là **vô dụng + tốn ~20% cost/22% reasoning token**. Nên file này **CẤM chứa overview**. Nó nằm ở `docs/SESSION_SPINE.md` (NGOÀI univ3) → `session_context.py` ưu tiên nạp #1, và không bị ghi đè khi update univ3.

**Quy trình SINH (đọc file thật → trích, CẤM phỏng đoán/bịa số):**
1. **Lệnh:** đọc `package.json`→`scripts`, `Makefile`, `pyproject.toml`, `composer.json`, `.github/workflows/*` → copy NGUYÊN chuỗi lệnh test / build / lint / dev / migrate. Không có script → ghi lệnh chạy trực tiếp (`pytest`, `go test ./...`). CẤM bịa lệnh không tồn tại.
2. **Đừng đụng:** grep `@generated`/`DO NOT EDIT`/`Code generated`; tìm `src/generated/`, `*.pb.go`, `prisma/migrations/` (đã commit), `dist/`,`build/`, lockfile, `infra/prod*`. Có → liệt kê path + lệnh regen nguồn.
3. **Thao tác tốn kém:** README/CI nói test/build/deploy chậm → ghi số đó. KHÔNG rõ mà repo có test suite → **HỎI user 1 câu** (AskUserQuestion: "Test suite chạy mất ~bao lâu? Có lệnh nào nặng cần chạy có target?"). CẤM bịa "~X phút".
4. **Quy ước:** chỉ ghi cái KHÁC mặc định mà agent không tự suy ra (vd "lỗi API qua `src/lib/errors.ts`, không throw raw"). Suy ra được từ code → BỎ.
5. **Gotchas:** để **RỖNG**. Chỉ điền theo add-on-failure (agent phạm cùng lỗi lần 2).

**Luật cứng khi viết file:** mỗi dòng phải là **lệnh verify được** hoặc **path cụ thể**. Rớt cửa "agent tự grep ra được không?" → BỎ. Không chắc mục nào → để placeholder `<…>` + hỏi user, đừng bịa.

### Template `docs/SESSION_SPINE.md` (điền từ bước trên; xoá dòng không áp dụng)
```markdown
# SESSION_SPINE — spine RIÊNG cho <project> (luật luôn-nạp; univ3 KHÔNG ghi đè)
> Chỉ chứa thứ agent KHÔNG tự grep ra + mệnh lệnh verify được. CẤM overview/mô tả kiến trúc.

## Lệnh (copy THẬT từ package.json/Makefile — không bịa)
- Install: `<lệnh>`
- Dev: `<lệnh>` (port <...>, cần <service> chạy trước)
- Test tất cả: `<lệnh>` (mất ~<...> phút — đừng chạy mù, dùng bản có target)
- Test 1 file/case: `<lệnh path>` / `<lệnh -t "tên">`
- Lint + typecheck: `<lệnh>` (chạy TRƯỚC khi báo xong)
- Build: `<lệnh>`
- Migration: `<lệnh>` (KHÔNG sửa file đã commit trong `<dir>`)

## Tooling
- Package manager: `<pnpm/npm/...>` — KHÔNG mix lock file.
- Runtime: `<Node 22 / Python 3.12 / ...>`

## Đừng đụng
- `<dir generated>/**` — sinh tự động, sửa nguồn `<x>` rồi chạy `<gen cmd>`
- `<infra/prod>/**` — cần review, đừng tự sửa
- `<lockfile / migration đã commit>`

## Thao tác TỐN KÉM (chạy có target, đừng chạy mù)
- `<test suite ... phút>` · `<build ... phút>` · `<deploy ...>`

## Quy ước (chỉ ghi cái KHÁC mặc định)
- `<vd: query DB qua repository layer, không gọi ORM trực tiếp từ route>`

## Definition of done
1. `<lint/typecheck>` pass
2. Test liên quan pass
3. Không thêm dependency mới nếu chưa hỏi

## Gotchas (add-on-failure — RỖNG lúc đầu, chỉ thêm khi agent phạm cùng lỗi lần 2)
_(trống)_
```

## Execution Rules — Áp dụng mọi lúc
> Nhắc lại khi setup project mới, luôn active trong mọi session.
- **KHÔNG CHẮC → HỎI NGAY.** Không tự đoán implementation, không assume. Dùng ask-back trước khi code.
- **KHÔNG dùng subprocess Python** để tạo job/chạy operation khi web server đang live. Luôn dùng API endpoint (curl/httpx POST).
- **Sau khi tạo job / trigger operation:** verify ngay bằng cách kiểm tra log hoặc gọi API check status — đừng assume "chắc chạy rồi".

### Template `docs/MD_FILES_TO_UPDATE.md` (khi tạo mới)
```markdown
# MD Files To Update

## Current Feature
_(trống — sẵn sàng cho feature tiếp theo)_

## Files To Update
_(trống)_
```

### Template `docs/REQUIREMENTS_CHECK.md` (khi tạo mới)
```markdown
# Server Requirements Checklist

[Claude hỏi user để điền: project name, tech stack, domain, ports, DB, env vars cần thiết]
```

## Checklist Thủ Công (cần user input)

### Git & GitHub
- [ ] `git init`
- [ ] Remote GitHub: `git remote add origin git@github.com:<user>/<repo>.git`
- [ ] SSH key cho GitHub — hỏi user: đã có chưa? Ở đâu?
  _Server không có browser để auth HTTPS; SSH key không hết hạn, không cần nhập password mỗi lần push._
- [ ] Branch mặc định `main`: `git branch -M main`

### Environment
- [ ] `.env.local` (hoặc `.env`) — hỏi user biến cần theo stack:
  - `[WEB/Next.js]`: NEXTAUTH_URL, NEXTAUTH_SECRET, DATABASE_URL, API keys...
  - `[BOT]`: BOT_TOKEN, WEBHOOK_URL...
  - `[API]`: DATABASE_URL, SECRET_KEY, PORT...
- [ ] `.env.example` — chưa có: tạo từ `.env` (keys only, placeholder values).
- [ ] `.gitignore` chứa `.env*` — kiểm tra và thêm nếu thiếu.
  _Nếu `.env` bị commit (kể cả private repo), secrets nằm trong git history mãi mãi — xoá file không xoá được khỏi history. Đã lộ là coi như lộ._

### Server (nếu self-hosted)
- [ ] Xem `docs/REQUIREMENTS_CHECK.md` để biết yêu cầu cụ thể.
- [ ] Deploy scripts: `deploy.sh` (production), `deploy-demo-local.sh` (quick).

### Per Project Type
**[WEB/Next.js]** `pnpm install` (dùng pnpm — shared store tiết kiệm disk) → `pnpm dlx prisma generate` (nếu Prisma) → `pnpm dlx prisma migrate deploy` (nếu có DB) → `pnpm run build`.
**[MOBILE/React Native]** `pnpm install` → iOS: `cd ios && pod install` → `pnpm dlx react-native run-android` / `run-ios`.
**[BOT/API — Node]** `pnpm install` → `pnpm start` hoặc `node index.js`.
**[BOT/API — Python]** `python3 -m venv venv && source venv/bin/activate` → `pip install -r requirements.txt` → test start + `python -m py_compile <main_file>`.

## Sau khi setup xong
Claude báo cáo:
- Đã tạo/kiểm tra những file nào
- Đã detect project type + apply skill nào
- Những gì còn cần user xử lý thủ công
- Bước tiếp theo để bắt đầu dev
