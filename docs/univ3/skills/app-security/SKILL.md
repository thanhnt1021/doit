---
name: app-security
description: TỰ ĐỘNG bật khi viết/sửa code có auth (login/session/JWT), payment, file upload, hoặc xử lý dữ liệu nhạy cảm — không cần user gọi. Cũng bật khi user nói "rà soát bảo mật app", "check security trước khi deploy", "code này có an toàn không". Trigger vi+en: app security, OWASP Top 10, input validation, injection (SQL/NoSQL/command/XSS/template), broken access control, authn/authz, file upload security, security headers, SSRF, dependency audit (npm audit/pip audit), RCE.
---

# App Security — Checklist OWASP

> Skill ngữ cảnh tự kích hoạt, self-contained. Gate §Security §0 (`check code`) tóm tắt ở `rules/GATES.md`.
> Lưu ý: skill này KHÁC `/thanhtra` (scan toàn repo) — đây là rule khi VIẾT code mới cho app.

## Khi nào dùng skill này
- Thêm/sửa endpoint, route, hoặc xử lý input của user (body/params/headers).
- Có auth, payment, file upload, hoặc xử lý dữ liệu nhạy cảm (PII, token, secret).
- Sau mỗi `pnpm install` / `pip install` (kéo theo dependency mới).
- Trước mỗi `quick deploy` / `check code` — chạy MUST DO §0 mọi lần, không chờ "nghi có lỗ hổng".

## Checklist cốt lõi (bắt buộc)

**§0 MUST DO — grep RCE trên files vừa sửa:**
- [ ] Grep `exec|spawn|child_process|os.system|subprocess.run|subprocess.call|eval|shell=True` (loại trừ test/node_modules/venv). Có hit → verify input từ **trusted source** (constant/env/DB do hệ thống tạo), KHÔNG từ request user.

**Input validation cho endpoint mới:**
- [ ] User input → shell command? KHÔNG BAO GIỜ (kể cả đã "sanitize").
- [ ] User input → file path? Dùng `path.basename()` + whitelist thư mục.
- [ ] User input → DB query? Parameterized / ORM — KHÔNG string concat.
- [ ] User input → HTML render? Escape hoặc framework auto-escape (React JSX, Jinja2).
- [ ] Endpoint cần auth → có middleware; endpoint tốn resource → có rate limiting.

**OWASP Top 10 (trọng yếu):**
- [ ] A01 Access Control: mọi endpoint có auth check server-side; verify ownership (user chỉ thấy data của mình); admin có role check; CORS chỉ allow domain cần.
- [ ] A02 Crypto: password hash bằng bcrypt/argon2 (KHÔNG MD5/SHA); token có expiry; HTTPS everywhere; secret KHÔNG hardcode.
- [ ] A03 Injection: SQL parameterized; command injection KHÔNG truyền user input vào shell; XSS escape input; template auto-escaping.
- [ ] A04 Insecure Design: rate limit auth endpoints (login/register/forgot); brute-force lockout sau N lần; business logic validate server-side.
- [ ] A05 Misconfig: debug OFF prod; default credentials đã đổi; error KHÔNG leak stack trace.
- [ ] A07 Auth: password ≥8 chars; session regenerate sau login; logout invalidate server-side.
- [ ] A08 Integrity: KHÔNG deserialize untrusted data (pickle/eval/JSON.parse từ user).
- [ ] A09 Logging: log auth events; log KHÔNG chứa password/token/PII; có alert suspicious.
- [ ] A10 SSRF: validate/whitelist URL khi app fetch external; block internal IP (127.0.0.1, 10.x, 192.168.x) nếu URL do user cung cấp.

**File upload security:**
- [ ] Validate file type bằng magic bytes (KHÔNG chỉ extension); limit size server-side.
- [ ] Rename file (KHÔNG dùng original filename); store ngoài webroot.
- [ ] Restrict executable types (.php/.py/.sh/.exe); scan malware nếu user khác download.

**Security headers (nginx / response):**
- [ ] `X-Frame-Options SAMEORIGIN`, `X-Content-Type-Options nosniff`, `Referrer-Policy strict-origin-when-cross-origin`, `Permissions-Policy` (camera/mic/geo off). CSP bắt đầu report-only, tune dần.

**Dependency audit — sau mỗi install:**
- [ ] Node: `pnpm audit --audit-level=high`. Python: `pip audit`. Có high/critical → fix TRƯỚC khi tiếp tục.
- [ ] Commit lock file (`pnpm-lock.yaml` / `requirements.txt`) cùng code thay đổi.

## Cạm bẫy / lỗi hay gặp
- "Sanitize" rồi vẫn truyền user input vào shell → vẫn RCE. Đáp án đúng: KHÔNG truyền, dùng API/arg array.
- Check quyền ở client thay vì server → bypass dễ dàng.
- Validate file chỉ bằng extension → đổi tên `.php` thành `.jpg` là qua mặt; phải check magic bytes.
- Hash password bằng MD5/SHA → dùng bcrypt/argon2.
- Hardcode secret trong code → xem `rules/GATES.md` §Env.
- Bỏ qua §0 vì "nghĩ chắc không có lỗ hổng" — phải chạy MỌI LẦN trước deploy.

## Verify trước khi báo xong
- [ ] Đã chạy grep RCE §0 trên files vừa sửa, không có hit nguy hiểm (hoặc đã verify trusted source).
- [ ] Mọi endpoint mới: auth + input validation + (nếu tốn resource) rate limiting đầy đủ.
- [ ] Đã chạy `pnpm audit` / `pip audit`, không còn high/critical; lock file đã commit.
- [ ] Không có secret/PII trong code và log.
