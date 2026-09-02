<!-- SINH TỰ ĐỘNG từ SPINE.md bởi scripts/gen_agents_md.py — KHÔNG sửa tay. -->
<!-- Codex/Cursor/Gemini đọc file này natively. Claude: thêm `@AGENTS.md` vào CLAUDE.md. -->

# Universal Rules v3 — SPINE (luật luôn nạp mỗi phiên)

> Nguồn CANONICAL của luật luôn-nạp. `AGENTS.md` (Codex/Cursor đọc) và phần Claude inject qua hook đều SINH TỪ file này — sửa ở đây, không sửa bản sinh ra.
> Giữ CỰC MỎNG: mỗi dòng ở đây ăn context của MỌI phiên. Chi tiết KHÔNG nằm ở đây — gặp tình huống thì đọc đúng file/skill ở bảng dưới.
> Muốn spine RIÊNG cho project: tạo `docs/SESSION_SPINE.md` (NGOÀI thư mục univ3) — bản đó được ưu tiên và không bị ghi đè khi update.

## Luật bất biến — áp dụng mọi lúc, không cần nhắc
1. Giao tiếp **tiếng Việt có dấu** (message, label, file MD, commit). Hook/pre-commit chặn file thiếu dấu.
2. Làm **vừa đủ scope** — không tự thêm feature/refactor/abstraction, **và KHÔNG tự làm THIẾU/subset khi port/build — parity đầy đủ, thiếu thì HỎI**. Mặc định KHÔNG tách abstraction (3 dòng lặp còn hơn 1 abstraction non; chỉ tách khi lặp ≥3 lần). Comment chỉ giải thích **WHY**, không WHAT. Không tự tạo file `.md`.
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
| Đầu ngày founder xả task rồi đi vắng · "có cái gì cần hook không" | `rules/WORKFLOWS.md` §Buổi-sáng |
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
| Build web/dự án thành **app iOS native** (SwiftUI) lên iPhone · "build iOS app" · "ký lại app" (re-sign toàn bộ) | skill **ios-native-app** |

## Luật vận hành (không trùng luật bất biến — nén 1 dòng/luật)
- **Build/fix xong → TỰ ĐỘNG commit (local) + deploy demo để test.** Nhưng **KHÔNG tự `push`/`merge`** (bảo vệ repo + main) — chỉ khi có lệnh rõ (`push`, `full update`). Sau deploy → báo cáo rồi DỪNG.
- Mọi `.md` mới (trừ `CLAUDE.md`/`AGENTS.md`/`README.md`) → tạo trong `docs/`. `CLAUDE.md`+`AGENTS.md` bắt buộc ở **root** project.
- Project có UI → **`docs/DESIGN.md` BẮT BUỘC** (SSOT token: màu/typography/spacing/radius/shadow/component). Đụng UI mà chưa có → **tạo trước** từ `templates/DESIGN_TEMPLATE.md` (rút token thật trong code, không bịa) rồi mới code. Hook `design_gate_enforce` chặn tất định file UI khi thiếu. Chi tiết: `rules/DOCS.md` §DESIGN.md.
- Sửa bất kỳ file nào trong thư mục univ3 → đẩy về SSOT repo `thanhnt1021/univ3` **trong cùng session** (`rules/WORKFLOWS.md` §sync-uni).
- Lệnh `sync uni` → chạy `~/.claude/universal-hooks/sync-uni.sh check` TRƯỚC; **cấm pull khi `check` chưa sạch**, cấm làm tay từng bước.
- **KHÔNG BAO GIỜ xin lỗi** — có lỗi thì đưa giải pháp ngay.
- Dựng tiến trình NỀN (http.server, browser Playwright, dev server, simulator) → **tự tắt trước khi kết thúc**; báo cáo THIẾU mục **"PID đã dựng / đã tắt"** = chưa xong việc. Server: `& SRV=$!` + `trap 'kill $SRV' EXIT` **trong CÙNG 1 lệnh** (`kill %1` ở lệnh Bash sau vô tác dụng — mỗi lệnh 1 shell). Playwright: `browser.close()` phải nằm trong `try/finally`, KHÔNG để cuối script (lỗi giữa chừng là browser sống mãi). Rác mồ côi quá 60' bị `stale-server-reaper.sh` thu dọn.
- Backup DB/file quan trọng: lưu 2 nơi (`/tmp/` + thư mục persistent) trong cùng lệnh.
- Package manager: `pnpm` cho project Node MỚI; **Fulfill (`EtsyFulfillChichub`) đã migrate sang `pnpm` (P043-A, 2026-08-14)** — không còn `package-lock.json`. Không mix 2 lock file.
- Root/sudo không NOPASSWD → gộp mọi lệnh vào **1 file `.sh`**, bảo user chạy `bash <script>.sh` một lần.

