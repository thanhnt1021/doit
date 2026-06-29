# OUTCOME

## Cơ Chế Theo Dõi Mục Tiêu — Không Bao Giờ Đi Lạc

---

Mỗi lần Claude nhận task, Claude phải biết **task này phục vụ mục tiêu gì**. Nếu task đang làm không dẫn đến mục tiêu → dừng lại, nói rõ, hỏi user.

Mục tiêu được định nghĩa trong file **`GOAL.md`** (trong `docs/`). Claude PHẢI đọc `GOAL.md` trước khi làm bất cứ gì.

---

## 1. HAI FILE, HAI NHIỆM VỤ

| File | Vai trò | Ai viết | Khi nào thay đổi |
|---|---|---|---|
| **`docs/universal_rules/rules/OUTCOME.md`** (file này) | Luật chơi — cơ chế track mục tiêu | Viết 1 lần, ít thay đổi | Chỉ khi muốn đổi luật |
| **`GOAL.md`** | Mục tiêu cụ thể hiện tại | User viết/cập nhật | Mỗi khi đổi mục tiêu hoặc hoàn thành milestone |

Claude đọc cả hai. `docs/universal_rules/rules/OUTCOME.md` dạy Claude CÁCH theo dõi. `GOAL.md` nói Claude đang theo dõi CÁI GÌ.

`docs/universal_rules/rules/OUTCOME.md` là file **universal** (nằm trong `docs/universal_rules/`). `GOAL.md` là file **project-specific** (nằm trong `docs/`).

---

## 2. CẤU TRÚC GOAL.md

User tạo `GOAL.md` theo format sau (hoặc gần giống). Template đầy đủ: xem `docs/universal_rules/templates/GOAL_TEMPLATE.md` trong cùng thư mục.

```markdown
# GOAL

_Last reviewed: [YYYY-MM-DD]_

## Mục tiêu cuối cùng
[1-2 câu mô tả đích đến. Rõ ràng. Đo được.]

## Thành công trông như thế nào
- [Tiêu chí 1: cụ thể, verify được]
- [Tiêu chí 2]
- [Tiêu chí 3]

## KHÔNG phải mục tiêu (ranh giới)
- [Thứ không làm 1]
- [Thứ không làm 2]

## Milestones
- [ ] Milestone 1: [mô tả]
- [ ] Milestone 2: [mô tả]
- [x] Milestone 0: [đã xong]

## Pending / Cần Quyết Định
- [ ] [Item chưa quyết định]

## Hiện tại đang ở đâu
[1-2 câu mô tả trạng thái hiện tại, cập nhật bởi user hoặc Claude]
```

---

## 3. QUY TRÌNH CLAUDE PHẢI TUÂN THỦ

### Bước 0: ĐỌC GOAL (mỗi conversation mới)

Trước khi làm BẤT CỨ GÌ, Claude đọc `GOAL.md`:
- Mục tiêu cuối cùng là gì?
- Đang ở milestone nào?
- Ranh giới "KHÔNG phải mục tiêu" là gì?

### Bước 1: GOAL-CHECK (trước mỗi task)

Khi user gửi task, Claude tự hỏi (ngầm, không show user):

```
Task này có DẪN ĐẾN mục tiêu cuối cùng không?
├── CÓ, trực tiếp        → Làm
├── CÓ, gián tiếp        → Làm, nhưng note lý do liên quan
├── KHÔNG RÕ              → Hỏi user: "Cái này liên quan đến [goal] thế nào?"
└── KHÔNG, đi ngược       → Cảnh báo: "Cái này nằm ngoài GOAL, muốn làm không?"
```

### Bước 2: DRIFT-CHECK (giữa chừng)

Trong quá trình thực thi task dài, sau mỗi **bước lớn** (tạo file mới, refactor component, sửa nhiều files), Claude tự kiểm tra:

```
Tao vừa làm [X]. Nó có đang đưa tao gần hơn [goal] không?
├── CÓ   → Tiếp tục
├── LỆCH → Dừng, báo user: "Tao đang [X] nhưng goal là [Y]. Tiếp không?"
└── KHOẢNG CÁCH QUÁ XA → Dừng ngay, liệt kê đã đi lạc bao xa
```

### Bước 3: MILESTONE-UPDATE (sau mỗi task xong)

Khi hoàn thành 1 task có ý nghĩa, Claude:
1. Đề xuất update `GOAL.md` milestone (tick `[x]`)
2. Cập nhật "Hiện tại đang ở đâu"
3. Gợi ý bước tiếp theo DẪN ĐẾN milestone kế tiếp

---

## 4. KHI GOAL VÀ TASK MÂU THUẪN

Đôi khi user gửi task mâu thuẫn với goal. Claude xử lý:

### Mâu thuẫn nhẹ (task hơi lệch):

```
⚠️ Task này [mô tả] hơi lệch so với goal hiện tại:
   Goal: [trích dẫn]
   Task: [mô tả]

Vẫn muốn làm? Hay điều chỉnh task cho khớp goal?
  A) Làm luôn — goal tạm gác
  B) Điều chỉnh task: [đề xuất cách điều chỉnh]
  C) Cập nhật goal — thêm [task] vào scope
```

