# CI/CD Templates — GitHub Actions Workflows

_Bổ sung `INFRA_v1.md` §10 (SSH deploy pattern). File này cung cấp workflow templates đầy đủ._

---

## 1. Node.js / Next.js — Lint + Typecheck + Test + Build + Deploy

```yaml
# .github/workflows/ci.yml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  check:
    name: Lint + Type Check + Build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4
        with:
          version: 9

      - uses: actions/setup-node@v4
        with:
          node-version: '[NODE_VERSION]'
          cache: 'pnpm'

      - run: pnpm install --frozen-lockfile

      - name: Lint
        run: pnpm run lint

      - name: Type Check
        run: pnpm exec tsc --noEmit

      - name: Build
        run: pnpm run build

      - name: Test
        run: pnpm run test --passWithNoTests

  security:
    name: Security Audit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4
        with:
          version: 9

      - uses: actions/setup-node@v4
        with:
          node-version: '[NODE_VERSION]'
          cache: 'pnpm'

      - run: pnpm install --frozen-lockfile
      - run: pnpm audit --audit-level=high

  deploy:
    name: Deploy to Production
    needs: [check, security]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: /home/deploy/scripts/deploy-[PROJECT_NAME].sh
```

---

## 2. Python — Lint + Test + Deploy

```yaml
# .github/workflows/ci.yml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  check:
    name: Lint + Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '[PYTHON_VERSION]'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Syntax check
        run: python -m py_compile [MAIN_FILE]

      - name: Lint (optional)
        run: |
          pip install ruff
          ruff check .
        continue-on-error: true

      - name: Test
        run: python -m pytest --tb=short -q
        continue-on-error: true

  security:
    name: Security Audit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '[PYTHON_VERSION]'
          cache: 'pip'

      - run: pip install pip-audit
      - run: pip-audit -r requirements.txt --strict
        continue-on-error: true

  deploy:
    name: Deploy to Production
    needs: check
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /home/deploy/[PROJECT_NAME]
            git pull origin main
            source venv/bin/activate
            pip install -r requirements.txt
            sudo systemctl restart [SERVICE_NAME]
            sleep 3
            sudo systemctl is-active [SERVICE_NAME]
```

---

## 3. Docker — Build + Push + Deploy

```yaml
# .github/workflows/ci.yml
name: Docker CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    name: Build & Push Docker Image
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Login to Docker Hub
        if: github.event_name == 'push'
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_TOKEN }}

      - name: Build and Push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name == 'push' }}
          tags: |
            [DOCKER_USERNAME]/[PROJECT_NAME]:latest
            [DOCKER_USERNAME]/[PROJECT_NAME]:${{ github.sha }}

  security:
    name: Container Security Scan
    needs: build
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: '[DOCKER_USERNAME]/[PROJECT_NAME]:latest'
          format: 'table'
          severity: 'CRITICAL,HIGH'

  deploy:
    name: Deploy
    needs: [build, security]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            docker pull [DOCKER_USERNAME]/[PROJECT_NAME]:latest
            docker stop [PROJECT_NAME] || true
            docker rm [PROJECT_NAME] || true
            docker run -d --name [PROJECT_NAME] \
              --env-file /home/deploy/[PROJECT_NAME]/.env \
              -p [PORT]:[PORT] \
              [DOCKER_USERNAME]/[PROJECT_NAME]:latest
```

---

## Template Variables

| Variable | Mô tả | Ví dụ |
|----------|--------|-------|
| `[PROJECT_NAME]` | Tên project / service | `myapp`, `reading-bot` |
| `[NODE_VERSION]` | Node.js version | `20`, `22` |
| `[PYTHON_VERSION]` | Python version | `3.10`, `3.12` |
| `[MAIN_FILE]` | Python entry point | `bot.py`, `web_api.py` |
| `[SERVICE_NAME]` | systemd service name | `mybot`, `web-api` |
| `[DOCKER_USERNAME]` | Docker Hub username | `myuser` |
| `[PORT]` | App port | `3000`, `8000` |

---

## GitHub Secrets cần setup

```
Repository → Settings → Secrets and variables → Actions

Bắt buộc (SSH deploy):
  SERVER_HOST      = IP hoặc domain VPS
  SERVER_USER      = deploy (non-root user)
  SSH_PRIVATE_KEY  = Private key (ed25519 recommended)

Docker (nếu dùng):
  DOCKER_USERNAME  = Docker Hub username
  DOCKER_TOKEN     = Docker Hub access token
```

---

## Cách dùng

1. Chọn template phù hợp (Node.js / Python / Docker)
2. Copy vào `.github/workflows/ci.yml`
3. Thay `[PLACEHOLDER]` bằng giá trị thật
4. Setup GitHub Secrets
5. Push → workflow tự chạy

---

## References

- SSH deploy pattern chi tiết: `INFRA_v1.md` §10
- Deploy key setup: `INFRA_v1.md` §10.4
- Security audit: `docs/universal_rules/rules/SECURITY_CHECKLIST.md` §4
