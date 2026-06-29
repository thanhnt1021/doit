# Git Workflow Rules

## Branch Strategy

- Làm việc trên nhánh `feature/[tên]` — **KHÔNG làm trực tiếp trên `main`**.
  _Lý do: `main` là production. Commit thẳng vào main = deploy thẳng lên production không qua review/test._
- Tên branch: `feature/short-kebab-description`
- Main branch luôn là `main` (dùng cho PR nếu có)

### Setup branch mới (bắt buộc khi tạo repo hoặc clone lần đầu)

Local branch và remote branch **PHẢI cùng tên `main`**. Kiểm tra bằng `git branch -vv`:
- Nếu thấy `[origin/master]` → remote dùng tên cũ. Đổi:
  ```
  git push origin main          # tạo main trên remote
  gh repo edit --default-branch main   # đổi default branch
  git push origin --delete master      # xoá master
  git branch -u origin/main           # set tracking
  ```
- Nếu thấy `[origin/main]` → OK, không cần làm gì.
_Lý do: local/remote tên khác nhau khiến `git push` fail hoặc tạo branch thừa. Thống nhất `main` ở cả 2 phía = không bao giờ gặp lỗi này._

## Feature Flow

```
feature: [tên]
  → git checkout -b feature/[tên]
  → code + fix
  → quick deploy (KHÔNG commit/push)
  → DỪNG, báo cáo, chờ feedback

[lặp lại: fix → quick deploy → chờ]

commit
  → update docs/MD_FILES_TO_UPDATE.md trước
  → update tất cả MD files trong list
  → clear docs/MD_FILES_TO_UPDATE.md
  → nếu commit hoàn thành milestone → đề xuất update docs/GOAL.md (tick + cập nhật "đang ở đâu")
  → nếu có sửa docs/universal_rules/* → push lên universal-workflow repo trước
  → git add [files] && git commit
  → git push -u origin HEAD                   ← BẮT BUỘC push (set tracking tự động)
  → git status                                ← BẮT BUỘC verify "up to date"

merge main / lên production
  → git checkout main && git merge --no-ff feature/[tên]
  → git push                                  ← BẮT BUỘC push (tự push tới tracked upstream)
  → git status                                ← BẮT BUỘC verify "up to date"
  → deploy production (restart service)
```

> **RULE CỨNG — git push:**
> - **KHÔNG BAO GIỜ** dùng `git push origin main` hoặc `git push origin [tên-branch-cụ-thể]`.
>   _Lý do: nếu remote branch tên khác (vd: `master` vs `main`), lệnh này tạo branch mới trên remote thay vì push đúng chỗ._
>   **Ngoại lệ duy nhất:** lần đầu setup `main` trên remote (xem mục "Setup branch mới" ở trên) — one-time command để tạo branch `main` khi remote chưa có.
> - **LUÔN** dùng `git push` (không args) cho branch đã có tracking, hoặc `git push -u origin HEAD` cho branch mới.
>   _Lý do: `git push` tự push tới tracked upstream — đúng 100% bất kể remote branch tên gì._
> - Sau mỗi `git push`, BẮT BUỘC chạy `git status` — output phải chứa "up to date". Nếu thấy "ahead of" → push sai, dừng lại kiểm tra.

## Deploy — 2 chế độ

### Quick Deploy (iterate nhanh, chưa commit)
- Build từ code hiện tại (uncommitted OK)
- Sync build sang demo dir, restart service
- **Không cần git push** — dùng khi đang iterate/debug, chưa muốn lưu vào git history
- Script: `sudo bash deploy-demo-local.sh`

### Full Deploy (sau khi commit)
- Pull từ GitHub → build → deploy
- Dùng khi muốn share link demo với người khác hoặc sau khi đã commit
- Script: `sudo bash deploy-demo.sh [branch]`

### Production Deploy
- Chỉ khi user nói "merge main" hoặc "lên production"
- Script: `sudo bash deploy.sh`

## Push lên universal-workflow repo

Khi sửa bất kỳ file nào trong `docs/universal_rules/`, phải push lên repo `universal-workflow` (Rule 7).

**Tại sao cần một clone riêng?**
`docs/universal_rules/` là thư mục thông thường bên trong project, không phải git repo của `universal-workflow`. Không thể push lên `github.com/[user]/universal-workflow` từ đó — cần có một git clone thật của repo đó.

**Quy trình:**

```bash
# 1. Kiểm tra clone còn tồn tại không (/tmp/ bị xóa khi reboot)
ls /tmp/universal-workflow/ 2>/dev/null || echo "cần clone lại"

# 2. Nếu không có → clone on-demand
GIT_SSH_COMMAND="ssh -i [SSH_KEY]" \
  git clone git@github.com:[user]/universal-workflow.git /tmp/universal-workflow

# 3. Copy các file đã sửa từ project vào clone
cp docs/universal_rules/*.md /tmp/universal-workflow/

# 4. Commit + push từ clone
cd /tmp/universal-workflow
git add [files đã thay đổi]
git commit -m "docs: ..."
GIT_SSH_COMMAND="ssh -i [SSH_KEY]" git push
```

**Lưu ý:**
- `/tmp/` bị xóa khi reboot — luôn kiểm tra trước khi dùng, clone lại nếu cần
- Clone trong `/tmp/` chỉ là công cụ tạm để push — bản làm việc thật là `docs/universal_rules/` trong project
- SSH key path và GitHub user là project-specific — xem `CLAUDE.md` của project hiện tại

---

## Git Rules

- **KHÔNG dùng `git add -A` hay `git add .` blindly** — stage từng file cụ thể.
  _Lý do: `git add -A` có thể vô tình commit file `.env`, credentials, file binary lớn, hoặc file debug tạm thời vào repo — một khi đã push lên GitHub (kể cả private repo) thì coi như đã lộ._

- **KHÔNG skip hooks (`--no-verify`)**.
  _Lý do: hooks chạy lint/type-check/test trước khi commit. Skip là bypass safety net — code broken sẽ vào repo._

- **KHÔNG force push lên `main`**.
  _Lý do: force push xóa git history của người khác đã pull về. Trên production branch, điều này có thể làm mất code không thể recover._

- **Commit message: mô tả "why" không chỉ "what"**.
  _Lý do: "what" đã có trong diff. "why" là thứ 6 tháng sau cần biết khi debug — "fix bug" vô nghĩa, "fix iOS zoom khi focus input vì font-size < 16px" mới có giá trị._

- **Luôn thêm `Co-Authored-By: Claude <model> <noreply@anthropic.com>`** vào cuối commit message (thay `<model>` bằng model đang dùng, vd: Opus 4.6, Sonnet 4.6).
  _Lý do: ghi nhận AI đã tham gia viết code trong commit history — minh bạch về cách code được tạo ra._
