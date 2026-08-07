# AGENTS-ORCH — điều phối subagent (pattern "đạo diễn")

Khi task lớn: main session KHÔNG tự cày; nó **spawn worker, đọc output, thẩm định, sai thì bắt làm lại kèm chỉ dẫn cụ thể**.

## Khi nào dùng subagent
- Song song hoá nhiều truy vấn ĐỘC LẬP (map nhiều mảng codebase cùng lúc).
- Bảo vệ context chính: việc tốn nhiều token đọc/tìm → giao subagent, chỉ nhận lại kết luận.
- **KHÔNG dùng** khi chỉ cần đọc 1 file / tìm 1 class → `Read`/`Glob` nhanh hơn.

## Brief worker
- Brief **như đồng nghiệp mới bước vào phòng** — nó KHÔNG thấy hội thoại này: đưa đủ absolute path, dòng số, việc cần làm rõ ràng. Prompt cộc lốc → kết quả nông.
- Subagent **stateless** (mỗi spawn là context mới) và **KHÔNG hiển thị cho user** → tự tóm tắt lại cho user bằng text.
- Nhiều subagent song song → **1 message, nhiều Agent call** (hoặc `run_in_background` để canh song song).
- **Không làm trùng việc worker**: đã giao research thì đừng tự grep lại cùng thứ.

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

## Quy tắc
- Main giữ context MỎNG: chỉ giữ rubric + kết luận từng worker; chi tiết nặng để worker gánh.
- **Model theo VAI, KHÔNG cào bằng**: main = model mạnh (thẩm định, quyết định). Worker chọn model theo loại việc:
  - Vai đã phân tầng sẵn ở frontmatter `agents/*.md`: **Ki-su = `opus`** (suy luận: viết plan/PRD), **Tho-xay = `sonnet`** (thực thi/verify cơ học). Cơ học rõ (search/đọc docs/gen test) → hạ tier; challenge nặng (soi bug bảo mật, migration nguy hiểm, debug hóc) → orchestrator **ép `opus` cho riêng lần spawn đó** qua tham số `model` của Agent tool (đè frontmatter, không cần đổi file).
  - Thứ tự Claude Code chọn model (cao→thấp): `CLAUDE_CODE_SUBAGENT_MODEL` (env) › tham số `model` lúc gọi › frontmatter `model:` › model luồng chính.
  - ⚠️ **CẤM set `CLAUDE_CODE_SUBAGENT_MODEL`** trong settings.json: nó cào bằng MỌI subagent về 1 model và **đè cả frontmatter lẫn tham số per-spawn** → phá phân tầng Ki-su/Tho-xay. Muốn 1 subagent 1 model khác nhau → dùng frontmatter (mặc định) hoặc tham số `model` per-spawn.
- Việc lặp máy móc cấu trúc biết trước (N mục × review × verify) → dùng **Workflow** (pipeline / adversarial-verify / judge-panel) thay vì tự tay điều phối — deterministic, tự re-run. Chỉ dùng khi user opt-in orchestration.
- Ghi kết quả từng vòng ra file (`docs/GOAL.md` PENDING / file report) — main session cũng có thể bị nén context.
