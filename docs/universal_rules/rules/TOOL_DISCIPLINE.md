# Tool Discipline — Dùng Tool Đúng Cách (Claude Code)

Cách Claude Code thật dùng tool: **ưu tiên tool chuyên dụng hơn shell, gọi song song khi độc lập, route search đúng chỗ.**
_Lý do tồn tại: nhiều file trong bộ rules cũ dạy thao tác bằng `grep -rn`/`cat`/`find` qua shell — anti-pattern trên Claude Code. Tool chuyên dụng giúp user review + cấp quyền dễ hơn, và chạy nhanh hơn._

---

## 1. Tool-first — KHÔNG dùng Bash cho việc đã có tool riêng

| Việc cần làm | Dùng tool | KHÔNG dùng Bash |
|---|---|---|
| Đọc file | `Read` | `cat`, `head`, `tail` |
| Sửa file | `Edit` | `sed`, `awk`, `perl -i` |
| Tạo/ghi đè file | `Write` | `echo >`, `cat <<EOF` |
| Tìm file theo tên | `Glob` | `find`, `ls -R` |
| Tìm nội dung trong code | `Grep` | `grep`, `rg` |
| Nói chuyện với user | Output text thẳng | `echo`, `printf` |

- **Chỉ dùng Bash cho việc thật sự cần shell**: chạy build/test/lint, git, cài package, khởi động service, thao tác hệ thống.
- Ngoại lệ: user yêu cầu rõ ràng dùng shell, hoặc đã xác minh tool chuyên dụng không làm được.

_Lý do: tool chuyên dụng hiển thị diff/kết quả rõ ràng để user review và cấp quyền; lệnh shell thì opaque, khó kiểm soát, và dễ chạm permission sai. Đây là điều CRITICAL trong system prompt của Claude Code._

## 2. Parallel tool calls — gọi song song khi độc lập

- Nhiều tool call **không phụ thuộc nhau** → gửi **trong CÙNG một message** để chạy song song.
  - Ví dụ: cần `git status` + `git diff` + `git log` → 1 message, 3 Bash call song song.
  - Ví dụ: đọc 4 file để nắm context → 4 Read call song song.
- Chỉ gọi **tuần tự** khi call sau cần kết quả của call trước.
- Với lệnh shell phụ thuộc nhau và phải đúng thứ tự → chain bằng `&&` trong 1 Bash call (đừng tách message).

_Lý do: gọi tuần tự những việc độc lập làm chậm gấp nhiều lần không cần thiết. Song song hóa là cách rẻ nhất để tăng tốc._

## 3. Search routing — chọn đúng công cụ tìm kiếm

| Tình huống | Dùng |
|---|---|
| Biết rõ tên file/class/function cụ thể | `Glob` hoặc `Grep` hoặc `Read` thẳng |
| Tìm trong 2-3 file đã biết | `Read` |
| Tìm mở (open-ended), cần nhiều vòng grep/glob, khám phá rộng | **Agent** (subagent `Explore`) |

- Đừng spawn subagent để đọc 1 file cụ thể — `Read`/`Glob` nhanh hơn.
- Ngược lại, đừng tự grep thủ công nhiều vòng cho câu hỏi rộng — giao cho subagent `Explore` (xem `docs/universal_rules/rules/SUBAGENTS.md`).

## 4. Vài quy ước nhỏ khi chạy lệnh

- Giữ nguyên working directory bằng **absolute path**, tránh `cd` (trừ khi user yêu cầu).
- Luôn **quote path có khoảng trắng**: `cd "thu muc/co space"`.
- Lệnh chạy lâu → dùng `run_in_background`, **không** `sleep` để chờ, **không** poll — sẽ được báo khi xong.
- Lệnh fail → **diagnose nguyên nhân**, không retry trong vòng lặp sleep.
- Trước khi tạo file/thư mục mới → `ls` kiểm tra thư mục cha tồn tại đúng chỗ.

---

## Liên kết
- Giao việc cho subagent + chạy nhiều agent song song: `docs/universal_rules/rules/SUBAGENTS.md`
- An toàn khi chạy lệnh phá hủy: `docs/universal_rules/rules/ACTION_SAFETY.md`
- Nguồn: system prompt Claude Code (`# Using your tools` — dedicated tools, parallel tool calls) + tool description của BashTool/GrepTool/GlobTool.
