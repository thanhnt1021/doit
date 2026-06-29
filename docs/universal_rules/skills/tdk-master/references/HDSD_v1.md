# HƯỚNG DẪN SỬ DỤNG — BỘ TÂY DU KÝ PIPELINE

## Bộ file này là gì?

4 file methodology + 1 file hướng dẫn, thiết kế để solo dev (hoặc small team) có thể:
- Biến ý tưởng thô thành sản phẩm hoàn chỉnh
- Đảm bảo chất lượng code + UX + growth
- Quản lý infrastructure tự host
- Tất cả chỉ bằng cách chat với Claude (Code hoặc Web)

---

## Cấu trúc bộ file

```
📁 project/
├── MASTER_v1.md      📿 Phật Tổ + Đường Tăng — Orchestrator
├── PGA_v1.md         🐵 Ngộ Không — Product Growth Analysis
├── INFRA_v1.md       🧔 Sa Tăng + 🐴 Bạch Long Mã — Infrastructure + CI/CD
├── RRI-T_v1.md       🐷 Bát Giới — Quality Assurance Testing
└── HDSD_v1.md           📖 File này — Hướng dẫn sử dụng
```

| File | Vai trò Tây Du Ký | Trả lời câu hỏi |
|---|---|---|
| MASTER | Phật Tổ + Đường Tăng | "Vấn đề là gì? Làm gì trước?" |
| PGA | Tôn Ngộ Không | "Build cái gì để GROW?" |
| INFRA | Sa Tăng + Bạch Long Mã | "Server/deploy/monitoring ra sao?" |
| RRI-T | Trư Bát Giới | "Code đã build có ĐÚNG không?" |

---

## Cách sử dụng

### Bước 1: Copy cả 4 file methodology vào folder dự án

```bash
cp MASTER_v1.md PGA_v1.md INFRA_v1.md RRI-T_v1.md ~/my-project/
```

Hoặc giữ trong 1 folder chung và reference khi cần.

### Bước 2: Mở Claude Code (hoặc Claude Web) và nói bất cứ gì

Bạn **KHÔNG CẦN** biết framework, không cần đọc methodology, không cần format câu hỏi. Chỉ cần nói điều bạn muốn bằng ngôn ngữ tự nhiên.

### Bước 3: Claude đọc MASTER_v1.md → tự route → tự chạy pipeline

MASTER_v1.md sẽ:
1. Parse câu nói thô của bạn
2. Hỏi ngược 2-3 câu nếu thiếu context (gom 1 lần, không hỏi rải rác)
3. Output plan: "Tao sẽ chạy [X] → [Y] → [Z]. OK?"
4. Bạn confirm → chạy từng phase

---

## Ví dụ câu nói — từ thô nhất đến rõ nhất

### Dự án mới

```
"tao muốn làm app đếm ngày yêu nhau cho couple"
"làm bot telegram tự động post quote hay mỗi sáng"
"tao muốn bán khoá học tarot online"
"làm cái quiz phong thuỷ kiểu personality test"
```

### Feature mới cho dự án đang có

```
"hatgiong cần thêm tính năng tặng report cho bạn"
"tarot bot cần chế độ rút bài hàng ngày"
"thêm affiliate cho hatgiong"
```

### Sự cố / Fix

```
"hatgiong bị 502 từ sáng"
"user báo thanh toán xong không nhận email"
"server sắp hết disk"
```

### Mơ hồ / Chưa biết muốn gì

```
"hatgiong bán chậm quá, không biết làm gì"
"tarot bot có user nhưng không ai quay lại"
"tao muốn kiếm thêm tiền từ mấy project đang có"
"chán quá không biết build gì tiếp"
```

### Infra / Deploy

```
"setup server mới cho dự án mới, ubuntu"
"chuyển hatgiong sang VPS mới"
"setup auto deploy cho tarot bot"
```

### Check chất lượng

```
"check xem checkout flow có bug gì không"
"test kỹ cái payment page trước khi push"
"review lại toàn bộ security cho hatgiong"
```

---

## Pipeline chạy như thế nào?

Tuỳ loại request, MASTER_v1.md route vào pipeline khác nhau:

### Dự án mới (full pipeline)

