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
feature: [tên] → git checkout -b feature/[tên] → code+fix → TỰ ĐỘNG commit (local) + deploy demo → DỪNG báo cáo
[lặp: fix → commit + deploy demo → chờ]
push (lệnh rõ) → update MD list + clear → milestone xong đề xuất update GOAL → (sửa univ3 → push SSOT trước)
       → git push -u origin HEAD → git status verify
merge main → git checkout main && git merge --no-ff feature/[tên] → git push → git status → deploy
```

## Deploy — 3 chế độ
- **Quick deploy** (iterate): build/fix xong → **tự động commit (local)** rồi sync sang demo, restart. Không push. (Commit + deploy demo an toàn, đảo ngược được — làm luôn, không chờ lệnh.)
- **Full deploy** (sau commit): pull GitHub → build → deploy (share link demo).
- **Production**: chỉ khi user nói "merge main"/"lên production".

## Git Rules
- **KHÔNG `git add -A`/`git add .`** — stage từng file cụ thể (tránh commit nhầm `.env`/credential/binary; đã push là coi như lộ).
- **KHÔNG `--no-verify`** (bypass lint/type/test = code broken vào repo).
- **KHÔNG force-push `main`** (xoá history người khác đã pull).
- **Commit message: WHY, không chỉ WHAT** — "what" đã có trong diff; "why" là thứ 6 tháng sau cần khi debug. "fix bug" vô nghĩa; "fix iOS zoom khi focus input vì font-size <16px" mới có giá trị.

> Push rule/bài học chung lên SSOT repo `thanhnt1021/univ3`: xem `rules/WORKFLOWS.md` §sync-uni (chiều PUSH) — quy trình DUY NHẤT.

## Tự đẩy khi cổng PII sạch
> Chốt 28/10/2026 (Task-28102026-02), chủ nhà: «đéo có cơ chế tách ra để auto đẩy à lần lồn nào cũng hỏi». Một lần lưu đã chép nguyên tên khách vào chú thích + ca thử rồi lên máy deploy; mỗi lần đẩy lại phải hỏi chủ nhà xem có sạch không.
- Cổng chung `~/.claude/universal-hooks/pii_commit_gate.py`: không cấu hình thì chỉ quét **bí mật** (token, khoá riêng, chuỗi kết nối có mật khẩu); dự án khai `.pii-gate.json` hoặc `--cau-hinh <tệp>` thì quét thêm **chữ khách thật** (họ tên, thư điện tử, dòng địa chỉ, từ hiếm) bằng dấu băm có muối lấy từ DB sống. Cache dấu băm phải nằm trong `.gitignore`.
- Gắn vào `pre-commit` của dự án: `python3 "$HOME/.claude/universal-hooks/pii_commit_gate.py" [--cau-hinh F] || exit 1`. Thiếu tệp cổng thì pre-commit **CHẶN**, không âm thầm cho qua.
- Đẩy bằng `pii_commit_gate.py --day`: cổng quét đoạn chưa đẩy, **sạch thì máy TỰ đẩy đủ mọi remote đã khai, KHÔNG hỏi chủ nhà**, rồi kiểm từng remote lệch `0 0`. Bẩn thì không đẩy, in đúng `tệp:dòng` và chỉ in dạng che `x…(n ký tự)`, **không bao giờ in chữ khách**.
- Trúng oan (địa danh, chữ kỹ thuật, tên ca thử có sẵn) thì thêm vào danh sách cho qua của dự án rồi làm mới cache. **Cấm `--no-verify`.**
- Cổng chỉ quét **phần THÊM** của mỗi lần lưu. Lịch sử đã đẩy lên remote chung thì không tự viết lại, phải báo chủ nhà.

## Viết lại lịch sử chưa đẩy không chặn thợ
> Chốt 29/10/2026 07:56, chủ nhà: «nếu giờ tao thả thêm thợ thì sao??? CẦN PHẢI TÌM CÁCH ĐỂ TASK KIỂU NÀY CHẠY ĐƯỢC NHANH NHẤT CÓ THỂ MÀ KHÔNG VA CHẠM TỚI NHỮNG CÁI KHÁC!!! ÁP DỤNG VỀ SAU.» Cách cũ (chờ kho trống thợ rồi chạy filter-repo ngay trong kho chính) bắt chờ hàng giờ, lỡ tay là mất cây làm việc của thợ đang chạy.
- Dùng `bash ~/.claude/universal-hooks/viet_lai_lich_su.sh --thay <tệp luật> [--ep-remote <remote deploy>]`. **Cấm** chạy filter-repo, `rebase -i`, `reset --hard/--keep` trong kho chính khi có thợ.
- Tệp luật «cũ==>mới» chứa chính chữ cần xoá → để **ngoài kho** (`/tmp`, quyền 600), không bao giờ commit.
- Chỉ viết lại **đoạn chưa đẩy** (mốc mặc định = đỉnh xa nhất của các remote chung). Remote chung (`origin`, `staging`…) **không đụng**. Remote deploy đã lỡ nhận bản cũ thì đẩy đè bằng `--force-with-lease` đúng mã cũ, ánh xạ qua commit-map.
- Viết lại **ngoài kho** (bản sao `clone --shared` ở `/tmp`). Kho chính chỉ bị **khoá vài giây** (`wlock git-lich-su`) lúc hoán đổi bằng `read-tree -m -u` + `update-ref` so-và-đổi. Tệp bẩn và tệp đã stage của thợ khác **giữ nguyên**. Thợ khác vừa lưu thêm thì viết lại từ đỉnh mới. Lô deploy đang dựng thì chờ, không hoán đổi.
- Trước khi hoán đổi: bundle sao lưu **2 nơi** + nhánh `backup/truoc-viet-lai-<giờ>`. **Không xoá nhánh sao lưu.**
- Báo cáo ghi **số giây giữ khoá** và kết quả `git log -S` từng chuỗi (phải 0 ở dòng thêm). Ca đo đầu tiên trên ChicHub: 166 lần lưu, giữ khoá 1,142 giây.
