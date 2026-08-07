# GIT — branch, push, rules an toàn

## Branch
- Làm trên `feature/[tên]` — **KHÔNG làm trực tiếp trên `main`** (main = production).
- Tên: `feature/short-kebab`. Local + remote **cùng tên `main`** (kiểm bằng `git branch -vv`).
- Nếu remote còn `master`: `git push origin main` → `gh repo edit --default-branch main` → `git push origin --delete master` → `git branch -u origin/main` (one-time).

## Push — RULE CỨNG
- **LUÔN** `git push` (branch đã có tracking) hoặc `git push -u origin HEAD` (branch mới).
- **KHÔNG BAO GIỜ** `git push origin main` / `git push origin [tên-branch]` — nếu remote tên khác (master vs main) sẽ tạo branch thừa. _Ngoại lệ duy nhất: one-time setup `main` ở trên._
- Sau MỖI `git push` → chạy `git status`, output phải chứa "up to date". Thấy "ahead of" → push sai, dừng kiểm tra.

## Flow tóm tắt
```
feature: [tên] → git checkout -b feature/[tên] → code+fix → quick deploy (KHÔNG commit) → DỪNG báo cáo
[lặp: fix → quick deploy → chờ]
commit → update MD list + clear → milestone xong đề xuất update GOAL → (sửa univ3 → push SSOT trước)
       → git add [file] && git commit → git push -u origin HEAD → git status verify
merge main → git checkout main && git merge --no-ff feature/[tên] → git push → git status → deploy
```

## Deploy — 3 chế độ
- **Quick deploy** (iterate, chưa commit): build từ code hiện tại (uncommitted OK), sync sang demo, restart. Không cần push.
- **Full deploy** (sau commit): pull GitHub → build → deploy (share link demo).
- **Production**: chỉ khi user nói "merge main"/"lên production".

## Git Rules
- **KHÔNG `git add -A`/`git add .`** — stage từng file cụ thể (tránh commit nhầm `.env`/credential/binary; đã push là coi như lộ).
- **KHÔNG `--no-verify`** (bypass lint/type/test = code broken vào repo).
- **KHÔNG force-push `main`** (xoá history người khác đã pull).
- **Commit message: WHY, không chỉ WHAT** — "what" đã có trong diff; "why" là thứ 6 tháng sau cần khi debug. "fix bug" vô nghĩa; "fix iOS zoom khi focus input vì font-size <16px" mới có giá trị.

> Push rule/bài học chung lên SSOT repo `thanhnt1021/univ3`: xem `rules/WORKFLOWS.md` §sync-uni (chiều PUSH) — quy trình DUY NHẤT.
