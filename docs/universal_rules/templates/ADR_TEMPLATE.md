# ADR Template — Architecture Decision Records

_Dùng khi project có 3+ quyết định kỹ thuật quan trọng. Mỗi ADR ghi lại 1 quyết định._

---

## Khi nào dùng ADR

- Project có ≥ 3 quyết định kỹ thuật (chọn framework, DB, auth method, deploy strategy...)
- Quyết định ảnh hưởng kiến trúc — khó thay đổi sau này
- Cần ghi lại "tại sao chọn A thay vì B" cho người đến sau

## Cấu trúc thư mục

```
docs/
└── adr/
    ├── README.md           ← index tất cả ADR
    ├── 001-database.md
    ├── 002-auth-method.md
    └── 003-deploy-strategy.md
```

---

## Template ADR

```markdown
# ADR-[NNN]: [Tiêu đề quyết định]

_Status: [Proposed | Accepted | Deprecated | Superseded by ADR-XXX]_
_Date: YYYY-MM-DD_
_Deciders: [ai quyết định]_

## Context

[Vấn đề gì cần giải quyết? Tại sao cần quyết định lúc này?]

## Decision

[Quyết định là gì? Viết rõ ràng, 1-2 câu.]

## Alternatives

| Option | Ưu điểm | Nhược điểm | Lý do loại |
|--------|----------|------------|------------|
| **[Chosen]** | ... | ... | **Được chọn** |
| [Alt 1] | ... | ... | ... |
| [Alt 2] | ... | ... | ... |

## Consequences

**Positive:**
- ...

**Negative:**
- ...

**Risks:**
- ...
```

---

## Template `docs/adr/README.md`

```markdown
# Architecture Decision Records

| # | Quyết định | Status | Date |
|---|-----------|--------|------|
| 001 | [Tiêu đề] | Accepted | YYYY-MM-DD |
| 002 | [Tiêu đề] | Accepted | YYYY-MM-DD |
```

---

## Rules

1. Đánh số tuần tự: `001`, `002`, `003`...
2. Mỗi ADR ghi **1 quyết định** — không gom nhiều quyết định vào 1 file
3. KHÔNG sửa ADR đã Accepted — tạo ADR mới với status "Superseded by ADR-XXX"
4. ADR nhỏ gọn: 1 trang là đủ, không viết essay
5. Chỉ tạo ADR cho quyết định **khó reverse** — không cần ADR cho "dùng tabs hay spaces"
