# Subagents, Skills & Compaction — Năng Lực Nâng Cao Claude Code

Ba cơ chế bộ rules cũ chưa nhắc tới: **uỷ thác cho subagent, skills (progressive disclosure), và nén context.**
_Lý do tồn tại: với task lớn, biết cách giao việc cho subagent (chạy song song, bảo vệ context chính) và hiểu compaction giúp làm việc quy mô lớn mà không vỡ context._

---

## 1. Subagents — uỷ thác & song song

**Khi nào dùng:**
- Cần **song song hoá** nhiều truy vấn độc lập (vd map nhiều mảng của codebase cùng lúc).
- **Bảo vệ context chính**: việc tốn nhiều token đọc/tìm → giao subagent, chỉ nhận lại kết luận.
- Khám phá rộng, nhiều vòng grep/glob → subagent `Explore`.

**KHÔNG dùng subagent khi:** chỉ cần đọc 1 file / tìm 1 class cụ thể → `Read`/`Glob` nhanh hơn.

**Quy tắc giao việc:**
- **Không làm trùng việc của subagent.** Đã giao research cho subagent thì đừng tự grep lại cùng thứ.
- Brief subagent **như đồng nghiệp mới bước vào phòng** — nó không thấy hội thoại này: đưa đủ đường dẫn file, dòng số, cái cần làm rõ ràng. Prompt cộc lốc → kết quả nông.
- Kết quả subagent **KHÔNG hiển thị cho user** → phải tự tóm tắt lại cho user bằng text.
- Chạy nhiều subagent song song → gửi **1 message với nhiều Agent call**.
- Subagent **stateless**: mỗi lần spawn là context mới, luôn dùng absolute path.

## 2. Skills — kỹ năng đóng gói (progressive disclosure)

- Skill = một `SKILL.md` + frontmatter (`name`, `description`, `when_to_use`, `allowed-tools`, ...), nằm ở `~/.claude/skills/` (user) hoặc `.claude/skills/` (project).
- **Progressive disclosure:** ban đầu chỉ load **metadata** (tên + mô tả ngắn) để tiết kiệm context; full `SKILL.md` chỉ load **khi invoke**.
- Khi một skill khớp yêu cầu → **gọi skill đó TRƯỚC** khi làm gì khác (blocking). Không nhắc tên skill mà không thực sự gọi.
- Hai chế độ chạy: **inline** (mở rộng vào hội thoại hiện tại) / **fork** (sub-agent riêng, token budget riêng).
- `allowed-tools` trong frontmatter giới hạn tool khi skill chạy. `user-invocable: false` → chỉ user gọi được, model không tự gọi.

> Bộ rules này (vd `thanhtra` security scan) chính là skill — đặt ở `skills/` với `SKILL.md` đúng chuẩn để Claude Code tự nhận.

## 3. Compaction — nén context khi hội thoại dài

- **Auto-compact:** tự nén khi token gần đầy (~92% cửa sổ context). Đừng để tới sát giới hạn rồi mới lo — nó tự xử lý, nhưng tóm tắt sẽ mất chi tiết.
- **Manual `/compact [instructions]`:** chủ động nén, có thể kèm hướng dẫn giữ lại gì.
- **Microcompact:** dọn các tool_result cũ ít giá trị mà giữ nguyên mạch chính (ít mất mát hơn full compact).
- Sau nén, hệ thống **re-inject** lại: vài file gần nhất, plan file, skills đang dùng, MCP instructions... nên mạch làm việc không đứt hẳn.

**Hệ quả thực tế cho bộ rules này:** đây là lý do `docs/universal_rules/rules/OUTCOME.md` ép ghi PENDING tasks vào `GOAL.md` — để khi context bị nén/mất, vẫn khôi phục được trạng thái từ file trên đĩa thay vì chỉ dựa vào trí nhớ hội thoại.

## 4. Orchestrator — main session giám sát & bắt làm lại (pattern "đạo diễn")

Main session (model mạnh nhất — Fable/Opus) KHÔNG tự cày việc lớn; nó **spawn worker, đọc output, thẩm định, thấy sai thì ra lệnh làm lại kèm chỉ dẫn sửa cụ thể**. Người dùng chỉ cần nói: _"spawn agent làm X, canh nó, sai thì bắt làm lại"_.

**Vòng lặp chuẩn (re-take loop):**
1. **Spawn** worker bằng Agent tool (`run_in_background: true` nếu muốn canh nhiều con song song) — brief như đồng nghiệp mới (mục 1).
2. **Thẩm định** output theo tiêu chí ĐÃ VIẾT RA TRƯỚC khi spawn (rubric/checklist — không chấm cảm tính).
3. Sai/thiếu → **SendMessage cho ĐÚNG agent đó** (theo tên/ID) với chỉ dẫn sửa cụ thể — agent giữ nguyên context cũ, KHÔNG spawn con mới làm lại từ đầu (mất context = lặp lại lỗi).
4. Đạt → nhận kết quả, chuyển bước tiếp / worker kế tiếp.

**Quy tắc:**
- Main giữ context MỎNG: chỉ giữ rubric + kết luận từng worker; chi tiết nặng để worker gánh.
- Phân vai model: main = model mạnh (thẩm định, quyết định); worker mặc định kế thừa model chính — chỉ hạ tier cho việc cơ học rõ ràng.
- Việc lặp máy móc với cấu trúc biết trước (N mục × review × verify) → dùng **Workflow** (pipeline/adversarial-verify/judge-panel) thay vì tự tay điều phối từng con — deterministic, tự re-run được.
- Ghi kết quả từng vòng vào file (GOAL.md PENDING / file report) — main session cũng có thể bị nén context (mục 3).

---

## Liên kết
- Khi nào search bằng Agent vs Glob/Grep: `docs/universal_rules/rules/TOOL_DISCIPLINE.md` §3
- Trí nhớ giữa session + session memory: `docs/universal_rules/rules/MEMORY_SYSTEM.md`
- Giữ mục tiêu qua compaction (GOAL.md PENDING): `docs/universal_rules/rules/OUTCOME.md`
- Nguồn: `tools/AgentTool/`, `tools/SkillTool/`, `services/compact/` trong source Claude Code.
