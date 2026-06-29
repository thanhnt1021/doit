# Hướng dẫn sử dụng — Universal Rules

Bộ rule dùng chung để Claude Code (và các agent khác) làm việc trên MỌI project theo cùng một kỷ luật: đọc context trước, hỏi khi mơ hồ, verify trước khi báo xong, không tự ý commit/deploy, bám GOAL, ghi audit log khi xoá/đổi.

> **Triết lý:** rule "phải luôn đúng" → đẩy xuống **hook** (harness tự ép, model không quên được). Rule "khi cần" → **skill** lazy-load. Phần còn lại → file chi tiết, chỉ đọc khi gặp tình huống. Bản đồ ở `INDEX.md`, luật bất biến ở `SESSION_SPINE.md`.

---

## 1. Cài vào một project (1 lần)

Từ thư mục gốc project đích:

```bash
# Cách nhanh nhất — script tự clone + copy + tạo CLAUDE.md/README/GOAL
curl -fsSL https://raw.githubusercontent.com/<user>/<repo>/main/bootstrap.sh | bash
```

Hoặc nếu đã có sẵn folder `docs/universal_rules/` (copy tay): chạy 2 installer dưới.

**Cài hook + skill (dùng chung mọi project, chạy 1 lần là đủ):**
```bash
python3 docs/universal_rules/hooks/install_hooks.py     # SessionStart spine, ask-back, verify, goal, tiếng Việt...
python3 docs/universal_rules/skills/install_skills.py   # 10 skill tự kích hoạt
```

Sau đó mở Claude Code trong project và gõ:
```
check requirements
```
Claude tự tạo file còn thiếu (`docs/GOAL.md`, `docs/REQUIREMENTS_CHECK.md`...) và hướng dẫn cấu hình.

---

## 2. Vòng lặp làm việc hằng ngày

```
feature: <tên>   →   (Claude tạo branch, hỏi Q&A, in plan, CHỜ bạn confirm)
   ↓ bạn gõ "làm đi"
Claude code từng bước + test       →   quick deploy (bạn tự verify)
   ↓ ưng
commit   /   full update            →   (update MD + GOAL + CHANGELOG, rồi commit/merge/deploy)
```

- **Không** bao giờ Claude tự commit/push/merge/deploy — chỉ khi bạn ra lệnh rõ (`commit`, `full update`, `merge main`).
- Sau `quick deploy` Claude **dừng** chờ bạn verify trên môi trường thật.
- Plan bạn đính kèm là **input để đối chiếu**, KHÔNG phải lệnh implement — Claude vẫn hỏi trước.

---

## 3. Cheat-sheet các lệnh (gõ trong Claude)

| Lệnh | Làm gì |
|---|---|
| `check requirements` | Setup/rà mọi thứ còn thiếu cho project mới |
| `read context` | Đọc CLAUDE.md + docs/ → Goal Check → "sẵn sàng" (không output thừa) |
| `report context` | Như trên + in summary có cấu trúc |
| `feature: <tên>` | Bắt đầu một tính năng đúng quy trình (branch → Q&A → plan → confirm → code) |
| `test demo` / `quick deploy` | Build + deploy demo, KHÔNG commit |
| `check code` | Quét bảo mật file vừa sửa (skill app-security) — BẮT BUỘC trước quick deploy |
| `commit` | Commit + push nhánh hiện tại (update MD/CHANGELOG trước) |
| `full update` | One-shot cuối task: update MD → commit → merge → restart → report |
| `commit all` | Như `full update` + push luôn repo universal-workflow (khi sửa rule) |
| `merge main` / `lên production` | Merge main + deploy production |
| `check goal` / `update goal` | Xem / cập nhật GOAL.md |
| `tdk: <câu hỏi>` | Định tuyến pipeline TDK (sản phẩm/QA/infra) |
| `check growth` / `check quality` / `setup server` | Skill product-growth / qa-multipass / infra |
| `sync uni` | Kéo bản rule mới nhất về project (không đè CLAUDE/README/GOAL/CHANGELOG) |

> Chi tiết quy trình lệnh dài: `rules/WORKFLOWS.md`. Bản đồ đầy đủ: `INDEX.md`.

---

## 4. Cái gì chạy TỰ ĐỘNG (không cần nhớ)

