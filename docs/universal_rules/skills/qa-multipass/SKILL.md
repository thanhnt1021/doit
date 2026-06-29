---
name: qa-multipass
description: Kích hoạt khi cần kiểm thử chất lượng toàn diện đa lượt trước release. Trigger vi+en: QA multi-pass, RRI-T, kiểm thử toàn diện, release gate, hard gate, weighted coverage, 7 dimensions (UI/UX, API/contract, performance, security, data roundtrip, infrastructure, edge cases), QA destroyer, edge case, malformed input, regression matrix, zero-FAIL, dimension floor, security gate. Dùng khi user muốn rà chất lượng kỹ trước khi ship/deploy.
---

# QA Multi-pass — RRI-T (🐷 Bát Giới)

> Skill ngữ cảnh tự kích hoạt. Kiểm thử toàn diện dựa trên phỏng vấn ngược (7 dimension, hard gates, weighted coverage).
> Chi tiết đầy đủ: `docs/universal_rules/skills/tdk-master/references/RRI-T_v1.md`. Điều phối/route: skill **tdk-master**.

## Khi nào dùng
- Trước release/deploy lớn: cần rà 7 dimension (UI/UX, API/contract, performance, security, data, infra, edge cases).
- Cần áp hard gates: Zero-FAIL, Zero-MISSING, Dimension Floor ≥70%, Security Gate ≥80%.
- Cần persona QA Destroyer (edge case, malformed input) + Regression Matrix.

## Cách dùng
Đọc `docs/universal_rules/skills/tdk-master/references/RRI-T_v1.md` → chạy QA multi-pass theo protocol, chấm Release Gate (Green/Yellow/Red).
Lệnh gõ tay tương đương: `check quality`.
