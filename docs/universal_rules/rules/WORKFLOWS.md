# Workflows & Commands — chi tiết

> Tách từ INDEX để index mỏng. Các quy trình lệnh dài: `feature:`, `full update`, `commit all`, `sync uni`, Goal Tracking Protocol, `report context`.
> Bảng tra + danh sách lệnh tóm tắt ở `docs/universal_rules/INDEX.md`. Luật bất biến ở `docs/universal_rules/SESSION_SPINE.md`.

## feature: Workflow

Khi nhận lệnh `feature: [tên]`, tuân theo 2 phase sau — **không nhảy thẳng vào code**.

> **⚠️ BƯỚC 0 — BẮT BUỘC, KHÔNG CÓ EXCEPTION:**
> Nhận lệnh `feature: [tên]` → **tạo branch `feature/tên` NGAY LẬP TỨC**, trước khi đọc context hay làm bất cứ thứ gì.
> Dù user đính kèm code/plan/patch đầy đủ đến đâu → **vẫn tạo branch trước.**
> _Lý do: không có branch = làm thẳng trên main = không thể rollback, không thể review riêng, không thể test song song._

> **⚠️ RULE CỨNG — KHÔNG BAO GIỜ bỏ qua Phase 1, dù user đính kèm plan chi tiết đến đâu.**
> Plan là input để Claude đối chiếu với codebase — **KHÔNG phải lệnh implement.**
> Vẫn phải đọc context, hỏi Q&A, và **chờ user confirm rõ ràng** trước khi viết bất kỳ dòng code nào.
>
> - **SAI:** `feature: [tên]` + plan → tạo branch → implement ngay.
> - **ĐÚNG:** `feature: [tên]` + plan → tạo branch → đọc context → **Analysis Phase** (Q&A unified + update GOAL) → **print Full Plan** → **chờ user confirm** → implement.

### Phase 1 — Analysis Phase

> ⚠️ **RULE CỨNG:** Không bao giờ bỏ qua Phase 1, dù user đính kèm plan chi tiết đến đâu. Plan là input để đối chiếu — **KHÔNG phải lệnh implement.**

**Bước 1.** Đọc plan/prompt của user.

**Bước 2.** Re-read context: các files codebase liên quan (schema, API routes, components, types...) + `GOAL.md` nếu có.

**Bước 3.** Chạy 3 tracks phân tích song song (ngầm, không output ra):
- **Track A — Codebase (ASK-BACK):** So plan vs code thực tế → classify findings: 🔴 CONFLICT / 🟡 AMBIGUITY / 🟠 RISK / 🔵 GAP / ⚪ ASSUMPTION. Quy tắc + format: xem `docs/universal_rules/rules/ASK-BACK.md`.
- **Track B — Goal (OUTCOME):** So plan vs `GOAL.md` → serve milestone nào? conflict goal nào? goal drift không? Quy tắc: xem `docs/universal_rules/rules/OUTCOME.md`.
- **Track C — Implementation:** Dependencies, technical decisions còn mở, test strategy cho từng bước.

**Bước 4.** Gom tất cả findings từ 3 tracks → dùng **AskUserQuestion tool** với tất cả questions (tối đa 7, ưu tiên 🔴>🟡>🟠>🔵>⚪, tối đa 4 câu/lần gọi, recommended option đặt đầu tiên, "Other" tự động có). Xem format chi tiết: `docs/universal_rules/rules/ASK-BACK.md` §6.

**Bước 5.** User chọn options → nhận answers.

**Bước 6.** Nếu có `GOAL.md` → update ngay dựa trên answers: link milestone, resolve conflicts, cập nhật `_Last reviewed_`.

**Bước 7.** Print **Full Implementation Plan** — đủ chi tiết để implement không cần hỏi thêm:
- Approach tổng thể
- Các bước theo thứ tự (mỗi bước test được độc lập)
- Files sẽ thay đổi
- Edge cases + cách xử lý (đã xác nhận ở bước 5)

**Bước 8.** Chờ user confirm (`làm đi`, `proceed`, `ok`, hoặc tương đương) → chuyển Phase 2.

> **Mục tiêu Phase 1:** Sau khi xong, implement được một mạch từ đầu đến cuối không cần dừng hỏi thêm.

