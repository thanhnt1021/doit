# Code-Index Architecture v1 — Khép vòng "bộ nhớ ngoài" cho codebase

> **Nguồn gốc:** Lời khuyên cộng đồng (AI quét source → sinh 2 file index/liệt-kê → mỗi lần code/fix cho AI đọc trước → giảm lỗi, giảm token, giảm thời gian).
>
> **Phát hiện khi rà univ2:** Ý tưởng này univ2 **đã có sẵn và chi tiết hơn** ở `rules/PROJECT_DOCS.md` (lệnh `docs project`) — `PROJECT_SUMMARY.md` = file index, `API_REFERENCE/SOCKET_EVENTS/DATABASE...` = phần liệt kê function/route/keyword. **Không cần thêm khái niệm mới.**
>
> **Vấn đề thật:** Khung có nhưng **chưa khép vòng** → giá trị không tự kích hoạt. Hụt đúng 2 mắt xích, và cả hai đều map vào mô hình 5 tầng ở [[RULE_ARCHITECTURE_v1]].
>
> **Phạm vi thiết kế này:** CHỈ thiết kế 2 mắt xích thiếu. KHÔNG sửa `PROJECT_DOCS.md` (nội dung sinh docs đã ổn).

---

## 1. Chẩn đoán — 3 lỗ hổng đo được bằng file thật

| Lỗ hổng | Bằng chứng (rà ngày 2026-06-29) | Hệ quả |
|---|---|---|
| **Không tự cập nhật / không cảnh báo lỗi thời** | `docs project` chỉ chạy khi user gõ tay. Không hook, không quality-gate nào so source vs summary. `_meta/GAP_ANALYSIS.md` grep `stale\|tự cập nhật\|code.?index` = rỗng | Index mục dần → AI đọc index sai còn **hại hơn** không có. Đây là điểm comm cộng đồng **cũng bỏ sót** |
| **Không ép đọc SUMMARY trước khi code** | `hooks/session_context.py` chỉ inject spine (7 luật + bản đồ rule). `SESSION_SPINE.md` / `INDEX.md` không có dòng "trước khi code/fix → đọc PROJECT_SUMMARY" | Lợi ích "giảm token/giảm lỗi" **phụ thuộc model tự nhớ** = đúng bệnh "lúc nhớ lúc quên" mà univ2 sinh ra để diệt |
| **Chưa dùng tại chính project** | `DOC-tool/docs/` mới có `TODO.md`, **chưa có** `PROJECT_SUMMARY.md` | Cơ chế nằm im |

**Kết luận:** không phải "làm lại", chỉ cần **2 mắt xích deterministic** + 1 lần seed dữ liệu. Khớp đúng phần **G2–G5 còn dở**.

---

## 2. Nguyên lý gốc (kế thừa [[RULE_ARCHITECTURE_v1]] §2)

1. **Thứ "phải luôn đúng" → harness ép, không để model tự giác.** → stale-gate là HOOK, không phải lời nhắc trong docs.
2. **Read-on-demand, KHÔNG nhồi summary vào spine.** Summary có thể vài KB; nhồi mỗi phiên phá nguyên tắc "spine cực mỏng". Chỉ thêm **1 dòng trỏ** vào bản đồ rule.
3. **Index lỗi thời nguy hiểm hơn không có index.** → ưu tiên cảnh báo staleness hơn là ép sinh đủ docs.
4. **Chỉ đáng dùng cho codebase đủ lớn.** Repo nhỏ / cấu trúc tốt thì Explore/grep đã đủ — xem §5 When-NOT.

---

## 3. Thiết kế 2 mắt xích

### Mắt xích A — STALE-GATE (Tầng 1, Hook) — chống index lỗi thời

**Cơ chế:** so `mtime` file source mới nhất với `mtime` của `docs/PROJECT_SUMMARY.md`.

| Thuộc tính | Quyết định | Lý do |
|---|---|---|
| Tầng | 1 — Hook (deterministic) | "Phải luôn đúng" → không để model nhớ |
| Điểm bắn (primary) | **SessionStart** — nếu stale, chèn **1 dòng** vào additionalContext: `⚠ PROJECT_SUMMARY.md cũ hơn source (N file đổi) — cân nhắc 'docs project'` | Rẻ, không chặn, thấy ngay đầu phiên. Cùng đòn bẩy `session_context.py` đang dùng |
| Điểm bắn (optional, hard) | **PreToolUse** khớp `git commit` → `permissionDecision:'ask'` kèm reason | Chặn mềm trước khi đóng băng commit với docs lỗi thời. Bật/tắt qua config |
| "Source" là gì | Glob cấu hình; default: code ext phổ biến, loại trừ `docs/ node_modules/ .git/ dist/ build/ *.lock` | Generic, không phụ thuộc ngôn ngữ |
| Ngưỡng | Source mới hơn summary > 0 (có thể đặt grace, vd bỏ qua nếu chỉ lệch < 1 ngày) | Tránh nhiễu khi vừa sinh xong |
| Fail-open | Lỗi/không có summary/không bật → emit rỗng, không vỡ phiên | Theo design `session_context.py:13` |
| Tắt khi không cần | Bỏ qua nếu repo < ngưỡng file (vd < 30 file code) hoặc thiếu `docs/PROJECT_SUMMARY.md` và project chưa opt-in | When-NOT §5 |

