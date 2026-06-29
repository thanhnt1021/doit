# RRI-T — REVERSE REQUIREMENTS INTERVIEW TESTING

## 🐷 Bát Giới — Kiểm thử Toàn diện dựa trên Phỏng vấn Ngược

---

```yaml
---
framework: TDK-Pipeline
role: RRI-T (Bát Giới)
version: 1.0
execution_protocol: v1
min_claude_model: sonnet
mode: [full, lite, code-path, regression, security, audit]
related_files: [MASTER_v1.md, PGA_v1.md, INFRA_v1.md]
---
```

**5 Personas × 7 Dimensions × 8 Stress Axes × Code-Path Analysis = Complete Quality**

Designed for Vietnamese Software · Optimized for Claude Code CLI
Multi-Pass Execution enforced by MASTER_v1.md

---

# PART 1: CLI EXECUTION PROTOCOL

> **Claude: đọc Part 1 TRƯỚC. Part 2 = knowledge base. Part 3 = templates.**
> **CRITICAL: MỌI execution phải dùng MULTI-PASS (EP.4). KHÔNG chạy gộp.**
> **Nếu đến từ MASTER pipeline → context đã có, skip EP.3.**

---

## EP.1 Khi nhận file này, Claude phải:

```
1. ĐỌC Part 1 — hiểu MULTI-PASS protocol
2. KHÔNG dump methodology ra cho user
3. Nếu từ MASTER → dùng context, chạy theo MASTER EP.8 enforcement
4. Nếu standalone → EP.3 Interactive Flow
5. LUÔN chạy multi-pass (EP.4) — KHÔNG BAO GIỜ gộp personas
6. LUÔN chạy self-check (EP.6) sau khi hoàn thành
```

## EP.2 Execution Modes

```
MODE 1: FULL TEST ("chạy RRI-T" / "test module X")
  → EP.3 → Multi-Pass EP.4 (5 personas) → Self-Check EP.6 → Output EP.7

MODE 2: LITE TEST ("quick test" / "check nhanh" / solo dev)
  → EP.3 → Multi-Pass EP.4 (3 personas) → Self-Check EP.6 → Output EP.7

MODE 3: CODE-PATH ONLY ("đọc code" / "trace code")
  → Hỏi module/file → Phase 1.5 only → Code-Path Map output

MODE 4: REGRESSION ("vừa fix bug" / "check regression")
  → Hỏi bug + files changed → Regression Matrix output

MODE 5: SECURITY AUDIT ("check security")
  → Security Auditor persona → D4 focused → OWASP mapping

MODE 6: SELF-AUDIT ("audit document" / "check methodology")
  → Multi-Layer Audit Protocol EP.8
```

## EP.3 Interactive Flow

```
BƯỚC 1: Thu thập context (HỎI, không đoán)
  Bắt buộc:
    - Module/feature cần test: [tên]
    - Tech stack: [ngắn gọn]
    - Có codebase access? [Y/N]
    - Solo hoặc team? [solo/small/enterprise]
  
  Tự infer:
    - Solo → Lite mode
    - Có codebase → Phase 1.5 bắt buộc
    - Vietnamese software → LOCALE stress bắt buộc

BƯỚC 2: Auto-Config
  Solo/small → Lite: 3 personas, 4 dimensions
  Enterprise → Full: 5 personas, 7 dimensions
  Có codebase → Phase 1.5 bắt buộc
  Vietnamese → Section 9 cross-reference bắt buộc
  Có payment → 📋 BA + 🔒 Security bắt buộc

BƯỚC 3: Confirm
  "Chạy RRI-T [Full/Lite] với [N] personas, [N] dimensions.
   Phase 1.5 Code-Path: [Có/Không].
   Multi-pass: [N] passes.
   OK?"
```

## EP.4 Multi-Pass Execution — CORE PROTOCOL

