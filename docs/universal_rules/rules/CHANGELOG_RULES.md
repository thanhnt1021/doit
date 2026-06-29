# CHANGELOG Rules — audit log của project

> Phỏng theo cách vận hành của [source-of-truth](https://github.com/ngocquang/source-of-truth).
> `docs/CHANGELOG.md` trả lời câu hỏi sống còn: **"cái này bị bỏ/đổi có CHỦ ĐÍCH, hay AI quên?"**
> Dành cho AI + dev đọc lại sau này — **KHÔNG** phải release-note cho người dùng cuối.

## ⛔ Nguyên tắc gốc: CHỈ UPGRADE — KHÔNG tạo catalog song song

source-of-truth dùng 6 file (overview / constitution / mission / roadmap / CHANGELOG / specs). Project theo hệ universal_rules **đã có sẵn tương đương** — nên **CHỈ thêm đúng `docs/CHANGELOG.md`**, TUYỆT ĐỐI KHÔNG bootstrap 5 file kia (trùng lặp + phá hệ đang chạy + xung đột hook).

| source-of-truth | Dùng file CÓ SẴN của hệ universal_rules |
|---|---|
| `constitution.md` | `CLAUDE.md` + `docs/universal_rules/` (+ `DESIGN.md` nếu có) |
| `mission.md` + `roadmap.md` | `docs/GOAL.md` (Now/Next/Later + "đang ở đâu" + PENDING) → xem `docs/universal_rules/rules/OUTCOME.md` |
| `specs/spec-*.md` | Tài liệu project trong `docs/` (xem `docs/universal_rules/rules/PROJECT_DOCS.md`) |
| `overview.md` (index) | `CLAUDE.md` (bản đồ trang + "What's DONE") |
| `CHANGELOG.md` | ⬅ **`docs/CHANGELOG.md`** — file DUY NHẤT được thêm mới |

## Khi nào PHẢI thêm entry (chỉ 4 loại sự kiện catalog-level)

- **Removed** — 1 feature / section / route bị xoá hoặc deprecate.
- **Renamed** — feature đổi tên (slug / tên file / route đổi).
- **Contract changed** — đổi 1 invariant đã ghi, đổi cấu trúc render, hoặc đổi hành vi mà nơi-gọi phải dựa vào.
- **Constitution change** — đổi nguyên tắc project: Tech Stack, Code Quality, Testing, **UX**, Performance (ở đây = `CLAUDE.md` / `DESIGN.md` / rule trong `docs/universal_rules/`).

## Khi nào KHÔNG cần entry

- Thêm feature / section MỚI (đã có trong code + `docs/GOAL.md`).
- Refactor nội bộ giữ nguyên hành vi.
- Bug fix làm code khớp lại spec (spec vốn đúng, code đuổi theo).
- Bump version asset (`?v=`), đổi cache, tinh chỉnh px/spacing thuần thị giác.

## Commit gate

Trước khi commit, nếu thay đổi rơi vào 4 loại trên → thêm entry vào `docs/CHANGELOG.md` **TRƯỚC**, rồi commit code + CHANGELOG **cùng lúc** (song song việc cập nhật `docs/GOAL.md` mà hook `goal_tracking_enforce.py` đã ép). Không rơi vào 4 loại → bỏ qua, chỉ cập nhật `GOAL.md` như cũ.

## Quy ước ghi

- 1 heading `## YYYY-MM-DD` mỗi ngày; ngày mới nhất **trên cùng**.
- Trong 1 ngày, gom theo thứ tự: **Removed → Renamed → Contract changed → Constitution change**.
- KHÔNG sửa entry ngày cũ (lịch sử bất biến). Phát hiện sót → ghi hôm nay kèm `(retroactive — thực sự đổi ngày <date>)`.
- Mỗi bullet 1–3 dòng. `Contract changed` BẮT BUỘC có `Old:` / `New:` / `Migration:` — không bao giờ bỏ trống; không cần migrate thì ghi `Migration: none — tương thích ngược`.

## Skeleton `docs/CHANGELOG.md`

```markdown
# CHANGELOG — audit log của project
> "cái này bị bỏ/đổi có CHỦ ĐÍCH, hay AI quên?" — cho AI + dev, KHÔNG phải release-note.
> Quy ước đầy đủ: docs/universal_rules/rules/CHANGELOG_RULES.md

## YYYY-MM-DD
### Removed
- **<slug>** — Reason: <vì sao>. Replaced by: <successor hoặc "nothing">.
### Renamed
- **<old>** → **<new>**. Reason: <vì sao>.
### Contract changed
- **<slug>** — Old: <cũ>. New: <mới>. Migration: <caller phải làm gì, hoặc "none — tương thích ngược">.
### Constitution change
- **<section>** — <đổi gì>. Reason: <vì sao>. Linked: <file/ADR nếu có>.
```

> Chi tiết schema gốc + decision tree đầy đủ: tham khảo `source-of-truth/skills/source-of-truth/references/changelog-guide.md`.