## Rule Budget (chống phình — mỗi dòng spine ăn context MỌI phiên; data: +20% cost/dòng thừa)
- Thêm 1 dòng luôn-nạp phải qua **4 cửa lọc** (rớt 1 → cắt): (1) agent tự `ls/grep/cat` ra được? → xoá; (2) thiếu nó agent làm **SAI/TỐN gì CỤ THỂ**? bằng 1 hành vi ("chạy npm thay pnpm") → giữ; "cho hiểu context" → xoá; (3) **VERIFY được**? viết mệnh lệnh (`chạy pnpm test`), không văn ("test kỹ"); (4) **mâu thuẫn** dòng khác? → sửa.
- **Add-on-failure**: chỉ thêm rule khi agent phạm **cùng lỗi lần 2**, không viết 400 dòng upfront. Ép được bằng hook/pre-commit/linter → **CHUYỂN xuống đó** (markdown = xác suất, hook/`permissions.deny` = cổng tất định).
- SSOT = **code base**. **Overview / cây thư mục / mô tả module → CẤM viết vào rule** (agent tự đọc; data: vô dụng mà vẫn tính phí). Plan/report xong → xoá. KHÔNG đọc `_meta/_archive/` (tài liệu chết).

## Skills — lazy rules (đọc SKILL.md tương ứng khi trúng tình huống)

> Harness có skill auto-discovery (Claude/Codex) tự kích hoạt theo description.
> Harness không có thì dùng bảng này làm index: gặp tình huống → đọc `skills/<name>/SKILL.md`.