> **Exception:** Plan đơn giản (< 3 files, không có ambiguity, không ảnh hưởng goal) → gom bước 3–5 thành 1 confirm ngắn, skip bước 7 nếu approach đã rõ.

### Phase 2 — Implement từng bước, test ngay

1. **Implement từng function/fix một** theo thứ tự đã thống nhất — không làm hết rồi mới test.
2. **Test kỹ sau mỗi bước** bằng chiến lược đã thống nhất trong Phase 1:
   - Quick deploy → verify trên browser/app
   - Hoặc test endpoint trực tiếp (curl, server log, DB state...)
3. **Confirm works** → mới chuyển sang bước tiếp theo.
4. **Trước `quick deploy` lần cuối → `check code` BẮT BUỘC** (xem `docs/universal_rules/rules/SECURITY_CHECKLIST.md` §0):
   - Grep exec/spawn/shell/eval trong files vừa sửa
   - Verify mọi user input đều được validate ở server-side
   - Nếu vừa chạy `npm install`/`pip install` → chạy audit ngay
5. Khi tất cả xong → quick deploy lần cuối → **báo cáo tổng kết** → **DỪNG chờ feedback**.

> **Exception:** Nếu gặp vấn đề không giải quyết được hoặc loop >2 lần → **dừng, tham vấn user ngay** — không tự thử mãi.

---

## full update Workflow

One-shot command cuối task — gom toàn bộ `commit` + `merge main` + restart service + report thành 1 lệnh duy nhất. User nói `full update` = ủy quyền Claude thực hiện tất cả các bước bên dưới **không cần hỏi thêm**.

> **Lệnh `full update` là lệnh rõ ràng của user** — không vi phạm Core Rule 1 (KHÔNG tự ý commit/push/merge). Khi user nói `full update`, Claude ĐƯỢC PHÉP commit, push, merge, restart.

### Các bước (thực hiện tuần tự)

**Bước 1 — Update MD files**
- Đọc `docs/MD_FILES_TO_UPDATE.md` → update tất cả MD files trong danh sách
- Update `CLAUDE.md` nếu có thay đổi kiến trúc / commands / config
- Nếu thay đổi thuộc 4 loại catalog-level (Removed/Renamed/Contract changed/Constitution change) → thêm entry `docs/CHANGELOG.md` TRƯỚC (xem `docs/universal_rules/rules/CHANGELOG_RULES.md`)
- Nếu commit hoàn thành milestone → update `GOAL.md` (tick `[x]`, cập nhật "đang ở đâu")
- Clear `docs/MD_FILES_TO_UPDATE.md` sau khi update xong

**Bước 2 — Commit + push**
- `git add [files cụ thể]` (KHÔNG `git add -A`)
- `git commit` với message mô tả "why"
- Nếu có sửa `docs/universal_rules/*` → push lên repo `universal-workflow` trước (theo `docs/universal_rules/rules/GIT_WORKFLOW.md`)
- `git push -u origin HEAD` (feature branch) hoặc `git push` (main)
- `git status` → verify "up to date"

**Bước 3 — Merge main** (chỉ khi đang trên feature branch)
- `git checkout main && git merge --no-ff feature/[tên]`
- `git push`
- `git status` → verify "up to date"
- Nếu đang trên `main` → skip bước này

**Bước 4 — Deploy production** (chọn đúng path theo project)
- Xem `CLAUDE.md` của project mục "Deploy workflow" để biết project dùng cách nào. Ba variant thường gặp:
  - **systemd service**: `sudo systemctl restart [service-name]` → verify `sudo systemctl is-active [service-name]`
  - **Docker Compose**: `cd [compose-dir] && docker compose build [service] && docker compose up -d --force-recreate [service]` → verify `docker ps` + `curl https://domain/` HTTP 200
  - **Quick deploy only (no service)**: skip bước này, ghi note "No production service"
- Nếu vừa deploy demo trong session (đã `docker compose build <service>` rồi recreate) → có thể skip bước này, chỉ cần verify containers + HTTP health

