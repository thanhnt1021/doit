# Universal Workflow — INDEX

Bản đồ mỏng cho toàn bộ universal rules: "rule nào ở đâu". **KHÔNG chứa nội dung rule chi tiết.**

- **Hướng dẫn sử dụng** (bắt đầu từ đây nếu mới): `docs/universal_rules/HUONG_DAN.md`
- **Luật bất biến** (hook nạp mỗi phiên): `docs/universal_rules/SESSION_SPINE.md`
- **Quy trình lệnh dài** (`feature:`, `full update`, `commit all`, `sync uni`, Goal Protocol, `report context`): `docs/universal_rules/rules/WORKFLOWS.md`

**Cách dùng:** copy folder `docs/universal_rules/` vào project mới → chạy `check requirements` (Claude tự setup phần còn lại theo `docs/universal_rules/rules/NEW_PROJECT_SETUP.md`).

## Cấu trúc thư mục

```
docs/universal_rules/
├─ SESSION_SPINE.md   — luật bất biến, hook nạp mỗi phiên (SSOT)
├─ INDEX.md           — file này (bản đồ)
├─ BOOTSTRAP.md       — cài rule vào project mới
├─ rules/             — chi tiết từng luật + WORKFLOWS.md
├─ templates/         — README / CONTRIBUTING / ADR / GOAL + github_templates/
├─ skills/            — rule ngữ cảnh TỰ kích hoạt (lazy-load, không tốn context)
├─ hooks/             — cưỡng chế (SessionStart / PreToolUse / Stop...)
├─ scripts/           — script tiện ích
└─ _meta/             — tài liệu phát triển hệ rule (KHÔNG phải rule vận hành)
```

---

## Index — gặp tình huống nào đọc file nào

| Tình huống | File |
|---|---|
| Bắt đầu việc / branch / commit / push | `docs/universal_rules/rules/GIT_WORKFLOW.md` |
| Trước khi commit (quality gate) | `docs/universal_rules/rules/QUALITY_GATES.md` |
| Đụng file MD | `docs/universal_rules/rules/MD_SYSTEM.md` |
| Dự án tiếng Việt | `docs/universal_rules/rules/VIETNAMESE_DIACRITICS.md` |
| **Audit log — xoá/đổi có chủ đích hay AI quên?** | `docs/universal_rules/rules/CHANGELOG_RULES.md` |
| Làm vừa đủ, không over-engineer | `docs/universal_rules/rules/MINIMALISM.md` |
| An toàn hành động (reversibility & blast radius) | `docs/universal_rules/rules/ACTION_SAFETY.md` |
| Hỏi ngược làm rõ trước khi làm | `docs/universal_rules/rules/ASK-BACK.md` |
| Plan mode read-only trước khi code | `docs/universal_rules/rules/PLAN_MODE.md` |
| Dùng tool đúng cách (tool-first, parallel) | `docs/universal_rules/rules/TOOL_DISCIPLINE.md` |
| Mô hình phân quyền (mode, allow/deny) | `docs/universal_rules/rules/PERMISSION_MODEL.md` |
| Kiến trúc trí nhớ (CLAUDE.md cascade) | `docs/universal_rules/rules/MEMORY_SYSTEM.md` |
| Hệ thống hook (event + exit code) | `docs/universal_rules/rules/HOOKS_REFERENCE.md` |
| Subagent / Skills / Compaction | `docs/universal_rules/rules/SUBAGENTS.md` |
| Theo dõi mục tiêu / goal drift | `docs/universal_rules/rules/OUTCOME.md` |
| Setup project mới / `check requirements` | `docs/universal_rules/rules/NEW_PROJECT_SETUP.md` |
| Tạo/update tài liệu dự án | `docs/universal_rules/rules/PROJECT_DOCS.md` |
| Code feature mới / fix bug ở codebase lớn → định vị trước | `docs/PROJECT_SUMMARY.md` (nếu project có) · thiết kế: `_meta/CODE_INDEX_ARCHITECTURE_v1.md` |
| .env / secret / biến môi trường | `docs/universal_rules/rules/ENV_RULES.md` |
| App-level security (OWASP) | `docs/universal_rules/rules/SECURITY_CHECKLIST.md` |
| UI / web / mobile | `docs/universal_rules/rules/UI_MOBILE_RULES.md` |
| Mobile web app (native feel) | `docs/universal_rules/rules/MOBILE_APP_STRICT_RULES.md` |
| **Cloudflare (Pages/Functions/D1/wrangler/auth/deploy)** | `docs/universal_rules/rules/CLOUDFLARE_RULES.md` |
| **Hệ thiết kế UI-UX của project (design system / `DESIGN.md`)** | `docs/universal_rules/rules/DESIGN_SYSTEM.md` |
| Bot (Telegram/Discord) | `docs/universal_rules/rules/BOT_COMMAND_RULES.md` |
| Google OAuth / NextAuth | `docs/universal_rules/rules/GOOGLE_OAUTH_SETUP.md` |
| Thanh toán QR SePay | `docs/universal_rules/rules/SEPAY_PAYMENT.md` |
| CI/CD (GitHub Actions) | `docs/universal_rules/rules/CI_CD_TEMPLATE.md` |
| Template README / CONTRIBUTING / ADR / GOAL / DESIGN / PR-Issue | `docs/universal_rules/templates/` |
| Quy trình lệnh dài (feature/full update/commit all/sync uni/report) | `docs/universal_rules/rules/WORKFLOWS.md` |
| Phân tích sản phẩm / growth | skill **product-growth** (PGA) |
| QA toàn diện (multi-pass) | skill **qa-multipass** (RRI-T) |
| Deploy / infra / CI-CD nâng cao | skill **infra** (INFRA) |
| Route pipeline TDK / hướng dẫn TDK | skill **tdk-master** (MASTER + HDSD) |
| Vì sao "lúc nhớ lúc quên" & kiến trúc hệ rule | `docs/universal_rules/_meta/RULE_ARCHITECTURE_v1.md` |