```
╔══════════════════════════════════════════════════════════════╗
║  CRITICAL: KHÔNG BAO GIỜ CHẠY GỘP PERSONAS.                ║
║  Mỗi pass = 1 persona = 100% focus = check KỸ hơn.         ║
║  Đây là "Khẩn Cô Chú" — enforce bởi MASTER_v1.md.             ║
╚══════════════════════════════════════════════════════════════╝

PASS 0: PHASE 1.5 — CODE-PATH ANALYSIS
  Input: Codebase access
  Action:
    - Đọc code modules trong scope
    - Trace 4 loại: Data Flow, State Mutation, Calculation, External Dep
    - Output: Code-Path Map (template T.5)
  Deliverable: Code-Path Map với [file:line] references
  → Dừng. User review. Confirm.

PASS 1: PERSONA 👤 END USER
  Focus: D1 UI/UX + D7 Edge Cases
  Input: Code-Path Map (from Pass 0)
  Action:
    - Checklist End User (Section 3.2)
    - Cross-reference Code-Path Map risks liên quan đến UX
    - Cross-reference Vietnamese checklist (Section 9)
    - Cross-reference Common Misses D1 + D7 (EP.6)
  Deliverable: Test cases formatted Q→A→R→P→T
  → Dừng. User review.

PASS 2: PERSONA 🔍 QA DESTROYER
  Focus: D2 API + D7 Edge Cases
  Input: Code-Path Map
  Action:
    - Checklist QA Destroyer (Section 3.4)
    - Code-Path Destruction Checklist (Section 3.4.1)
    - Cross-reference Common Misses D2 + D7 (EP.6)
  Deliverable: Test cases
  → Dừng. User review.

PASS 3: PERSONA 🔒 SECURITY AUDITOR
  Focus: D4 Security
  Input: Code-Path Map
  Action:
    - Checklist Security (Section 3.6)
    - Cross-reference Common Misses D4 (EP.6)
  Deliverable: Test cases
  → Dừng. User review.

[FULL MODE ONLY]
PASS 4: PERSONA 📋 BUSINESS ANALYST
  Focus: D2 API + D5 Data Integrity
  Action: Section 3.3 + Calculation Verification
  
PASS 5: PERSONA 🔧 DEVOPS
  Focus: D3 Performance + D6 Infrastructure
  Action: Section 3.5

PASS FINAL: SELF-CHECK (EP.6)
  → Chạy toàn bộ self-check checklist
  → Bổ sung test cases nếu thiếu
  → Output: Final report

LITE MODE: Pass 0 → Pass 1 → Pass 2 → Pass 3 → Self-Check
  (3 personas: 👤 + 🔍 + 🔒, thêm 📋 nếu có payment)
  
FULL MODE: Pass 0 → Pass 1 → 2 → 3 → 4 → 5 → Self-Check
```

## EP.5 Confidence Indicator

```
Mỗi test case / finding:

🟢 HIGH: Dựa trên code đọc trực tiếp + data thực tế
🟡 MEDIUM: Dựa trên architecture description + patterns
🔴 LOW: Dựa trên assumption, cần verify

Format: [finding] — Confidence: [🟢|🟡|🔴] (basis: ___)
```

## EP.6 Self-Check Protocol — BẮT BUỘC sau mỗi run

