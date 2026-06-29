# DoIt — Weekly Life Dashboard

## Ngôn ngữ
Luôn giao tiếp bằng tiếng Việt có dấu.

## Git Config
- **Account**: thanhnt1021
- **Repo**: https://github.com/thanhnt1021/doit
- **Identity**: `thanhnt1021 <thanhnt1021@users.noreply.github.com>`
- **gh account**: phải switch sang `thanhnt1021` trước khi push

```bash
gh auth switch --user thanhnt1021
git push
```

Nếu push bị lỗi "repository not found":
```bash
git remote set-url origin https://thanhnt1021:$(gh auth token)@github.com/thanhnt1021/doit.git
git push
git remote set-url origin https://github.com/thanhnt1021/doit.git  # reset lại
```

## Deploy
- **Domain**: doit.jst4.fun
- **Platform**: Cloudflare Pages (auto-deploy từ GitHub main)
- **Build command**: `npm run build`
- **Build output**: `dist`

## Tech Stack
- Vite + React (JSX)
- Inline styles (dark theme, mobile-first)
- Google Fonts: Crimson Pro, JetBrains Mono

> Đọc docs/universal_rules/INDEX.md để áp dụng universal workflow rules.