---

## Skills — rule ngữ cảnh tự kích hoạt

Chỉ `description` nằm trong context; body lazy-load khi đúng tình huống → không nhồi context. Cài 1 lần dùng chung mọi project:

```
python3 docs/universal_rules/skills/install_skills.py
```

| Skill | Tự kích hoạt khi | Lệnh gõ tay (tùy chọn) |
|---|---|---|
| `sepay-payment` | tích hợp thanh toán QR SePay | — |
| `google-oauth` | đăng nhập Google / NextAuth | — |
| `mobile-webapp` | web app mobile native-feel | — |
| `app-security` | viết code app có auth/upload/payment | `check code` |
| `bot-commands` | thêm/sửa lệnh bot | — |
| `ci-cd` | tạo pipeline GitHub Actions | — |
| `product-growth` | phân tích sản phẩm / growth / positioning | `check growth` |
| `qa-multipass` | QA toàn diện multi-pass | `check quality` |
| `infra` | setup server / deploy / monitoring | `setup server` |
| `tdk-master` | route pipeline TDK từ câu hỏi thô | `tdk: [câu hỏi]` |

Skill **self-contained** (chi tiết nằm trong `skills/<name>/references/`) — copy sang project khác chạy được ngay.

---

## Universal Commands

Chi tiết quy trình các lệnh phức tạp → `docs/universal_rules/rules/WORKFLOWS.md`.