**Bước 5 — Report**
- Output tóm tắt ngắn gọn:
  ```
  -- full update --
  Branch: [branch] -> main
  Commit: [hash] [message ngắn]
  Deploy: [systemctl name restarted / docker compose restarted / skipped]
  MD files updated: [danh sách]
  ```

### Lưu ý

- Nếu bất kỳ bước nào fail → **DỪNG ngay**, báo lỗi, KHÔNG tiếp tục bước sau
- Nếu có merge conflict → **DỪNG**, báo user, KHÔNG tự resolve
- `full update` KHÔNG bao gồm deploy demo — chỉ restart service (production)
- Nếu cần deploy demo trước khi commit → dùng `quick deploy` riêng trước

---

## commit all Workflow

One-shot command khi cần commit + push ra **cả 2 repos** (project hiện tại + `universal-workflow`) trong cùng 1 lần. Dùng khi đã sửa `docs/universal_rules/` và muốn sync lên cả 2 nơi ngay lập tức.

> **Lệnh `commit all` là lệnh rõ ràng của user** — không vi phạm Core Rule 1. Khi user nói `commit all`, Claude ĐƯỢC PHÉP commit, push, merge, restart.

### Các bước (thực hiện tuần tự)

**Bước 1 — Update MD files** (giống `full update` Bước 1)
- Đọc `docs/MD_FILES_TO_UPDATE.md` → update tất cả MD files trong danh sách
- Update `CLAUDE.md` nếu có thay đổi kiến trúc / commands / config
- Nếu thay đổi thuộc 4 loại catalog-level (Removed/Renamed/Contract changed/Constitution change) → thêm entry `docs/CHANGELOG.md` TRƯỚC (xem `docs/universal_rules/rules/CHANGELOG_RULES.md`)
- Clear `docs/MD_FILES_TO_UPDATE.md` sau khi update xong

**Bước 2 — Push repo `universal-workflow`** (nếu `docs/universal_rules/` có thay đổi)
- Kiểm tra: `git diff --name-only HEAD -- docs/universal_rules/` hoặc `git status`
- Nếu có file thay đổi trong `docs/universal_rules/`:
  1. Check `/tmp/universal-workflow/` còn tồn tại không (bị xóa khi reboot)
  2. Nếu chưa có: `GIT_SSH_COMMAND="ssh -i ${BOOTSTRAP_SSH_KEY:-~/.ssh/id_rsa}" git clone git@github.com:thanhnt1021/universal-workflow.git /tmp/universal-workflow`
  3. Copy **chỉ những file đã thay đổi** từ `docs/universal_rules/` → `/tmp/universal-workflow/`
  4. Trong `/tmp/universal-workflow/`: `git add [files]` → `git commit` → `GIT_SSH_COMMAND="..." git push`
  5. Verify push thành công trước khi tiếp tục
  6. **Xóa ngay**: `rm -rf /tmp/universal-workflow` — **KHÔNG để lại sau khi push xong** (tránh tạo safe-harbor cho attacker trong /tmp)
- Nếu không có thay đổi → **skip bước này hoàn toàn**, ghi chú "Universal-workflow: skipped (no changes)"

**Bước 3 — Commit + push project hiện tại**
- `git add [files cụ thể]` (KHÔNG `git add -A`)
- `git commit` với message mô tả "why"
- `git push -u origin HEAD` (feature branch) hoặc `git push` (main)
- `git status` → verify "up to date"

**Bước 4 — Merge main** (chỉ khi đang trên feature branch)
- `git checkout main && git merge --no-ff feature/[tên]`
- `git push`
- Nếu đang trên `main` → skip bước này

**Bước 5 — Deploy production** (chọn đúng path theo project — xem Bước 4 của `full update` Workflow)
- systemd: `sudo systemctl restart [name]` → `sudo systemctl is-active [name]`
- Docker Compose: `docker compose build [svc] && docker compose up -d --force-recreate [svc]` → verify HTTP 200
- Không có production service → skip

**Bước 6 — Report**
```
-- commit all --
Universal-workflow repo: pushed [N files] / skipped (no changes)
Branch: [branch] -> main
Commit: [hash] [message ngắn]
Service: [tên] restarted / N/A
MD files updated: [danh sách]
```

