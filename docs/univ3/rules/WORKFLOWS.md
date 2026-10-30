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
- **`check` in khối «⚠ HỎI ANH: dự án này chưa có bot/nhóm nhận việc»** (dự án thiếu `docs/bot-nhan-viec.json`, hoặc đã chọn «để sau») → main hỏi anh bằng AskUserQuestion 3 lựa chọn (a) dựng ngay theo skill `bot-nhan-viec` · (b) để sau · (c) không cần, rồi GHI lựa chọn bằng `sync-uni.sh bot-nhan-viec khong-can|de-sau` (dựng xong: `… da-co --bot @ten --nhom "Tên nhóm"`). Chọn (c) hoặc đã có → lần sau im; (b) → lần sync sau hỏi lại. Khối hỏi không chặn check/pull.

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

## §Tin-gửi-người-vận-hành — viết bằng NGÔN NGỮ CỦA HỌ, không phải của lập trình viên

**Ca thật 07/09/2026.** Một worker gửi tin vào nhóm *Hệ thống Fulfill TheChic* (Phương, My,
Hạnh — **không ai là lập trình viên**), phần nghiệp vụ viết rất tốt, nhưng cuối tin ghi:
*"Chi tiết đầy đủ … nằm ở tệp trong kho mã nguồn: `docs/handoff/DON-NUOT-MON-…md`"*.
Founder: *"mày nhắc tới tệp kho mã nguồn làm gì? chỉ 1 mình tao là Dev hiểu thôi."*
Team **không mở được kho mã nguồn** → câu đó vô dụng với người đọc, lại làm tin trông rối.

**LUẬT.** Mọi tin gửi ra ngoài cho **người vận hành** (nhóm Telegram của team, email cho
sup/xưởng, tin cho khách) **CẤM** chứa:
đường dẫn tệp mã nguồn (`docs/…`, `src/…`, đuôi `.md` `.ts` `.py` `.sh` `.json`) · mã commit ·
tên nhánh (`origin/main`) · `file.ts:123` · tên hàm · tên bảng / cột CSDL ·
các chữ *kho mã nguồn, repo, commit, branch, build, deploy, BUILD_ID, migration, schema*.

