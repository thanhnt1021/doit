# ASK-BACK

> **Auto-trigger trong `feature:` workflow:** Cơ chế phân tích này (Track A) tự động chạy trong Phase 1 Analysis — không cần prefix `ask back`. Dùng standalone bằng prefix `ask back` khi muốn phân tích ngoài feature workflow.

## Cơ Chế Phản Hồi Ngược Trước Khi Thực Thi

---

Khi user mở đầu message bằng `ask back`, Claude KHÔNG thực thi ngay. Claude phân tích plan so với hệ thống hiện tại, phát hiện ambiguity/conflict/gap, rồi hỏi ngược bằng **selectable options** để user chọn nhanh.

---

## 1. KHI NÀO KÍCH HOẠT

### Trigger

Message của user BẮT ĐẦU bằng một trong các lệnh:

| Lệnh | Hành vi |
|---|---|
| `ask back` | Phân tích plan → hỏi ngược → đợi trả lời → rồi mới làm |
| `ask back then do` | Phân tích → hỏi → user trả lời → tự động thực thi luôn |
| `just do` | Bỏ qua ask-back, thực thi ngay (override) |

### Không kích hoạt khi

- Message ngắn, rõ ràng, không có ambiguity (ví dụ: "fix lỗi typo dòng 42")
- User nói `just do`
- Không có plan/prompt phức tạp đi kèm

---

## 2. QUY TRÌNH ASK-BACK

```
User gửi plan
     │
     ▼
┌─────────────────────────┐
│  PHASE 1: ĐỌC HIỂU     │  Đọc plan + đọc codebase hiện tại
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  PHASE 2: SO SÁNH       │  Plan nói gì vs code thực tế có gì
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  PHASE 3: PHÁT HIỆN     │  Tìm conflict, gap, ambiguity, risk
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  PHASE 4: HỎI NGƯỢC     │  Generate + run interactive CLI prompt (Clack)
└────────────┬────────────┘
             │
             ▼
      User chọn options
             │
             ▼
┌─────────────────────────┐
│  PHASE 5: THỰC THI      │  Làm theo plan + câu trả lời
└─────────────────────────┘
```

---

## 3. PHASE 1 — ĐỌC HIỂU

Claude đọc song song:

**Từ plan/prompt của user:**
- Mục tiêu cuối cùng là gì?
- Liệt kê các thay đổi được yêu cầu
- Các constraint/điều kiện đặc biệt
- Thứ tự ưu tiên (nếu có)

**Từ codebase hiện tại:**
- Tech stack (package.json, framework, language)
- Cấu trúc thư mục
- Database schema (nếu có)
- Các file sẽ bị ảnh hưởng bởi plan
- State hiện tại: có gì đang broken? có uncommitted changes?

---

## 4. PHASE 2 — SO SÁNH

Claude tạo bảng mapping ngầm (không show user):

```
Plan yêu cầu X  ←→  Code hiện tại đã có X' (khác một chút)
Plan yêu cầu Y  ←→  Code không có gì liên quan
Plan yêu cầu Z  ←→  Code đã có Z (trùng hoàn toàn)
Plan không nhắc W ←→  Code có W mà plan sẽ phá vỡ
```

---

## 5. PHASE 3 — PHÁT HIỆN

Claude phân loại findings vào 6 categories:

| # | Loại | Mô tả | Cần hỏi? |
|---|---|---|---|
| 🔴 | **CONFLICT** | Plan mâu thuẫn với code hiện tại | BẮT BUỘC hỏi |
| 🟡 | **AMBIGUITY** | Plan nói không rõ, có thể hiểu 2+ cách | BẮT BUỘC hỏi |
| 🟠 | **RISK** | Làm được nhưng có thể break thứ khác | Nên hỏi |
| 🔵 | **GAP** | Plan thiếu thông tin cần thiết để implement | Nên hỏi |
| ⚪ | **ASSUMPTION** | Claude sẽ giả định X nếu user không nói gì | Hỏi nếu critical |
| 🟢 | **CLEAR** | Rõ ràng, không cần hỏi | Không hỏi |

**Quy tắc:** Chỉ hỏi 🔴🟡🟠🔵⚪ — KHÔNG hỏi 🟢. Nếu mọi thứ đều 🟢 → skip ask-back, thực thi luôn.

---

## 6. PHASE 4 — HỎI NGƯỢC (AskUserQuestion tool)

Claude KHÔNG output câu hỏi dạng text. Thay vào đó: dùng **`AskUserQuestion` tool** — native trong Claude Code CLI, hiện thị interactive UI với selectable options, auto có "Other" option.

### 6.1 Quy trình

**Bước 1 — Gom questions:**
Từ Phase 3, collect tất cả findings cần hỏi (tối đa 7, ưu tiên 🔴 > 🟡 > 🟠 > 🔵 > ⚪).

**Bước 2 — Call AskUserQuestion:**
- Tối đa **4 câu hỏi mỗi lần gọi** (giới hạn tool)
- Nếu có 5-7 câu → chia 2 lần gọi (nhóm critical trước)
- "Other" option tự động có — không cần thêm thủ công

**Bước 3 — Đọc answers + proceed:**
Tool trả về answers dạng object. Claude đọc → tạo Full Plan → implement.

---

### 6.2 Quy tắc dùng AskUserQuestion