### Lưu ý
- Nếu bất kỳ bước nào fail → **DỪNG ngay**, báo lỗi, KHÔNG tiếp tục
- Nếu merge conflict → **DỪNG**, báo user
- Universal-workflow repo dùng SSH key: `${BOOTSTRAP_SSH_KEY:-~/.ssh/id_rsa}` (đặt biến `BOOTSTRAP_SSH_KEY` nếu dùng key riêng)
- Repo URL: `git@github.com:thanhnt1021/universal-workflow.git`

---

## sync uni Workflow

**Repo gốc (SSOT):** `https://github.com/thanhnt1021/universal-workflow` — repo PRIVATE, clone bằng `gh`/git đã auth (KHÔNG dùng `curl raw...`). Repo là nguồn chân lý DUY NHẤT; bản trong `docs/universal_rules/` của từng project chỉ là cache.

Mỗi bản copy có `VERSION` + `MANIFEST.txt` (sha256 từng file, sinh bằng `scripts/gen_manifest.sh`). **Drift check 1 lệnh** — chạy trong `docs/universal_rules/` của project:
```bash
shasum -a 256 -c MANIFEST.txt --quiet && echo "✓ khớp SSOT $(cat VERSION)" || echo "⚠️ DRIFT — chạy sync uni"
```

### Chiều PULL — user nói `sync uni` (hoặc "pull uni", "update uni rules", "đồng bộ universal rules"):

1. **Clone** repo `thanhnt1021/universal-workflow` vào thư mục tạm
2. **So sánh manifest trước** (nhanh): `diff docs/universal_rules/MANIFEST.txt /tmp/_uw/MANIFEST.txt` — khớp thì báo "đã mới nhất", DỪNG. Lệch → so file-by-file:
   - File nào **thay đổi** (diff)
   - File nào **mới thêm** trong repo
   - File nào **đã xoá** khỏi repo (còn trong project nhưng không còn trong repo)
3. **Báo cáo** danh sách thay đổi cho user xem trước
4. **Thực hiện** cập nhật:
   - Copy file mới/thay đổi từ repo → `docs/universal_rules/` (gồm cả `VERSION` + `MANIFEST.txt`)
   - Copy subdirectories (`rules/`, `templates/`, `skills/`, `hooks/`, `scripts/`, `_meta/`) nếu có
   - Xoá file không còn trong repo (trừ file project-specific — vd hook/playbook riêng như bộ Canva của C-HX)
   - **KHÔNG copy** `README.md` của repo vào `docs/universal_rules/` (đó là README của repo, không phải rule file)
   - Nếu `hooks/` đổi → copy bản mới vào `~/.claude/universal-hooks/` (nơi hook chạy THẬT, được `~/.claude/settings.json` trỏ tới)
5. **Tạo file project-specific nếu chưa có:**
   - `README.md` ở root ← từ `docs/universal_rules/templates/README_TEMPLATE.md`
   - `docs/GOAL.md` ← từ `docs/universal_rules/templates/GOAL_TEMPLATE.md`
6. **KHÔNG overwrite** nếu đã tồn tại: `CLAUDE.md`, `README.md`, `docs/GOAL.md`, `docs/CHANGELOG.md` (audit log của project — xem `docs/universal_rules/rules/CHANGELOG_RULES.md`)
7. **Dọn dẹp** thư mục tạm
8. **Báo cáo** kết quả → **DỪNG**, chờ user confirm commit

### Chiều PUSH — rule mới/sửa sinh ra Ở PROJECT (bắt buộc, đừng để rule kẹt lại project):

Khi một phiên làm việc tạo/sửa rule trong `docs/universal_rules/` của project (bài học mới, mục rule mới):
1. Copy file đó về repo local `~/PycharmProjects/universal-workflow/` (đúng đường dẫn tương ứng)
2. Bump `VERSION` (patch: sửa nội dung; minor: thêm file/mục lớn) + chạy `bash scripts/gen_manifest.sh`
3. Commit + push repo (`gh auth switch --user thanhnt1021` trước)
4. Nhắc user: các project khác nhận bản mới khi chạy `sync uni`
> _Lý do có chiều PUSH: 6/2026 audit phát hiện 6 bản copy drift hết vì rule mới sinh ở project nào nằm lại đó (doit — project Cloudflare gốc — không có CLOUDFLARE_RULES.md; iloveus thiếu QUALITY_GATES 0.D). SSOT chỉ sống khi rule mới chảy NGƯỢC về repo._

