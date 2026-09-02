# univ3 — Universal Rules v3

Bộ rule siêu gọn cho vibe coder dùng **Claude Code CLI + OpenAI Codex CLI**. Mục tiêu: agent luôn đạt hiệu quả tốt nhất, không rườm rà, không context rot.

- **Bắt đầu:** `HUONG_DAN.md`
- **Luật luôn-nạp:** `SPINE.md` (canonical) → `AGENTS.md` (sinh tự động, Codex đọc)
- **Bản đồ + lệnh:** `INDEX.md`
- **Trạng thái/thiết kế:** `_meta/ROADMAP.md` · `../UNIV3_BLUEPRINT.md`

Cài: `python3 install.py --harness all`

Triết lý (bài học SDD→RDD): spec là **tấm bản đồ**, không phải bộ luật. Single source of truth = code base. Thứ "phải luôn đúng" → hook/pre-commit ép, không dựa model nhớ. Rule không liên quan là distractor chủ động → lazy-load qua skill. Trước khi thêm rule luôn-nạp: "xoá đi agent có sai không? ép được bằng hook không?"

> v2 (`universal_rules/`) đã ngừng dùng — univ3 thay thế hoàn toàn.