```
SAU KHI HOÀN THÀNH TẤT CẢ PASSES, Claude TỰ CHECK:

CHECK 1: COVERAGE
  □ Đã trace Code-Path cho mọi file trong scope?
    → List: [files traced] vs [files in scope but not traced]
    → Missing → bổ sung
  
  □ Mỗi applicable dimension có ≥ threshold test cases?
    Lite: ≥ 3 per dimension
    Full: ≥ 5 per dimension
    → Count per dimension → bổ sung nếu thiếu

CHECK 2: COMMON MISSES — D1 UI/UX
  □ Button throttle / debounce sau click?
  □ Loading state giữa transitions?
  □ Optimistic UI vs server response mismatch?
  □ Form state khi navigate away rồi back?
  □ Mobile keyboard push layout?
  □ Toast/notification timing + z-index + dismissal?
  □ Scroll position preservation khi back?
  □ Empty state / zero state?
  □ Error state có recovery path rõ ràng?
  □ Disabled state visual distinction?
  □ Focus trap trong modals?
  □ Vietnamese text overflow (~30% dài hơn EN)?

CHECK 3: COMMON MISSES — D2 API
  □ Race condition khi click nhanh liên tiếp?
  □ Retry logic idempotent? (POST retry tạo duplicate?)
  □ Server response > 5s — client timeout handling?
  □ Pagination edge (page 0, beyond last page)?
  □ Request body quá lớn — rejection graceful?
  □ CORS configuration đúng?
  □ API versioning?

CHECK 4: COMMON MISSES — D3 Performance
  □ N+1 query? (loop gọi DB per item)
  □ Missing database index trên cột WHERE/ORDER BY?
  □ Bundle size check? Lazy loading?
  □ Image optimization (format, size, lazy load)?
  □ Caching strategy (CDN, browser, server)?

CHECK 5: COMMON MISSES — D4 Security
  □ Horizontal access (user A xem/sửa data user B)?
  □ Input sanitization (XSS trong user-generated content)?
  □ SQL injection (raw queries)?
  □ Rate limiting trên auth + payment endpoints?
  □ Sensitive data trong API response (password hash, tokens)?
  □ File upload: type + size validation server-side?
  □ CSRF protection?
  □ JWT/session: expiry + refresh + revoke?

CHECK 6: COMMON MISSES — D5 Data
  □ Concurrent write → last-write-wins hay conflict detection?
  □ Timezone: UTC storage, GMT+7 display?
  □ VND formatting: chấm phân cách ngàn (1.234.567 ₫)?
  □ Orphaned references khi delete parent record?
  □ Cascade delete configured correctly?
  □ Soft delete vs hard delete — consistent?

CHECK 7: COMMON MISSES — D7 Edge Cases
  □ Vietnamese diacritics: search "nguyen" → "Nguyễn"?
  □ Empty string vs null vs undefined — handled consistently?
  □ Max length input (paste 1MB text)?
  □ Double submit (click 2x nhanh)?
  □ Network interruption mid-operation (payment, upload)?
  □ Browser back button during multi-step flow?
  □ Copy-paste special characters (smart quotes, emoji)?
  □ Concurrent same-user sessions (2 tabs)?

→ Mỗi item chưa check → tạo test case → thêm vào report.
→ Chỉ output report SAU KHI self-check hoàn thành.
```

## EP.7 Output Format

```
════════════════════════════════════════════════════════
RRI-T [FULL/LITE] REPORT — [Module Name]
Date: [auto]
Mode: [Full/Lite] | Personas: [list] | Dimensions: [list]
Passes completed: [N] | Self-check: [DONE/PENDING]
════════════════════════════════════════════════════════

1. PROJECT CONTEXT
   [5-10 dòng summary]

2. CODE-PATH MAP (Pass 0)
   [Top risks with file:line references]

3. TEST SUITE BY PASS
   
   PASS 1 — 👤 End User (D1 + D7):
     P0: [test cases]
     P1: [test cases]
   
   PASS 2 — 🔍 QA Destroyer (D2 + D7):
     P0: [test cases]
     P1: [test cases]
   
   PASS 3 — 🔒 Security (D4):
     P0: [test cases]
     P1: [test cases]
   
   [Pass 4, 5 if Full mode]

4. SELF-CHECK ADDITIONS
   [Test cases added from EP.6 Common Misses]

5. SCORING DASHBOARD
   [Template T.3]

6. VIETNAMESE CHECKLIST (nếu applicable)
   [Relevant items from Section 9]

7. TOP STRESS COMBOS cho project này

8. REGRESSION DEPENDENCIES
   [If fix test X → re-run Y, Z]

9. NEXT STEPS + HANDOFF
   → Nếu trong MASTER pipeline: "RRI-T xong. [N] P0 FAILs. 
      Fix trước rồi deploy, hay deploy rồi fix?"
   → Nếu standalone: "Chạy P0 tests trước. Fix. Re-run Delta."

════════════════════════════════════════════════════════
```

