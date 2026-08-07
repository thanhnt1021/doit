---
name: tdk-master
description: Kích hoạt khi user đưa ý tưởng thô và muốn biến thành sản phẩm nhưng chưa rõ làm gì tiếp — "tôi có ý tưởng này...", "biến ý tưởng thô thành sản phẩm", "nên bắt đầu từ đâu", hoặc gõ `tdk: [câu hỏi]`. Bộ điều phối: parse input thô, validate vấn đề (3-Whys, scope guard) rồi route sang nhánh growth / QA / deploy. Trigger en: route idea to pipeline, orchestrator, validate problem statement.
---

# TDK MASTER — Orchestrator (Phật Tổ + Đường Tăng)

> Skill ngữ cảnh tự kích hoạt. Bộ điều phối: parse input thô → validate problem → route tới skill đúng.
> Chi tiết đầy đủ: `references/MASTER_v1.md`.

## Khi nào dùng
- User mô tả ý tưởng/sản phẩm còn thô, chưa rõ cần làm gì tiếp.
- Cần validate Problem Statement (`[user] cần [hành động] vì [insight]`), 3-Whys, Scope Guard trước khi build.
- Cần biết câu hỏi nên route sang nhánh nào: **product-growth**, **qa-multipass**, hay **infra**.

## Cách dùng
1. Đọc `references/MASTER_v1.md` → parse input + chạy Problem Validation.
2. Route sang skill con tương ứng (skill đó tự chứa methodology của nó):
   - Growth / positioning / adoption → skill **product-growth**.
   - QA toàn diện / multi-pass → skill **qa-multipass**.
   - Deploy / server / CI-CD → skill **infra**.
3. Mỗi skill con self-contained; khi route tới, để skill đó tự đọc reference của mình.

Lệnh gõ tay tương đương: `tdk: [câu hỏi thô]`.
