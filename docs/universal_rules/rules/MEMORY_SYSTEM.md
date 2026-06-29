# Memory System — Kiến Trúc Trí Nhớ Của Claude Code

Cách Claude Code load context và nhớ giữa các session. Bộ rules cũ chỉ quản lý trí nhớ bằng `CLAUDE.md` + `GOAL.md` (thủ công); file này mô tả toàn bộ cơ chế thật để tận dụng.
_Lý do tồn tại: hiểu cascade + giới hạn kích thước + auto-extract giúp đặt thông tin đúng chỗ, đúng độ ưu tiên, và không vượt giới hạn khiến rules bị cắt âm thầm._

---

## 1. Cascade load CLAUDE.md (load sau = ưu tiên cao hơn)

```
1. Managed   /etc/claude-code/CLAUDE.md         (tổ chức đặt)
2. User      ~/.claude/CLAUDE.md                (global, mọi project)
3. Project   ./CLAUDE.md, .claude/CLAUDE.md, .claude/rules/*.md   (CWD → root)
4. Local     ./CLAUDE.local.md                  (gitignored, cá nhân)
5. Auto-mem  ~/.claude/projects/{git-root}/memory/MEMORY.md
6. Team-mem  .../memory/team/MEMORY.md
```

Mọi instruction trong các file này **OVERRIDE hành vi mặc định** — Claude phải tuân đúng như viết.

## 2. Import & format

- Import file khác bằng `@path` (relative / `~` / absolute) — chỉ trong text, **max depth 5** (import lồng nhau quá 5 cấp sẽ dừng).
- Frontmatter memory file: `name`, `description`, `type`, `paths`.
- 4 loại memory: `user` (về người dùng), `feedback` (cách làm việc), `project` (việc đang làm), `reference` (link tài nguyên).

## 3. Giới hạn kích thước — VƯỢT LÀ BỊ CẮT

| File | Giới hạn |
|---|---|
| `CLAUDE.md` | **40.000 ký tự** (đã có trong `docs/universal_rules/rules/MD_SYSTEM.md`) |
| `MEMORY.md` (entrypoint) | **200 dòng / 25.000 bytes** — vượt sẽ truncate tại newline + cảnh báo |
| Session memory | 12.000 token tổng, 2.000 token/section |

_Lý do: vượt giới hạn không báo lỗi to — nó **âm thầm cắt** phần cuối. Rules quan trọng để cuối file có thể biến mất mà không ai biết. Giữ CLAUDE.md gọn, tách chi tiết ra file riêng + `@import`._

## 4. Auto-extract memory

- Cuối mỗi lượt, một subagent có thể tự rút thông tin đáng nhớ từ **các message gần nhất** và ghi vào `memory/`.
- Nó **chỉ** dùng nội dung hội thoại gần đây — không grep source, không đọc code, không chạy git để "xác minh".
- Không lặp lại thứ đã có trong `CLAUDE.md`.

## 5. Session memory (phục vụ compaction)

- File notes riêng cho phiên, template cố định nhiều section. Chỉ cập nhật **nội dung**, không sửa/xóa section header.
- Trigger khi context lớn dần (vd >10k token). Dùng để giữ mạch khi nén context (xem `docs/universal_rules/rules/SUBAGENTS.md` mục Compaction).

## 6. Team memory & cảnh báo độ cũ

- Team memory (`memory/team/`) sync đầu session, có validation chống path traversal/symlink escape. **TUYỆT ĐỐI không lưu secret/API key/credential** vào team memory (chia sẻ nhiều người).
- **Memory > 1 ngày** kèm cảnh báo: đó là quan sát tại một thời điểm, **có thể đã lỗi thời** — verify lại với code hiện tại trước khi tin (vd file/flag/function nêu trong memory có thể đã đổi).

---

## Liên kết
- Quy tắc file MD + giới hạn CLAUDE.md: `docs/universal_rules/rules/MD_SYSTEM.md`
- Theo dõi mục tiêu giữa session (GOAL.md): `docs/universal_rules/rules/OUTCOME.md`
- Re-inject sau khi nén context: `docs/universal_rules/rules/SUBAGENTS.md` (Compaction)
- Nguồn: `memdir/`, `utils/memory/`, `services/extractMemories/`, `services/SessionMemory/` trong source Claude Code.
