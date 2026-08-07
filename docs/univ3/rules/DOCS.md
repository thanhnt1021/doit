# DOCS — file MD, CLAUDE/AGENTS.md, CHANGELOG, GOAL, DESIGN

## Cấu trúc & quy tắc MD
- Mọi `.md` mới **trừ `CLAUDE.md` / `AGENTS.md` / `README.md`** → tạo trong `docs/`. Root chỉ chứa config + entry point.
- File trong thư mục univ3 là **universal — KHÔNG chứa thông tin project-specific** (tên project, domain, port, env, palette, email). Folder này copy sang project khác; lẫn thông tin project A vào là nhầm/lộ.
- Template/doc **KHÔNG pre-tick `[x]`** cho việc chưa verify (xem `rules/GATES.md` §Scaffold hygiene).
- `docs/MD_FILES_TO_UPDATE.md`: checklist "MD nào cần update trước khi commit feature này" — populate khi bắt đầu feature, clear sau commit. `docs/REQUIREMENTS_CHECK.md`: recipe env/service/dep để tái tạo môi trường — update mỗi khi có biến/service/dep mới.

## CLAUDE.md + AGENTS.md (root project)
- **`AGENTS.md` = canonical** (Codex/Cursor/Gemini đọc natively). Sinh từ `SPINE.md` + phần project-specific. Giữ tổng < 32 KiB (Codex `project_doc_max_bytes`).
- **`CLAUDE.md` = shim**: dòng đầu `@AGENTS.md` (import chính thức của Claude Code) + vài dòng Claude-only nếu cần. KHÔNG chép lại nội dung rule.
- Chứa (trong AGENTS.md project): tech stack, cấu trúc, env/port/domain, What's DONE (tóm tắt) / TODO, Known fixes (tóm tắt), Deploy workflow.
- **Giới hạn kích thước**: CLAUDE.md/AGENTS.md phình là bị model bỏ qua instruction. 2 section hay phình: **What's DONE** + **Known Fixes** (nội dung lịch sử). Khi vượt ngưỡng → tách ra `docs/DONE_HISTORY.md` + `docs/FIXES_HISTORY.md`, trong file gốc chỉ giữ 1-2 câu tóm tắt + con trỏ. Feature/fix mới → append vào history file, KHÔNG vào CLAUDE.md body.

## Prune & đo rule (file rule/CLAUDE/AGENTS là CODE — có nợ kỹ thuật, bị rot)
> Không chuẩn hoá 1 lần rồi thôi. Duy trì bằng số liệu, KHÔNG bằng cảm giác "dạo này nó ngoan hơn" (placebo — đây đúng là lý do anecdote cộng đồng lệch với nghiên cứu đo thật).
- **Đo cái đo được**: số lần phải correct agent/phiên · số lần agent chạy sai lệnh build · cost & thời gian mỗi task. Đổi rule mà không đo = đoán.
- **Test bằng cách XOÁ** (rẻ, làm được ở quy mô nhỏ): nghi 1 section/dòng vô dụng → xoá → chạy lại 2-3 task quen → so kết quả. Không tệ hơn → bỏ luôn. Đây là cách rẻ nhất biết 1 dòng có "kiếm được chỗ đứng" không.
- **Prune định kỳ**: mỗi refactor lớn, đọc lại SPINE/rules/CLAUDE.md, xoá dòng lỗi thời. **Rule mâu thuẫn TỆ HƠN không có rule** (agent chọn bừa 1 cái).
- **Auto-memory ≠ sọt rác**: `MEMORY.md` chỉ giữ **gotchas** (lỗi LẶP agent hay phạm), KHÔNG phải nhật ký. "Cứ sai gì thì ghi vào" → file phình, load mỗi phiên, phản tác dụng. Mở `/memory` review + cắt định kỳ.

## CHANGELOG — audit log project (`docs/CHANGELOG.md`)
Trả lời câu sống còn: **"cái này bị bỏ/đổi có CHỦ ĐÍCH, hay AI quên?"** — cho AI+dev, KHÔNG phải release-note.