> **Lưu ý:** `sync uni` KHÔNG tự commit vào project. User phải nói `commit` riêng.

---

## Goal Tracking Protocol

Áp dụng khi project có `docs/GOAL.md` + `docs/OUTCOME.md`. Chi tiết từ góc độ user: xem `docs/universal_rules/rules/OUTCOME.md` mục **CÁCH VẬN HÀNH**.

### Trigger A — `read context`

Sau khi đọc xong tất cả docs:

1. Đọc `GOAL.md` → extract mục tiêu cuối + milestone hiện tại
2. Output 1 dòng: `📌 Goal: [X] | 📍 Đang ở: [milestone]`
3. Nếu `_Last reviewed_` > 7 ngày **hoặc** có `Pending / Cần Quyết Định` chưa giải quyết → hiện danh sách + hỏi user có gì cần update không (options A/B/C theo format trong docs/universal_rules/rules/OUTCOME.md)
4. Nếu user confirm OK → cập nhật `_Last reviewed_` thành ngày hôm nay trong `GOAL.md`
5. Nếu không có `GOAL.md` → hỏi muốn tạo không (theo docs/universal_rules/rules/OUTCOME.md mục 7)
6. **Sau đó mới báo "Đã hiểu, sẵn sàng nhận lệnh."**

### Trigger B — `feature: [tên]` (Track B trong Analysis Phase)

Chạy song song với Track A trong Phase 1 bước 3. Claude so plan vs `GOAL.md`:
1. Feature serve milestone nào? Nếu không có → flag để thêm mới.
2. Plan có conflict với goal hiện tại không?
3. Plan có nằm ngoài scope goals không (goal drift)?

Findings gom vào batch Q&A chung (bước 4). Sau khi user confirm → **update `GOAL.md` ngay** (bước 6): link milestone, resolve conflicts, cập nhật `_Last reviewed_`.

### Trigger C — `commit`

Trước khi viết commit message, check: commit này có hoàn thành milestone nào không?
- **Có** → đề xuất update `GOAL.md` (tick `[x]`, cập nhật "Hiện tại đang ở đâu") — user confirm trước khi include trong commit
- **Không** → skip hoàn toàn, không hỏi thừa

### Goal-Check và Drift-Check (implicit, không trigger bởi lệnh)

Mỗi khi nhận task bất kỳ: tự check ngầm task có dẫn đến goal không. Nếu lệch → cảnh báo + options. Xem đầy đủ trong `docs/universal_rules/rules/OUTCOME.md` mục 3-4.

---

## report context — Output Format

Sau khi đọc xong tất cả files, **bắt buộc output** một summary có cấu trúc như sau. Chỉ dùng khi lệnh là `report context` — nếu lệnh là `read context` thì **không output gì**, chỉ báo "Đã hiểu, sẵn sàng nhận lệnh."

### 1. Tech Stack
Liệt kê ngắn: framework, DB, auth, AI/external services, deploy, port/domain.

### 2. Architecture Overview
Mô tả ngắn cách hệ thống hoạt động tổng thể: các lớp chính, data flow cốt lõi.
Nếu có background job / async processing → mô tả rõ pattern đó.

### 3. Key Flows
Các luồng người dùng / nghiệp vụ chính — mỗi flow 3–5 bước, dạng bullet ngắn gọn.
Chỉ list các flow quan trọng, không cần list hết.

### 4. Current Status
- **Done:** các tính năng đã hoàn chỉnh và tested (chỉ list những cái quan trọng)
- **TODO / In Progress:** những gì còn cần làm hoặc đang dở

### 4b. Goals (nếu project có GOAL.md)
- **Mục tiêu cuối:** [1 câu]
- **Milestone đang ở:** [tên milestone + % ước tính]
- **Pending:** [danh sách items nếu có, hoặc "không có"]

### 5. Workflow Quick Ref
- Branch hiện tại + strategy
- Deploy commands (demo / production)
