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
4. Xong → **tự động commit (local) + deploy demo** → báo cáo tổng kết → **DỪNG chờ feedback**. (Commit + deploy demo an toàn — làm luôn; **KHÔNG tự `push`/`merge`**, chờ lệnh rõ.)
5. Gặp vấn đề loop >2 lần → dừng, tham vấn user, không tự thử mãi.

## `full update` — one-shot cuối task (lệnh rõ của user = được phép commit/push/merge/deploy)

1. **Update MD**: đọc `docs/MD_FILES_TO_UPDATE.md` → update hết + `CLAUDE.md`/`AGENTS.md` nếu đổi kiến trúc; 4 loại catalog-level → `docs/CHANGELOG.md` TRƯỚC (`rules/DOCS.md`); milestone xong → `docs/GOAL.md`; clear list.
2. **Nếu sửa file trong univ3** → đẩy SSOT trước (§sync-uni chiều PUSH).
3. **Commit + push**: `git add [file cụ thể]` (KHÔNG `-A`) → commit (WHY) → `git push -u origin HEAD` (feature) / `git push` (main) → `git status` verify "up to date".
4. **Merge main** (nếu đang ở feature): `git checkout main && git merge --no-ff feature/[tên]` → `git push` → verify.
5. **Deploy production** (theo `CLAUDE.md` project — systemd `restart`+`is-active` / docker `build`+`up -d --force-recreate`+`curl` 200 / no-service skip).
6. **Report** ngắn: branch→main, commit, deploy, MD updated.

> Bất kỳ bước fail / merge conflict → **DỪNG ngay**, báo user, không tự resolve. (`full update` không gồm deploy demo — dùng `quick deploy` riêng nếu cần.)

## `sync uni` — CHẠY SCRIPT, CẤM LÀM TAY

Repo SSOT: `git@github.com:thanhnt1021/univ3.git` (PRIVATE, tài khoản `thanhnt1021`). Bản trong `docs/univ3/` mỗi project chỉ là cache.

> **BÀI HỌC 2026-08-25 — vì sao mục này bị viết lại:** thứ tự đúng đã nằm sẵn ở đây bằng chữ, model vẫn tự diễn lại thành "pull đè trước, vá sau" → suýt mất watchdog + cổng trần-worker vừa dựng xong trên máy. **Luật markdown = xác suất; script + cổng exit≠0 = tất định.** Nên các bước làm tay đã bị XOÁ khỏi mục này — còn để lại là còn có người diễn lại.

**3 lệnh, đúng thứ tự này, không có đường khác:**
```bash
~/.claude/universal-hooks/sync-uni.sh check   # backup + bảng khác biệt 3 nguồn + đếm hook. KHÔNG ghi gì.
#   (MODEL đọc bảng diff → quyết giữ bản nào → gộp TAY vào clone SSOT script đã in đường dẫn)
~/.claude/universal-hooks/sync-uni.sh push --bump minor -m "..."   # bump VERSION + gen_manifest + verify + push SSOT
~/.claude/universal-hooks/sync-uni.sh pull    # chỉ chạy được khi check SẠCH; rsync về + install.py + cổng cuối
```

**Phân vai — script KHÔNG tự gộp, KHÔNG tự sửa file luật:**

| | Việc |
|---|---|
| **SCRIPT** (máy móc, không được sai) | backup 3 nguồn ra 2 nơi · liệt kê khác biệt **A repo ⇄ B SSOT ⇄ C `~/.claude` đang chạy** + in `diff` từng tệp · đếm/liệt kê hook `settings.json` trước-sau · **CHẶN CỨNG exit 4** khi local/máy có thứ SSOT chưa có · verify shasum + VERSION + hook-không-giảm + script-không-mất · **tự khôi phục từ backup** khi cổng đỏ |
| **MODEL** (phán đoán, bash làm không nổi) | đọc bảng diff · quyết giữ bản nào · gộp tay · xử mâu thuẫn · ghi rõ trong báo cáo đã quyết gì và vì sao |

- **Nguồn C (`~/.claude/` đang chạy) là nguồn hay bị bỏ quên nhất** — hook + script vừa dựng nằm ở đó trước khi kịp lên SSOT. `check` bắt buộc soi nguồn này.
- Tệp CỐ Ý chỉ ở máy → khai `~/.claude/universal-hooks/LOCAL_ONLY.txt` (hoặc `docs/univ3/LOCAL_ONLY.txt`), 1 tên/dòng — hết bị báo drift.
- Hook/script MỚI đẩy lên SSOT phải thêm tên vào `HOOK_FILES` trong `install.py`, không thì máy/project khác không nhận được.
- Xung đột lúc `push` (worker khác vừa push) → script **DỪNG**, không tự resolve. Báo rồi hỏi.
- **Vùng tạm gắn định danh project — CẤM lấy phần tử đầu tiên khi bung ký tự đại diện.** `/tmp/sync-uni-state/` dùng CHUNG cả máy: `cat /tmp/sync-uni-state/*/clone.txt | head -1` ra clone của project KHÁC (25/8 đã chép đè lên việc dở của `vevoi`). Cần clone của mình → `sync-uni.sh clone`. Clone mang dấu `.git/univ3-owner`; `push`/`pull` lệch dấu → exit 7. Hook `sync_state_owner_enforce.py` chặn tất định mọi lệnh GHI trỏ sang vùng project khác.
- Sau `pull`: `git add docs/univ3 AGENTS.md` — **CẤM `git add -A`**.