**Cần đưa chi tiết thì:** dán thẳng bảng/danh sách vào tin · gửi **tệp đính kèm**
(`sendDocument`) · hoặc viết *"cần bản đầy đủ thì nhắn lại nhóm, em gửi"*.
**Cần chỉ chỗ:** đưa **link bấm được** (`fulfill.thechic.site/...`), không đưa đường dẫn tệp.
**Cần báo đã sửa xong:** nói bằng **hiện tượng người dùng thấy** ("từ giờ đơn thiếu món sẽ
hiện cảnh báo đỏ"), không nói commit/build/deploy.
**TUYỆT ĐỐI KHÔNG** bảo người ta tự mở kho mã nguồn.

**KHÔNG áp cho:** nhóm **kỹ thuật** (`--loai=ky-thuat`, `-1003849385640`) và chat riêng của
founder — tin kỹ thuật ở đó là **đúng chỗ**. Mã đơn `A67-4163738170`, mã hàng/SKU, tên xưởng,
phần cá nhân hoá **không phải** yếu tố kỹ thuật — team CẦN chúng, cấm cắt.

**KHUÔN TIN NHÓM HỆ THỐNG — P118 (05/10/2026, cổng tất định `tin_nhom_khuon.py`).** Anh Thành:
*"Tin nhắn … lúc nào cũng quá dài dòng"* + *"lần sau gửi vào như này mà chỉ gửi ảnh thì rất khó nói
chuyện. cần có rõ ràng câu hỏi 1, 3 option là 1A, 1B, 1C, câu hỏi 2 2 option là 2A, 2B... có cả chữ
trên ảnh chứ"* (ca gốc: tin Task-05102026-02 xin duyệt = album 5 ảnh, chữ chỉ "Duyệt hoặc Cần sửa").
- **Một lối gửi duy nhất:** `node scripts/task-dev.mjs tin --ma Task-ddmmyyyy-NN …` — máy chủ ghép
  tin từ từng ô, tự trả lời nối vào tin gốc của việc. Bắn thẳng Telegram vào nhóm Hệ thống bị chặn.
- **Khuôn:** dòng đầu `[Task-ddmmyyyy-NN] tiêu đề ≤ 70` · `Đã làm:` (hoặc `Hỏi:`) · `Xem ở:` ·
  `Cần làm: **tên người** — làm gì` · ≤ 1 dòng phụ · dòng cuối `Xem thêm chi tiết trong này: <link thẻ>`
  (máy tự gắn). Thân ≤ 6 dòng, ≤ 600 ký tự, 1 link (không tính link thẻ), ≤ 3 ảnh đi cùng chữ.
- **Tin HỎI / XIN DUYỆT:** câu hỏi **đánh số** `1.`, `2.` (mỗi câu một dòng), mỗi lựa chọn mang mã
  `1A · 1B · 1C`, `2A · 2B` để người trả lời gõ "1B, 2A". **Mọi ảnh kèm phải có chữ ghi trên ảnh**
  (số ảnh + mã lựa chọn / số câu, vd "1A · bản trước") — khai `--nhan-anh`, máy chủ in dải chữ lên ảnh.
  Thiếu câu đánh số, thiếu mã lựa chọn, ảnh thiếu chữ → cổng chặn.

**NGƯỜI GỬI LÀ MÁY — CẤM MẠO DANH NGƯỜI THẬT.** Ca thật 24/09/2026: một worker gửi tin hỏi
chị Phương, mở đầu *"Chị Phương ơi, em Thành đây"*, xưng "em" suốt bài, kết *"em làm theo đúng
ý chị"* — Dev là người thật và **không hề viết tin đó** (phải gỡ 4 tin, gửi lại bản đúng giọng).
Tin do máy soạn thì máy **tự xưng là trợ lý hệ thống**, gọi người nhận bằng tên và vai của họ:
*"Trợ lý hệ thống ChicHub xin hỏi chị Phương…"*, nói rõ **câu hỏi do máy đặt thay mặt đội kỹ
thuật** và **câu trả lời sẽ được chuyển cho Dev quyết**. **CẤM** ký tên / nhập vai bất kỳ người
thật nào trong công ty, **kể cả Dev**. Lý do: người nhận tưởng đang nói chuyện với người thật
thì mọi cam kết trong tin bị hiểu là **lời hứa của người đó** — họ sắp việc, hẹn xưởng, trả lời
khách theo lời hứa đó, còn người bị mượn tên thì không biết gì.

**NHẮC TÊN AI THÌ VIẾT ĐẬM TÊN NGƯỜI ĐÓ** (Dev chốt 24/09/2026): `**Phương**`, `**chị Hạnh**`,
`**My**` — kể cả khi tên nằm giữa câu. Nhóm chạy hàng chục tin mỗi ngày, ai cũng lướt nhanh;
tên in đậm để người có phần trong tin nhận ra ngay là đang hỏi mình mà trả lời, khỏi tin trôi.
Áp cho **mọi loại tin**: tin hỏi, tin báo đã sửa xong, tin giải thích.

**TINH TUÝ CÁCH GỬI TIN — chuẩn chung mọi dự án (chưng cất 08/10/2026 từ dự án chạy thật).**
Các mục trên là ca gốc của một dự án; dưới đây là phần áp cho MỌI dự án có tin gửi người (nhóm
chat vận hành, đối tác, Dev). Mã nhóm/tên người/đường lệnh cụ thể thuộc cấu hình từng dự án.
- **Ngắn + ẢNH khoanh đỏ đúng chỗ đang nói.** Thân tin ≤ 6 dòng; chi tiết để trên thẻ việc.
  Mặc định đính kèm là **ẢNH** (infographic / ảnh chụp có khoanh + chữ ghi trên ảnh); **PDF chỉ khi**
  tài liệu dài nhiều trang **hoặc Dev nói rõ "PDF"** (ca thật: luật một trang gửi kèm PDF bị chửi
  "không phải lúc nào cũng pdf"). Tài liệu gửi người là infographic, không phải tường chữ (§Tài-liệu-gửi-người).
- **Mỗi tin gắn MÃ VIỆC + LINK THẺ VIỆC** (dòng đầu mã, dòng cuối link "xem thêm chi tiết") và
  trả lời nối vào tin gốc của việc đó — người đọc bấm một lần là thấy toàn cảnh, tin không trôi.
- **Mọi tin có lựa chọn → câu đánh số + mã lựa chọn, KHÔNG nút bấm — trả lời bằng Reply gõ mã.** Câu `1.`, `2.`;
  lựa chọn `1A · 1B`, `2A · 2B`; dòng cuối tin bắt buộc «↩ Trả lời (Reply) tin này, gõ mã: 1A hoặc 1B» (gõ
  "1B, 2A" là đủ, mã + chữ thêm = bổ sung). Dev chốt 08/10/2026 bỏ hẳn nút phiếu chọn inline (nút lag, nhãn
  dài bị cắt «…», nút "Bổ sung" không rõ gõ ở đâu). Máy đọc Reply ghi vào thẻ, thả ❤ + Reply nối «Đã ghi: 1A».
  Khuôn đầy đủ + mẫu «một luồng · hai cửa · một trạng thái»: skill **ui-ux** `references/quy-trinh-va-tin.md`.
- **Tin "chỉ cần biết" cũng phải được XÁC NHẬN.** Dòng cuối xin Reply `1A Đã đọc / 1B Chưa rõ` (hoặc `OK`); "Đã đọc" →
  thẻ việc **tự chuyển Xong**. Người nhận trả lời tiếp vào thẻ đã Xong → thẻ **tự mở lại** về "cần
  làm" và báo bên xử lý (không để câu trả lời nằm im trong thẻ đóng).
- **Người trả lời phải thấy câu trả lời đã được nhận**: thả một dấu đã-nhận (vd ❤) lên tin hỏi + tin
  trả lời ngay khi ghi vào thẻ, rồi mới thi công.
- **Tin RIÊNG cho Dev: dòng đầu mang nhãn `🔴 Cần trả lời` hoặc `🟢 Chỉ để biết`**, gom thành **một
  tin mỗi phiên** (tin + ảnh), không tin thử nghiệm, không tin lặp, không bắn nhiều tin lẻ.
- **Báo lại lời người khác → chép NGUYÊN VĂN «…» trước, diễn giải sau**, động từ đúng mức:
  "sẽ hỏi" ≠ "đồng ý" ≠ "đã làm". Ca thật (3 lần/1 ngày): đối tác viết «sẽ báo dev thêm» bị báo
  lại thành «đã đồng ý bật» → Dev quyết trên một lời hứa không có.
- **Không hỏi lại điều đã có người quyết.** Người đúng vai đã trả lời mã lựa chọn trên thẻ → làm theo,
  không hỏi Dev lần nữa. Thật sự cần Dev chọn → hỏi NGAY bằng cơ chế hỏi của harness, mỗi lựa chọn
  có ví dụ cụ thể (ảnh/số/tên màn) — cấm để danh sách "chờ anh quyết" bằng chữ rồi bỏ đó.
- **Việc Dev phải làm tay (máy bị cổng chặn xoá) → đưa ĐÚNG MỘT lệnh chạy tệp `.sh` có sẵn** (vd
  `bash scripts/don-thu-muc-tam.sh`); thiếu thì viết thêm vào tệp đó. **Cấm** dán chuỗi `rm …` rời
  bắt Dev chép tay.
- **Xong việc người dùng nhìn thấy → tự gửi tin**, không "soạn sẵn chờ duyệt"; việc chỉ Dev dùng thì
  không gửi nhóm (ghi sổ đã-gửi để cổng khỏi nhắc).

**Cổng tất định:** `enforce/claude/hooks/tin_van_hanh_gate.py` (PreToolUse · Bash) — chặn cứng
lệnh gửi Telegram vào nhóm vận hành khi nội dung còn dính các cụm trên, in ra đúng cụm bị bắt
và câu thay thế. Cửa thoát dùng-một-lần: `cua_thoat.py mo tin-van-hanh "<lý do>"`.

## §Tài-liệu-gửi-người — INFOGRAPHIC, không phải trang toàn chữ

**Ca thật 08/10/2026.** Cùng một ngày: 2 ảnh hướng dẫn Flowdy (sơ đồ bước đánh số + icon + giờ, ít
chữ) được anh Thành khen; PDF hỏi Merchize (1C) 2 trang toàn bảng chữ song ngữ bị chửi: *"nhìn trông
kinh … đéo có hình minh hoạ infographic visual gì cả đéo ai mà hiểu … fix root cause"*. Gốc bệnh: thợ
viết Markdown cho lập trình viên rồi in thẳng ra PDF.

**LUẬT.** Mọi tài liệu gửi **NGƯỜI** — đối tác, xưởng, team vận hành, anh Thành — dạng **PDF, ảnh,
hay .md đính kèm** đều phải là **infographic**:
- Có **sơ đồ**: bước đánh số và/hoặc luồng đúng ✅ / sai ❌, **icon** đầu mỗi ý, khối màu phân vai.
- **Ít chữ**: mỗi ý một dòng ngắn; ≤ 420 chữ/trang. **Đủ thông tin**: không bớt ý nào của bản gốc.
- Hỏi thì có **khối câu hỏi đánh số** (Q1/Q2, mỗi lựa chọn mang mã 1A · 1B).
- Xuất **PNG từng trang + PDF**; khung dọc 1080×1600 đọc rõ trên điện thoại.
- Tệp **.md** gửi người: **nhúng ảnh infographic ở đầu tệp**, ý ngắn có icon, bảng nhỏ «Thứ xin · Vì sao
  · Ví dụ», câu hỏi đặt riêng một khối; không có đoạn văn trơn > 300 ký tự.
- Gửi ra ngoài công ty: không tên hệ thống nội bộ, không khoá, không dữ liệu khách thật (dùng số giả).

**Làm thế nào (dự án có sẵn mẫu):** chép `docs/templates/infographic-tai-lieu.html` → sửa nội dung →
`node docs/templates/xuat-infographic.mjs <tệp.html> <thư-mục-ảnh> <tệp.pdf>` (ra PNG + PDF, báo trang
tràn, tự chạy cổng). Dự án chưa có mẫu thì dựng theo đúng các khối trên.

**Cổng tất định:** `docs/templates/kiem-infographic.py <tệp…>` — PDF: mỗi trang khối hình (màu đậm / nền
màu nhạt trên phần có mực) ≥ 0,35 và ≤ 420 chữ; .md: có ảnh nhúng ở 15 dòng đầu, không đoạn văn trơn >
300 ký tự; ảnh: khối hình ≥ 0,35. Đo 08/10: PDF 1C cũ 0,14–0,16 (rớt), bản infographic 0,47–0,61 (đạt).
Gắn sẵn vào `scripts/task-dev.mjs tin --tep` — PDF rớt cổng là không gửi.

## §Goal Protocol (tóm tắt — chi tiết `rules/DOCS.md`)

- `read context`: đọc `docs/GOAL.md` → output `📌 Goal: [X] | 📍 Đang ở: [milestone]`; `_Last reviewed_` >7 ngày hoặc có PENDING → hỏi update; rồi mới báo "Đã hiểu, sẵn sàng."
- `feature:` Track B: so plan vs GOAL (đã nêu Phase 1). `commit`: milestone xong → đề xuất tick `[x]` + cập nhật "đang ở đâu" (user confirm trước).
- Goal-check ngầm mỗi task: task có dẫn tới goal không? Lệch → cảnh báo + options. **Claude chỉ sửa GOAL.md khi user đồng ý.** PENDING trong GOAL.md = phao cứu trạng thái khi context bị nén.

## `read context` / `report context`
- `read context`: đọc `CLAUDE.md`/`AGENTS.md` + `docs/` (trừ nội dung đã skill-hoá) → Goal check → "Đã hiểu, sẵn sàng." → DỪNG (KHÔNG output summary).
- `report context`: như trên + output summary (Tech stack / Architecture / Key flows / Current status / Goals / Workflow ref).