## EP.8 Delta Mode

```
INPUT: Previous report + Bugs fixed + Files changed
OUTPUT: Delta Report (chỉ thay đổi)
  BUGS FIXED: [list]
  REGRESSION CHECK: [test ID]: [re-run result]
  SCORE CHANGES: [Dimension]: [old%] → [new%]
  REMAINING P0 FAILs: [count]
  VERDICT: [🟢|🟡|🔴]
```

## EP.9 Multi-Layer Self-Audit

```
Dùng để audit BẤT KỲ document/methodology/product:

LAYER 1: STRUCTURAL — "Thiếu section/concept nào?"
LAYER 2: CONSISTENCY — "Sections reference nhau đúng?"
LAYER 3: DEPTH — "Execute từng instruction — stuck ở đâu?"
LAYER 4: SELF-REFERENTIAL — "Pass tiêu chuẩn của chính nó?"
LAYER 5: ADVERSARIAL — "Hiểu sai ở đâu? Skip gì? Edge case?"
```

---

# PART 2: METHODOLOGY KNOWLEDGE BASE

> **Claude: reference khi analyzing. Không dump.**

---

## 1. TRIẾT LÝ

> *Đừng chỉ test xem phần mềm có CHẠY không. Test xem nó có SỐNG ĐƯỢC trong tay người dùng thực tế không.*

### Bốn kết quả kiểm thử

| Kết quả | Ký hiệu | Ý nghĩa | Score |
|---|---|---|---|
| PASS | ✅ | Đúng spec VÀ tốt cho user | 1.0 |
| PAINFUL | ⚠️ | Hoạt động nhưng UX kém | 0.5 |
| FAIL | ❌ | Sai spec hoặc không hoạt động | 0.0 |
| MISSING | 🔲 | Feature chưa có | 0.0 |

**FAIL vs PAINFUL boundary:**

| | ❌ FAIL | ⚠️ PAINFUL |
|---|---|---|
| User hoàn thành task? | KHÔNG | CÓ, nhưng khó chịu |
| Data mất/sai? | CÓ | KHÔNG |
| Workaround? | Không hoặc > 5 bước | ≤ 3 bước |

Rule: Nghi ngờ → đánh FAIL.

---

## 2. GLOSSARY

| Thuật ngữ | Nghĩa |
|---|---|
| RRI-T | Reverse Requirements Interview + Testing |
| Persona | Vai trò giả định khi test |
| Dimension (D1-D7) | 7 lĩnh vực kiểm thử |
| Stress Axis | 8 chiều áp lực |
| Q→A→R→P→T | Question → Answer → Requirement → Priority → Test case |
| P0/P1/P2/P3 | Priority: P0 = showstopper, P3 = nice-to-have |
| Hard Gate | Điều kiện bắt buộc — vi phạm = block release |
| Code-Path Map | Danh sách risks từ code trace (file:line) |

---

## 3. 5 TESTING PERSONAS

### 3.1 Overview

| Persona | Tư duy | Focus |
|---|---|---|
| 👤 End User | "Tôi dùng hàng ngày" | Workflow, UX, offline |
| 📋 Business Analyst | "Rules phải đúng" | Business rules, RBAC, audit |
| 🔍 QA Destroyer | "Tôi sẽ phá" | Edge cases, errors, concurrent |
| 🔧 DevOps | "Hệ thống chịu được?" | Deploy, scaling, recovery |
| 🔒 Security Auditor | "Ai lạm dụng?" | AuthN/Z, injection, abuse |

### 3.2 👤 End User

*"Mỗi sáng mở app, tôi làm gì?"*

Checklist:
- Daily workflow end-to-end (happy path)
- First-time experience (onboarding)
- Repeated task efficiency (bulk, shortcuts)
- Context switching (đang A → B → quay A)
- Offline/poor connectivity
- Mobile vs Desktop