## §File-Ownership — file này CỦA AI, push ĐI ĐÂU?

3 câu trước khi commit file bất kỳ: **(1) chung hay riêng? (2) push repo nào? (3) máy khác pull kiểu gì?**

| Loại | Nhận diện | Push đi đâu |
|---|---|---|
| 1. Chung (universal) | Trong univ3 **VÀ** có trong `MANIFEST.txt` | SSOT (§sync-uni PUSH) → fan-out qua `sync uni` |
| 2. Riêng project | Code app, docs project (GOAL/PROJECT_SUMMARY/CHANGELOG/DESIGN), asset | Repo project |
| 3. Riêng-nhưng-trong-univ3 | KHÔNG có trong MANIFEST + khai trong `LOCAL_ONLY.txt` | Repo project — **TUYỆT ĐỐI không đẩy SSOT** |
| 4. Cá nhân/nhạy cảm | Secret, `.env`, token, tài liệu cá nhân | KHÔNG push đâu — `.gitignore` |

Decision tree khi commit: file có trong MANIFEST → loại 1 (bắt buộc chiều PUSH). File MỚI trong univ3 → **HỎI bắt buộc** (A. chung→SSOT / B. riêng→thêm `LOCAL_ONLY.txt` / C. nhạy cảm→`.gitignore`). File ngoài univ3 → repo project (nhưng nếu chứa BÀI HỌC dùng chung → hỏi trích phần chung về SSOT). File lạ mình KHÔNG tạo → KHÔNG tự commit, HỎI. `MANIFEST.txt` = ranh giới máy-đọc "chung"; `LOCAL_ONLY.txt` = ý định người khai "riêng".

## §Buổi-sáng — gom cổng HOOK vào MỘT lượt duyệt, rồi chạy một mạch

> Chốt 26/08/2026. Founder xả task buổi sáng rồi **đi tập gym** — từ lúc đó mỗi câu hỏi là
> một phiên đứng im. Nên mọi thứ cần chủ nhà chốt phải dồn về ĐẦU NGÀY, một lượt.

1. **Trước khi làm bất cứ việc nào** (founder mở đầu bằng *"có cái gì cần hook không, đẩy
   lên confirm trước hết"*): rà cả mớ task hôm nay xem việc nào **cần hook mới** hoặc **cần
   nới hook đang có** — nặng nhất là việc **sửa dữ liệu** và việc **đụng tệp dùng chung**
   (`.htaccess`, `nginx.conf`, sheet, DB). Gom TẤT CẢ vào **một lượt `AskUserQuestion` duy
   nhất**. Không có gì cần hook thì nói thẳng "không cần", đừng hỏi lấy lệ.
2. **Founder duyệt xong + xả hết task → coi như founder đã đi vắng.** Từ đó **chỉ việc
   chạy**: không hỏi nữa, không dựng thêm cổng chặn để chờ người. Gặp chỗ mơ hồ mà không
   phá được gì → chọn phương án an toàn nhất, GHI vào báo cáo, đi tiếp.
3. **Sau MỖI lệnh founder gửi thêm: hỏi lại một câu "còn task gì nữa không"** — nhưng
   **vẫn chạy tiếp bình thường, không dừng chờ trả lời**. Task bổ sung thì lặp lại bước 1
   cho riêng nó: cần hook thì gom `AskUserQuestion` một lượt, không cần thì làm luôn.
4. **Cần báo tiến độ/kết quả cho founder (đang đi vắng)** → chạy `~/.claude/universal-hooks/tg-notify.sh "nội dung"` — nhóm đích đã cố định sẵn trong `telegram_config.env`, **CẤM đi dò token/hỏi chọn nhóm**.

Hệ quả bắt buộc với hook: hook **không được `ask`** trong ngày làm việc — chỉ `allow` kèm
nhắc, hoặc `deny` cho thứ làm mất dữ liệu / mất việc của người khác. Cần người quyết →
đưa vào lượt duyệt buổi sáng, đừng chặn giữa chừng.

## §Goal Protocol (tóm tắt — chi tiết `rules/DOCS.md`)

- `read context`: đọc `docs/GOAL.md` → output `📌 Goal: [X] | 📍 Đang ở: [milestone]`; `_Last reviewed_` >7 ngày hoặc có PENDING → hỏi update; rồi mới báo "Đã hiểu, sẵn sàng."
- `feature:` Track B: so plan vs GOAL (đã nêu Phase 1). `commit`: milestone xong → đề xuất tick `[x]` + cập nhật "đang ở đâu" (user confirm trước).
- Goal-check ngầm mỗi task: task có dẫn tới goal không? Lệch → cảnh báo + options. **Claude chỉ sửa GOAL.md khi user đồng ý.** PENDING trong GOAL.md = phao cứu trạng thái khi context bị nén.

## `read context` / `report context`
- `read context`: đọc `CLAUDE.md`/`AGENTS.md` + `docs/` (trừ nội dung đã skill-hoá) → Goal check → "Đã hiểu, sẵn sàng." → DỪNG (KHÔNG output summary).
- `report context`: như trên + output summary (Tech stack / Architecture / Key flows / Current status / Goals / Workflow ref).
