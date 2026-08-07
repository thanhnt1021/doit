---
name: qa-multipass
description: Kích hoạt khi user muốn test kỹ trước khi ship — "kiểm thử toàn diện", "test kỹ trước khi ship", "rà chất lượng trước khi deploy", "QA nghiêm ngặt", release gate. Kiểm thử đa lượt theo 7 dimension (UI/UX, API, performance, security, data, infra, edge cases) với hard gates. Trigger en: comprehensive QA, multi-pass testing, edge case, malformed input, regression. Lệnh tay: `check quality`.
---

# QA Multi-pass — RRI-T (🐷 Bát Giới)

> Skill ngữ cảnh tự kích hoạt. Kiểm thử toàn diện dựa trên phỏng vấn ngược (7 dimension, hard gates, weighted coverage).
> Chi tiết đầy đủ: `references/RRI-T_v1.md`. Điều phối/route: skill **tdk-master**.

## Khi nào dùng
- Trước release/deploy lớn: cần rà 7 dimension (UI/UX, API/contract, performance, security, data, infra, edge cases).
- Cần áp hard gates: Zero-FAIL, Zero-MISSING, Dimension Floor ≥70%, Security Gate ≥80%.
- Cần persona QA Destroyer (edge case, malformed input) + Regression Matrix.

## Cách dùng
Đọc `references/RRI-T_v1.md` → chạy QA multi-pass theo protocol, chấm Release Gate (Green/Yellow/Red).
Lệnh gõ tay tương đương: `check quality`.