Questions:
- "Task nào user làm > 10 lần/ngày?"
- "Đang edit form, mất mạng 30s — data mất?"
- "User phone rẻ, 3G chậm — load được?"

### 3.3 📋 Business Analyst

*"Mọi con số phải khớp."*

Checklist:
- Business rules accuracy
- RBAC per permission
- Data consistency cross-module
- Reporting accuracy
- Audit trail

Calculation Verification (bắt buộc sau Phase 1.5):

| Bước | Hành động |
|---|---|
| 1. Inventory | List TẤT CẢ formulas trong code [file:line] |
| 2. Chain Trace | Trace full chain qua retry/partial/error paths |
| 3. Cross-check | Output khớp giữa display/DB/log? |
| 4. Edge Values | 0, max, partial, multi-call aggregation |

### 3.4 🔍 QA Destroyer

*"Mọi thứ có thể sai SẼ sai."*

Checklist:
- Edge cases (boundary, null, empty, overflow)
- Error paths & recovery
- Concurrent operations
- Rapid sequential actions
- Undo/redo chains

#### 3.4.1 Code-Path Destruction Checklist (bắt buộc sau Phase 1.5)

| Loại | Câu hỏi destruction |
|---|---|
| Data Flow | Empty/null/unexpected type → crash? silent fail? |
| State Mutation | Interleaved handler access → data loss? overwrite? |
| DB Query | LIMIT hardcoded? Large dataset? Missing index? |
| Calculation | ALL code paths (retry/partial) → formula đúng? |
| External Call | Timeout? Error handling? Resource leak? |
| Callback/Parse | Malformed input → crash? bypass? |
| Regex | Edge cases → match sai? miss? |
| Authorization | Delete/update: ownership check? Horizontal access? |
| Resource Cleanup | Global resources: close/cleanup on shutdown? |

Rule: Mỗi mục PHẢI reference code cụ thể (file:line hoặc function name).

### 3.5 🔧 DevOps

*"Chạy đúng trên máy dev nhưng chết production."*

Checklist:
- Deployment reliability (zero-downtime?)
- Scaling behavior
- Resource consumption (CPU, memory, disk)
- Backup/restore
- DB migration safety
- Monitoring & alerts

### 3.6 🔒 Security Auditor

*"Mọi input là hostile."*

Checklist:
- Authentication & authorization bypass
- Input sanitization (XSS, SQL injection, CSRF)
- Data exposure (API leak sensitive data?)
- Rate limiting & abuse
- Sensitive data handling
- Dependency vulnerabilities

---

## 4. STRESS TEST 8 CHIỀU

| # | Chiều | Test Scenario |
|---|---|---|
| 1 | ⏱️ TIME | Deadline 5 phút, bulk ops |
| 2 | 📊 DATA | 1000 rows, search/filter/export |
| 3 | ❌ ERROR | Save sai, undo, recovery |
| 4 | 👥 COLLAB | 5 người cùng edit |
| 5 | 🚨 EMERGENCY | Supplier hủy, sự cố bất ngờ |
| 6 | 🔐 SECURITY | NV nghỉ việc, revoke access |
| 7 | 🏗️ INFRA | Server chết 2AM |
| 8 | 🌐 LOCALE | Tiếng Việt có dấu |

### Top Stress Combos

| Combo | Risk | Scenario |
|---|---|---|
| TIME × EMERGENCY | 🔴 | Deadline + sự cố |
| COLLAB × ERROR | 🔴 | Multi-user + conflict |
| COLLAB × SECURITY | 🔴 | Permission bypass concurrent |
| INFRA × DATA | 🔴 | Migration + traffic |
| INFRA × EMERGENCY | 🔴 | Server down + deadline |
| TIME × DATA | 🔴 | Bulk ops under pressure |

### Project-Specific Combos (bắt buộc)