```
Bạn: "tao muốn làm X"
  ↓
📿 MASTER: Hỏi ngược → Problem Statement → Route
  ↓
🐵 PGA: Phân tích growth → Hook loop → Positioning → Action roadmap
  ↓
🧔 INFRA: Setup server → Deploy config → Monitoring
  ↓
  Build code
  ↓
🐷 RRI-T: Test 5 personas × 7 dimensions → Fix bugs
  ↓
🧔 INFRA: Deploy → Smoke test
  ↓
🐵 PGA Delta: Check growth metrics sau launch
```

### Feature mới

```
Bạn: "thêm feature X"
  ↓
📿 MASTER: Classify → Route PGA
  ↓
🐵 PGA: Check affected dimensions → Action plan
  ↓
  Build
  ↓
🐷 RRI-T Lite: Test affected areas
```

### Fix bug / Sự cố

```
Bạn: "bị lỗi X"
  ↓
📿 MASTER: Classify → Route RRI-T hoặc INFRA
  ↓
🐷 RRI-T Regression: Trace bug → Fix → Regression check
  hoặc
🧔 INFRA: Server triage → Fix → Verify
```

### Không biết muốn gì

```
Bạn: "bán chậm quá"
  ↓
📿 MASTER: Hỏi ngược 2-3 câu → Classify
  ↓
🐵 PGA Full: Deep analysis → Top gaps → Action roadmap
```

---

## Quy tắc quan trọng

### Cho người dùng (bạn)

1. **Nói thô được.** Bạn là Phật Tổ — chỉ cần ra đề bài. MASTER_v1.md sẽ translate.
2. **Không cần biết gọi file nào.** MASTER_v1.md tự route.
3. **Review output mỗi phase.** Claude sẽ dừng và hỏi confirm trước khi chuyển phase.
4. **Nếu thấy thiếu, nói luôn.** "Check thêm X đi" hoặc "Phần này chưa đủ kỹ".

### Cho Claude (AI assistant)

1. **Đọc MASTER_v1.md TRƯỚC.** Mọi conversation bắt đầu từ MASTER.
2. **Không dump methodology.** Không giải thích framework trừ khi user hỏi.
3. **Hỏi gom, không hỏi rải.** Tối đa 3 câu, gom 1 lần.
4. **Output plan trước khi làm.** User confirm rồi mới chạy.
5. **Mỗi RRI-T pass = 1 persona.** Không chạy gộp — chạy từng persona riêng để check kỹ.

---

## Versioning

Tất cả file trong bộ chia sẻ version number:

```
v1.0   ← Bản đầu tiên (hiện tại)
v1.1   ← Hotfix nhỏ
v1.4.5 ← Cải thiện incremental
v2.0   ← Major rewrite
```

Khi update 1 file, bump version cho TẤT CẢ files để đồng bộ. Ghi changelog vào cuối mỗi file.

---

## FAQ

**Q: Dùng Claude Code hay Claude Web?**
A: Claude Code tốt hơn — đọc được codebase, chạy Phase 1.5 Code-Path trực tiếp. Claude Web dùng được cho phase analysis (PGA, PMT) nhưng không trace code được.

**Q: Phải ném cả 4 file mỗi lần?**
A: Lý tưởng thì có. Nhưng nếu context window tight, chỉ cần MASTER_v1.md + file relevant (VD: chỉ check growth → MASTER + PGA).

**Q: File quá dài, Claude không đọc hết?**
A: MASTER_v1.md được thiết kế lazy-load — nó chỉ instruct Claude đọc file nào khi cần, không bắt đọc hết 4 file cùng lúc.

**Q: Gửi cho người khác dùng được không?**
A: Được. Gửi cả 5 files (kể cả HDSD_v1.md này). Họ chỉ cần đọc HDSD_v1.md → copy vào folder → chat với Claude.

**Q: Dùng cho team lớn được không?**
A: Bộ này thiết kế cho solo dev / small team (1-3 người). Team lớn hơn cần thêm: stakeholder management (từ PMT gốc), approval workflow, multi-repo strategy.

---

*HDSD_v1.md — Hướng Dẫn Sử Dụng Bộ Tây Du Ký Pipeline v1.0*