### Mâu thuẫn nặng (task đi ngược goal):

```
🔴 Task này trực tiếp mâu thuẫn với goal:
   Goal nói: "[KHÔNG phải mục tiêu: X]"
   Task yêu cầu: "[làm X]"

  A) Bỏ qua goal, làm task này
  B) Bỏ task, quay lại goal
  C) Đổi goal — cập nhật GOAL.md
```

### Goal quá khó:

Nếu trong quá trình làm, Claude phát hiện goal (hoặc milestone) **không khả thi** với approach hiện tại:

```
🟡 Milestone [X] có thể không khả thi vì:
   - [Lý do 1]
   - [Lý do 2]

Đề xuất:
  A) Đổi approach: [mô tả approach mới]
  B) Đổi milestone: [mô tả milestone thực tế hơn]
  C) Bỏ milestone này, skip sang milestone tiếp
  D) Tao tự xử — cho tao thông tin rồi tao quyết
```

---

## 5. CÁCH CLAUDE THAM CHIẾU GOAL

### Trong output/response

Claude KHÔNG lặp lại goal mỗi message (annoying). Thay vào đó:

**Khi bắt đầu session mới:**
```
📌 Goal: [1 dòng tóm tắt]
📍 Đang ở: [milestone hiện tại]
→ Task tiếp: [gợi ý dựa trên milestone]
```

**Khi hoàn thành task:**
```
✅ Xong: [mô tả]
📍 Tiến độ: [milestone X] → [% hoặc mô tả]
→ Tiếp: [gợi ý task tiếp]
```

**Khi phát hiện drift:**
```
⚠️ Tao đang [làm gì] nhưng nó không rõ liên quan đến [goal]. Tiếp?
```

### Trong code comments (không cần)

Claude KHÔNG thêm comments kiểu "// This serves GOAL milestone 3" vào code. Goal tracking là meta-level, không xuống code.

---

## 6. KẾT HỢP VỚI ASK-BACK

Trong `feature:` workflow, ASK-BACK (Track A) và OUTCOME goal-check (Track B) chạy **song song** trong Phase 1 Analysis — xem `docs/universal_rules/INDEX.md` mục `feature: Workflow`.

Khi dùng standalone `ask back` prefix:

```
ask back

[plan dài]
```

→ Claude sẽ:
1. Đọc `GOAL.md` trước
2. Phân tích plan (theo ASK-BACK)
3. **Thêm 1 câu hỏi đặc biệt** nếu plan lệch goal:

```
### 🔴 CONFLICT: Plan vs Goal

GOAL.md nói: "[mục tiêu]"
Plan này: "[mô tả phần lệch]"

→ Chọn:
  A) Plan đúng — cập nhật GOAL.md
  B) Goal đúng — điều chỉnh plan cho khớp
  C) Làm cả hai — plan trước, goal sau
```

---

## 7. KHI KHÔNG CÓ GOAL.md

Nếu Claude không tìm thấy `GOAL.md` trong project:

```
⚠️ Không tìm thấy GOAL.md. Muốn tao:
  A) Tạo GOAL.md từ context hiện tại (tao sẽ hỏi vài câu)
  B) Làm không cần goal tracking
  C) Dùng task hiện tại làm goal tạm
```

Nếu user chọn A → Claude hỏi:
```
1. Mục tiêu cuối cùng của project này là gì? (1-2 câu)
2. Thành công trông như thế nào? (2-3 tiêu chí)
3. Có gì KHÔNG nên làm không?
```

Rồi tạo `GOAL.md` từ câu trả lời (copy từ `docs/universal_rules/templates/GOAL_TEMPLATE.md` + điền thông tin).

---

## 8. CẬP NHẬT GOAL.md

### Ai cập nhật?

- **User:** Bất cứ lúc nào — đổi mục tiêu, thêm/bỏ milestone
- **Claude:** Chỉ khi user đồng ý — tick milestone xong, cập nhật "đang ở đâu"

### Claude đề xuất cập nhật khi:

- Hoàn thành milestone → "Tick [x] milestone X?"
- Phát hiện goal outdated → "GOAL.md nói [X] nhưng thực tế đã [Y]. Cập nhật?"
- Scope thay đổi → "Task mới ngoài scope. Thêm vào GOAL.md?"

### Format đề xuất:

```
📝 Đề xuất cập nhật GOAL.md:

- [x] Milestone 3: Fix lỗi server  ← TICK
- Hiện tại: "Server hoạt động, styles 00-03 lưu được. Còn 04-05."  ← CẬP NHẬT

Đồng ý?
  A) OK, cập nhật
  B) Chỉnh lại: [user sửa]
  C) Không cập nhật
```

---

## TÓM TẮT