```
Derive stress combos TỪ CODE — không chỉ generic:
1. Đọc Code-Path Map
2. Xác định cross-module dependencies
3. Tạo stress combos cho mỗi dependency
4. Project-specific > generic
```

---

## 5. 7 TESTING DIMENSIONS

| Dim | Mục tiêu | Key Check |
|---|---|---|
| D1: UI/UX | Trực quan, responsive | 0 visual deviation, WCAG |
| D2: API | Đúng contract | 100% match spec |
| D3: Performance | Nhanh, ổn định | p95 < 500ms |
| D4: Security | An toàn, đúng quyền | 0 unauthorized access |
| D5: Data | Đúng, đầy đủ, nhất quán | 100% roundtrip accuracy |
| D6: Infrastructure | Ổn định, recoverable | RTO < 15m |
| D7: Edge Cases | Xử lý bất thường | Graceful, no crash |

---

## 6. QUY TRÌNH PHASES

| Phase | Tên | Lite | Full |
|---|---|---|---|
| 1 | PREPARE | 30m | 1-2h |
| 1.5 | CODE-PATH | 30-60m | 1-3h |
| 2 | DISCOVER | 1-2h | 3-5h |
| 3 | STRUCTURE | 1h | 2-4h |
| 4 | EXECUTE | 1-3h | 2-8h |
| 5 | ANALYZE | 30m | 1-2h |

### Phase 1.5: Code-Path Analysis

4 loại trace:

**Trace 1: Data Flow** — Tìm null/empty/unexpected type
```
Với mỗi function xử lý user input:
  Input từ đâu? → Có thể null/empty? → Xử lý null thế nào? → Output đi đâu?
```

**Trace 2: State Mutation** — Tìm shared state conflict
```
Với mỗi shared state:
  Ai đọc? → Ai ghi? → Interleaved? → Data loss?
```

**Trace 3: Calculation Chain** — Tìm formula sai
```
Với mỗi calculation:
  Formula ở đâu? → Input qua bao nhiêu bước? → Bypass path? → Output khớp?
```

**Trace 4: External Dep & DB** — Tìm timeout/leak
```
External: Timeout? Error handling? Retry idempotent? Cleanup?
DB: LIMIT hardcoded? Missing index? N+1?
```

---

## 7. TEST CASE FORMAT: Q→A→R→P→T

```
ID:          [MODULE]-[DIMENSION]-[NUMBER]
Persona:     [👤|📋|🔍|🔧|🔒]

Q: [Câu hỏi CỤ THỂ từ góc nhìn persona]
A: [Expected behavior — measurable]
R: [REQ-XXX: Requirement]
P: [P0|P1|P2|P3]

T: TEST CASE
   Precondition: [Setup]
   Steps: 1... 2... 3...
   Expected: [Chi tiết — số liệu, text, timing]
   Dimension: [D1-D7]
   Stress: [nếu có]
   Code-Path: [file:line nếu từ Phase 1.5]

Result: [✅|⚠️|❌|🔲]
Regression: [Test IDs ảnh hưởng nếu fix]
Confidence: [🟢|🟡|🔴]
```

---

## 8. SCORING & HARD GATES

### Weighted Coverage

```
Weight: P0=4  P1=2  P2=1  P3=0.5
Score:  ✅=1.0  ⚠️=0.5  ❌=0.0  🔲=0.0

Weighted Score = Σ(level_score × weight) / Σ(total × weight) × 100%
```

### Hard Gates (không ngoại lệ)

| Gate | Condition | Effect |
|---|---|---|
| P0 Zero-FAIL | Bất kỳ P0 FAIL | 🔴 Block release |
| P0 Zero-MISSING | Bất kỳ P0 MISSING | 🔴 Block release |
| Dimension Floor | Bất kỳ dim < 70% | 🔴 Block |
| Security Gate | D4 < 80% | 🔴 Block |

### Release Gate

| Coverage | Status | Action |
|---|---|---|
| ≥ 85% | 🟢 Green | Release |
| 70-84% | 🟡 Yellow | Release with known issues |
| < 70% | 🔴 Red | Block |