| Skill | Khi nào dùng |
|---|---|
| `app-security` | TỰ ĐỘNG bật khi viết/sửa code có auth (login/session/JWT), payment, file upload, hoặc xử lý dữ liệu nhạy cảm — không cần user gọi. Cũng bật khi user nói "rà soát bảo mật app", "check security trước khi deploy", "code này có an toàn không... |
| `bot-commands` | Kích hoạt khi thêm/sửa/xóa lệnh cho bot Telegram (python-telegram-bot), Discord hay chatbot framework khác. User thường nói "thêm lệnh /abc cho bot", "sao gõ lệnh bot không hiện trong menu", "đăng ký command mới". Trigger vi+en - command... |
| `cheapkeyai` | Kích hoạt khi tích hợp AI/LLM qua proxy cheapkeyai.shop (OpenAI-compatible, nền New API) — gọi Claude/GPT/Gemini/Grok/DeepSeek bằng 1 SDK openai duy nhất. User thường nói "gọi AI qua cheapkeyai", "cheapapikey", "thêm chatbot AI", "dịch b... |
| `ci-cd` | Kích hoạt khi tạo pipeline CI/CD hoặc GitHub Actions tự động build/test/deploy. User thường nói "setup GitHub Actions", "tự động deploy khi push", "chạy test/lint trong CI", "deploy lên VPS qua SSH". Trigger vi+en - continuous integratio... |
| `google-oauth` | Kích hoạt khi tích hợp đăng nhập Google vào dự án Next.js. User thường nói "thêm đăng nhập bằng Google", "Sign in with Google", "social login", hoặc gặp lỗi "redirect_uri_mismatch", "access_denied". Trigger vi+en - Google Login, đăng nhậ... |
| `infra` | Kích hoạt khi cần dựng/vận hành hạ tầng tự host hoặc deploy chắc chắn — "setup server", "deploy production", "dựng hạ tầng", "cấu hình nginx/SSL", "monitoring", "rollback khi deploy fail". Trigger en: setup server, deploy production, inf... |
| `ios-native-app` | >- Kích hoạt khi muốn biến 1 web/dự án thành app iOS NATIVE (SwiftUI) cài lên iPhone thật, hoặc ký/build lại app đã có. User nói "build iOS app", "làm app iOS cho dự án này", "đưa app lên iPhone", "ký lại app", "re-sign app", "app hết hạ... |
| `mobile-webapp` | Kích hoạt khi làm web app mobile cảm giác native (giao diện điện thoại, mobile-first, responsive, bottom nav, PWA, chống zoom iOS, safe area, phone frame). Trigger vi: web app mobile, giao diện điện thoại, native feel, thanh điều hướng d... |
| `new-project-setup` | Kích hoạt khi khởi tạo/thiết lập dự án mới hoặc chạy lệnh "check requirements". Trigger vi+en - setup project mới, khởi tạo dự án, "check requirements", scaffold project, bootstrap repo, kiểm tra + tạo file còn thiếu (CLAUDE.md/README/GO... |
| `new-site` | >- Kích hoạt khi user muốn tạo một trang/web mới trên Cloudflare + GitHub chỉ bằng một câu chat — "tạo trang mới", "dựng site mới", "làm cho tao trang X", "new site X", "spin up a site". Tự động hoá trọn gói headless: scaffold code, tạo ... |
| `product-growth` | Kích hoạt khi cần đánh giá/cải thiện sản phẩm về mặt tăng trưởng — "sản phẩm này bán được không", "định vị thế nào", "làm sao để tăng trưởng", "sao user không quay lại", growth, positioning, adoption, retention, virality, monetization. T... |
| `project-docs` | Kích hoạt khi tạo hoặc cập nhật tài liệu dự án. Trigger vi+en - "docs project", "tổng hợp dự án", "viết docs cho project", "update docs", generate/update project documentation, PROJECT_SUMMARY, API reference, APP_FLOW, tài liệu kiến trúc... |
| `qa-multipass` | Kích hoạt khi user muốn test kỹ trước khi ship — "kiểm thử toàn diện", "test kỹ trước khi ship", "rà chất lượng trước khi deploy", "QA nghiêm ngặt", release gate. Kiểm thử đa lượt theo 7 dimension (UI/UX, API, performance, security, data... |
| `seo-geo` | Kích hoạt khi làm SEO/GEO cho web — lên Google, được AI (ChatGPT/Perplexity/AI Overviews) trích dẫn, xử canonical/www, sitemap, robots.txt, schema JSON-LD, og:image. CŨNG bật khi DỰNG/LAUNCH website mới (mọi web PHẢI có OG share card + t... |
| `sepay-payment` | Kích hoạt khi tích hợp thanh toán QR chuyển khoản qua SePay (đặc biệt Next.js App Router). User thường nói "thêm cổng thanh toán / nạp tiền", "tạo QR chuyển khoản", "webhook báo có tiền", "chống mất đơn khi server crash". Trigger vi+en -... |
| `tdk-master` | Kích hoạt khi user đưa ý tưởng thô và muốn biến thành sản phẩm nhưng chưa rõ làm gì tiếp — "tôi có ý tưởng này...", "biến ý tưởng thô thành sản phẩm", "nên bắt đầu từ đâu", hoặc gõ `tdk: [câu hỏi]`. Bộ điều phối: parse input thô, validat... |
