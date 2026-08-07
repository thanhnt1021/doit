# univ3 — INDEX (bản đồ thư mục + lệnh)

Bản đồ "tình huống → đọc gì" nằm ở `SPINE.md` (bản DUY NHẤT, luôn-nạp). File này chỉ liệt kê **cấu trúc** + **lệnh** + **skill**. KHÔNG chứa nội dung rule.

## Cấu trúc
```
docs/univ3/
├─ SPINE.md          — luật luôn-nạp (canonical). AGENTS.md sinh từ đây.
├─ AGENTS.md         — SINH TỰ ĐỘNG (gen_agents_md.py). Codex/Cursor đọc; Claude @import.
├─ INDEX.md          — file này (bản đồ thư mục + lệnh)
├─ HUONG_DAN.md      — cài đặt + dùng (bắt đầu ở đây nếu mới)
├─ VERSION · MANIFEST.txt   — phiên bản + sha256 (drift-check)
├─ rules/            — 6 file chi tiết: WORKFLOWS · GIT · DOCS · GATES · ASK-BACK · AGENTS-ORCH
├─ skills/           — 13 skill ngữ cảnh (lazy-load; body chỉ đọc khi trúng)
├─ enforce/          — cưỡng chế: pre-commit (mọi harness) · claude/hooks · codex/
├─ templates/        — README/CONTRIBUTING/ADR/GOAL/DESIGN + github_templates
├─ scripts/          — gen_agents_md.py · gen_manifest.sh · security-check.sh
├─ install.py        — 1 installer (--harness claude|codex|all)
└─ _meta/            — ROADMAP (trạng thái gate) · _archive/ (đã chết, KHÔNG grep)
```

## Cài đặt
```bash
python3 docs/univ3/install.py --harness all      # Claude + Codex + git pre-commit
```
Chi tiết + cách copy sang project mới: `HUONG_DAN.md`.

## Lệnh (chi tiết: `rules/WORKFLOWS.md`)
| Lệnh | Hành động |
|---|---|
| `feature: [tên]` | Branch → Analysis (Q&A) → Full Plan chờ duyệt → implement+test từng bước → DỪNG |
| `test demo` / `quick deploy` | Build+deploy demo, KHÔNG commit/push → DỪNG |
| `check code` | App security check (skill app-security) — BẮT BUỘC trước mỗi quick deploy |
| `commit` | Commit + push nhánh hiện tại (update MD/CHANGELOG/GOAL nếu cần trước) |
| `full update` | One-shot cuối task: update MD → commit+push → merge → deploy → report |
| `merge main` / `lên production` | Merge main + deploy production |
| `check requirements` | Setup mọi thứ còn thiếu (skill new-project-setup) |
| `docs project` | Tạo/update tài liệu dự án (skill project-docs) |
| `read context` / `report context` | Đọc docs + Goal-check → "sẵn sàng" (report thì kèm summary) |
| `check goal` / `update goal` | Xem/đề xuất update GOAL.md |
| `sync uni` | Pull rule mới từ SSOT + drift-check (KHÔNG overwrite file project) |
| `tdk: [câu hỏi]` · `check growth` · `check quality` · `setup server` | Route tới skill tdk-master / product-growth / qa-multipass / infra |

## Skills (13 — tự kích hoạt theo description; bảng đầy đủ trong AGENTS.md)
`sepay-payment` · `google-oauth` · `mobile-webapp` · `app-security` · `bot-commands` · `ci-cd` · `seo-geo` · `project-docs` · `new-project-setup` · `product-growth` · `qa-multipass` · `infra` · `tdk-master`

Cài chung mọi project qua `install.py` (Claude: `~/.claude/skills/`, Codex: `~/.agents/skills/`).
