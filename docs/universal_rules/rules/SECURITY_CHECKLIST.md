# Security Checklist — App-level Security

_Bổ sung `INFRA_v1.md` (server-level). File này focus vào application-level security._
_Dùng khi project có auth, payment, file upload, hoặc xử lý dữ liệu nhạy cảm._

---

## 0. MUST DO — Bắt buộc trước mỗi `quick deploy` (gọi bằng `check code`)

> **Tại sao section này tồn tại:** Server bị compromise tháng 8/2024 qua lỗ hổng app code.
> Mỗi feature mới là thêm attack surface. Attacker exploit → chạy lệnh dưới quyền app user → cài miner/backdoor.
> Check này phải chạy **mọi lần**, không phải chỉ khi "nghi có lỗ hổng".

### A. Grep RCE risk trong files vừa sửa

```bash
# Chạy trên files vừa thay đổi trong feature này
grep -rn "exec\|spawn\|child_process\|os\.system\|subprocess\.run\|subprocess\.call\|eval\|shell=True" \
  [files vừa sửa] | grep -v "test_\|node_modules\|venv\|\.pyc"
```

→ Nếu có kết quả: verify input đến từ **trusted source** (constant, env var, DB value do hệ thống tạo ra) — **KHÔNG** từ request body/params/headers của user.

### B. Checklist input validation cho endpoint mới

```
□ User input → shell command?   KHÔNG BAO GIỜ (kể cả sau khi "sanitize")
□ User input → file path?       Phải dùng path.basename() + whitelist thư mục
□ User input → DB query?        Parameterized query / ORM — không string concat
□ User input → HTML render?     Escape hoặc dùng framework auto-escape (React JSX, Jinja2)
□ Endpoint cần auth?            Có auth middleware — không public khi không cần
□ Endpoint tốn resource?        Có rate limiting
```

### C. Dependency audit — BẮT BUỘC sau mỗi `npm install` hoặc `pip install`

```bash
# Node.js — chạy NGAY sau npm install, trước khi làm gì khác
npm audit --audit-level=high

# Python — chạy NGAY sau pip install
pip audit
```

→ **Nếu có high/critical: fix trước khi tiếp tục**. Không deploy code có known vulnerability.
→ Commit lock file (`package-lock.json` / `requirements.txt`) cùng lúc với code thay đổi.

---

## 1. OWASP Top 10 — Checklist thực dụng

### A01: Broken Access Control
```
□ Mọi API endpoint có auth check (middleware/decorator)
□ Không dùng client-side check thay server-side
□ Verify ownership: user chỉ truy cập được data của mình
□ Admin routes có role check riêng
□ CORS config chỉ allow domains cần thiết
```

### A02: Cryptographic Failures
```
□ Passwords hash bằng bcrypt/argon2 (KHÔNG MD5/SHA)
□ Sensitive data encrypted at rest (DB encryption, file encryption)
□ Tokens (JWT, session) có expiry hợp lý
□ HTTPS everywhere — không có mixed content
□ Secrets KHÔNG hardcode trong code (xem docs/universal_rules/rules/ENV_RULES.md)
```

### A03: Injection
```
□ SQL: Dùng parameterized queries / ORM — KHÔNG string concatenation
□ NoSQL: Validate input type trước khi query
□ Command injection: KHÔNG truyền user input vào shell commands
□ XSS: Escape/sanitize mọi user input trước khi render HTML
□ Template injection: Dùng auto-escaping (Jinja2, React JSX)
```

### A04: Insecure Design
```
□ Rate limiting trên auth endpoints (login, register, forgot password)
□ Rate limiting trên API endpoints tốn resource (AI calls, file processing)
□ Brute force protection: lockout sau N lần sai
□ Business logic validation ở server-side, không chỉ client
```

### A05: Security Misconfiguration
```
□ Debug mode OFF trong production
□ Default credentials đã đổi (DB, admin panel)
□ Error messages KHÔNG leak stack trace / internal info cho user
□ Unnecessary features/endpoints disabled
□ Security headers trong response (xem Section 3)
```

### A06: Vulnerable Components
```
□ npm audit / pip audit — KHÔNG có critical/high vulnerabilities
□ Dependencies update định kỳ (ít nhất monthly)
□ KHÔNG dùng packages bị abandoned (>2 năm không update)
□ Lock file (package-lock.json / requirements.txt) commit vào repo
```

### A07: Authentication Failures
```
□ Password policy: minimum 8 chars
□ Session tokens regenerate sau login
□ Logout invalidate session ở server-side
□ "Remember me" token riêng, không dùng session token
□ Multi-factor auth cho admin accounts (nếu applicable)
```