> **Đây là phần comm cộng đồng KHÔNG có** — và là giá trị thật univ2 thêm vào.

### Mắt xích B — AUTO-READ (Tầng 4 Index + Tầng 5 Prompt) — kích hoạt lợi ích

**Cơ chế:** thêm **1 dòng** vào bản đồ rule trong `SESSION_SPINE.md` (template) — đúng kiểu các dòng "tình huống → đọc file" đã có.

```
| Code feature mới / fix bug ở codebase lớn | đọc `docs/PROJECT_SUMMARY.md` trước (định vị) |
```

| Thuộc tính | Quyết định | Lý do |
|---|---|---|
| Tầng | 4 (dòng trỏ trong spine) + 5 (viết theo "trước khi… → đọc…") | Read-on-demand, không tốn token mỗi phiên |
| KHÔNG làm | Không nhồi nội dung summary vào spine | Giữ spine ≤ 6000 ký tự (`session_context.py:20` MAX_CHARS) |
| Điều kiện kích hoạt | Chỉ khi project có `docs/PROJECT_SUMMARY.md` | Không bắt đọc file không tồn tại |

---

## 4. Lộ trình (nối tiếp G2–G5 của [[RULE_ARCHITECTURE_v1]])

| Gate | Việc | Output | Điều kiện qua |
|---|---|---|---|
| **CI-1** ✅ | Stale-check (Mắt xích A) `stale_warning()` trong `session_context.py` | Hàm so mtime + 1 dòng cảnh báo | ✅ 4/4 test: stale→cảnh báo, cũ→im, repo nhỏ→bỏ, chưa-opt-in→im |
| **CI-2** ✅ | Dòng auto-read (Mắt xích B) trong `SESSION_SPINE.md` + `INDEX.md` | 2 dòng trỏ | ✅ Spine 2982 ký tự (< 6000); grep thấy dòng |
| **CI-3** ✅ | PreToolUse(Bash) soft-gate `code_index_commit_gate.py` — TỰ GATING (chỉ "ask" khi git commit + stale; chưa có summary → im), không cần cờ env | Hook + đăng ký trong `install_hooks.py` | ✅ 3/3 test: commit+stale→ask, lệnh khác→exit0, chưa-opt-in→exit0 |
| **CI-4** ✅ | Seed `docs/PROJECT_SUMMARY.md` cho univ2 + `docs/.code_index_skip` (loại `src/` vendored) | File summary thật + skip-config | ✅ Summary mô tả univ2 (5 tầng, hooks, install). **Lưu ý:** code univ2 nằm trong `docs/` (SKIP_DIRS loại theo thiết kế chung) → stale-gate IM trên CHÍNH project này, đúng vì univ2 là project rules/docs |
| **CI-5** | Đo 7 ngày: lần code/fix sau có tự đọc summary? cảnh báo stale có nổ đúng lúc? | Review | Triệu chứng "AI mò lại cả repo / docs lỗi thời" giảm rõ |

> **Trạng thái (2026-06-29):** CI-1→CI-4 xong & verify. Phát sinh: thêm cơ chế **per-project skip-dir** (`docs/.code_index_skip`) cho repo vendored source — đúng phần "glob cấu hình" của thiết kế. Còn CI-5 (đo theo thời gian, không làm ngay được). **CẦN chạy lại `install_hooks.py`** để đẩy `session_context.py` (refactor `is_stale`) + `code_index_commit_gate.py` ra global.

**Nguyên tắc:** không nhảy gate khi gate trước chưa đạt output. Đo bằng hành vi thật.

---

## 5. When-NOT (chống over-engineer — bám luật bất biến #2)

Bỏ qua toàn bộ tầng code-index khi:
- Repo **nhỏ / cấu trúc rõ** → Explore/grep agent đã đủ, summary chỉ thêm gánh bảo trì.
- Project **đổi quá nhanh ở giai đoạn đầu** → summary stale liên tục, cảnh báo thành nhiễu. Bật lại khi kiến trúc ổn định.
- Không có ai chịu chạy `docs project` định kỳ → đừng bật stale-gate để khỏi cảnh báo suông.

> Quy mô đáng bật: monolith / codebase lớn (vd kiểu ERP nhiều module) — đúng ca mà lời khuyên gốc nhắm tới.

---

*v1 — Thiết kế 2 mắt xích thiếu (stale-gate + auto-read) cho cơ chế PROJECT_DOCS đã có. Trọng tâm: biến "bộ nhớ ngoài" từ thủ-công-dễ-mục thành deterministic-tự-cảnh-báo. Chưa code — chờ duyệt.*