| Lệnh | Hành động |
|---|---|
| `feature: [tên]` | Tạo branch → Analysis Phase (Q&A) → Full Plan → chờ confirm → implement+test từng bước → DỪNG |
| `test demo` / `quick deploy` | Build + deploy demo, **KHÔNG commit/push** |
| `check code` | App Code Security check (skill `app-security`) — BẮT BUỘC trước mỗi `quick deploy` |
| `commit` | Commit + push nhánh hiện tại (update MD + CHANGELOG nếu cần trước) |
| `merge main` / `lên production` | Merge main + deploy production |
| `check requirements` | Setup mọi thứ còn thiếu theo `NEW_PROJECT_SETUP.md` |
| `read context` | Đọc CLAUDE.md + docs/ (trừ nội dung đã skill-hóa) → Goal Check → "Đã hiểu, sẵn sàng." → DỪNG |
| `report context` | Như `read context` + output summary (format trong WORKFLOWS) |
| `check goal` / `update goal` | Xem/đề xuất update GOAL.md (xem `OUTCOME.md`) |
| `full update` | One-shot cuối task: update MD → commit+push → merge → restart → report |
| `commit all` | Như `full update` + push cả repo `universal-workflow` |
| `sync uni` | Pull universal rules mới nhất, dọn file thừa (KHÔNG overwrite CLAUDE/README/GOAL/CHANGELOG project) |
| `tdk: [câu hỏi]` / `check growth` / `check quality` / `setup server` | Route tới skill tdk-master / product-growth / qa-multipass / infra |

---

## Luật bất biến → `SESSION_SPINE.md`

7 luật bất biến (tiếng Việt có dấu · làm vừa đủ · đọc trước khi sửa · verify trước khi báo xong · hỏi khi mơ hồ · bám GOAL · action-safety) **chỉ định nghĩa một nơi**: `docs/universal_rules/SESSION_SPINE.md` (hook nạp mỗi phiên). Chi tiết từng luật ở file tương ứng trong `rules/`. KHÔNG chép lại ở đây.

## Luật vận hành (đặc thù — không trùng SESSION_SPINE)

1. **KHÔNG tự ý** `git commit/push/merge`/deploy production — chỉ khi có lệnh rõ ràng (`commit`, `full update`...). Chi tiết: `rules/GIT_WORKFLOW.md`.
2. Sau `quick deploy` → báo cáo rồi **DỪNG**, không làm gì thêm (user tự verify trên môi trường thật).
3. Mọi file `.md` mới (trừ `CLAUDE.md`) → tạo trong `docs/`.
4. `CLAUDE.md` bắt buộc ở **root** project (Claude Code đọc khi khởi động).
5. Khi commit: update MD files liên quan + clear `docs/MD_FILES_TO_UPDATE.md`; nếu thay đổi thuộc 4 loại catalog-level → thêm entry `docs/CHANGELOG.md` (xem `rules/CHANGELOG_RULES.md`).
6. Thêm env var / service / dependency mới → update `docs/REQUIREMENTS_CHECK.md`.
7. Sửa bất kỳ file nào trong `docs/universal_rules/` → **push lên repo `universal-workflow` ngay trong cùng session** (xem `rules/GIT_WORKFLOW.md`).
8. Backup DB / file quan trọng: **luôn lưu 2 nơi** — `/tmp/` (nhanh) + thư mục persistent — trong cùng lệnh (`/tmp/` mất khi reboot).
9. **Package manager**: dùng `pnpm` cho project Node.js **MỚI**; project legacy có `package-lock.json` → giữ `npm`. KHÔNG mix 2 lock file. Chi tiết: `rules/NEW_PROJECT_SETUP.md`.
10. **KHÔNG dùng subprocess Python** để tạo job khi web server đang live → luôn dùng API endpoint (subprocess có event loop riêng, chết khi kết thúc → job không chạy).
11. **Cài hooks khi setup project mới**: `python3 docs/universal_rules/hooks/install_hooks.py` (notify, askback_enforce, viet_diacritics_check, goal_tracking, quality_gate).
12. **KHÔNG BAO GIỜ xin lỗi** — có lỗi thì đưa giải pháp ngay, không viết "xin lỗi/sorry".
13. **Root/sudo không NOPASSWD** → gộp mọi lệnh vào **1 file `.sh`**, bảo user chạy `bash <script>.sh` một lần. KHÔNG đưa nhiều lệnh lẻ.

> Action-safety, minimalism, verify, tool-discipline, ask-back đã có file riêng trong `rules/` — index này chỉ trỏ, không lặp.