---

## 9. VIETNAMESE-SPECIFIC TESTING

### Text & Encoding

| # | Test | Expected |
|---|---|---|
| 1 | Search "nguyen" → "Nguyễn"? | Diacritic-insensitive |
| 2 | Sort Ân, Bình, Cường, Đức | Đúng thứ tự VN (Đ sau D) |
| 3 | VN text ~30% longer | UI không vỡ |
| 4 | Diacritics small font 10px | Dấu rõ, không cắt |
| 5 | Input methods Telex/VNI | Smooth, no shortcut conflict |
| 6 | PDF export VN content | Dấu đúng, font embedded |

### Numbers, Currency, Dates

| # | Test | Expected |
|---|---|---|
| 7 | VND 1234567 | 1.234.567 ₫ |
| 8 | VND input "1.234.567" or "1234567" | Accept both |
| 9 | Phone +84 / 0912345678 | Accept both |
| 10 | Date display | DD/MM/YYYY |
| 11 | Timezone | UTC storage, GMT+7 display |

### Cross-cutting

| Concern | Test | Dimension |
|---|---|---|
| JWT + tên VN | Token encode/decode "Nguyễn" | D4 |
| Email template | "Nguyễn Văn A" render đúng | D5 |
| Sort/filter VN | 1000 tên VN sort + filter | D3 |
| Error messages | Tiếng Việt đúng ngữ pháp | D1 |
| URL slugs | /bao-cao vs /báo-cáo | D2 |

---

## 10. LITE MODE CONFIG

```
Personas: 3/5 — bắt buộc 👤 + 🔍, chọn 1:
  Có payment → + 📋 BA
  Public-facing → + 🔒 Security
  Self-hosted → + 🔧 DevOps

Dimensions: 4/7 — bắt buộc D1 + D2 + D7, chọn 1:
  Xử lý tiền/data → + D5
  Public-facing → + D4
  High traffic → + D3

Stress: 4/8 — bắt buộc TIME + ERROR + DATA + LOCALE

Total: 30-50 test cases, 4.5-8 giờ
```

---

## 11. REGRESSION MATRIX

```
BUG FIX: [Bug ID] [Mô tả]
MODULE: [module]
FILES CHANGED: [list]

DIRECT: □ Re-run test gốc  □ Re-run P0 cùng module
CROSS-MODULE: □ Modules liên quan  □ Re-run P0+P1
SIDE-EFFECT: □ Performance  □ UI  □ Data calculation

RESULT: [✅ All pass | ❌ New failures: ___]
```

---

## 12. ANTI-PATTERNS

| # | Pattern | Fix |
|---|---|---|
| 1 | "Test mọi thứ" không prioritize | P0 trước, luôn luôn |
| 2 | Copy-paste personas | Mỗi persona GÓC NHÌN khác |
| 3 | Pass/Fail binary, bỏ qua PAINFUL | Log PAINFUL = UX debt |
| 4 | Test xong quên | Archive + Regression Matrix |
| 5 | Chase 100% coverage | Weighted scoring phạt P0 FAIL |
| 6 | Solo dev chạy Full | PHẢI dùng Lite |
| 7 | Security last | D4 = hard gate, chạy sớm |
| 8 | Chạy gộp personas | **MULTI-PASS bắt buộc** |

---

## 13. INTEGRATION VỚI BỘ TDK

```
MASTER → RRI-T:
  TYPE A Phase 6 → RRI-T Lite sau build
  TYPE B Phase 4 → RRI-T Lite affected areas
  TYPE C2 → RRI-T Regression mode
  TYPE F → RRI-T mode theo scope

RRI-T → MASTER:
  P0 FAIL → MASTER routes fix (TYPE C)
  🔲 MISSING → MASTER validates via PGA: build or not?

RRI-T → PGA:
  ⚠️ PAINFUL findings → PGA input (friction in G1/G2/G6)
  UX debt accumulated → PGA reassess growth impact

RRI-T → INFRA:
  D6 FAIL → INFRA fix infra issue
  DevOps persona findings → INFRA address
  Performance findings → INFRA optimize
```

