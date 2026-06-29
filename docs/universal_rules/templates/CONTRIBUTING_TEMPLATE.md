# Contributing Template

_Template cho `CONTRIBUTING.md` ở root project. Copy và điền thông tin project-specific._

---

## Template

```markdown
# Contributing — [Project Name]

## Quick Start

```bash
# Clone repo
git clone git@github.com:[user]/[repo].git
cd [repo]

# Install dependencies
[pnpm install / pip install -r requirements.txt]

# Setup environment
cp .env.example .env
# Điền values vào .env (xem .env.example cho hướng dẫn)

# Run dev
[pnpm run dev / python main.py]
```

## Branch Naming

Format: `[type]/[short-description]`

| Type | Dùng khi |
|------|----------|
| `feature/` | Thêm tính năng mới |
| `fix/` | Sửa bug |
| `refactor/` | Tái cấu trúc, không đổi behavior |
| `docs/` | Chỉ thay đổi tài liệu |
| `chore/` | Config, dependencies, scripts |

Ví dụ: `feature/user-auth`, `fix/login-crash`, `docs/api-reference`

> Chi tiết: `docs/universal_rules/rules/GIT_WORKFLOW.md`

## Commit Convention

Format: `type: short description`

```
feat: add user login with Google OAuth
fix: resolve crash when empty input submitted
docs: update API reference for /users endpoint
chore: upgrade next.js to 16.1
refactor: extract validation logic to utils
```

> Chi tiết: `docs/universal_rules/rules/QUALITY_GATES.md` §6

## Pull Request Process

1. Tạo branch từ `main` (theo naming convention trên)
2. Implement + test locally
3. Chạy quality gates trước khi push:
   - Type/lint check pass
   - Build pass
   - Runtime test pass
4. Push + tạo PR vào `main`
5. Điền PR template (tự động hiện khi tạo PR trên GitHub)
6. Request review

## Code Review Checklist

Reviewer kiểm tra:

- [ ] Code giải quyết đúng vấn đề được mô tả
- [ ] Không có security issues (injection, hardcoded secrets, missing auth)
- [ ] Error handling hợp lý — không swallow errors
- [ ] Naming rõ ràng, code đọc được
- [ ] Tests cover happy path + edge cases quan trọng
- [ ] Không có TODO/FIXME bị bỏ quên
- [ ] Docs đã update nếu behavior thay đổi

## Testing Requirements

- **Trước khi tạo PR**: test manual trên local environment
- **Unit tests**: viết cho business logic quan trọng
- **Integration tests**: viết cho API endpoints / data flows
- **Không bắt buộc 100% coverage** — focus vào paths quan trọng

## Questions?

Mở issue trên GitHub hoặc liên hệ [maintainer].
```

---

## Khi nào tạo CONTRIBUTING.md

- Project có > 1 contributor
- Project open-source
- Project có onboarding mới thường xuyên
- User yêu cầu tạo

## Notes

- Copy template trên vào `CONTRIBUTING.md` ở root project
- Thay `[placeholders]` bằng thông tin thật
- CONTRIBUTING.md nằm ở **root** (cùng level với README.md) — GitHub tự detect