```
GOAL.md = Đích đến. Luôn đọc trước. Luôn kiểm tra.

Trước mỗi task:  "Task này có dẫn đến goal không?"
Giữa chừng:      "Tao có đang đi đúng hướng không?"
Sau task:         "Goal tiến thêm bao nhiêu?"

Lệch → Cảnh báo + hỏi.
Mâu thuẫn → Dừng + options.
Xong milestone → Đề xuất update.
Không có goal → Hỏi tạo mới.
```

---

## CÁCH VẬN HÀNH — Nhìn Từ Góc Độ User

> Đây là hướng dẫn thực tế: **mày làm gì → Claude sẽ làm gì → kết quả là gì**.

---

### Lần đầu dùng — Tạo GOAL.md

Nếu chưa có `GOAL.md`:

1. Gõ `read context` — Claude sẽ hỏi "Muốn tạo GOAL.md không?"
2. Trả lời 3 câu: mục tiêu là gì / thành công trông ra sao / không làm gì
3. Claude tạo `GOAL.md` → mày review và sửa tay nếu cần

Hoặc tự copy `docs/universal_rules/templates/GOAL_TEMPLATE.md` → điền tay.

---

### Trigger A — Session mới (`read context`)

**Mày làm:** gõ `read context` (đầu mỗi conversation)

**Claude làm:**
1. Đọc `GOAL.md` → extract mục tiêu + milestone hiện tại
2. Output 1 dòng: `📌 Goal: [X] | 📍 Đang ở: [milestone]`
3. Nếu `_Last reviewed_` > 7 ngày **hoặc** có pending milestones chưa có tiến độ → hỏi:
   ```
   📋 Goals check — pending:
     - [ ] Milestone X: [mô tả]
     - [ ] Milestone Y: [mô tả]

   Có gì cần cập nhật không?
     A) Vẫn đúng, tiếp tục
     B) Có thay đổi — [mày mô tả]
     C) Muốn tao đề xuất next step
   ```
4. Mày confirm/update → nếu cần Claude sửa `GOAL.md` + cập nhật `_Last reviewed_`
5. **Sau đó mới báo "Đã hiểu, sẵn sàng nhận lệnh."**

**Kết quả:** Mỗi session bắt đầu với Claude biết rõ mày đang làm gì và tại sao — không bao giờ lạc.

---

### Trigger B — Bắt đầu feature (`feature: [tên]`)

**Mày làm:** gõ `feature: tên-feature [+ mô tả nếu có]`

**Claude làm:**
1. Tạo branch
2. Read context + `GOAL.md`
3. Chạy **Analysis Phase** — 3 tracks song song:
   - **Track A:** So plan vs codebase (ASK-BACK format) → CONFLICT/AMBIGUITY/RISK/GAP/ASSUMPTION
   - **Track B:** So plan vs GOAL → serve milestone nào? conflict goal nào? goal drift không?
   - **Track C:** Implementation gaps, dependencies, test strategy
4. Gom tất cả → **1 batch Q&A** (selectable options, max 7, có `← khuyến nghị`)
5. Mày chọn options
6. Claude **update `GOAL.md`** ngay: link milestone, resolve conflicts, cập nhật `_Last reviewed_`
7. Claude **print Full Plan** (approach, steps theo thứ tự, files affected, edge cases)
8. Mày confirm → implement

**Kết quả:** Mỗi feature bắt đầu với full analysis, goals đã sync, plan đã review — implement thẳng không cần dừng hỏi thêm.

---

### Trigger C — Commit (`commit`)

**Mày làm:** gõ `commit`

**Claude làm:**
1. Check: commit này có hoàn thành milestone nào không?
2. Nếu có → đề xuất:
   ```
   📝 Đề xuất update GOAL.md:
     - [x] Milestone X: [tên]         ← tick
     - "Hiện tại đang ở đâu": [câu mới]  ← cập nhật

   OK không?
     A) OK, cập nhật luôn trong commit này
     B) Chỉnh lại: [mày sửa]
     C) Không cập nhật lần này
   ```
3. Nếu không → skip hoàn toàn, không hỏi thừa

**Kết quả:** `GOAL.md` luôn phản ánh tiến độ thực tế, update cùng lúc với code — không bao giờ outdated.

---

### Bất kỳ lúc nào — Manual

**Mày sửa tay `GOAL.md`** bất cứ khi nào muốn: thêm milestone, đổi mục tiêu, tick done, update "đang ở đâu". Claude đọc lại ở session tiếp theo.

**Lệnh tắt:**
- `check goal` → Claude show tóm tắt GOAL.md + tiến độ + đề xuất bước tiếp theo
- `update goal` → Claude đề xuất những gì nên update dựa trên việc vừa làm trong session

---

### Khi task lệch goal — tự động, mày không cần làm gì

Claude tự báo:
```
⚠️ Task này [mô tả] hơi lệch so với goal hiện tại.
   Goal: [trích dẫn]
   Task: [mô tả phần lệch]

   A) Làm luôn — tạm bỏ qua goal
   B) Điều chỉnh task cho khớp goal
   C) Cập nhật goal — thêm task này vào scope
```
