---
name: infra
description: Kích hoạt khi setup server, deploy, monitoring, infrastructure, pipeline CI/CD nâng cao (tự host). Trigger vi+en: setup server, deploy production, infrastructure, monitoring, health check, rollback, migration safety, systemd, docker compose, nginx, SSL, CI/CD pipeline nâng cao, config drift, per-OS upgrade, cron registry, server hardening, deploy checklist. Dùng khi cần dựng/vận hành hạ tầng tự host hoặc quy trình deploy chắc chắn.
---

# Infrastructure & CI/CD — INFRA (🧔 Sa Tăng + 🐴 Bạch Long Mã)

> Skill ngữ cảnh tự kích hoạt. Server setup, deploy, monitoring, pipeline.
> Chi tiết đầy đủ: `docs/universal_rules/skills/tdk-master/references/INFRA_v1.md`. Điều phối/route: skill **tdk-master**.
> CI/CD cơ bản (GitHub Actions template) → `docs/universal_rules/rules/CI_CD_TEMPLATE.md` hoặc skill **ci-cd**.

## Khi nào dùng
- Dựng server mới, deploy production (systemd / docker compose), cấu hình nginx/SSL.
- Cần deploy checklist (tests pass, build OK, health-check sau deploy, rollback khi fail).
- Monitoring, config-drift, per-OS upgrade, cron/registry.

## Cách dùng
Đọc `docs/universal_rules/skills/tdk-master/references/INFRA_v1.md` → theo section tương ứng (setup / deploy / monitoring / security audit).
Lệnh gõ tay tương đương: `setup server`.