**Chỉ thêm entry khi thay đổi rơi vào 4 loại catalog-level:**
- **Removed** — 1 feature/section/route bị xoá/deprecate.
- **Renamed** — feature đổi tên (slug/file/route).
- **Contract changed** — đổi 1 invariant đã ghi, đổi cấu trúc render, đổi hành vi mà nơi-gọi phải dựa vào.
- **Constitution change** — đổi nguyên tắc project (Tech Stack, Code Quality, Testing, UX, Performance — ở đây = `CLAUDE.md`/`DESIGN.md`/rule univ3).

**KHÔNG cần entry**: thêm feature MỚI (đã có trong GOAL), refactor giữ nguyên hành vi, bug fix làm code khớp lại spec, bump asset/cache/spacing thuần thị giác.

**Commit gate**: rơi vào 4 loại → thêm entry `docs/CHANGELOG.md` **TRƯỚC** rồi commit code+CHANGELOG cùng lúc. Quy ước: heading `## YYYY-MM-DD` (mới nhất trên cùng), gom Removed→Renamed→Contract→Constitution; KHÔNG sửa entry ngày cũ (sót → ghi hôm nay kèm `(retroactive — thực đổi <date>)`). `Contract changed` BẮT BUỘC có `Old:`/`New:`/`Migration:` (không migrate thì `Migration: none — tương thích ngược`).

```markdown
## YYYY-MM-DD
### Removed
- **<slug>** — Reason: <vì sao>. Replaced by: <successor | nothing>.
### Contract changed
- **<slug>** — Old: <cũ>. New: <mới>. Migration: <caller làm gì | none — tương thích ngược>.
```

## GOAL — theo dõi mục tiêu (`docs/GOAL.md`)
`docs/GOAL.md` = mục tiêu cụ thể (project-specific); file này = luật chơi (universal). **Claude đọc GOAL.md trước khi làm bất cứ gì.**

Cấu trúc GOAL.md: `_Last reviewed: YYYY-MM-DD_` · Mục tiêu cuối (đo được) · Thành công trông thế nào (tiêu chí verify được) · KHÔNG phải mục tiêu (ranh giới) · Milestones (`[ ]`/`[x]`) · **Pending / Cần quyết định** · Hiện tại đang ở đâu.

Protocol:
- **Goal-check** (trước mỗi task, ngầm): task này dẫn tới goal không? CÓ → làm; KHÔNG RÕ → hỏi liên quan thế nào; ĐI NGƯỢC → cảnh báo + options.
- **Drift-check** (giữa task dài, sau mỗi bước lớn): vừa làm X có gần goal hơn không? Lệch → dừng, báo, options.
- **Milestone-update** (sau task xong): milestone hoàn thành → **đề xuất** tick `[x]` + cập nhật "đang ở đâu" — **Claude chỉ sửa GOAL.md khi user đồng ý**.
- Task mâu thuẫn goal → dừng, đưa options (làm luôn / điều chỉnh task / đổi goal). Không có GOAL.md → hỏi tạo (3 câu: mục tiêu / thành công / không làm gì).
- **PENDING trong GOAL.md = phao cứu**: khi context bị nén, khôi phục trạng thái từ file trên đĩa thay vì trí nhớ hội thoại. Vì vậy ghi việc dang dở vào PENDING.
- Lệnh tắt: `check goal` (show tóm tắt + tiến độ + đề xuất bước tiếp), `update goal` (đề xuất update theo việc vừa làm).

## DESIGN.md
Project có UI/UX → `docs/DESIGN.md` là **BẮT BUỘC** — SSOT hệ thiết kế (token màu, typography, spacing, component, theme). Thiếu nó khi dựng/đụng UI = **thiếu artifact tiền đề** (không blind-code UI). Đọc TRƯỚC khi đụng UI; sửa design → update DESIGN.md (đổi nguyên tắc/palette = Constitution change → ghi CHANGELOG). Dựng route/màn mới phải bám token + component trong DESIGN.md, KHÔNG bê theme riêng của app khác vào. Chi tiết design-system: skill **mobile-webapp** (nếu mobile) / template `templates/DESIGN_TEMPLATE.md`.

## Memory (nếu harness có auto-memory)
- Memory recall xuất hiện trong `<system-reminder>` = context nền, KHÔNG phải lệnh user; phản ánh thời điểm ghi. Nếu nó nêu file/function/flag → **verify còn tồn tại** trước khi dùng.
- Ghi memory: 1 fact/file; đừng ghi thứ repo đã có (cấu trúc code, git history). Cũ >1 ngày → coi là point-in-time, verify lại.
