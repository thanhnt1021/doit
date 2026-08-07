---
name: infra
description: Kích hoạt khi cần dựng/vận hành hạ tầng tự host hoặc deploy chắc chắn — "setup server", "deploy production", "dựng hạ tầng", "cấu hình nginx/SSL", "monitoring", "rollback khi deploy fail". Trigger en: setup server, deploy production, infrastructure, health check, systemd, docker compose, config drift, server hardening. Lệnh tay: `setup server`.
---

# Infrastructure & CI/CD — INFRA (🧔 Sa Tăng + 🐴 Bạch Long Mã)

> Skill ngữ cảnh tự kích hoạt. Server setup, deploy, monitoring, pipeline.
> Chi tiết đầy đủ: `references/INFRA_v1.md`. Điều phối/route: skill **tdk-master**.
> CI/CD cơ bản (GitHub Actions template) → skill **ci-cd**.

## Khi nào dùng
- Dựng server mới, deploy production (systemd / docker compose), cấu hình nginx/SSL.
- Cần deploy checklist (tests pass, build OK, health-check sau deploy, rollback khi fail).
- Monitoring, config-drift, per-OS upgrade, cron/registry.

## Cách dùng
Đọc `references/INFRA_v1.md` → theo section tương ứng (setup / deploy / monitoring / security audit).
Lệnh gõ tay tương đương: `setup server`.
