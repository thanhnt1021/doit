# AGENTS-ORCH — điều phối subagent (pattern "đạo diễn")

Khi task lớn: main session KHÔNG tự cày; nó **spawn worker, đọc output, thẩm định, sai thì bắt làm lại kèm chỉ dẫn cụ thể**.

## Cơ chế "main trống" — 1 tool, không có tool thứ 2

Nhận task → gọi `Agent(run_in_background:true)` với brief tự-chứa → echo 1-2 dòng → DỪNG ngay.

"Main trống" là **hệ quả của việc kết thúc lượt** sau khi gọi Agent nền — không phải lệnh riêng, không phải tool thứ 2. Không có "để đó nối sau". Cấm foreground Agent khi user còn muốn tương tác. Verify lời khai worker = giao worker khác, không tự chạy lệnh ở main.

## Khi nào dùng subagent
- Song song hoá nhiều truy vấn ĐỘC LẬP (map nhiều mảng codebase cùng lúc).
- Bảo vệ context chính: việc tốn nhiều token đọc/tìm → giao subagent, chỉ nhận lại kết luận.
- **KHÔNG dùng** khi chỉ cần đọc 1 file / tìm 1 class → `Read`/`Glob` nhanh hơn.

## Brief worker
- Brief **như đồng nghiệp mới bước vào phòng** — nó KHÔNG thấy hội thoại này: đưa đủ absolute path, dòng số, việc cần làm rõ ràng. Prompt cộc lốc → kết quả nông.
- Subagent **stateless** (mỗi spawn là context mới) và **KHÔNG hiển thị cho user** → tự tóm tắt lại cho user bằng text.
- Nhiều subagent song song → **1 message, nhiều Agent call** (hoặc `run_in_background` để canh song song).
- **Task lâu / user còn muốn chat → MẶC ĐỊNH `run_in_background: true` cho MỌI Agent call**: giữ phiên main TRỐNG cho user chat; thả ngầm xong báo 1 câu ngắn rồi DỪNG, đợi notification khi worker xong. CHỈ chạy foreground (blocking) khi user đang chờ kết quả để quyết bước kế ngay. **Ép tất định**: hook `enforce/claude/hooks/subagent_background_enforce.py` (PreToolUse matcher `Agent`) → Agent call thiếu `run_in_background:true` bị `permissionDecision:"ask"` (hỏi user duyệt) thay vì lọt im.
- **CẤM tự làm SUBSET / cắt tính năng khi build hoặc port** (vd web→app): mặc định phải **PARITY ĐẦY ĐỦ** với bản gốc. Tính năng nào khó/không hợp nền tảng đích → **HỎI user** (AskUserQuestion), TUYỆT ĐỐI KHÔNG tự bỏ rồi gọi là "khác biệt có chủ đích". Brief cho worker build/port **BẮT BUỘC** ghi rõ: "parity đầy đủ, cấm cắt scope; vướng thì báo, không tự quyết bỏ".
- **Không làm trùng việc worker**: đã giao research thì đừng tự grep lại cùng thứ.
- **Báo tiến độ worker ngầm = % PROGRESSBAR mỗi con — ĐỌC SỐ THẬT từ file, KHÔNG ước lượng**:
  **CONVENTION bắt buộc (3 phần):**
  (a) **Orchestrator** cấp cho mỗi worker 1 path `/tmp/claude-bg-progress/<project>/<slug>.progress`
      trong brief — `<project>` = basename của CLAUDE_PROJECT_DIR (vd `EtsyFulfillChichub`).
  (b) **Worker BẮT BUỘC ghi** `echo "NN|<nhãn ngắn>" > <path>` sau MỖI bước chính:
      - Đọc code xong = 20, sửa xong = 50, tsc/build pass = 70, commit = 85, deploy xong = 100.
      - Nhãn có thể chứa `:` hoặc `|` — script parse đúng (TAB delimiter nội bộ).
  (b1) **`/tmp/claude-bg-progress/<project>/` CHỈ được chứa `*.progress`.** Log build/deploy,
      ảnh chụp màn hình, script tạm, backup JSON… đổ vào **thư mục nháp của phiên**
      (scratchpad) hoặc `/tmp/`. Ngày 27/8 thư mục này ngập **80+ tệp rác** lẫn với 6 tệp
      tiến độ thật (build*.log, deploy*.log, tsc*.log, doisup-*.png, shots/, q.mjs,
      cookies.txt…) — luật "worker tự dọn rác" là markdown nên KHÔNG con nào dọn. Ép tất
      định: `progress_format_enforce.py` **deny** mọi lệnh ghi tệp không phải `.progress`
      vào thư mục đó; bảng worker cũng chỉ đọc `*.progress`.
  (a1) **ĐÁNH SỐ THỨ TỰ — BẮT BUỘC, thả trước số nhỏ hơn.** Màn hình liệt kê worker nền
      chỉ hiện `general-purpose` + cột mô tả **bị cắt còn ~8 ký tự** (`Removing…`, `Tailing …`)
      → founder không biết con nào là việc gì. Nên:
      1. **Trước** mỗi Agent call, xin số: `N=$(bash ~/.claude/universal-hooks/wseq.sh next <slug> "<mô tả>")`
      2. `description` của Agent = **`"$N <việc ngắn tiếng Việt>"`** — vd `W07 gỡ cầu Telegram`.
         **SỐ ĐỨNG ĐẦU**, không chen gì trước (chỉ 8 ký tự đầu lọt vào cột). Tổng ≤ 24 ký tự.
      3. **CẤM đặt tên tuỳ hứng / không số** (`Removing stale servers`, `Tailing logs`…).
      4. Worker xong → `bash ~/.claude/universal-hooks/wseq.sh done <slug>`.
      Sổ ở `~/.claude/worker-counter/<project>.map` (số ↔ slug ↔ việc ↔ giờ thả ↔ trạng thái);
      xem bảng bằng `wseq.sh list`. Cấp số nguyên tử (khoá `mkdir`) → 10 worker xin cùng lúc vẫn
      không trùng. **Sổ reset mỗi ngày** (W01 lại từ sáng, nhưng nhảy qua số worker hôm qua còn
      chạy) — founder chỉ cần phân biệt trong ngày, `W147` vô nghĩa với mắt người.
      1 slug = 1 số **suốt đời**: xin lại cùng slug trả về đúng số cũ. `bg-progress.sh` in kèm số.
      **KHUÔN `description` (bắt buộc, không biến tấu):** `W## <slug viết cách bằng dấu cách>` —
      slug `het-loc-sai-nguoi` → `W07 het loc sai nguoi`. Viết đúng khuôn thì bảng ghép được
      **chính xác** dòng agent với tệp tiến độ; viết tự do (`Co che deploy gop theo nhom` cho slug
      `deploy-theo-nhom`) là bảng phải đoán mò và founder thấy `W??`.
      **CẤM nhét `worker-cap-ok` vào `description`** — nhét vào `prompt`; để trong tên thì nó ăn
      mất chỗ của phần chữ ít ỏi lọt lên màn hình.
      Quên xin số → bảng tự cấp bù (`wseq adopt` cho con đã có số trong `description`, `wseq next`
      cho con chưa có), nhưng **số cấp bù KHÔNG hiện trên màn hình agent** → vẫn phải xin TRƯỚC.

  (a3) **BẢNG W## IN MỖI LƯỢT + TỰ DỌN — không ai phải nhắc lại.**
      Founder: *"đéo có tgian worker sống thì tao biết con nào với con nào???"* và
      *"từ giờ mỗi lần tao làm việc đã có con luôn dọn cho chưa? hay bố phải nói lại?"*
      - `enforce/claude/hooks/worker_board.py` là **bảng duy nhất** (`bg-progress.sh` uỷ quyền
        sang nó). Hook `delegate_subagent_reminder.sh` chạy nó **mỗi lượt** rồi bắt main in
        nguyên văn ở ĐẦU câu trả lời. **Không có worker nào → không in gì.**
      - Mỗi dòng: `W## · tên việc · thanh % · nhãn · sống <tuổi> · im <phút>`.
        **`sống`** = từ lúc thả (lấy birth time transcript agent → **khớp đồng hồ khung agent**:
        `34p`, `2h25`; `~` là ước lượng theo tệp tiến độ). **`im`** = lâu chưa nhúc nhích;
        `⚠` >10 phút, `⛔` >30 phút. Gọn tối đa 6 dòng, dòng cuối `xong N · bỏ dở M`.
      - **Tự dọn mỗi lần in bảng** (không cần cron): đạt 100% → `done/<ngày>__<slug>__xong.progress`;
        nguội >120 phút **cả nhịp tim lẫn tiến độ** → `__bo-do`. Ba trạng thái **đang chạy · đã
        xong · chết/bỏ dở** phải tách bạch. `done/` **giữ lại, không xoá** (`worker_board.py --lich-su`).
        Agent còn sống mà tệp bị dọn nhầm → **kéo trả về** thư mục chính.
      - `worker-watchdog.sh` **bỏ qua slug đã có tệp trong `done/`** (nếu không, mỗi lần dọn là một
        loạt 🔴 giả — 25/8 đã bắn oan `bit-loi-tat-quy-trinh` im 115 phút và `fix-shops-assign` im
        121 phút, cả hai đã bàn giao xong), và **ân hạn 25 phút** trước khi kêu "chưa ghi tiến độ".
      - **Giới hạn thật:** worker TỰ hoàn thành thì `TaskStop` trả `Task is not running (status:
        completed)` → **không xoá được khỏi danh sách của giao diện**. Vậy **bảng này là nguồn sự
        thật duy nhất**; đừng hứa với founder là dọn được danh sách kia.
      - `statusLine` (`worker_board.py --statusline`) in 1 dòng `W07 85% · W08 50%` — kênh **tất
        định**, không phụ thuộc model có chịu in bảng hay không.

  (a2) **1 worker = 1 slug CỐ ĐỊNH SUỐT ĐỜI.** Resume / đổi brief / mở rộng scope bao nhiêu lần
      cũng **CẤM đổi tên file progress** — worker vẫn ghi tên cũ nên đổi slug = worker **biến mất**
      **khỏi bảng** dù đang chạy. Muốn đổi tên hiển thị → đổi *nhãn*, không đổi *slug*.
  (c) **Báo cáo tiến độ** = chạy `~/.claude/universal-hooks/bg-progress.sh` (đọc % THẬT từ file,
      tự lấy scope từ `CLAUDE_PROJECT_DIR` — CHỈ đọc file của project hiện tại, không lẫn project khác),
      **CẤM tự ước lượng/vẽ tay %**. Kết quả trả về 1 dòng/worker, ví dụ:
  ```
  A backend parity        ████████████████████  100% ✓
  B iOS app parity        ██████████████░░░░░░   70%
  C rule ...              ████████░░░░░░░░░░░░   40%
  ```
  (d) **ĐỐI CHIẾU mỗi lần báo**: số worker đang chạy (`ListAgents` / transcript `tasks/a*.output`)
      vs số file `.progress`. **Lệch = NÓI NGAY** ("worker X chạy 40 phút chưa ghi tiến độ"), cấm im
      rồi báo bảng thiếu con.
  (e) **Watchdog BẮT BUỘC, không phải tuỳ chọn** — `~/.claude/universal-hooks/worker-watchdog.sh`
      tự chạy nền qua hook `SessionStart`, quét 60s; worker im quá ngưỡng → cảnh báo Telegram **và**
      chèn thẳng vào phiên CLI qua hook `UserPromptSubmit` để orchestrator tự xử lý. Watchdog phải là
      **script shell độc lập**: con điều phối bằng LLM cũng chết vì lỗi API 529 như mọi worker nên
      không tự giám sát được. Chi tiết: `docs/WORKER-WATCHDOG.md` của project.