- **Spine** (`SESSION_SPINE.md`): hook `session_context.py` nhét 7 luật bất biến vào **mỗi phiên** — tiếng Việt có dấu, làm vừa đủ, đọc trước khi sửa, verify trước khi báo xong, hỏi khi mơ hồ, bám GOAL, action-safety.
- **Hook cưỡng chế**: chặn commit khi GOAL chưa review, chặn file tiếng Việt thiếu dấu, ép verify trước khi báo "xong", ép ask-back.
- **Skill tự kích hoạt**: khi task chạm đúng ngữ cảnh (payment, oauth, mobile, bot, security, ci-cd, growth, QA, infra) — chỉ nạp khi cần, không tốn context.

Muốn spine **riêng cho 1 project** (không bị ghi đè khi update rule): tạo `docs/SESSION_SPINE.md` (NGOÀI `universal_rules/`) — hook ưu tiên file đó.

---

## 5. Hai file "trí nhớ" của project

- **`docs/GOAL.md`** — mục tiêu + milestone + "đang ở đâu" + pending. Claude bám nó để không lệch hướng; hook ép review trước khi commit.
- **`docs/CHANGELOG.md`** — audit log: ghi khi **xoá / đổi tên / đổi hợp đồng / đổi nguyên tắc** (4 loại). Trả lời "cái này mất có chủ đích hay AI quên?". Quy ước: `rules/CHANGELOG_RULES.md`. **Chỉ thêm đúng file này — KHÔNG bootstrap catalog 6-file song song** (project đã có CLAUDE.md/GOAL.md tương đương).

---

## 6. Cập nhật & lan rule sang project khác

- Sửa rule ở **nguồn dev** (repo này) → `commit all` để push lên repo universal-workflow.
- Ở project khác: `sync uni` để kéo bản mới (chỉ đụng file chung, giữ file riêng của project).

---

## 7. Cấu trúc thư mục

```
docs/universal_rules/
├─ SESSION_SPINE.md   luật bất biến (hook nạp mỗi phiên)
├─ INDEX.md           bản đồ "rule nào ở đâu"
├─ HUONG_DAN.md       file này
├─ BOOTSTRAP.md       cài vào project mới
├─ rules/             chi tiết từng luật + WORKFLOWS.md
├─ templates/         README / CONTRIBUTING / ADR / GOAL + github_templates
├─ skills/            10 skill tự kích hoạt (gồm tdk-master/product-growth/qa-multipass/infra)
├─ hooks/  scripts/   cưỡng chế + tiện ích
└─ _meta/             tài liệu phát triển hệ rule (không phải rule vận hành)
```

---

## 8. UI/UX & `DESIGN.md` (hệ thiết kế project)

Phân biệt:
- `rules/UI_MOBILE_RULES.md` + `rules/MOBILE_APP_STRICT_RULES.md` = **cách build UI** (kỹ thuật chung mọi project).
- **`docs/DESIGN.md`** = **hệ thiết kế CỦA project này** (palette, typography, spacing, component spec, token) — nguồn sự thật để UI nhất quán.

Nếu project có UI/hệ thiết kế (Figma/Canva-exact như C-HX, hoặc ≥3 trang chung style): tạo `docs/DESIGN.md` từ `templates/DESIGN_TEMPLATE.md` (project-specific, NGOÀI `universal_rules/`), thêm `> Design system: docs/DESIGN.md` vào `CLAUDE.md`, đọc nó TRƯỚC khi đụng UI. Đổi nguyên tắc thiết kế → ghi `Constitution change` vào `docs/CHANGELOG.md`. Quy tắc đầy đủ: `rules/DESIGN_SYSTEM.md`.

---

## 9. Gỡ rối nhanh

- **Skill không nhận:** mở phiên Claude mới (skill cài vào `~/.claude/skills/` cần restart).
- **Hook không chạy:** chạy lại `install_hooks.py`; kiểm tra `~/.claude/settings.json`.
- **Spine không xuất hiện:** kiểm tra có `docs/universal_rules/SESSION_SPINE.md` không; chạy thử `python3 hooks/session_context.py`.
- **Ref tới rule:** mọi đường dẫn dùng dạng đầy đủ `docs/universal_rules/...` — đọc từ gốc project là thấy.
