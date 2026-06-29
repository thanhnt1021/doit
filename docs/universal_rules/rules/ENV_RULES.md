# ENV Rules — Quản lý biến môi trường & secrets

_Áp dụng cho mọi project. Claude đọc file này khi `check requirements` hoặc setup project mới._

---

## 1. Cấu trúc file bắt buộc

```
project-root/
├── .env                 ← secrets thật (KHÔNG commit)
├── .env.example         ← template có key, KHÔNG có value (commit vào repo)
└── .gitignore           ← phải chứa .env*
```

### `.env.example` — Luôn đồng bộ với `.env`

```bash
# === DATABASE ===
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# === API KEYS ===
API_KEY=your_api_key_here
API_SECRET=your_api_secret_here

# === APP CONFIG ===
PORT=3000
NODE_ENV=production
```

**Quy tắc:**
- Mỗi khi thêm/xóa biến trong `.env` → update `.env.example` **trong cùng commit**
- Value trong `.env.example` phải là placeholder rõ ràng (`your_xxx_here`, `change_me`)
- Comment nhóm theo chức năng (Database, API, App config...)
- `.env.example` PHẢI được commit vào repo — đây là tài liệu sống cho team

### `.gitignore` — Bắt buộc chứa

```gitignore
# Environment files
.env
.env.local
.env.*.local
.env.production
.env.staging

# KHÔNG ignore .env.example — file này cần commit
!.env.example
```

---

## 2. Phân loại Secrets

| Mức độ | Loại | Ví dụ | Xử lý |
|--------|------|-------|--------|
| **Critical** | Credentials có thể gây thiệt hại tài chính/dữ liệu | DB password, API key trả phí, JWT secret, encryption key | KHÔNG BAO GIỜ log, KHÔNG hardcode, rotate khi nghi lộ |
| **Sensitive** | Credentials nội bộ, ít rủi ro tài chính | Bot token, internal API key, webhook URL | Không commit, nhưng có thể share qua kênh bảo mật |
| **Public** | Config không phải secret | PORT, NODE_ENV, APP_URL, feature flags | Có thể commit trong `.env.example` với giá trị thật |

---

## 3. Per-environment table

| Biến | Dev | Staging | Production |
|------|-----|---------|------------|
| `NODE_ENV` | development | staging | production |
| `DATABASE_URL` | localhost DB | staging DB | production DB |
| `API_KEY` | test key | test key | production key |
| `LOG_LEVEL` | debug | info | warn |
| `DEBUG` | true | true | false |

**Quy tắc:**
- KHÔNG BAO GIỜ dùng production secrets trong dev/staging
- Staging dùng credentials riêng, tách biệt hoàn toàn với production
- Dev có thể dùng chung test credentials

---

## 4. Secret Rotation Checklist (Khi nghi lộ)

Khi phát hiện secret có thể bị lộ (commit nhầm vào git, share qua kênh không an toàn, log chứa secret):

```
NGAY LẬP TỨC (trong 15 phút):
  □ Revoke/rotate secret bị lộ tại nguồn (dashboard API provider, DB server)
  □ Update .env trên tất cả server/environment
  □ Restart service để nhận secret mới
  □ Verify service hoạt động bình thường

SAU KHI ỔN ĐỊNH:
  □ Nếu secret bị commit vào git → KHÔNG chỉ xóa file
    → Phải dùng git filter-branch hoặc BFG Repo-Cleaner để xóa khỏi history
    → Hoặc chấp nhận secret đã lộ và rotate
  □ Kiểm tra access log — ai đã truy cập repo trong thời gian secret bị lộ?
  □ Update REQUIREMENTS_CHECK.md với secret mới (nếu tên biến đổi)
  □ Document incident trong commit message
```

---

## 5. Rules cho Claude Code

1. **KHÔNG BAO GIỜ** ghi giá trị secret thật vào file được commit (code, config, docs, `.env.example`)
2. **KHÔNG BAO GIỜ** log secret ra console/file — kể cả khi debug
3. Khi tạo project mới → tạo `.env.example` ngay từ đầu
4. Khi thêm biến mới vào `.env` → nhắc user update `.env.example`
5. Khi `check requirements` → verify `.gitignore` có `.env*`
6. Khi `commit` → verify không có file `.env` trong staged changes

---

## References

- Quality gate liên quan: `docs/universal_rules/rules/QUALITY_GATES.md` §4 (MD Files Updated) — `.env.example` phải đồng bộ
- Security checklist: `docs/universal_rules/rules/SECURITY_CHECKLIST.md` — app-level security bao gồm secrets management
- Server setup: `INFRA_v1.md` §4.1 — EnvironmentFile trong systemd