---

# PART 3: TEMPLATES

## T.1 Test Case Template

```
ID:          [MODULE]-[DIMENSION]-[NUMBER]
Persona:     [👤|📋|🔍|🔧|🔒]
Q: ___
A: ___
R: REQ-___
P: [P0|P1|P2|P3]
T: Precondition: ___
   Steps: 1.___ 2.___ 3.___
   Expected: ___
   Dimension: [D1-D7]
   Stress: ___
   Code-Path: [file:line]
Result: [✅|⚠️|❌|🔲]
Regression: ___
Confidence: [🟢|🟡|🔴]
```

## T.2 Regression Matrix Template

```
BUG FIX: ___ MODULE: ___ FILES: ___
DIRECT: □ Test gốc [ID]  □ P0 cùng module [IDs]
CROSS: □ Modules: ___  □ P0+P1: [IDs]
SIDE: □ Perf  □ UI  □ Data
RESULT: [✅|❌ New: ___]
```

## T.3 Scoring Dashboard

```
MODULE: ___  DATE: ___  MODE: [Full|Lite]

│ Dimension        │ Tests │ ✅ │ ⚠️ │ ❌ │ 🔲 │ Weighted │ Status │
│ D1: UI/UX        │       │    │    │    │    │      %   │        │
│ D2: API          │       │    │    │    │    │      %   │        │
│ D3: Performance  │       │    │    │    │    │      %   │        │
│ D4: Security     │       │    │    │    │    │      %   │        │
│ D5: Data         │       │    │    │    │    │      %   │        │
│ D6: Infra        │       │    │    │    │    │      %   │        │
│ D7: Edge Cases   │       │    │    │    │    │      %   │        │
│ TOTAL            │       │    │    │    │    │      %   │        │

HARD GATES:
  P0 FAIL:       ___ → [PASS/BLOCK]
  P0 MISSING:    ___ → [PASS/BLOCK]
  D4 Security:   ___% → [PASS/BLOCK]
  Min Dimension: ___% → [PASS/BLOCK]

VERDICT: [🟢 RELEASE | 🟡 CONDITIONAL | 🔴 BLOCKED]
```

## T.4 Triage Template

```
P0 FAIL COUNT: ___
By dimension: D1:__ D2:__ D3:__ D4:__ D5:__ D6:__ D7:__
Root cause groups: ___
Dependency chains: ___

Batch 1 (Quick < 2h): □ ___ □ ___
Batch 2 (Heavy > 1d):  □ ___

Post-fix: Remaining P0: ___  Score: ___%  Decision: [🟢|🟡|🔴]
```

## T.5 Code-Path Map Template

```
CODE-PATH MAP — [Project]  Date: ___  Mode: [Full|Lite]

DATA FLOW RISKS:
  [P?] [file:line] — [function]
    Input: ___  Risk: ___  Impact: ___  Test: →

STATE MUTATION RISKS:
  [P?] [shared_state] — [file:line]
    Readers: ___  Writers: ___  Conflict: ___  Test: →

CALCULATION RISKS:
  [P?] [file:line] — [formula]
    Chain: ___  Miss path: ___  Test: →

EXTERNAL DEP RISKS:
  [P?] [file:line] — [service]
    Timeout: ___  Error: ___  Retry: ___  Cleanup: ___  Test: →

DB QUERY RISKS:
  [P?] [file:line] — [query]
    LIMIT: ___  Index: ___  N+1: ___  Test: →

SUMMARY: Total ___ risks  P1:__ P2:__ P3:__
Top 3: 1.___ 2.___ 3.___
```

---

*RRI-T_v1.md — Bộ Tây Du Ký Pipeline v1.0*
*🐷 Bát Giới — Quality Assurance Testing Engine*
*Multi-Pass Execution · Common Misses Registry · Self-Check Protocol*