> **Bài học trả giá** — 24/8: 1 worker treo **106 phút** ở bước chạy test, không ai biết, phát hiện
> muộn. 25/8: **2 worker chạy 1 tiếng mà vô hình** trên bảng (orchestrator đổi slug giữa chừng
> `pipeline-macode` → `fix-ky-hieu-ma-the`, worker vẫn ghi tên cũ) → founder tưởng chúng chết. Luật
> ghi progress đã có sẵn, nhưng **thiếu cơ chế phát hiện khi worker KHÔNG ghi** — lỗ hổng nằm ở
> chính luật, nên (a2)/(d)/(e) là bắt buộc.

## §Trần-worker — tối đa 5 worker/dự án, trùng mảng thì GỬI VÀO worker đang chạy

> Bài học thật (2026-08-25): thả **11 worker song song** trên cùng một dự án → **load average 228–566, có lúc còn ~63 MB RAM trống** (máy 10 nhân/16 GB), **8 shell nền** trong đó **6 shell là vòng `until ps ... sleep` canh cùng một tài nguyên**, **4 `http.server` mồ côi**, 264 tiến trình CoreSimulator; hai worker ghi đè CSS của nhau (mất 1250 dòng, phải khôi phục từ backup) và cache-bust lệch nhau làm giao diện vỡ; hai worker đẩy FTP cùng lúc → 9 tệp lệch. Nguyên văn founder: *"phải có quy định tối đa thôi để máy tao còn làm được việc… chưa kịp thì cho hàng chờ. cái nào cùng worker đang xử lý thì mới add vào worker chứ"*.

1. **Trần 5 worker đồng thời / dự án** (founder chốt 25/8: *"tối đa 4-5 — ưu tiên xong nhanh"*). Vượt → **xếp hàng chờ**, xong một mới thả một. Hook `worker_cap_enforce.py` (PreToolUse `Agent`) đếm worker đang chạy bằng mtime transcript `~/.claude/projects/<dự-án>/*/subagents/agent-*.jsonl` (≤15 phút = đang chạy) và **deny** khi quá trần. Đổi trần: `UNIV3_WORKER_MAX`.
   **Chỉ đếm worker ĐANG LÀM VIỆC**: con **đã trả báo cáo cuối** bị loại khỏi số đếm dù transcript vẫn mới (thông báo nền đánh thức nó trả lời rồi ngủ tiếp). Trước khi sửa, 25/8 xác treo chiếm chỗ làm worker mới bị chặn oan. Hook liệt kê xác treo kèm lệnh **`TaskStop`** — xem §LUẬT SỐ 1.
