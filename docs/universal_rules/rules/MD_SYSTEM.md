# MD File System Rules

## Cấu trúc chuẩn

```
project-root/
  CLAUDE.md                          ← bắt buộc ở root (Claude Code CLI đọc khi khởi động)
  README.md                          ← project README ở root (từ templates/README_TEMPLATE.md)
  docs/
    GOAL.md                          ← project goal (từ templates/GOAL_TEMPLATE.md)
    CHANGELOG.md                     ← audit log project (xem rules/CHANGELOG_RULES.md)
    DESIGN.md                        ← hệ thiết kế UI-UX project (nếu có UI — xem rules/DESIGN_SYSTEM.md)
    universal_rules/                 ← copy nguyên folder này sang project mới
      SESSION_SPINE.md               ← luật bất biến, hook nạp mỗi phiên (SSOT)
      INDEX.md                       ← bản đồ "rule nào ở đâu" (đọc trước)
      BOOTSTRAP.md                   ← cài rule vào project mới
      rules/                         ← chi tiết từng luật
        GIT_WORKFLOW.md  QUALITY_GATES.md  MD_SYSTEM.md  MINIMALISM.md
        ACTION_SAFETY.md  ASK-BACK.md  OUTCOME.md  TOOL_DISCIPLINE.md
        PLAN_MODE.md  PERMISSION_MODEL.md  MEMORY_SYSTEM.md  HOOKS_REFERENCE.md
        SUBAGENTS.md  NEW_PROJECT_SETUP.md  PROJECT_DOCS.md  ENV_RULES.md
        VIETNAMESE_DIACRITICS.md  SECURITY_CHECKLIST.md  CHANGELOG_RULES.md
        UI_MOBILE_RULES.md  MOBILE_APP_STRICT_RULES.md  BOT_COMMAND_RULES.md
        GOOGLE_OAUTH_SETUP.md  SEPAY_PAYMENT.md  CI_CD_TEMPLATE.md
        WORKFLOWS.md                 ← quy trình lệnh dài (feature/full update/...)
      templates/                     ← chỉ dùng khi tạo file mới
        README_TEMPLATE.md  CONTRIBUTING_TEMPLATE.md  ADR_TEMPLATE.md  GOAL_TEMPLATE.md  DESIGN_TEMPLATE.md
        github_templates/            ← PR + Issue templates cho GitHub
      skills/                        ← rule ngữ cảnh TỰ kích hoạt (gồm product-growth/qa-multipass/infra/tdk-master)
      hooks/  scripts/               ← cưỡng chế + tiện ích
      _meta/                         ← tài liệu phát triển hệ rule (RULE_ARCHITECTURE_v1, GAP_ANALYSIS...)
    REQUIREMENTS_CHECK.md            ← tạo tự động khi `check requirements`
    MD_FILES_TO_UPDATE.md            ← tạo tự động khi `check requirements`
    [các file MD khác của project]   ← tất cả vào /docs
```

## Quy tắc

- Mọi file `.md` mới **trừ `CLAUDE.md` và `README.md`** → tạo trong `/docs/`.
  _Lý do: giữ root project sạch. Root chỉ chứa config và entry point, không phải tài liệu. `README.md` là ngoại lệ vì GitHub hiển thị nó ở trang chính của repo._

- `CLAUDE.md` ở root, có dòng: `> Chi tiết đầy đủ: docs/universal_rules/INDEX.md`
  _Lý do: Claude Code CLI chỉ đọc `CLAUDE.md` ở root khi khởi động. Nếu không có dòng reference này, Claude sẽ không biết đến bộ universal rules và không apply workflow đúng._

- Files trong `universal_rules/` là universal — **không chứa thông tin project-specific** (tên project, domain, port, env vars...).
  _Lý do: folder này được copy nguyên sang project mới. Nếu có thông tin của project A trong đây, khi copy sang project B sẽ gây nhầm lẫn hoặc lộ thông tin._

- TDK methodology (MASTER/PGA/RRI-T/INFRA/HDSD) nay nằm trong `skills/{tdk-master,product-growth,qa-multipass,infra}/references/` — **không chứa thông tin project-specific**. Version đồng bộ (tất cả _v1...).
  _Lý do: skill dùng chung nhiều project. Methodology là framework, không phải config._

