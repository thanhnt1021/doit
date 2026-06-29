---
name: tdk-master
description: Kích hoạt khi user đưa ý tưởng/câu hỏi thô về sản phẩm và cần ĐỊNH TUYẾN pipeline TDK (Tây Du Ký), hoặc gõ lệnh `tdk: [câu hỏi]`. Trigger vi+en: route pipeline TDK, orchestrator, parse input thô, biến ý tưởng thành sản phẩm, validate problem statement, 3-Whys, scope guard, chọn nên chạy PGA (growth) hay RRI-T (QA) hay INFRA (deploy). Đây là bộ điều phối — đọc trước để biết câu hỏi nên đi nhánh nào.
---

# TDK MASTER — Orchestrator (Phật Tổ + Đường Tăng)

> Skill ngữ cảnh tự kích hoạt. Bộ điều phối của TDK Pipeline: parse input thô → validate problem → route tới module đúng.
> Chi tiết đầy đủ: `docs/universal_rules/skills/tdk-master/references/MASTER_v1.md`. Hướng dẫn bộ TDK: `references/HDSD_v1.md`.

## Khi nào dùng
- User mô tả ý tưởng/sản phẩm còn thô, chưa rõ cần làm gì tiếp.
- Cần validate Problem Statement (`[user] cần [hành động] vì [insight]`), 3-Whys, Scope Guard trước khi build.
- Cần biết câu hỏi nên route sang nhánh nào: **product-growth** (PGA), **qa-multipass** (RRI-T), hay **infra** (INFRA).

## Cách dùng
1. Đọc `references/MASTER_v1.md` → parse input + chạy Problem Validation.
2. Route sang skill con tương ứng (đọc reference của nó):
   - Growth/positioning/adoption → `references/PGA_v1.md` (skill **product-growth**).
   - QA toàn diện/multi-pass → `references/RRI-T_v1.md` (skill **qa-multipass**).
   - Deploy/server/CI-CD → `references/INFRA_v1.md` (skill **infra**).
3. Tất cả file methodology nằm cùng `references/` nên cross-reference giữa chúng còn nguyên.

Lệnh gõ tay tương đương: `tdk: [câu hỏi thô]`.