2. **Việc mới TRÙNG MẢNG với worker đang chạy → `SendMessage` vào chính worker đó, CẤM spawn mới** — nó đã có ngữ cảnh và không tranh tệp với chính mình. Hook trả `ask` khi phát hiện trùng từ khoá. **Chỉ gộp khi ĐỦ CẢ 3 điều kiện** ở §Trần worker §Cây quyết định — thiếu 1 là mở worker mới / vào hàng chờ.
   **ĐỊA CHỈ gửi là MÃ ĐỊNH DANH `a…`** (trường `agentId` trả về lúc thả worker, hoặc bảng worker) — **KHÔNG phải chuỗi trong `<task-notification from="…">`: đó là TÊN LOẠI THỢ, gửi vào là trượt hẳn** (`No agent named 'tho-fulfill' is reachable`, tin rơi mất). Hook `worker_dia_chi_gate.py` (PreToolUse `SendMessage`) chặn tất định, danh sách tên loại thợ đọc từ `agents/*.md` + `agentType` trong `*.meta.json`, không viết cứng.
   **⛔ `SendMessage` KHÔNG PHẢI CỬA SAU ĐỂ NÉ CỔNG.** Giao việc thi công MỚI qua `SendMessage`
   cho worker đang chạy phải qua **đúng những cổng** mà `Agent` phải qua — trước hết là cổng
   NHẠI LẠI (`nhai_lai_gate.py`) và cổng "founder hỏi ≠ founder ra lệnh" (`founder_lenh_gate.py`).
   *Bằng chứng 07/09/2026:* main bị `nhai_lai_gate` chặn đúng khi gọi `Agent` (chưa tra gì),
   quay sang giao 2 việc mới cho worker đang chạy bằng `SendMessage` — **cổng không nổ**, việc
   lọt thẳng. Nguyên nhân đo được: `settings.json` đăng ký hai cổng đó với matcher `'Agent'`
   duy nhất, và trong mã `AGENT_TOOLS = {"Agent","Task"}` trả 0 ngay với mọi tool khác.
   Founder: *"tao tưởng có hook rồi??? tại sao vẫn mắc lỗi"*.
   **Cách vá đã áp dụng:** cả hai cổng thêm matcher `SendMessage` + gọi chung
   `giao_viec_moi.py` — chỉ chặn tin **GIAO VIỆC MỚI** (tiêu đề "THÊM VIỆC / NẠP THÊM /
   VIỆC n —", hoặc động từ thi công kèm brief ≥ 400 ký tự); tin **điều phối / hỏi trạng thái /
   trả lời / khai `VÙNG: CHỈ ĐỌC`** vẫn qua thẳng. ⛔ Cấm chặn bừa mọi `SendMessage` — nghẽn
   điều phối là phản tác dụng.

3. **Một tệp/vùng = một worker tại một thời điểm** (nhất là CSS/JS/template dùng chung). Cần sửa vùng người khác đang giữ → chờ hoặc nhờ chính worker đó.
   **⛔ LUẬT NÀY ĐỨNG TRÊN MỌI NGƯỠNG TẢI.** Điều kiện "chỉ gộp khi worker kia chưa quá 70%" nói về TẢI; điều 3 nói về AN TOÀN cây mã. Trùng vùng mà con kia đã 86% thì **vẫn phải gộp hoặc xếp hàng**, TUYỆT ĐỐI không mở worker mới cho vùng đó.
   *Bài học thật 2026-08-26 (EtsyFulfillChichub, 5 worker chung một cây mã):* điều phối bám ngưỡng 70% nên mở worker mới cho vùng `src/lib/fulfill/` mà worker khác đang giữ ở 86%. Con mới `git add` vơ vét → cuốn phần đang viết dở của con kia vào commit `deeddc1`: `supplier-actions.ts:44` `import { probeSupplierOrderWithRetry }` trong khi `push-verify.ts` chưa export hàm đó → **nhánh main không biên dịch được, lô deploy gãy** (demo/prod thoát vì build ở thư mục trung lập nên không swap), phải vá vội bằng `cafcb38`.
   **Ba cổng tất định đã dựng sau vụ đó** (markdown là xác suất, hook là cổng):
   - `enforce/claude/hooks/worker_cap_enforce.py` — đọc VÙNG TỆP THẬT mỗi worker đang ghi (rút `file_path` của Edit/Write và `git add <tệp>` trong transcript của nó) và **deny** khi việc mới đụng vùng đó. Cửa thoát `worker-cap-ok` **chỉ mở cổng vượt trần, KHÔNG mở cổng trùng vùng** — vượt trần chỉ nặng máy, trùng vùng thì gãy build.
   - `enforce/claude/hooks/git_add_scope_enforce.py` — **deny** `git add -A` · `git add .` · `git add -u` · `git commit -a/-am`; bắt add đích danh từng tệp, kèm danh sách tệp đang thay đổi để tự soi.
   - Cổng `tsc --noEmit` **trước khi push** trong script deploy theo lô: chạy trong git worktree tách rời tại đúng commit sắp đẩy (không phải cây làm việc bẩn), gãy thì lô dừng khi **chưa** push đi đâu. Đo thật: bắt đúng lỗi của `deeddc1` trong 40 giây ở local, thay vì gãy sau 2,5 phút build trên VPS.
   **Hàng chờ có lưu bền** (founder 26/8: *"chặn thì vẫn phải cho vào list chờ để xong còn thả ra"*): mọi việc bị chặn (vượt trần HOẶC trùng vùng) được `enforce/claude/hooks/worker_queue.py` ghi thành vé JSON ở `~/.claude/worker-queue/<dự án>/` **lưu nguyên văn brief**, hiện trên bảng worker, và hook nhắc thả ở đúng ba thời điểm điều phối buộc phải đọc: `SubagentStop` (một con vừa xong), `PreToolUse Agent` (định thả con mới), `UserPromptSubmit`. Hook KHÔNG tự gọi `Agent` **trực tiếp** — nó là tiến trình con. **Đính chính 09/09/2026 (P088, O1.1):** hook **gọi được GIÁN TIẾP** — `tu_tha_ve.py` (commit `45e600ff`) dùng tuỳ chọn hook `asyncRewake` (async, chạy nền, exit code 2 → `enqueueTaskNotificationReminder`) để **đánh thức phiên main NGOÀI LƯỢT**, rồi chính main tự gọi `Agent`. Đã đo end-to-end 3 lượt: vé nằm trong hàng chờ tự chạy, không ai gõ gì. Vòng khép kín cho ô "vé thả được ngay" (S02) là **TỰ ĐỘNG HẲN**; *ghi vé + ép nhìn thấy* vẫn đúng cho các loại việc khác (S08/S11/S20/S21/S25 — xem `viec_state.py`, M0 phiếu P088).

   **Worker bị dừng GIỮA CHỪNG TỰ quay lại hàng chờ — điều phối KHÔNG được phép "tự nhớ"** (founder 27/8, sau 2 lần quên trong một buổi sáng: *"tại sao nó lại treo????? bố mày đã bảo khi nào có chỗ trống thì phải đưa nó vào chờ mà???"*). Lỗ hổng cũ: hàng chờ chỉ nhận việc ở **cổng vào** (lúc `Agent` bị deny vì trùng vùng/vượt trần); worker **đã chạy rồi mới bị `TaskStop`/kill/chết vì lỗi** thì rơi mất sạch — không vé, không ai nhắc. Ca HGT (W20) nằm chết 2 tiếng, trên bảng chỉ còn dòng ma `58% · ❓ không tìm thấy agent`. Nay `enforce/claude/hooks/worker_relapse.py` quét mỗi lượt `UserPromptSubmit`/`SubagentStop`: agent nào harness đã báo kết thúc mà **chưa trả báo cáo cuối** và **chưa đạt 100%** → **tự dựng lại vé** kèm brief NGUYÊN VĂN, mốc %, nhãn việc đang dở, dấu vết commit/stash để lượt sau chạy tiếp chứ không làm lại từ đầu. Đã trả báo cáo cuối / đã 100% / đã có worker khác đang làm lại cùng slug → **KHÔNG sinh vé** (chống vé rác). Nhắc thả **to dần**: vé chờ ≥ 15 phút mà vùng đã trống thì đầu khối đổi thành `⛔ ĐANG BỎ RƠI VIỆC — THẢ NGAY LƯỢT NÀY`, và mỗi vé mang nhãn `✅ THẢ ĐƯỢC NGAY` / `⏸ còn kẹt`.
   **Brief nguyên văn lấy ở đâu**: `.meta.json` của subagent CHỈ có `agentType/description/toolUseId` — KHÔNG có `prompt`. Phải lần về khối `tool_use` Agent trong transcript phiên cha; và **worker có thể do một worker KHÁC thả ra** (`parentAgentId`, `spawnDepth: 2`) nên phải quét cả transcript của worker mẹ, không chỉ tệp phiên.
   **Nguồn phán sống/chết** = `worker_relapse.ids_ket_thuc()`: đọc **đủ cả** transcript phiên cha (tăng dần, có nhớ đệm) và đọc thêm **bảng danh sách subagent** do harness tự chèn (`<id> · <type> · killed|completed · started …`). Bản cũ chỉ đọc **4 MB cuối** và chỉ bắt `<task-notification>`; đo 27/8: hai ca `TaskStop` thật KHÔNG sinh khối đó, còn thông báo của HGT thì đã trôi khỏi 4 MB cuối sau 2 tiếng → cả hai bị coi là *còn sống mãi mãi*. Hệ quả dây chuyền: xác chiếm chỗ trong trần worker, và bảng vẽ dòng ma. **Trạng thái kết thúc là MỘT CHIỀU** — thấy `running` ở bản ghi sau KHÔNG được gỡ kết luận cũ (khối danh sách bị lặp nguyên văn do prompt cache; gỡ theo `running` làm 6 worker đã xong bị coi là còn chạy).
   **Bảng worker**: dòng của worker đã chết phải nằm ở khối RIÊNG `◆ ĐÃ DỪNG giữa chừng — việc chưa xong, PHẢI THẢ LẠI`, kèm cột `✅ có vé chờ` / `⚠ CHƯA CÓ VÉ`; **CẤM vẽ chung khối "đang chạy"** (thanh %, "sống 2h05" làm founder tưởng việc đang cày). Dòng tiến độ không tìm ra agent nào mà nguội > 30 phút → tự đóng vào `done/` (trước là 120 phút — đủ cho một dòng ma sống 2 tiếng).
4. **Worker tự dọn tài nguyên nền của mình** khi xong (`http.server`, iOS Simulator, tiến trình nền). Lưới an toàn: `stale-server-reaper.sh` + `don-may.sh` (macOS) — `install.py` tự cắm LaunchAgent `univ3.stale-server-reaper` + `univ3.don-may` 1800 giây/lần; Linux in dòng crontab. Thứ riêng máy của `don-may.sh` khai ở `~/.claude/don-may/cau-hinh.sh` (mẫu `don-may.cau-hinh.example`).
5. **Cấm mỗi worker tự dựng vòng `until/while ... ps ... sleep`** canh cùng một tài nguyên → dùng khoá dùng chung `templates/deploy_lock.py` (`with deploy_lock("prod", wait=900):`). Khoá theo **TÀI NGUYÊN**, không theo tên script — nên script tên gì cũng bị chặn; khoá tự hết hạn và tự nhả khi chủ chết. Hook trả `ask` cho lệnh vòng canh tự chế.

## §Cây-mã-chung — khi nào worktree riêng, khi nào sửa thẳng cây chung

> Bài học thật (2026-08-27, EtsyFulfillChichub): worker A `git commit --amend` trong cây dùng chung → commit `12f7522` **cuốn theo `docs/NGHIEN-CUU-GMAIL-TU-DONG.md` đang stage của worker B**. Worker C phải bỏ cây chung build ở worktree riêng vì cây chung đang đỏ do WIP của worker D.

**Mặc định: SỬA THẲNG CÂY CHUNG.** Worktree lấy base = commit đầu phiên, nên đụng tệp vừa merge là lệch bản (đã trả giá ở P05x). Worktree chỉ giải quyết *nhiễu*, không giải quyết *tranh tệp* — tranh tệp trị bằng §Trần-worker điều 3.

**BẮT BUỘC worktree riêng (`isolation: worktree`) khi trúng 1 trong 3:**
1. Việc **chỉ tạo tệp MỚI / độc lập** (script, tài liệu, module chưa ai đụng) — không có gì để lệch bản.
2. Việc cần **build / `tsc` / test toàn cây** làm cổng kiểm — cây chung luôn bẩn vì WIP của người khác, chạy ở đó là báo động giả.
3. Việc cần **checkout một commit khác HEAD** (bisect, dựng lại bản cũ, so hai bản).

**CẤM worktree khi**: sửa tệp vừa merge của phiếu khác, hoặc việc cần thấy WIP mới nhất của cây chung.

**Ba luật cứng trên cây chung — có cổng tất định:**
- `git add` **đích danh từng tệp**. `-A` / `.` / `-u` / `commit -a` bị `git_add_scope_enforce.py` **deny**.
- **`git commit` phải NÊU ĐÍCH DANH đường dẫn**: `git commit -m "..." -- <tệp của bạn>`. `git commit` trần lấy **cả index dùng chung** — index là của chung, ai `git add` xong chưa kịp commit là tệp của họ đi theo commit của bạn. *Xảy ra thật 27/8*: commit `50187a6` (worker email) cuốn `scripts/check-prod-demo-parity.sh` mà worker hạ tầng vừa stage. Cùng hook chặn khi index có tệp mà chính lệnh đó không `git add`.
- **CẤM `git commit --amend` khi index có tệp đang stage** — `--amend` gói CẢ index vào commit cũ (đúng kiểu `12f7522`) và viết lại sha nên vé deploy đăng ký theo sha cũ thành vé chết. Thiếu tệp thì tạo **commit MỚI**. Chỉ sửa lời nhắn: `git commit --amend --only -m "..."` (`--only` không kèm đường dẫn = không hót index). Cùng hook chặn.
- **CẤM sửa script đang có lượt chạy dài** (deploy, batch). Bash đọc script top-level theo **offset byte** — file dài ra là lượt đang chạy nhảy vào giữa câu lệnh mới. Script chạy lâu phải **tự ghim**: chép mình ra `/tmp`, `bash -n`, rồi `exec` bản đó (xem `deploy-promote.sh`, `deploy-batch.sh`). Sửa script chưa có cơ chế ghim → **xin khoá `wlock deploy` và kiểm `ps` trước**.

## §Deploy-không-cần-push — kênh vận chuyển code phải nằm TRONG tầm mình

> Bài học thật (2026-08-27): worker push cả `origin` (prod) lẫn `staging` (demo) lên GitHub khi founder chưa duyệt, lý do **có thật**: script deploy lấy code bằng `git fetch origin` + `git reset --hard <sha>`, không push thì deploy không chạy. Luật "không push khi chưa gật" đá nhau với luật kỹ thuật, và **luật thua**.

**Nguyên tắc**: đường vận chuyển code lên máy chủ **KHÔNG được đi qua nơi cần người duyệt**. Nếu deploy bắt buộc phải push public, worker sẽ push — cấm bằng chữ vô ích.

**Cách làm**: bare repo NỘI BỘ ngay trên máy chủ (`git clone --bare --local <app-dir> /root/<dự-án>-deploy.git`), lô deploy `git push <remote-nội-bộ> <sha>:refs/heads/main` qua SSH; build + promote `fetch` từ đó. Rollback theo sha giữ nguyên (bare repo có đủ lịch sử). GitHub trở lại đúng vai **nơi xuất bản** — chỉ push khi founder gõ `push` / `full update`. Cổng tất định: `enforce/claude/hooks/git_push_gate_enforce.py` **deny** `git push` tới remote github/gitlab/bitbucket khi tin nhắn người dùng gần nhất không có từ duyệt (miễn trừ repo SSOT `univ3`).

## §Tự-dọn-rác-worker — hệ thống tự phát hiện, tự hồi phục; founder KHÔNG phải sờ vào

> Founder 27/08/2026, nguyên văn: *"mấy cái như này mày phải **tự động** chứ nhỉ sao cứ để tao phải sờ vào?"* — nói về một con ghi "Build local" mà im 31 phút, và một con đã bị dừng cả tiếng vẫn nằm trên bảng đếm giờ.
> **Nguyên nhân gốc tìm ra:** `worker-watchdog.sh` lúc đó **KHÔNG CHẠY** — nó tự thoát sau 45 phút rảnh (log 26/8 23:05) và chỉ được bật lại ở `SessionStart`. Phiên dài cả ngày thì không ai bật lại → không có gì canh. Nhắc suông cũng vô nghĩa khi con canh đã chết.

**Ba cổng tất định (không phải dòng nhắc):**

1. **MỘT con canh cho CẢ NGÀY — đầu ngày dựng, chốt ngày giết.** Founder 27/08/2026, nguyên văn: *"mỗi lần tao gõ thế nó tạo ra 100 con chó à? bố mày sẽ có **đầu-ngày** và **chốt-ngày**… đầu-ngày thì mới tạo 1 con chó, canh cả ngày. còn chốt-ngày thì sẽ giết."*
   - **Dựng**: lệnh `/dau-ngay` (`/sod`) chạy `worker-watchdog.sh start`, dán PID ra cho founder thấy.
   - **Giết**: lệnh `/chot-ngay` (`/eod`) **bước 5, sau khi đã gửi báo cáo**, chạy `worker-watchdog.sh stop` rồi verify `status` = `KHÔNG CHẠY`. Giết sớm giữa ngày = mù.
   - **Không tự thoát nữa**: `WATCHDOG_IDLE_EXIT_MIN` mặc định **0**. Để 45 phút thì tối 26/8 hết worker là con canh tự chết, sáng 27/8 năm worker chạy không có gì canh, một con treo 51 phút không ai biết.
   - **Cờ tắt chỉ sống một ngày**: `stop` ghi **ngày VN** vào `~/.claude/worker-watchdog.OFF`; sang ngày mới cờ tự hết hiệu lực → `ensure` dựng lại. Chốt ngày xong quên gõ đầu ngày cũng không hở.
   - **`ensure` là lưới an toàn, KHÔNG phải máy đẻ**: vẫn gọi ở `SessionStart` + `UserPromptSubmit` + `PreToolUse:Agent` để vá khi con canh chết bất đắc kỳ tử, nhưng **idempotent tuyệt đối** — 3 lớp chặn (cờ tắt còn hiệu lực · khoá chính còn chủ sống · khoá SINH `mkdir` nguyên tử chặn hai `ensure` song song). Đo thật 27/8: 20 lần `ensure` liên tiếp = **0 giây, đúng 1 tiến trình**; 20 lần **song song** khi chưa có con nào = **đúng 1 tiến trình**.
   - **`stop` phải giết dứt điểm**: vòng lặp nằm trong `sleep 60` nên `kill` thường trễ tới 1 phút → `stop` chờ có hạn 8 giây rồi `kill -9`, và in `✅ Con canh đã tắt hẳn` / `⚠️ CHƯA tắt được`.
2. **Watchdog TỰ NHẢ khoá**, không chỉ nhắc (`tu_nha_khoa`, chạy mỗi vòng 60 giây):
   - chủ khoá **đã chết** → nhả ngay (trước đây `wlock` chỉ thu hồi khi có ai gọi `acquire`/`status`; không ai gọi thì hàng chờ đứng im vô hạn);
   - chủ khoá **còn sống** nhưng worker giữ nó có **agent im VÀ tệp tiến độ không nhích** ≥ `HARD_RELEASE_MIN` (45 phút) → nhả.
   - **Ngưỡng đặt theo số đo thật, không đoán**: `next build` trên VPS 235–266 giây (max 4 phút 26); cả lô build + promote demo + prod 3–25 phút. 45 phút ≈ gấp 10 lần bước dài nhất → không giết oan.
   - **CỐ Ý KHÔNG GIẾT AGENT**: giết nửa chừng để lại cây git đỏ làm cả team vướng (đã xảy ra sáng 27/8). Chỉ trả **tài nguyên**; code và công sức của worker không bị đụng. Mỗi lần tự xử ghi log + đẩy vào hàng đợi cảnh báo CLI + Telegram, nói rõ nhả cái gì và vì sao — không có chuyện "tự nhiên mất worker".
4. **SỔ TRẠNG THÁI KHÔNG PHẢI SỰ THẬT — mọi chỗ ĐỌC phải đối chiếu AGENT SỐNG.** Sổ (hàng chờ, vùng đang giữ, tệp `.progress`, vé `wlock`, khoá `.lock`) được GHI ở một sự kiện; sự kiện DỌN trượt một lần là sổ nói dối vĩnh viễn — 27/8: vé W130 nằm hàng chờ trong khi chính nó đang chạy 84% (bảng vẽ hai lần), vé bị chặn vì "W127 giữ vùng" trong khi W127 chết từ lâu, tệp `.progress` mồ côi đếm giờ như worker sống. **Cấm thêm lệnh dọn thủ công — phép dọn phải nằm NGAY TRONG hàm đọc** (`worker_queue.doc()` gọi `doi_soat()`; `khoa_dang_giu`/`ve_xep_hang` hỏi PID còn sống). Nhận diện việc bằng **SỐ VÉ W### hoặc slug**, KHÔNG so brief nguyên văn (brief luôn bị sửa lúc thả). Gỡ vé = đổi đuôi `.da-chay`, KHÔNG xoá. Không đo được agent sống -> KHÔNG dọn gì (thà thừa còn hơn xoá oan).
3. **Bảng tự sạch xác treo** — agent mà **harness đã báo kết thúc** chỉ còn hiện `XAC_HIEN_PHUT` (10 phút) rồi biến mất, và dòng tiến độ của nó được đóng sang `done/…__bo-do`. Trước đây dùng chung hằng `NGUOI_HAN_PHUT` = 120 phút với việc dọn tệp tiến độ nên xác nằm lại 2 tiếng. Hai hằng phải TÁCH: hạ hằng dọn tệp là dọn oan worker đang cày.

**Phân biệt "đang chờ có lý do" với "treo" — bằng tín hiệu thật, không bằng mỗi đồng hồ:** tiến trình chủ còn sống không? tệp tiến độ có nhích? transcript agent có mới? khoá đang chờ có chủ hợp lệ? Thiếu mọi mốc đo được thì **để yên**, không đoán.

## §Đọc-nguồn-lúc-in — CẤM phán trạng thái bằng dữ liệu nhớ sẵn

> Founder 27/08/2026, nguyên văn: *"sao sửa qua bao nhiêu lần RRI-T đủ kiểu giờ vẫn đéo có cơ chế nhận ra lô kết thúc là thế buồi nào?? con chó canh của tao đâu????"*

**LUẬT:** mọi câu kết luận về trạng thái (bảng worker, cảnh báo watchdog, dòng `➜`, tin Telegram) **phải đọc lại nguồn tất định NGAY TẠI THỜI ĐIỂM IN**. Cấm in lại chuỗi/PID/mốc đã chụp lúc tạo bản ghi, cấm suy ra trạng thái từ một phần tín hiệu.

**Ca cảnh cáo (27/08/2026):** W166 · W167 · W169 ngồi chờ lô deploy **hơn một tiếng**. Số đo thật lúc đó: `chain.log` ghi lô cuối **xong 17:37:52** · `ps` không còn `next build` nào · khoá deploy đã nhả · demo đã lên `d64c91f`. Suốt thời gian đó bảng in *"➜ 5 worker đang chạy bình thường, KHÔNG cần can thiệp"*. Gốc: `chain.log`/`deploy-queue` — cuốn sổ DUY NHẤT ghi "lô nào xong lúc nào" — **không file nào trong hệ canh đọc tới**; ba nguồn còn lại đều IM khi worker chờ một thứ đã xong nên hệ kết luận "bình thường".

**Cách làm đúng — một hàm, năm nguồn:** `~/.claude/universal-hooks/worker_state.py` là nơi DUY NHẤT trả trạng thái, đọc đủ ① khoá `wlock` + PID còn sống ② vé xếp hàng `wlock` ③ `deploy-queue/<proj>/{pending,done}` + `chain.log` ④ tệp `.progress` (mtime) ⑤ tiến trình build/deploy thật (`ps`). Watchdog · `wlock.sh` · bảng worker đều **gọi hàm đó**, không tự suy.

- **Ngưỡng theo VIỆC, không theo phút cứng.** Một lượt lô build+deploy dự án này mất **6–24 phút** (số đo `chain.log` 27/8). Chờ 10 phút **trong lúc** lô đang chạy = bình thường, cấm kêu. Chờ quá 2 phút **sau khi** lô đã xong = BẤT THƯỜNG, báo động ngay.
- **Câu chữ phải nói HÀNH ĐỘNG.** Thay `KHÔNG cần can thiệp` bằng `W166 · W167 · W169 đang chờ lô 20260827-171328 — lô này ĐÃ XONG lúc 17:37, khoá đã nhả → CẦN CAN THIỆP: đánh thức bằng SendMessage`. Kết luận (`chờ cái đã xong`) luôn **đè** triệu chứng (`im lặng`), không để triệu chứng in chồng lên.
- **Cảnh báo ghi TÊN TÀI NGUYÊN, không ghi mô tả chủ khoá.** `wlock.sh` từng nhồi nguyên chuỗi *"PID 1234 còn sống"* vào bản ghi rồi đóng băng; hàng giờ sau bảng vẫn giục đi kill một cái xác. Người in tự gọi `worker_state.chu_khoa(res)`.
- **Chống tái phát bằng lệnh chạy được**, không bằng lời hứa: `bash ~/.claude/universal-hooks/worker-watchdog.sh tu-kiem` · `python3 ~/.claude/universal-hooks/worker_state.py --tu-kiem` · `python3 ~/.claude/universal-hooks/worker_board.py --tu-kiem`. Sửa hệ canh mà không chạy đủ ba lệnh này = chưa xong việc.

### §Sổ-cái-VIỆC (M0-M2, phiếu P088, 09/09/2026) — khác tầng với `worker_state.py`

`worker_state.py` (mục trên) trả trạng thái **WORKER** (khoá, lô deploy, tiến trình). `viec_state.py`
(`~/.claude/universal-hooks/viec_state.py`) trả trạng thái **VIỆC** — kể cả việc CHƯA thành worker (vé
hàng chờ) và việc đã xong mà chưa dọn (xác treo `S12`, cháu chết không báo cáo `S25`). Root cause chữa:
trạng thái một việc rải trên 6+ cuốn sổ, không nơi nào trả lời "việc này đang ở đâu, ai phải đẩy, đẩy bằng
lệnh gì" trong MỘT câu.

- **Một hàm, chín nguồn, GỌI LẠI không TÍNH LẠI**: `trang_thai_viec(cwd)` hỏi lại đúng module chủ của từng
  nguồn (`worker_queue`, `worker_state`, `worker_cap_enforce.running_workers`, `worker_chau.canh_bao`,
  `deploy_ban_giao_gate.quet`) — cấm parse lại tệp vé, cấm `git log` tính lại, cấm quét `spawnDepth` lần
  hai. Mỗi bản ghi có đúng 5 trường: `ma · trang_thai (S00-S28) · ai_day · lenh_day · im_bao_lau`.
- **Ngân sách hot-path**: `ve_de_sau_gate.py` (chặn `Stop` mỗi lượt) gọi `trang_thai_viec(nang=False,
  sieu_nhe=True)` — bỏ hai nguồn đo được là NẶNG (`worker_chau.quet()` ~1,7 giây quét sâu transcript cháu;
  `deploy_ban_giao_gate.quet()` ~0,1 giây chạy `git log`) và cả hai nguồn vừa (`cho_cai_da_xong`/
  `ve_deploy`, ~45ms cộng lại) — giữ đúng nguồn nặng nhất-đáng-giá-nhất (`running_workers`, cho `S12`,
  ~75ms). `--json`/`--ban-do`/`tu_tha_ve.py` polling nền dùng `nang=True` (đầy đủ, không chặn lượt).
- **`TaskStop` tự động (S12) đi qua CỔNG CHỨNG MINH M5**, không phải mặc định bật — xem mục "Vì sao TRƯỚC
  ĐÂY không có hook tự kill" bên trên. Cài ở `tu_tha_ve.py`; tắt khẩn `UNIV3_TU_THA_TASKSTOP_TAT=1`.
- **Con canh tự chạy lô deploy (demo + prod)**: `worker-watchdog.sh::p088_tu_dong_deploy()`, mặc định
  **TẮT** (`UNIV3_WATCHDOG_AUTO_DEPLOY=1` để bật — cờ an toàn, founder tự bật sau khi soát code). Chỉ GỌI
  `scripts/deploy-batch.sh run` theo đúng cách một người gõ tay đã làm — **không sửa** script deploy. Gap
  đã biết (chưa giải quyết trong lượt 09/09): `deploy-batch.sh` chạy cổng parity prod≡demo SAU KHI đã
  promote prod, không phải TRƯỚC như lý tưởng — xem Debate Log phiếu P088 mục O2.1 trước khi bật cờ.
- **Nhả khoá theo VIỆC** (không đợi 45 phút cứng): `worker-watchdog.sh::tu_nha_khoa()` thêm nhánh — khoá
  `deploy`/`build` còn chủ sống nhưng `chain.log` đã ghi lô (sau mốc acquire) XONG và `ps` không còn tiến
  trình build/deploy thật → nhả ngay (đệm 120 giây). Ngưỡng 45 phút GIỮ NGUYÊN làm lưới cuối.

## §QA-tập-trung — tách THI CÔNG khỏi KIỂM THỬ (bắt buộc khi nhiều worker cùng đụng UI)

> Bài học thật (2026-08-24): 4 worker UI chạy song song, brief con nào cũng ghi "verify bằng iOS Simulator, test 1 device rộng + 1 device vừa" → **5 device booted cùng lúc, 708 tiến trình CoreSimulator, load average 566, còn ~63MB RAM trống**, máy founder gần đơ. Lỗi KHÔNG nằm ở việc dùng simulator mà ở chỗ **mỗi worker tự boot một con**.

1. Worker **THI CÔNG KHÔNG boot iOS Simulator** (cũng không mở trình duyệt). Nó tự xác minh bằng thứ đọc được: đọc lại `file:dòng` vừa sửa · `grep` · đếm bằng script · tính contrast ratio bằng script · đọc thẳng giá trị CSS (`font-size`, `padding`, `opacity`). Brief BẮT BUỘC ghi nguyên câu: **"KHÔNG boot iOS Simulator — kết thúc bằng mục CẦN QA KIỂM"**.
2. Worker thi công kết thúc báo cáo bằng mục **"CẦN QA KIỂM"**: **trang nào** (đường dẫn/URL) · **soi điểm gì** (đo cái gì, ngưỡng bao nhiêu) · **so với ảnh bằng chứng nào**.
3. Orchestrator gom mọi mục "CẦN QA KIỂM" → spawn **ĐÚNG 1 worker QA** chạy **sau cùng**: boot **ĐÚNG 1 device**, kiểm toàn bộ các mảng **trong một lượt**, đọc ảnh chụp bằng tool `Read`.
4. Cần so 2 cỡ màn → **TUẦN TỰ**: `xcrun simctl shutdown <udid-1>` xong mới boot con thứ hai. **CẤM boot song song.**
5. QA xong → `xcrun simctl shutdown` + tắt http server nền, không bỏ lại tiến trình rác.
6. **Ép tất định**: hook `enforce/claude/hooks/sim_one_device_enforce.py` (PreToolUse `Bash`) — đang có ≥1 device `agent-*` ở trạng thái Booted mà lệnh lại boot thêm con nữa → `permissionDecision:"deny"` kèm cách dùng lại device đang chạy. Boot lại đúng con đang booted / `shutdown` / `screenshot` vẫn cho qua. Cửa thoát khi founder đã đồng ý chạy song song: thêm `SIM_MULTI_OK=1` vào đầu lệnh.

KHÔNG đổi: verify UI mobile vẫn **BẮT BUỘC** bằng Safari trong iOS Simulator, vẫn **CẤM** kết luận bằng chrome-devtools phone view. Thay đổi duy nhất là **ai được boot và boot bao nhiêu con** (đáp án: chỉ QA, đúng 1 con). How-to: skill **mobile-webapp** §15.

## §Trần worker song song + xếp hàng tài nguyên dùng chung

- **Tối đa 5 worker song song / 1 project.** Vượt trần thì **vào hàng chờ**, không thả thêm. (Founder chốt 25/8 khi được hỏi thẳng: *"Tối đa 4-5 — ưu tiên xong nhanh"* — sau khi 11 con đẩy load average lên 566, chỉ còn ~63 MB RAM trống trên máy 10 nhân/16 GB. Máy yếu hoặc việc nặng build/simulator thì hạ bằng `UNIV3_WORKER_MAX`.) 8 con song song = mỗi con chậm **gấp 3-5 lần** vì giành cùng một bộ tài nguyên (RAM, cổng 3000, browser, DB dev) — làm 20 phút việc thật mà mất 1-2 tiếng.
- **Ép tất định**: hook `enforce/claude/hooks/worker_cap_enforce.py` — PreToolUse `Agent` đếm worker đang chạy của dự án (mtime transcript `~/.claude/projects/<dự-án>/*/subagents/agent-*.jsonl`, ≤15 phút = đang chạy, **trừ con đã trả báo cáo cuối** — xem §LUẬT SỐ 1) → **deny** khi quá trần, kèm bảng worker đang chạy để gửi việc vào đúng con; **deny** khi việc mới ghi vào VÙNG TỆP mà worker khác đang giữ; **ask** khi việc mới trùng mảng với một worker đang chạy (ép đúng dòng đầu của bảng dưới). PreToolUse `Bash` trả **ask** cho vòng canh tự chế `until/while … ps … sleep` → chỉ sang `wlock.sh`. Cửa thoát khi founder đã đồng ý: thêm `worker-cap-ok` vào `description`/`prompt`/lệnh.
  - **Vùng cắt tới TẦNG MẢNG CON, không dừng ở nhánh thư viện.** `src/lib/drive` ≠ `src/lib/pipeline`
    ≠ `src/lib/fulfill`; `src/app/api/orders` ≠ `src/app/api/fulfill`. Đoạn đường dẫn chỉ là hộp chứa
    (`src`, `lib`, `app`, `api`, `components`, nhóm route `(dashboard)`, đoạn động `[id]`…) thì đi sâu
    thêm một tầng nữa mới ra vùng thật.
    > Bài học 26/8: cắt ở `src/lib` làm một việc sửa nhánh **drive** bị chặn vì worker khác đang sửa
    > nhánh **pipeline** — hai thư mục không đụng file nào của nhau — việc nằm chờ vô ích **21 phút**.
  - **Tệp dùng chung tầng trên = vùng `dung-chung`, ai đụng cũng chặn nhau**: tệp nằm thẳng trong hộp
    chứa (`src/lib/db.ts`, `src/lib/datetime.ts`, `src/types/*`, `src/app/globals.css`, layout gốc,
    `packages/<gói>`). Đây mới là chỗ đáng chặn.
  - **Vùng của việc MỚI KHÔNG suy từ chữ trong brief — brief phải KHAI theo khuôn.**
    Từ 07/09/2026 (founder chốt qua AskUserQuestion: *"Bắt brief khai vùng theo khuôn cố định,
    cấm đoán hẳn"*) mọi brief mở đầu bằng ba dòng:
    `GHI: <đường dẫn sẽ ghi, cách nhau bằng khoảng trắng>` · `ĐỌC: <chỗ chỉ đọc>` ·
    `TÀI NGUYÊN: <db-dev · db-that · dev-3000 · prisma · build>`.
    Thiếu dòng `GHI:` → **cổng chặn ngay** kèm ví dụ dán được (vé đã nằm hàng chờ từ trước
    khuôn mới vẫn thả lại được — tương thích ngược). Thuần đọc → `GHI: -`; không giành tài
    nguyên → `TÀI NGUYÊN: -`. Dòng `ĐỌC:` **không bao giờ** tính là tranh chấp.
    Nhánh "suy vùng từ văn xuôi" đã BỎ HẲN: trong một buổi 07/09 nó bắt phải vá bốn lần
    (khai giữa dòng · dòng lệnh CHẠY bị tính là GHI · thư mục nhật ký gộp với thư mục hook ·
    phần VÍ DỤ nhắc tên thư mục worker khác đang giữ) — lần thứ tư chặn oan đúng brief đi vá nó.
  - *(lịch sử, đã gỡ)* Thứ tự cũ: (a) brief tự khai dòng
    `VÙNG: <đường dẫn sẽ ghi>` → tin tuyệt đối; (b) không khai → rút đường dẫn trong brief nhưng **bỏ
    những dòng nêu ví dụ / dặn "KHÔNG đụng"**; (c) không suy được → **cho qua**, không chặn oan.
    Việc chỉ sửa công cụ trong `~/.claude/universal-hooks/` mang vùng riêng `tools/univ3`, **không bao
    giờ** coi là trùng vùng với kho mã dự án (26/8 từng chặn oan đúng ca này).
### HAI loại "gộp" — KHÁC HẲN NHAU, cấm lẫn lộn

> Chính chỗ lẫn này làm founder phải đợi 2 tiếng (25/8).

| | **Loại 1 — GỘP CONTEXT** | **Loại 2 — GỘP TÀI NGUYÊN** |
|---|---|---|
| Gộp cái gì | Việc mới **nhét vào worker đang chạy** | Worker chạy **độc lập**, chỉ **khâu build/deploy** xếp chung 1 lượt |
| Vì sao | Worker đó đã nắm sẵn context vùng file | Đỡ tốn thời gian chờ build/deploy chồng nhau |
| Dính context nhau? | Có | **KHÔNG** |
| Điều kiện | ĐỦ CẢ 3 (bảng dưới) | Mặc định, áp cho **mọi** worker |

**Loại 1 — điều kiện ĐỦ CẢ 3, thiếu 1 là KHÔNG gộp:**

| # | Điều kiện |
|---|---|
| 1 | Cùng chủ đề / cùng vùng file với worker đang chạy |
| 2 | Worker đó **chưa quá 70%** (đã 85% = sắp chốt → để nó xong, việc mới đi chỗ khác) |
| 3 | Worker đó **chưa gộp quá 2 lần** |

Ngoài ra: **cấm trộn** việc khảo sát / tích hợp dài với việc sửa lỗi gấp — việc dài nuốt việc gấp.

**Loại 2 — mặc định MỚI:** worker **KHÔNG tự deploy**; nó chỉ commit + push + **đăng ký hàng chờ deploy**.
Một worker `deploy-theo-nhom` build **1 lượt** → demo → prod cho cả nhóm.

#### Lệnh cụ thể (đo thật 25/8: 24 lượt build → 3, VPS bận 120 phút → 15 phút)

| Ai | Làm gì |
|---|---|
| **Worker** (mọi worker) | `git commit` **kèm trailer `Worker: <slug>`** → `git push` → `deploy-batch.sh register --owner=<slug> --smoke=<1 route của mảng mình>` → **DỪNG**. Cấm `deploy-remote.sh`, cấm `ssh … deploy-zd.sh`. |
| **Điều phối** | `deploy-batch.sh run` (gom theo cửa sổ 12 phút **hoặc** đủ 4 vé, cái nào trước) · `run --now` khi việc gấp chặn team. |

Trailer `Worker:` là thứ duy nhất cho phép quy commit gãy về đúng worker khi vé đã dọn — **thiếu trailer là mất dấu**.
Lô tự truy thủ phạm (`git blame` dòng lỗi → commit → worker; không map được thì nhị phân bằng `tsc --noEmit` trong worktree riêng) và **tự cô lập** (`git revert` commit hỏng, phần còn lại vẫn lên) — 1 commit hỏng KHÔNG chặn cả nhóm.

#### 3 lỗ hổng "chồng lớp" đã trả giá thật — đừng lặp lại

| Lỗ | Bằng chứng | Luật |
|---|---|---|
| **Sửa script deploy lúc nó ĐANG chạy** | Bash đọc script theo từng đoạn (nhớ offset byte) → đọc nửa cũ nửa mới: `syntax error line 35`, rồi `RC: unbound variable` → **build xong 13 GB RAM mà không swap** | Script deploy phải **tự chép ra bản snapshot rồi `exec` bản đó** (bất biến suốt lượt chạy) + `bash -n` trước khi chạy. Không dựa vào việc người ta "nhớ không sửa". |
| **Khoá kiểu "tồn tại file"** | Worker dọn dẹp `rm` luôn `/var/lock/*.lock` vì `ps` không thấy ai chạy → khoá biến mất | Khoá phải canh **PID + lease** (như `wlock.sh`), và sau khi cầm khoá vẫn phải **soi tiến trình thật** trước khi build. File khoá là thứ yếu. |
| **Hai lớp khoá ĐỘC LẬP** | Khoá local và khoá trên máy chủ không biết nhau → ai `ssh` vào gõ tay `pnpm build` là lọt | **Xâu chuỗi**, mỗi tầng đúng **1 cửa**: local `deploy-batch` → máy chủ `deploy-zd`. Tầng máy chủ là **trọng tài cuối** và phải phát hiện được cả build không đi qua tầng trên. |

Ngưỡng RAM chặn build phải lấy từ **số đo đỉnh thật** (mỗi lượt build tự ghi lại), không đặt bằng cảm giác — đo được 1 lượt `next build` ăn **13 GB / 15,6 GB** máy chủ, nên **2 build song song là bất khả thi**, phải xếp hàng.


### Cây quyết định khi có job mới (xét ĐÚNG thứ tự này)

| Bước | Hỏi | Nếu ĐÚNG |
|---|---|---|
| 1 | Job **đang chặn team làm việc** (Phương/Hậu không thao tác được)? | **Chen lên đầu, thả ngay** — kể cả đang đủ trần. Nói rõ với founder đang tạm gác việc nào. |
| 2 | Cùng chủ đề với worker đang chạy **VÀ** con đó <70% **VÀ** chưa gộp quá 2 lần? | **Gộp context** (loại 1) vào worker đó bằng `SendMessage`. |
| 3 | Còn chỗ dưới trần 5 worker? | **Mở worker mới NGAY** (xin số `wseq` trước). |
| 4 | Đã đủ 5 worker? | **Vào hàng chờ** — và **PHẢI nói với founder**: đang xếp hàng, xếp sau việc gì, dự kiến khi nào tới lượt. Cấm thả lén vượt trần, cấm im lặng. |
| 5 | (mọi nhánh trên) Đến khâu build/deploy | Đi qua **gộp tài nguyên** (loại 2) — **không con nào tự deploy riêng**. |

> **Điểm dễ hiểu nhầm:** "không thuộc nhóm nào" **KHÔNG** đồng nghĩa "phải xếp hàng".
> Xếp hàng **chỉ** xảy ra khi **đủ trần 5 worker**. Việc độc lập mà còn chỗ thì **chạy song song
> ngay** — đó mới là nhanh nhất.
- **Tài nguyên dùng chung PHẢI xin khoá trước khi dùng** — `~/.claude/universal-hooks/wlock.sh` (nguồn: `enforce/claude/hooks/wlock.sh`): hàng đợi + ưu tiên `urgent|normal|low` + timeout (mặc định 15 phút, hết giờ trả **mã 75** chứ không treo) + tự thu hồi khoá mồ côi (chủ khoá chết / lease hết hạn) + chờ lâu thì đẩy cảnh báo vào phiên CLI qua hàng đợi `worker-alerts` của watchdog.
  5 loại khoá: `build` (1 build tại 1 thời điểm — 2 build chồng = OOM) · `devserver` (cổng 3000) · `browser` (Playwright / chrome-devtools) · `dbdev` (ghi DB dev) · `deploy`.

  ```bash
  W=~/.claude/universal-hooks/wlock.sh; ME=<slug worker>
  bash $W wait build --owner=$ME --pid=$$ --timeout=900 || exit 75   # NẰM CHỜ tới lượt
  trap 'bash '"$W"' release build --owner='"$ME"' >/dev/null' EXIT INT TERM
  # hoặc gọn 1 dòng, tự nhả kể cả khi lệnh lỗi:
  bash $W run build --owner=$ME -- pnpm build
  ```

  - **`wlock wait` là lệnh chờ khoá DUY NHẤT được dùng.** Nó tự nằm chờ tới lượt, in tiến trình
    chờ định kỳ (chờ ai, đứng thứ mấy, còn bao lâu) và chỉ trả về khi đã cầm khoá hoặc hết giờ.
    **CẤM worker tự viết `until … acquire … sleep 60 … done`, và CẤM dò chữ trong output.**
    Thứ duy nhất được xét là **mã thoát**: `0` = đã cầm khoá · `75` = hết giờ chờ · `2` = sai cú pháp.
    > Bài học 26/8: worker `import-pod-folder` **được cấp khoá ngay lần 1** (wlock in
    > `ĐÃ CẤP khoá 'deploy'…`) nhưng vòng lặp tự chế dò chữ tiếng Anh `acquired|ok|granted`
    > → không khớp → tưởng trượt → `sleep 60` → xin lại → **xếp hàng sau chính mình**, kẹt 15
    > phút và chặn 2 worker phía sau. Worker `man-khoa-nut` lặp y hệt, giữ khoá 15 phút trong
    > lúc đang ngủ.
  - **Xin/chờ khoá mà CHÍNH MÌNH đang giữ → wlock trả `0` NGAY** kèm cảnh báo "đang giữ rồi,
    dùng luôn" (áp cho cả `acquire`, `wait` và `run`). Không bao giờ còn cảnh tự xếp hàng sau
    chính mình. Nhả đúng **một lần** khi xong.
  - Hook `worker_cap_enforce.py` (PreToolUse `Bash`) nhận diện vòng lặp tự chế quanh `wlock`
    và kiểu dò chữ `acquired|granted|ĐÃ CẤP` → nhắc chuyển sang `wlock wait`.

  - **CẤM build vào thư mục dist DÙNG CHUNG — luôn qua script an toàn.** `next build` **xoá sạch** thư mục dist trước khi ghi, nên một lượt `pnpm build` trần ở thư mục gốc giết ngay dev server của worker khác (đo 25/8 trên EtsyFulfillChichub: `/login` từ 200 → treo sau **15 giây**, log `ENOENT ... routes-manifest.json`; kèm hàng loạt `Cannot find module './9607.js'` mà worker tưởng là lỗi code). Worker phải gọi **script build an toàn của project** (`pnpm build` được bọc sẵn) hoặc chỉ định thư mục riêng `NEXT_DIST_DIR=.next-<slug>`.
  - **Project chưa có cổng chặn thì DỰNG cổng ở tầng cấu hình build, đừng chỉ viết luật** — luật markdown là xác suất, cấu hình là tất định. Với Next.js: `distDir` chọn theo **phase** (`phase-production-build` đổi mặc định sang `.next-build`; `phase-development-server` và `phase-production-server` giữ `.next`). Chỉ đổi phase BUILD là bắt buộc, vì PM2 trên VPS chạy `pnpm start` **không** set `NEXT_DIST_DIR` — đổi cả phase chạy sẽ làm gãy prod. Mọi script deploy đều khai báo `NEXT_DIST_DIR` tường minh nên env luôn thắng mặc định → deploy không đổi hành vi.
  - Acquire/release ở **2 lệnh Bash khác nhau** (agent) → bắt buộc truyền `--owner=<slug>` cả hai lần và `--pid=none`; lease tự hết hạn sau 20 phút, gia hạn bằng `wlock renew`.
  - Điều phối viên nhìn toàn cảnh bằng **`bash $W status`**: ai giữ khoá gì, từ bao giờ, PID còn sống không, ai đang xếp hàng.

- **TỆP DÙNG CHUNG phải sửa theo lối TẢI-VỀ → SỬA → ĐẨY — CẤM đẩy bản trong kho mã đè lên bản đang chạy.** Tối thiểu: `.htaccess`, `.user.ini`, `index.html`, `order.php`, `assemble.py`, `clone-cart.js`, `longchau-redesign.css`, `timber.js` và **mọi tệp cấu hình máy chủ** (nối thêm bằng `UNIV3_SHARED_FILES`).
  > Bài học 25/8, 11:53: worker sửa link `/pages/lien-he` đẩy bản `.htaccess` trong kho mã đè lên bản đang chạy → xoá sạch 4 luật chặn của worker bảo mật: `/admin.php` (trang quản trị cũ, **không có chống dò mật khẩu**) và `/admin-config.php` (chứa chuỗi mã hoá mật khẩu) từ **403 → 200, mở với cả Internet**; `/orders-status.json`, `/fetcher.php`, `/count.php` mất luật chặn. Mật khẩu không lộ chỉ vì PHP vẫn thực thi nên thân phản hồi 0 byte — **ăn may, không phải thiết kế**. `ps aux | grep ftp_push` KHÔNG bắt được vì worker kia dùng script tên riêng.
  - **Ép tất định**: hook `enforce/claude/hooks/shared_file_deploy_enforce.py` (PreToolUse `Bash`) tự ghi nhật ký mỗi lần TẢI VỀ, rồi khi thấy lệnh ĐẨY: **deny** nếu tệp dùng chung được nêu đích danh — hoặc là tệp **cấu hình máy chủ** nằm trong thư mục sắp đẩy — mà chưa từng tải về, hoặc bản sắp đẩy cũ hơn lần tải; **ask** khi đẩy cả thư mục build (chỉ có tệp dùng chung loại thường) hoặc khi lệnh không nêu tệp nào. Nhận diện theo **hành vi** (`lftp/ftp/scp/rsync/curl -T/aws s3/wrangler` + script tên kiểu deploy), không theo một tên script cố định. Cửa thoát: thêm `shared-ok` vào lệnh.
  - `templates/deploy_guard.py` in **cảnh báo tệp dùng chung** ngay trong lượt đẩy (ngoài phần chặn `.env`/`docs/`/`*.bak-*`).
- **VERIFY LẠI PROD Ở CUỐI PHIÊN, verify giữa chừng KHÔNG tính** — worker khác có thể đè lên ngay sau đó (đúng ca `.htaccess`, chỉ bị phát hiện nhờ verify lại). Hook trên bắt cả `Stop`/`SubagentStop`: phiên có đẩy mà chưa gọi HTTP tới prod sau lần đẩy cuối → **chặn đóng phiên đúng một lần** kèm lệnh `curl` mẫu (nhớ kiểm cả các đường dẫn ĐÁNG LẼ vẫn phải 403).
- **Hằng số dùng chung có đúng MỘT chủ.** Ví dụ `VERSION` trong `assemble.py` bị hai worker ghi qua ghi lại, một lần **lùi version về giá trị cũ** (còn dấu vết `assemble.py.bak-cartrevert`) → cache-bust lệch, trang lấy CSS cũ. Ai không phải chủ thì `SendMessage` nhờ chủ đổi, không tự sửa.

> **Bài học trả giá — 25/8**: 8 worker song song trên 1 máy → build đè `.next` của dev server **3 lần** (worker khác chết ngay, `/api/auth` trả 500, phải dựng lại + làm lại từ đầu); **2 build chồng nhau gây OOM 3 lần** (mỗi build 6.6-8.6 GB / máy 15 GB); browser tranh nhau ("browser is already running") → có con kẹt **1h37** ở khâu chụp ảnh; 1 worker bị **chồng 5 đợt việc** → chạy 1h37 chưa xong. Luật "song song hoá" đã có sẵn nhưng **thiếu trần số + thiếu khoá tài nguyên** — nên trần 5 và `wlock` là bắt buộc, không phải khuyến nghị.

## Re-take loop (vòng lặp chuẩn)
1. **Spawn** worker (brief đầy đủ như trên).
2. **Thẩm định** output theo **rubric/checklist ĐÃ VIẾT RA TRƯỚC khi spawn** — không chấm cảm tính.
3. Sai/thiếu → tiếp tục **ĐÚNG agent đó** (theo tên/ID) với chỉ dẫn sửa cụ thể — agent giữ context cũ; KHÔNG spawn con mới làm lại từ đầu (mất context = lặp lại lỗi).
4. Đạt → nhận kết quả, chuyển worker kế.

## Flow Kỹ sư ↔ Thợ xây (role-split debate — dùng khi việc cần PLAN trước khi code)
> 2 vai có tên: `ki-su` (Kỹ sư, mù code, viết phiếu) và `tho-xay` (Thợ xây, thấy code, phản biện + thi công). Xem `agents/Ki-su.md`, `agents/Tho-xay.md`. Chủ nhà = user (luôn). Orchestrator = phiên chính, làm người đưa thư.

1. **Chủ nhà** chọn 1 việc → orchestrator spawn **Ki-su** viết phiếu `docs/ticket/P###.md` (chỉ từ docs, mọi giả định code → Task 0 Anchor).
2. Orchestrator spawn **Tho-xay** CHALLENGE: chạy Task 0 (verify anchor bằng lệnh thật), đối chiếu code, ghi objection `O1.x` kèm `file:dòng` vào Debate Log.
3. Còn objection → spawn **Ki-su** RESPOND: mỗi objection phán **ACCEPT / DEFEND / REFRAME / DEFER→CHỦ NHÀ**, bump phiếu version. Lặp 2↔3 đến hết objection.
4. `DEFER→CHỦ NHÀ` xuất hiện → orchestrator **HỎI user** (đây là quyết định scope/tầm nhìn, không tự quyết).
5. Hết objection → **Chủ nhà duyệt** (gõ "go") → spawn **Tho-xay** EXECUTE: thi công + test + Discoveries.

**Kênh liên lạc = chính file phiếu** (Debate Log), không cần file phụ. 2 tab riêng cũng chạy được flow này (bàn giao thủ công qua file phiếu) nhưng mặc định dùng 1 session + orchestrator cho tự động.

## Chống MÕM (subagent làm thật, không kể chuyện) — BẮT BUỘC
> Output subagent KHÔNG hiển thị cho user; nó bị tối ưu để "nghe như xong". Orchestrator là chốt chặn DUY NHẤT → phải kiểm bằng máy, cấm relay lời khai.
1. **Ép bằng chứng, không nhận văn xuôi**: subagent khẳng định gì phải kèm `file:dòng` / output lệnh thật.
2. **Task 0 chống mõm từ đầu**: giả định phải verify bằng lệnh trước khi làm.
3. **Orchestrator tự kiểm lại**: nó bảo "test pass"/"đã sửa" → chạy lại `git status --short`, `git diff --stat`, và lệnh test/grep → đối chiếu. Không khớp = mõm, bắt làm lại.
4. **Rubric viết TRƯỚC khi spawn** (đã có ở Re-take loop) → chấm theo checklist.
5. **Phản biện đối kháng**: việc quan trọng → spawn agent thứ 2 độc lập nhiệm vụ BÁC BỎ; sống sót mới tin.

## §Tự-đính-chính — worker ĐƯỢC bác chẩn đoán của người giao, và phải soi lại lời khai của CHÍNH MÌNH
> Chiều ngược của §Chống MÕM: trên kia là điều phối kiểm worker; ở đây là worker kiểm NGƯỜI GIAO và kiểm CHÍNH NÓ.
> Ca thật 04/09/2026 — ba lần worker tự sửa lại mình, cả ba đều cứu việc: ① bác giả thuyết *"worker nặng bị cắt vì quá tải"* (đo 53 nhật ký: con chạy TRỌN lớn hơn con bị cụt) → khỏi dựng cổng theo giả thuyết sai; ② bác chẩn đoán *"chỗ giữ không tự nhả khi worker xong"* (phần nhả vốn chạy đúng; sai thật ở *"không đo được thì buông vùng"*); ③ tự nhận đã khai sai *"không đẻ chặn oan mới"* rồi tìm ra đúng một chặn oan do bản vá của mình và vá tiếp. Cả ba đều do người giao viết tay vào từng brief — brief sau quên là mất, nên thành luật.

1. **Bác chẩn đoán của người giao là ĐÚNG VIỆC, không phải cãi.** Người giao đoán sai là chuyện thường. Bác phải kèm bằng chứng đo được (`file:dòng`, output lệnh) — bác suông không tính.
2. **Trước khi đóng, soi lại chính báo cáo sắp gửi**: câu nào khẳng định mà chưa có bằng chứng → đi kiểm rồi mới gửi, ghi rõ *đã kiểm gì, kết quả ra sao*.
3. **Khai sai thì tự đính chính, CẤM im.** Thấy lời khai trước của mình sai → nói thẳng trong báo cáo cuối: sai chỗ nào, bản sửa ra sao. Sửa lén còn tệ hơn khai sai.
4. **Cấm dựng cổng / viết code theo giả thuyết CHƯA chứng minh.** Giả thuyết bị bác → báo rõ *"đã bác + số đo"*, không cứ thế làm tiếp theo brief.

> Bản rút gọn cho worker nằm ở `agents/tho-fulfill.md` và `agents/Tho-xay.md` (đó mới là tệp worker thật sự nạp).

## LUẬT SỐ 1 — Worker ĐANG LÀM VIỆC = BẤT KHẢ XÂM PHẠM · worker ĐÃ TRẢ BÁO CÁO = KILL NGAY

> Bài học thật (2026-08-25, founder nổi giận, nhắc nhiều lần): trên màn hình còn đứng
> `◯ general-purpose  Sửa giỏ hàng không hoạt độ… 1h 38m 15s` — **worker đó đã trả báo cáo cuối từ lâu**.
> Coordinator đọc trạng thái `running` rồi áp máy móc "bất khả xâm phạm" nên không dám kill. Hậu quả: mỗi
> lần một thông báo nền chạm vào, con xác lại tỉnh dậy **bắn lại đúng bản báo cáo cũ — 4 lần liên tiếp**
> (con `a5f3e7d9` 3 lần), tốn token và làm nhiễu. Trạng thái `running` lúc đó là **RÁC, không phải đang làm việc**.

### "Đang chạy" nghĩa là gì — định nghĩa DUY NHẤT
**Đang chạy = CHƯA trả báo cáo cuối và đang thực sự làm việc.** Không phải "khung điều phối còn hiện `running`",
không phải "đồng hồ còn đếm giờ". Trạng thái hiển thị KHÔNG phải bằng chứng.

1. **Worker đã trả báo cáo cuối = XONG VIỆC** — dù trạng thái hiển thị vẫn `running` và đồng hồ vẫn chạy.
   Coordinator **PHẢI `TaskStop` con đó NGAY TRONG CÙNG LƯỢT nhận báo cáo**: không chờ, không nhìn trạng thái,
   không "để đấy phòng khi cần hỏi thêm" (cần hỏi thì mở con mới, rẻ hơn một con xác đếm giờ 1h38m).
2. **"Bất khả xâm phạm" CHỈ áp cho worker CHƯA trả báo cáo và đang thực sự làm việc.** Với đúng loại đó,
   không được kill/pause trừ 1 trong 4 trường hợp: (a) founder bảo dừng; (b) treo/chết thật (xem dấu hiệu dưới);
   (c) làm SAI cách; (d) ĐỤNG CÙNG FILE với task ưu tiên hơn.
3. **Đổi chủ đề chat KHÔNG được kill luồng khác.** Mỗi lượt: hỏi "đang có luồng nào ĐANG LÀM VIỆC?" → để yên;
   tin nhắn mới = thêm/chỉnh ĐÚNG luồng liên quan. Nhiều mảng độc lập (khác file) = chạy **SONG SONG cùng lúc**.

### Dấu hiệu nhận biết XÁC TREO (thấy 1 trong 4 là kill, không cần đủ cả 4)
- **Đã trả báo cáo cuối** — dấu hiệu mạnh nhất, tự nó đã đủ.
- **Gửi lại báo cáo trùng nội dung lần thứ hai** — chắc chắn là xác bị thông báo nền đánh thức, không phải việc mới.
- **Đã ghi mốc `100|…` vào `/tmp/claude-bg-progress/<dự án>/<slug>.progress`** mà vẫn hiện `running`.
- **Tiến trình liên quan ở CPU 0,0% kéo dài** — 25/8 có **2 `xcodebuild` treo CPU 0,0% giữ simulator**,
  làm worker khác **xếp hàng 50 phút vô ích**. Lệnh soi:
  `ps -eo pid,pcpu,etime,comm | awk '$2+0==0.0 && $3 ~ /-|^[0-9]+:[0-9][0-9]:/ {print}'`
  → thấy `xcodebuild` / `http.server` / `Simulator` treo thì `kill` tiến trình **và** kill worker giữ nó.

### Cổng tất định đi kèm
`enforce/claude/hooks/worker_cap_enforce.py` **tự loại xác treo khỏi số đếm trần** (đọc ngược transcript:
lượt cuối là khối `text` không kèm `tool_use` = đã trả kết quả về cha; hoặc `[Request interrupted by user]`).
Khi phát hiện xác treo nó in thẳng danh sách kèm câu **"DỌN NGAY … `TaskStop` từng con"**. Nhờ vậy trần 5
không còn bị xác chiếm chỗ chặn oan worker mới.

### Vì sao TRƯỚC ĐÂY không có hook tự kill — và điều kiện đã đổi (09/09/2026, P088 Q5)
- **Không có cách kill riêng một worker từ hook.** Đo thật: cả phiên 42 subagent nhưng `pgrep claude` chỉ ra
  **1 tiến trình `claude`** — subagent chạy trong cùng tiến trình cha. Hook mà `kill` thì giết cả phiên founder.
  Điều này **vẫn đúng** — `TaskStop` tự động (dưới đây) đi qua đúng cơ chế `asyncRewake` đánh thức MAIN rồi
  main tự gọi tool `TaskStop`, không phải hook tự `kill` tiến trình hệ điều hành.
- **Dấu hiệu "text không kèm tool_use" đã bị LOẠI BỎ 28/08/2026** vì gây kill oan 2 worker "vừa nói vừa làm"
  (đo trên 728 transcript: sai 12.137/12.529 khoảnh khắc — `worker_cap_enforce.py:48-77`). Đoạn "Cổng tất
  định đi kèm" phía trên mô tả tín hiệu ĐÃ BỊ LOẠI — câu "lượt cuối là khối text không kèm tool_use = đã trả
  kết quả" là **hoá thạch**, không dùng làm điều kiện tắt được nữa.
- ⭐ **Founder chốt Q5 (09/09/2026, phiếu P088): "PHẢI CHẮC CHẮN NÓ CHẾT" — máy ĐƯỢC PHÉP tự `TaskStop`, với
  điều kiện đã qua CỔNG CHỨNG MINH bằng số (M5), không phải lời hứa.** Nguồn DUY NHẤT: harness xác nhận
  kết thúc cho đúng `agentId` (`worker_relapse.ids_ket_thuc()`, qua `viec_state.py`/`worker_cap_enforce.
  running_workers()` — cấm suy từ hình dạng nội dung). Đo 2 lần cách nhau ≥ 60 giây, cùng kết quả mới hành
  động (M0 luật số 4). Cài ở `tu_tha_ve.py::s12_xac_nhan_hai_lan()`; đối chứng âm đo được 09/09 = 0 (33/33
  worker đã đóng nhận đúng, 1 worker sống + 4 ca khó K1-K4 dựng transcript giả lập đều KHÔNG bị chấm nhầm —
  chi tiết `docs/ticket/P088-...md` §M5, Debate Log). **Đối chứng âm khác 0 → cấm bật**, quay về "chỉ nhắc".
- **Founder ra lệnh DỪNG một việc → hành động ĐẦU TIÊN trong lượt là `TaskStop` đúng agentId** (P103 H5, 15/09/2026): `SendMessage` chỉ dùng để dặn việc TIẾP THEO, không phải lệnh dừng — nó chỉ tới worker ở lượt gọi công cụ kế tiếp (độ trễ harness), còn `TaskStop` gần-tức-thì. Cổng ép: `worker_dia_chi_gate.py` — tin `SendMessage` chứa mệnh lệnh dừng (`DỪNG`/`STOP`/`dừng ngay`) tới đúng một agentId mà lượt đó CHƯA gọi `TaskStop` cho id ấy → `deny` (10/10/2026 đổi từ `ask`: hộp xin quyền làm đứng luồng khi founder vắng máy), kèm câu lối ra "gọi TaskStop trước".

## Quy tắc
- Main giữ context MỎNG: chỉ giữ rubric + kết luận từng worker; chi tiết nặng để worker gánh.
- **Model theo VAI, KHÔNG cào bằng**: main = model mạnh (thẩm định, quyết định). Worker chọn model theo loại việc:
  - Vai đã phân tầng sẵn ở frontmatter `agents/*.md`: **Ki-su = `opus`** (suy luận: viết plan/PRD), **Tho-xay = `sonnet`** (thực thi/verify cơ học). Cơ học rõ (search/đọc docs/gen test) → hạ tier; challenge nặng (soi bug bảo mật, migration nguy hiểm, debug hóc) → orchestrator **ép `opus` cho riêng lần spawn đó** qua tham số `model` của Agent tool (đè frontmatter, không cần đổi file).
  - Thứ tự Claude Code chọn model (cao→thấp): `CLAUDE_CODE_SUBAGENT_MODEL` (env) › tham số `model` lúc gọi › frontmatter `model:` › model luồng chính.
  - ⚠️ **CẤM set `CLAUDE_CODE_SUBAGENT_MODEL`** trong settings.json: nó cào bằng MỌI subagent về 1 model và **đè cả frontmatter lẫn tham số per-spawn** → phá phân tầng Ki-su/Tho-xay. Muốn 1 subagent 1 model khác nhau → dùng frontmatter (mặc định) hoặc tham số `model` per-spawn.
- Việc lặp máy móc cấu trúc biết trước (N mục × review × verify) → dùng **Workflow** (pipeline / adversarial-verify / judge-panel) thay vì tự tay điều phối — deterministic, tự re-run. Chỉ dùng khi user opt-in orchestration.
- Ghi kết quả từng vòng ra file (`docs/GOAL.md` PENDING / file report) — main session cũng có thể bị nén context.
