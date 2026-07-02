# Bootstrap — Universal Workflow Rules

Bộ workflow rules dùng chung cho mọi project làm việc với **Claude Code CLI**.

> **QUAN TRONG — ĐỌC KỸ TRƯỚC KHI LÀM:**
>
> Tất cả file rules `.md` phải được đặt vào **`docs/universal_rules/`** của dự án đích.
>
> **TUYỆT ĐỐI KHÔNG copy/write file rules ra root project.**
>
> Cấu trúc đúng:
> ```
> my-project/
> ├── CLAUDE.md              ← file duy nhất ở root (project-specific)
> ├── docs/
> │   └── universal_rules/   ← TẤT CẢ rules files vào đây
> │       ├── SESSION_SPINE.md   ← luật bất biến (hook nạp mỗi phiên)
> │       ├── INDEX.md           ← bản đồ
> │       ├── BOOTSTRAP.md
> │       ├── rules/             ← chi tiết từng luật + WORKFLOWS.md
> │       ├── templates/         ← README/CONTRIBUTING/ADR/GOAL + github_templates
> │       ├── skills/  hooks/  scripts/  _meta/
> └── src/ ...
> ```

---

## Hướng dẫn cho AI Agent (Claude Code)

**Khi user bảo bootstrap project mới bằng file này:**

1. **CHẠY script `bootstrap.sh`** — đây là cách đáng tin nhất:
   ```bash
   bash /path/to/bootstrap.sh
   ```
   hoặc clone repo rồi chạy script bên trong.

2. **Nếu không chạy được script**, thực hiện THỦ CÔNG theo đúng thứ tự:
   - `mkdir -p docs/universal_rules` trong dự án đích
   - Copy `*.md` ở root repo (`SESSION_SPINE.md`, `INDEX.md`, `BOOTSTRAP.md`) vào `docs/universal_rules/` — **KHÔNG PHẢI root project**
   - Copy subdirectories: `rules/`, `templates/`, `skills/`, `hooks/`, `scripts/`, `_meta/`
   - Tạo/cập nhật `CLAUDE.md` ở root với reference line

3. **KHÔNG BAO GIỜ:**
   - Copy/write file rules ra root project
   - Đọc nội dung file rồi write lại thay vì copy nguyên file
   - Bỏ qua bước tạo `docs/universal_rules/`

---

## 3 cách để bootstrap project mới

### Cách 1 — Nhanh nhất: chạy script (curl)

```bash
curl -fsSL https://raw.githubusercontent.com/thanhnt1021/universal-workflow/main/bootstrap.sh | bash
```

Script tự động:
- Tạo `docs/universal_rules/` và copy toàn bộ (root `*.md` + `rules/`, `templates/`, `skills/`, `hooks/`, `scripts/`, `_meta/`)
- Tạo hoặc cập nhật `CLAUDE.md` ở root
- Tạo `README.md` ở root từ `templates/README_TEMPLATE.md` (nếu chưa có)
- Tạo `docs/GOAL.md` từ `templates/GOAL_TEMPLATE.md` (nếu chưa có)
- Dọn dẹp file thừa

> **SSH key khác mặc định?**
> ```bash
> curl -fsSL https://raw.githubusercontent.com/thanhnt1021/universal-workflow/main/bootstrap.sh \
>   | BOOTSTRAP_SSH_KEY=~/.ssh/my_key bash
> ```

---

### Cách 2 — Chạy từng bước thủ công

**Bước 1 — Clone repo và copy rules vào `docs/universal_rules/`:**

```bash
# Tạo thư mục đích — BẮT BUỘC phải là docs/universal_rules/
mkdir -p docs/universal_rules

# SSH (recommended cho server)
GIT_SSH_COMMAND="ssh -i ~/.ssh/id_rsa" \
  git clone git@github.com:thanhnt1021/universal-workflow.git /tmp/_uw
cp /tmp/_uw/*.md docs/universal_rules/
for d in rules templates skills hooks scripts _meta; do
  cp -r /tmp/_uw/$d docs/universal_rules/ 2>/dev/null || true
done
rm -rf /tmp/_uw
```

> **SSH key khác?** Thay `~/.ssh/id_rsa` bằng path key của bạn.
>
> **Máy local / có HTTPS credentials?**
> ```bash
> git clone https://github.com/thanhnt1021/universal-workflow.git /tmp/_uw
> cp /tmp/_uw/*.md docs/universal_rules/
> rm -rf /tmp/_uw
> ```

**Bước 2 — Tạo hoặc cập nhật CLAUDE.md (ở root project):**

`CLAUDE.md` là file bắt buộc của Claude Code CLI — phải đặt ở root project. **Không bao giờ overwrite nếu đã tồn tại.**