### A08: Data Integrity Failures
```
□ Verify integrity của packages (lock files)
□ CI/CD pipeline có security scan
□ KHÔNG deserialize untrusted data (pickle, eval, JSON.parse từ user)
```

### A09: Logging & Monitoring Failures
```
□ Log auth events (login success/fail, password change)
□ Log access to sensitive data
□ Logs KHÔNG chứa passwords, tokens, hoặc PII
□ Log rotation configured (tránh disk full)
□ Alert cho suspicious activities (nhiều login fail, unusual patterns)
```

### A10: Server-Side Request Forgery (SSRF)
```
□ Validate/whitelist URLs khi app fetch external resources
□ KHÔNG cho user input trực tiếp vào URL fetch
□ Block internal IPs (127.0.0.1, 10.x, 192.168.x) nếu app fetch user-provided URLs
```

---

## 2. File Upload Security

```
□ Validate file type (check magic bytes, KHÔNG chỉ extension)
□ Limit file size (server-side, không chỉ client)
□ Rename uploaded files (KHÔNG dùng original filename)
□ Store ngoài webroot (không serve trực tiếp qua URL)
□ Scan malware nếu file sẽ được download bởi users khác
□ Restrict executable file types (.php, .py, .sh, .exe)
```

---

## 3. Security Headers (nginx / response)

```nginx
# Thêm vào nginx server block hoặc app response
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
# CSP tuỳ project — bắt đầu report-only, tune dần
# add_header Content-Security-Policy "default-src 'self'; ..." always;
```

---

## 4. Dependency Audit

```bash
# Node.js
npm audit                    # Check vulnerabilities
npm audit fix               # Auto-fix (minor/patch)
npm audit --audit-level=high  # Fail nếu có high/critical

# Python
pip audit                    # Cần install: pip install pip-audit
pip audit --fix             # Suggest fixes
pip audit --strict          # Fail nếu có bất kỳ vulnerability nào

# Chạy audit ÍT NHẤT mỗi tháng hoặc trước mỗi production deploy
```

---

## 4.5 Scaffold / fork hygiene — khi copy auth kit hoặc project mẫu

Khi fork một kit (auth, payment, bot...) từ project cũ sang project mới, BẮT BUỘC:

- [ ] **Đổi mọi định danh mang tên project cũ**: tên cookie/session (`doit_session` → `<project>_session`), tên bucket, prefix key, comment... Grep tên project cũ trong toàn bộ kit trước khi dùng: `grep -ri "<tên-project-cũ>" functions/ src/`.
  _Lý do (sự cố thật 6/2026): auth kit fork từ doit mang nguyên cookie `doit_session` sang iloveus + makeitworks production — cookie trùng tên giữa các site cùng parent domain có thể ghi đè session của nhau._
- [ ] **Default credential (seed user/password) PHẢI đổi ngay khi site live** — và KHÔNG dùng chung một credential cho nhiều project. Sau khi user đổi, cập nhật doc (đừng để doc ghi password cũ).
  _Lý do: `123456` dùng chung 3 project + ghi công khai trong git doc = lộ 1 nơi thủng cả cụm._
- [ ] **Secret sinh mới cho mỗi project** (`SESSION_SECRET`, API key...) — không copy secret giữa project.
- [ ] Doc setup của kit để checklist `[ ]` chưa tick — chỉ tick sau khi verify trên project MỚI (xem MD_SYSTEM.md, luật template honesty).

---

## 5. Template `docs/SECURITY.md` (project-level)

```markdown
# Security — [Project Name]

_Last reviewed: YYYY-MM-DD_

## Authentication
[Mô tả auth method: JWT/session/OAuth, token storage, expiry]

## Authorization
[Roles, permissions, ownership checks]

## Data Protection
[Encryption at rest/transit, PII handling, backup encryption]

## Known Risks & Mitigations
| Risk | Severity | Mitigation | Status |
|------|----------|------------|--------|
| ... | High/Med/Low | ... | Done/TODO |

## Audit Log
| Date | Action | Result |
|------|--------|--------|
| YYYY-MM-DD | npm audit | 0 vulnerabilities |
| YYYY-MM-DD | Security review | [summary] |
```

---

## References

- Server-level security: `INFRA_v1.md` §1 (SSH, firewall, fail2ban) + §11 (Security Audit)
- **Hardening patterns for Docker + Cloudflare stack:** `INFRA_v1.md` §11.2 (SSH 2FA, UFW restrict to CF IPs, nginx DNS resolver for docker upstream, rkhunter cron, DMARC progressive, docker.sock defense in depth)
- Secrets management: `docs/universal_rules/rules/ENV_RULES.md`
- Quality gate: `docs/universal_rules/rules/QUALITY_GATES.md` — dependency audit gate
