# WORKFLOWS — quy trình lệnh dài + File Ownership + Goal Protocol

Bảng lệnh tóm tắt ở `INDEX.md`. Luật bất biến ở `SPINE.md`. Git chi tiết ở `rules/GIT.md`.

## `feature: [tên]` — 2 phase, KHÔNG nhảy thẳng vào code

> **BƯỚC 0 (bắt buộc, không ngoại lệ):** nhận `feature: [tên]` → tạo branch `feature/tên` NGAY, trước khi đọc context. Dù user đính kèm plan/patch đầy đủ đến đâu vẫn tạo branch trước.
> _Không branch = làm thẳng trên main = không rollback, không review riêng, không test song song._

> **RULE CỨNG:** không bao giờ bỏ Phase 1 dù user đính kèm plan chi tiết. **Plan là input để đối chiếu codebase — KHÔNG phải lệnh implement.**

### Phase 1 — Analysis
1. Đọc plan/prompt + re-read context (schema, API, components, types) + `docs/GOAL.md`.
2. Chạy 3 track song song (ngầm): **A-Codebase** (so plan vs code → phân loại 🔴CONFLICT/🟡AMBIGUITY/🟠RISK/🔵GAP/⚪ASSUMPTION — xem `rules/ASK-BACK.md`); **B-Goal** (so plan vs GOAL: serve milestone nào? conflict? drift?); **C-Impl** (dependencies, technical decisions mở, test strategy).
3. Gom findings → **HỎI** (Claude: `AskUserQuestion` tool; Codex/khác: hỏi dạng danh sách option đánh số) — tối đa 7 câu, ưu tiên 🔴>🟡>🟠>🔵>⚪, recommended đặt đầu. Chi tiết format: `rules/ASK-BACK.md`.
4. User trả lời → nếu có `GOAL.md`, update ngay (link milestone, resolve conflict, `_Last reviewed_`).
5. **Trình Full Plan chờ duyệt qua plan-mode của harness** (Claude: `ExitPlanMode`; Codex: `/plan-mode`) — approach, các bước test được độc lập, file thay đổi, edge case đã xác nhận. KHÔNG dùng text tự chế "gõ làm đi" để xin duyệt khi harness có plan-mode.
6. User duyệt → Phase 2.

> Exception: plan đơn giản (<3 file, không ambiguity, không đụng goal) → gộp 2-4 thành 1 confirm ngắn.

### Phase 2 — Implement từng bước, test ngay
1. Implement từng function/fix một theo thứ tự đã chốt — không làm hết rồi mới test.
2. Test kỹ sau mỗi bước (quick deploy verify / test endpoint trực tiếp) → confirm works → mới sang bước sau.
3. **Trước quick deploy lần cuối → `check code` BẮT BUỘC** (skill app-security / `rules/GATES.md` §Security §0).
4. Xong → quick deploy → báo cáo tổng kết → **DỪNG chờ feedback**.
5. Gặp vấn đề loop >2 lần → dừng, tham vấn user, không tự thử mãi.

## `full update` — one-shot cuối task (lệnh rõ của user = được phép commit/push/merge/deploy)

1. **Update MD**: đọc `docs/MD_FILES_TO_UPDATE.md` → update hết + `CLAUDE.md`/`AGENTS.md` nếu đổi kiến trúc; 4 loại catalog-level → `docs/CHANGELOG.md` TRƯỚC (`rules/DOCS.md`); milestone xong → `docs/GOAL.md`; clear list.
2. **Nếu sửa file trong univ3** → đẩy SSOT trước (§sync-uni chiều PUSH).
3. **Commit + push**: `git add [file cụ thể]` (KHÔNG `-A`) → commit (WHY) → `git push -u origin HEAD` (feature) / `git push` (main) → `git status` verify "up to date".
4. **Merge main** (nếu đang ở feature): `git checkout main && git merge --no-ff feature/[tên]` → `git push` → verify.
5. **Deploy production** (theo `CLAUDE.md` project — systemd `restart`+`is-active` / docker `build`+`up -d --force-recreate`+`curl` 200 / no-service skip).
6. **Report** ngắn: branch→main, commit, deploy, MD updated.

> Bất kỳ bước fail / merge conflict → **DỪNG ngay**, báo user, không tự resolve. (`full update` không gồm deploy demo — dùng `quick deploy` riêng nếu cần.)

## `sync uni` — đồng bộ với SSOT repo `thanhnt1021/univ3`

Repo SSOT: `git@github.com:thanhnt1021/univ3.git` (PRIVATE, clone bằng `gh`/git đã auth — tài khoản `thanhnt1021`). Bản trong `docs/univ3/` của mỗi project chỉ là cache; có `VERSION` + `MANIFEST.txt` (sha256). **Drift check 1 lệnh** (chạy trong thư mục univ3):
```bash
shasum -a 256 -c MANIFEST.txt --quiet && echo "✓ khớp SSOT $(cat VERSION)" || echo "⚠️ DRIFT — sync uni"
```