```bash
# Nếu chưa có CLAUDE.md
if [ ! -f CLAUDE.md ]; then
  cat > CLAUDE.md << 'EOF'
# [Tên Project]

## ⚠️ CRITICAL WORKFLOW RULES (KHÔNG BAO GIỜ vi phạm)

1. **`feature: [tên]`** → tạo branch → đọc context → hỏi Q&A 1 batch → **DỪNG chờ user confirm rõ ràng** (`làm đi`, `go ahead`...) → mới được code. Plan đính kèm là INPUT để đối chiếu, **KHÔNG phải lệnh implement**.
2. **KHÔNG tự** `git commit`, `git push`, `git merge`, deploy production — chỉ khi user ra lệnh rõ.
3. **Sau quick deploy** → báo cáo kết quả → **DỪNG**, không làm gì thêm.

> Chi tiết đầy đủ: docs/universal_rules/INDEX.md

## Overview
[Mô tả ngắn]

## Tech Stack
[Liệt kê tech stack]

## What's DONE ✓
- [x] Project scaffolding

## What's TODO
- [ ] ...
EOF
  echo "✅ Created CLAUDE.md"
fi

# Nếu đã có CLAUDE.md — thêm CRITICAL WORKFLOW RULES nếu chưa có
if ! grep -q "CRITICAL WORKFLOW RULES" CLAUDE.md; then
  # Insert critical rules block at the top (after first heading line)
  RULES_BLOCK='
## ⚠️ CRITICAL WORKFLOW RULES (KHÔNG BAO GIỜ vi phạm)

1. **`feature: [tên]`** → tạo branch → đọc context → hỏi Q\&A 1 batch → **DỪNG chờ user confirm rõ ràng** (`làm đi`, `go ahead`...) → mới được code. Plan đính kèm là INPUT để đối chiếu, **KHÔNG phải lệnh implement**.
2. **KHÔNG tự** `git commit`, `git push`, `git merge`, deploy production — chỉ khi user ra lệnh rõ.
3. **Sau quick deploy** → báo cáo kết quả → **DỪNG**, không làm gì thêm.

> Chi tiết đầy đủ: docs/universal_rules/INDEX.md
'
  # Use sed to insert after first line that starts with "# "
  # Lưu ý: syntax 0,/pattern/ chỉ hoạt động trên GNU sed (Linux).
  # macOS cần: brew install gnu-sed, sau đó dùng gsed thay sed.
  sed -i "0,/^# /{/^# /a\\${RULES_BLOCK}
  }" CLAUDE.md
  echo "✅ Added CRITICAL WORKFLOW RULES to CLAUDE.md"
else
  echo "✅ CLAUDE.md already has CRITICAL WORKFLOW RULES"
fi
```

**Bước 3 — Dọn dẹp:** xóa file BOOTSTRAP.md ở root (canonical copy đã có trong `docs/universal_rules/`):

```bash
if [ -f "BOOTSTRAP.md" ] && [ -f "docs/universal_rules/BOOTSTRAP.md" ]; then
  rm -f BOOTSTRAP.md
  echo "✅ Removed BOOTSTRAP.md from project root"
fi
```

---

### Cách 3 — 1 lệnh git clone (không cần curl)

```bash
# Đích đến BẮT BUỘC: docs/universal_rules/ — KHÔNG PHẢI root
mkdir -p docs/universal_rules
GIT_SSH_COMMAND="ssh -i ~/.ssh/id_rsa" \
  git clone git@github.com:thanhnt1021/universal-workflow.git /tmp/_uw \
  && cp /tmp/_uw/*.md docs/universal_rules/ \
  && for d in rules templates skills hooks scripts _meta; do cp -r /tmp/_uw/$d docs/universal_rules/ 2>/dev/null; done; \
  rm -rf /tmp/_uw
```

Sau đó chạy bước 2 ở Cách 2 để setup CLAUDE.md.

---

### Bước cuối (mọi cách) — Trong Claude Code CLI

```
check requirements
```

Claude tự tạo các file còn thiếu (`docs/MD_FILES_TO_UPDATE.md`, `docs/REQUIREMENTS_CHECK.md`) và hướng dẫn cấu hình thủ công.

---

## Nội dung bộ rules

Danh sách đầy đủ: xem [`README.md`](./README.md). Dưới đây là các file core:

| File | Mô tả |
|------|-------|
| `SESSION_SPINE.md` | Luật bất biến — hook nạp mỗi phiên (root) |
| `INDEX.md` | Bản đồ "rule nào ở đâu" + command table (root) |
| `rules/GIT_WORKFLOW.md` | Branch strategy, feature flow, deploy modes |
| `rules/MD_SYSTEM.md` | Cấu trúc /docs, quy tắc MD files |
| `rules/QUALITY_GATES.md` | Type check, build pass, commit format |
| `rules/NEW_PROJECT_SETUP.md` | Logic của lệnh `check requirements` |
| `rules/ASK-BACK.md` | Cơ chế hỏi ngược trước khi thực thi |
| `rules/OUTCOME.md` | Goal tracking protocol |
| `rules/CHANGELOG_RULES.md` | Audit log — xoá/đổi có chủ đích hay AI quên |
| `rules/WORKFLOWS.md` | Quy trình lệnh dài (feature/full update/...) |

Các file chuyên biệt trong `rules/` (dùng khi project cần): `UI_MOBILE_RULES.md`, `MOBILE_APP_STRICT_RULES.md`, `BOT_COMMAND_RULES.md`, `VIETNAMESE_DIACRITICS.md`, `GOOGLE_OAUTH_SETUP.md`, `SEPAY_PAYMENT.md`, `ENV_RULES.md`, `SECURITY_CHECKLIST.md`, `CI_CD_TEMPLATE.md`

Skill (tự kích hoạt): `product-growth`, `qa-multipass`, `infra`, `tdk-master`, `app-security`, `bot-commands`, `mobile-webapp`, `sepay-payment`, `google-oauth`, `ci-cd`

Templates trong `templates/`: `README_TEMPLATE.md`, `CONTRIBUTING_TEMPLATE.md`, `ADR_TEMPLATE.md`, `GOAL_TEMPLATE.md`, `github_templates/`

---

## Cập nhật rules

Chạy lại Cách 1 hoặc Cách 3 — các file trong `docs/universal_rules/` sẽ được overwrite bằng version mới nhất.