- `read context` đọc `universal_rules/` nhưng **KHÔNG load nội dung đã skill-hóa** (tdk, security, payment, oauth, mobile, bot) — chúng tự kích hoạt qua skill khi đúng tình huống, hoặc trigger bằng lệnh (`tdk:`, `check quality`, `check growth`, `setup server`, `check code`).
  _Lý do: các file này lớn (~90KB riêng tdk). Load mỗi session = lãng phí context window. Chỉ load khi cần (lazy-load qua skill)._

## docs/MD_FILES_TO_UPDATE.md

File tracking để đảm bảo docs luôn đồng bộ với code — populate khi bắt đầu feature, clear sau khi commit.

_Vấn đề nó giải quyết: khi làm feature, dễ quên update tài liệu. File này là checklist nhắc "những file MD nào cần update trước khi commit feature này". Không có nó, docs dần dần lỗi thời so với code._

Template nội dung:
```
## Current Feature
[tên feature]: [mô tả ngắn]

## Files To Update
- CLAUDE.md (What's DONE)
- docs/REQUIREMENTS_CHECK.md (nếu có env/service mới)
- [các file khác liên quan]
```

## docs/REQUIREMENTS_CHECK.md

Checklist setup server cho project này — phải update mỗi khi có env var / service / dependency mới.

_Vấn đề nó giải quyết: khi deploy lên server mới (hoặc onboard người mới), nếu không có danh sách đầy đủ env vars / services cần thiết, app sẽ crash và rất khó debug tại sao. File này là "recipe" để tái tạo môi trường chạy được._

Cấu trúc xem `NEW_PROJECT_SETUP.md`.

## CLAUDE.md

Chứa thông tin project-specific để Claude có context ngay khi mở session:
- **`## ⚠️ CRITICAL WORKFLOW RULES` block** — BẮT BUỘC, đặt ngay sau heading `#`. Chứa 3 rules cứng: (1) feature workflow phải Q&A trước khi code, (2) không tự commit/push/merge/deploy, (3) dừng sau quick deploy. Phải nằm **trực tiếp** trong CLAUDE.md — không chỉ reference.
  _Lý do: CLAUDE.md là file DUY NHẤT Claude Code CLI tự động đọc mỗi session. Rules trong file được reference (`docs/universal_rules/*.md`) phụ thuộc vào việc Claude có chịu mở ra đọc không — không đảm bảo. Critical rules phải nằm trong file được auto-load._
- Tech stack, cấu trúc thư mục
- Env vars, ports, domain
- What's DONE (tóm tắt) / TODO
- Known fixes (tóm tắt — xem file history để tránh tìm lại)
- Reference line: `> Chi tiết đầy đủ: docs/universal_rules/INDEX.md`
- Reference line: `> TDK Pipeline: skill tdk-master` (hoặc `docs/universal_rules/skills/tdk-master/references/HDSD_v1.md`)

_Lý do CLAUDE.md quan trọng: Claude không có memory giữa các session. Không có file này, mỗi session mới Claude phải hỏi lại từ đầu về project, mất thời gian và dễ làm sai._

### Giới hạn kích thước CLAUDE.md — ≤40k chars

Claude Code CLI cảnh báo khi CLAUDE.md vượt 40k chars, ảnh hưởng performance. Khi project lớn dần, 2 section hay phình to nhất là **What's DONE** và **Known Fixes Applied** — đây là nội dung lịch sử, không phải context cần thiết cho task mới.

**Quy tắc:** Khi CLAUDE.md vượt 35k chars, tách 2 section đó ra file riêng:

| File | Nội dung |
|------|----------|
| `docs/DONE_HISTORY.md` | Toàn bộ danh sách tính năng đã hoàn thành |
| `docs/FIXES_HISTORY.md` | Toàn bộ danh sách bug đã gặp + cách fix |

**Trong CLAUDE.md giữ lại:**
- `## What's DONE ✓` → dòng tóm tắt ngắn (1-2 câu, liệt kê tên tính năng chính) + `> Lịch sử đầy đủ: docs/DONE_HISTORY.md`
- `## Known Fixes Applied` → 1 dòng hướng dẫn + `> Lịch sử đầy đủ: docs/FIXES_HISTORY.md`

**Khi thêm feature mới:**
- Append vào `docs/DONE_HISTORY.md` (không thêm vào CLAUDE.md body)
- Update dòng tóm tắt trong CLAUDE.md nếu cần

**Khi gặp bug + fix:**
- Append vào `docs/FIXES_HISTORY.md`
- KHÔNG thêm vào CLAUDE.md

**`read context` shorthand** nên bổ sung đọc 2 file này khi task liên quan đến lịch sử feature hoặc debug.