**Chiều PULL** (`sync uni`): clone repo → `diff MANIFEST.txt` (khớp → "đã mới nhất", DỪNG) → báo file thay đổi/mới/xoá → copy về (gồm `VERSION`+`MANIFEST`) → xoá file không còn trong repo TRỪ file khai trong `LOCAL_ONLY.txt` → KHÔNG overwrite `CLAUDE.md`/`AGENTS.md`/`README.md`/`docs/GOAL.md`/`docs/CHANGELOG.md` nếu đã có → hook đổi thì cài lại (`install.py`) → báo cáo → DỪNG chờ user `commit`.

**Chiều PUSH — QUY TRÌNH DUY NHẤT** (rule mới/sửa sinh ở project phải chảy ngược, đừng để kẹt):
0. Phân loại theo §File-Ownership: file trong `LOCAL_ONLY.txt` → KHÔNG đẩy; file mới chưa rõ chung/riêng → HỎI rồi mới đi tiếp.
1. Copy file về SSOT clone `~/PycharmProjects/univ3-ssot/` (clone lại nếu chưa có — xem `HUONG_DAN.md` §Cập nhật), đúng đường dẫn tương ứng.
2. Bump `VERSION` (patch: sửa nội dung; minor: thêm file/mục lớn) + chạy `bash scripts/gen_manifest.sh` (+ `python3 scripts/gen_agents_md.py` nếu sửa SPINE).
3. Commit + push repo SSOT (`gh auth switch --user thanhnt1021` trước nếu đang tài khoản khác).
4. Nhắc: project khác nhận bản mới khi `sync uni`.
> _Chỉ có MỘT quy trình push-SSOT này. Không copy `*.md` flat, không bỏ qua VERSION/manifest — làm sai phá drift-check._

## §File-Ownership — file này CỦA AI, push ĐI ĐÂU?

3 câu trước khi commit file bất kỳ: **(1) chung hay riêng? (2) push repo nào? (3) máy khác pull kiểu gì?**

| Loại | Nhận diện | Push đi đâu |
|---|---|---|
| 1. Chung (universal) | Trong univ3 **VÀ** có trong `MANIFEST.txt` | SSOT (§sync-uni PUSH) → fan-out qua `sync uni` |
| 2. Riêng project | Code app, docs project (GOAL/PROJECT_SUMMARY/CHANGELOG/DESIGN), asset | Repo project |
| 3. Riêng-nhưng-trong-univ3 | KHÔNG có trong MANIFEST + khai trong `LOCAL_ONLY.txt` | Repo project — **TUYỆT ĐỐI không đẩy SSOT** |
| 4. Cá nhân/nhạy cảm | Secret, `.env`, token, tài liệu cá nhân | KHÔNG push đâu — `.gitignore` |

Decision tree khi commit: file có trong MANIFEST → loại 1 (bắt buộc chiều PUSH). File MỚI trong univ3 → **HỎI bắt buộc** (A. chung→SSOT / B. riêng→thêm `LOCAL_ONLY.txt` / C. nhạy cảm→`.gitignore`). File ngoài univ3 → repo project (nhưng nếu chứa BÀI HỌC dùng chung → hỏi trích phần chung về SSOT). File lạ mình KHÔNG tạo → KHÔNG tự commit, HỎI. `MANIFEST.txt` = ranh giới máy-đọc "chung"; `LOCAL_ONLY.txt` = ý định người khai "riêng".

## §Goal Protocol (tóm tắt — chi tiết `rules/DOCS.md`)

- `read context`: đọc `docs/GOAL.md` → output `📌 Goal: [X] | 📍 Đang ở: [milestone]`; `_Last reviewed_` >7 ngày hoặc có PENDING → hỏi update; rồi mới báo "Đã hiểu, sẵn sàng."
- `feature:` Track B: so plan vs GOAL (đã nêu Phase 1). `commit`: milestone xong → đề xuất tick `[x]` + cập nhật "đang ở đâu" (user confirm trước).
- Goal-check ngầm mỗi task: task có dẫn tới goal không? Lệch → cảnh báo + options. **Claude chỉ sửa GOAL.md khi user đồng ý.** PENDING trong GOAL.md = phao cứu trạng thái khi context bị nén.

## `read context` / `report context`
- `read context`: đọc `CLAUDE.md`/`AGENTS.md` + `docs/` (trừ nội dung đã skill-hoá) → Goal check → "Đã hiểu, sẵn sàng." → DỪNG (KHÔNG output summary).
- `report context`: như trên + output summary (Tech stack / Architecture / Key flows / Current status / Goals / Workflow ref).
