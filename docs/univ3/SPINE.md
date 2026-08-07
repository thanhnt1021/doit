# Universal Rules v3 — SPINE (luật luôn nạp mỗi phiên)

> Nguồn CANONICAL của luật luôn-nạp. `AGENTS.md` (Codex/Cursor đọc) và phần Claude inject qua hook đều SINH TỪ file này — sửa ở đây, không sửa bản sinh ra.
> Giữ CỰC MỎNG: mỗi dòng ở đây ăn context của MỌI phiên. Chi tiết KHÔNG nằm ở đây — gặp tình huống thì đọc đúng file/skill ở bảng dưới.
> Muốn spine RIÊNG cho project: tạo `docs/SESSION_SPINE.md` (NGOÀI thư mục univ3) — bản đó được ưu tiên và không bị ghi đè khi update.

## Luật bất biến — áp dụng mọi lúc, không cần nhắc
1. Giao tiếp **tiếng Việt có dấu** (message, label, file MD, commit). Hook/pre-commit chặn file thiếu dấu.
2. Làm **vừa đủ scope** — không tự thêm feature/refactor/abstraction. Mặc định KHÔNG tách abstraction (3 dòng lặp còn hơn 1 abstraction non; chỉ tách khi lặp ≥3 lần). Comment chỉ giải thích **WHY**, không WHAT. Không tự tạo file `.md`.
3. **Đọc file trước khi sửa**; bắt chước style xung quanh.
4. **Verify trước khi báo xong**: chạy build/test/lint thật, báo cáo trung thực (fail thì nói fail). **KHÔNG đoán trạng thái kiểm chứng được** (file/route/DB/secret/deploy/mật khẩu) — check bằng 1 lệnh rồi mới nói; cấm nguỵ trang phỏng đoán bằng "chắc là/phòng xa". Chi tiết: `rules/GATES.md` §0.
5. **Mơ hồ / xung đột / rủi ro / thiếu thông tin** → HỎI (cơ chế hỏi của harness), KHÔNG đoán. Chi tiết: `rules/ASK-BACK.md`.
6. Bám **`docs/GOAL.md`**; phát hiện lệch mục tiêu thì dừng và hỏi. Chi tiết: `rules/DOCS.md`.
7. Hành động **khó đảo ngược hoặc phạm vi rộng** (commit/push/merge/deploy, `rm -rf`, DROP, force-push, gửi mail/Slack, upload ra ngoài) → xác nhận trước. Authorization KHÔNG bắc cầu. Chi tiết: `rules/GATES.md` §Action-Safety.

## Bản đồ rule — gặp tình huống nào thì đọc gì (BẢN DUY NHẤT)
| Tình huống | Đọc |
|---|---|
| Code feature mới / fix bug ở codebase lớn | `docs/PROJECT_SUMMARY.md` (đọc TRƯỚC để định vị — nếu project có) |
| Bắt đầu việc / branch / commit / push / lệnh dài (`feature:`, `full update`, `sync uni`) | `rules/WORKFLOWS.md` · `rules/GIT.md` |
| Trước khi commit (quality gate, verify, security §0, env) | `rules/GATES.md` |
| Đụng file MD / CHANGELOG / GOAL / tài liệu / trí nhớ | `rules/DOCS.md` |
| File chung hay riêng, push đi đâu (SSOT vs project vs cá nhân) | `rules/WORKFLOWS.md` §File-Ownership |
| Hỏi ngược làm rõ trước khi làm | `rules/ASK-BACK.md` |
| Điều phối subagent / task lớn / orchestrator / flow Kỹ sư↔Thợ xây · lệnh `guide subagent` | `rules/AGENTS-ORCH.md` · `GUIDE_SUBAGENT.md` (khi user gõ "guide subagent" → đọc + trình bảng nhắc nhanh) |
| App security (OWASP) / trước deploy | skill **app-security** (`check code`) |
| UI / web / mobile / native-feel | skill **mobile-webapp** |
| SEO / GEO / canonical / og / sitemap | skill **seo-geo** |
| Bot Telegram/Discord | skill **bot-commands** · Google OAuth: skill **google-oauth** · Thanh toán QR SePay: skill **sepay-payment** |
| CI/CD GitHub Actions | skill **ci-cd** |
| Setup project mới / `check requirements` | skill **new-project-setup** |
| Tạo/update tài liệu dự án / `docs project` | skill **project-docs** |
| Phân tích growth · QA multi-pass · Deploy/infra · Route ý tưởng thô | skill **product-growth** · **qa-multipass** · **infra** · **tdk-master** |
| Gọi AI/LLM qua proxy cheapkeyai.shop (Claude/GPT/Gemini/Grok/DeepSeek · số dư + chi phí kiểu New API · thay v98store đã chết) | skill **cheapkeyai** |

## Luật vận hành (không trùng luật bất biến — nén 1 dòng/luật)
- **KHÔNG tự** `commit/push/merge`/deploy production — chỉ khi có lệnh rõ (`commit`, `full update`…). Sau `quick deploy` → báo cáo rồi DỪNG.
- Mọi `.md` mới (trừ `CLAUDE.md`/`AGENTS.md`/`README.md`) → tạo trong `docs/`. `CLAUDE.md`+`AGENTS.md` bắt buộc ở **root** project.
- Sửa bất kỳ file nào trong thư mục univ3 → đẩy về SSOT repo `thanhnt1021/univ3` **trong cùng session** (`rules/WORKFLOWS.md` §sync-uni).
- **KHÔNG BAO GIỜ xin lỗi** — có lỗi thì đưa giải pháp ngay.
- Backup DB/file quan trọng: lưu 2 nơi (`/tmp/` + thư mục persistent) trong cùng lệnh.
- Package manager: `pnpm` cho project Node MỚI; project legacy có `package-lock.json` giữ `npm`. Không mix 2 lock file.
- Root/sudo không NOPASSWD → gộp mọi lệnh vào **1 file `.sh`**, bảo user chạy `bash <script>.sh` một lần.

## Rule Budget (chống phình — mỗi dòng spine ăn context MỌI phiên; data: +20% cost/dòng thừa)
- Thêm 1 dòng luôn-nạp phải qua **4 cửa lọc** (rớt 1 → cắt): (1) agent tự `ls/grep/cat` ra được? → xoá; (2) thiếu nó agent làm **SAI/TỐN gì CỤ THỂ**? bằng 1 hành vi ("chạy npm thay pnpm") → giữ; "cho hiểu context" → xoá; (3) **VERIFY được**? viết mệnh lệnh (`chạy pnpm test`), không văn ("test kỹ"); (4) **mâu thuẫn** dòng khác? → sửa.
- **Add-on-failure**: chỉ thêm rule khi agent phạm **cùng lỗi lần 2**, không viết 400 dòng upfront. Ép được bằng hook/pre-commit/linter → **CHUYỂN xuống đó** (markdown = xác suất, hook/`permissions.deny` = cổng tất định).
- SSOT = **code base**. **Overview / cây thư mục / mô tả module → CẤM viết vào rule** (agent tự đọc; data: vô dụng mà vẫn tính phí). Plan/report xong → xoá. KHÔNG đọc `_meta/_archive/` (tài liệu chết).