- **`header`** — tối đa 12 ký tự, label ngắn cho câu hỏi (ví dụ: `"Scope"`, `"Auth"`, `"Deploy"`)
- **`options`** — 2-4 options, mỗi option có `label` (ngắn) + `description` (hệ quả cụ thể)
- **Recommended option** — đặt **đầu tiên** trong list + thêm `"(Recommended)"` vào cuối `description`
- **`multiSelect: true`** — dùng khi câu hỏi cho phép chọn nhiều (ví dụ: "chọn features muốn enable")
- **"Other"** — tự động có, user có thể type custom text — không cần thêm vào options
- **Tóm tắt plan** — output dạng text trước khi gọi tool (1-3 dòng: mục tiêu + số findings)

### 6.3 Template

```
// Trước khi gọi tool — output tóm tắt:
"Tao hiểu mày muốn: [X]. Ảnh hưởng: [Y files]. Phát hiện [N] điểm cần xác nhận."

// Gọi AskUserQuestion với 1-4 questions:
{
  question: "[N/TOTAL] 🔴 CONFLICT — [Mô tả ngắn]. [1-2 câu context]",
  header: "[Label ≤12 ký tự]",
  multiSelect: false,
  options: [
    { label: "[Option 1]", description: "[Hệ quả] (Recommended)" },
    { label: "[Option 2]", description: "[Hệ quả]" },
    { label: "[Option 3]", description: "[Hệ quả]" },  // tối đa 4
  ]
}
```

---

## 7. PHASE 5 — THỰC THI

Sau khi user trả lời (chọn options), Claude:

1. **Ghi nhận** tất cả lựa chọn
2. **Tạo execution plan** cuối cùng (dựa trên plan gốc + câu trả lời)
3. **Thực thi** theo thứ tự hợp lý
4. **Nếu gặp vấn đề mới** trong quá trình thực thi → dừng lại hỏi tiếp (nhưng chỉ khi critical)

---

## 8. VÍ DỤ THỰC TẾ

### User gửi:

```
ask back

Thêm tính năng dark mode cho app. Dùng CSS variables.
Toggle ở header. Lưu preference vào localStorage.
```

### Claude phân tích → output tóm tắt + gọi AskUserQuestion:

```
Tao hiểu mày muốn: Thêm dark mode toggle, CSS vars, persist localStorage.
Ảnh hưởng: globals.css, App.jsx, Header.jsx, 8+ components. Phát hiện 4 điểm cần xác nhận.
```

### Claude gọi AskUserQuestion tool (tối đa 4 câu/lần):

```json
{
  "questions": [
    {
      "question": "[1/4] AMBIGUITY — Scope dark mode. Plan nói 'CSS variables' nhưng 12 files dùng Tailwind hardcoded colors. Refactor toàn bộ hay chỉ CSS vars?",
      "header": "Scope",
      "multiSelect": false,
      "options": [
        { "label": "Refactor toàn bộ", "description": "Đúng intent plan, sạch nhất (Recommended)" },
        { "label": "Chỉ đổi CSS vars", "description": "Ít code — phần lớn app vẫn giữ light" },
        { "label": "Chỉ top-level body/header", "description": "Nhanh, ít risk — dark mode không hoàn chỉnh" }
      ]
    },
    {
      "question": "[2/4] RISK — 5 SVG icons dùng fill='black' sẽ invisible trên dark bg. Xử lý thế nào?",
      "header": "SVG icons",
      "multiSelect": false,
      "options": [
        { "label": "Đổi sang currentColor", "description": "1 dòng/icon, tự adapt (Recommended)" },
        { "label": "Giữ nguyên", "description": "Zero effort — icon khó thấy trên dark" },
        { "label": "Tạo 2 bộ icon", "description": "Đẹp nhất — double asset" }
      ]
    },
    {
      "question": "[3/4] GAP — Default mode khi user mở app lần đầu?",
      "header": "Default mode",
      "multiSelect": false,
      "options": [
        { "label": "Default light", "description": "Predictable, không bất ngờ (Recommended)" },
        { "label": "Theo system preference", "description": "Respect OS setting" },
        { "label": "Bắt user chọn lần đầu", "description": "Explicit — thêm friction" }
      ]
    },
    {
      "question": "[4/4] ASSUMPTION — Thêm transition 200ms khi toggle để tránh flash?",
      "header": "Transition",
      "multiSelect": false,
      "options": [
        { "label": "OK, thêm vào", "description": "Smooth UX (Recommended)" },
        { "label": "Không cần transition", "description": "Đổi ngay lập tức" }
      ]
    }
  ]
}
```

### User chọn options → Claude nhận answers → thực thi theo lựa chọn.

---

## 9. TUNING

### Điều chỉnh độ "hỏi nhiều"

Nếu Claude hỏi quá nhiều:
```
ask back --quick
```
→ Chỉ hỏi 🔴 CONFLICT và 🟡 AMBIGUITY. Bỏ qua RISK/GAP/ASSUMPTION.

Nếu muốn hỏi kỹ:
```
ask back --thorough
```
→ Hỏi tất cả 5 loại, không giới hạn 7 câu.

### Điều chỉnh format

Nếu muốn câu trả lời nhanh hơn:
```
ask back --yn
```
→ Tất cả câu hỏi chỉ Yes/No, Claude tự chọn default cho mọi thứ, user chỉ confirm hoặc reject.

---

## TÓM TẮT

```
ask back = Đọc plan → So với code → Phát hiện vấn đề → Hỏi options → Đợi user chọn → Làm

Không hỏi khi mọi thứ rõ ràng.
Hỏi ngắn gọn, có options chọn nhanh.
Ưu tiên: CONFLICT > AMBIGUITY > RISK > GAP > ASSUMPTION.
Tối đa 7 câu hỏi.
Luôn có recommendation.
```
