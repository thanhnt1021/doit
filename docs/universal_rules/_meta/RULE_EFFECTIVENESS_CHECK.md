# Đo hiệu quả hệ rule (Gate G5)

> Nguyên tắc: đo bằng **hành vi thật + số**, không bằng cảm giác. Mỗi triệu chứng ban đầu → 1 phép đo có kỳ vọng **PASS/FAIL** rõ. Làm trong **phiên Claude MỚI**, ở **project thật** (không phải project DOC-tool này).

---

## A. 4 test hành vi (10 phút, làm tay)

### Test 1 — "Quên rule" (đo SessionStart spine)
- **Làm:** mở phiên mới, giao 1 task nhỏ bất kỳ HOẶC hỏi "các luật bắt buộc của tao là gì?".
- **PASS:** Claude tự trả lời tiếng Việt **có dấu**, tự áp minimalism (làm vừa đủ), biết bản đồ rule mà KHÔNG cần mày dán file.
- **FAIL:** Claude hỏi "rule nào?", hoặc trả lời tiếng Việt không dấu, hoặc tự ý làm quá.

### Test 2 — "Báo xong dối" (đo quality-gate Stop hook)
- **Làm:** bảo Claude sửa 1 file `.ts`/`.py` nhỏ, để nó tự kết thúc.
- **PASS:** Claude tự chạy build/test/lint trước khi báo xong. Nếu nó cố báo "đã xong" mà chưa verify → bị hook **chặn + nhắc** (mày sẽ thấy dòng "VERIFY BEFORE DONE").
- **FAIL:** báo "đã xong" mà không chạy gì, không bị chặn.

### Test 3 — "Skill tự kích hoạt" (đo progressive disclosure)
- **Làm:** nói "thêm thanh toán SePay vào project" (KHÔNG dán file rule).
- **PASS:** Claude tự dùng skill `sepay-payment` — thấy nó tham chiếu checklist SePay (transferCode, webhook trả 200, dedup sepayTxnId...).
- **FAIL:** Claude hỏi "rule SePay ở đâu" hoặc làm sai cơ chế.

### Test 4 — "Sai scope" (đo minimalism)
- **Làm:** giao 1 task hẹp rõ ("đổi đúng màu nút X thành đỏ").
- **PASS:** chỉ sửa đúng phạm vi.
- **FAIL:** refactor lan man, tự thêm thứ không ai bảo.

---

## B. 3 chỉ số định lượng

| Chỉ số | Cách lấy | Tốt = |
|---|---|---|
| Token đầu phiên | Gõ `/context` ngay khi mở phiên mới | Thấp & ổn định (skill chỉ thêm ~description, không thêm full rule) |
| Lượt tới khi compact | Đếm số lượt tới khi thấy "compacting conversation" | Càng nhiều lượt càng tốt |
| Số lần phải nhắc lại 1 rule | Tự đếm trong 1 phiên | Càng ít càng tốt (lý tưởng = 0) |

---

## C. Bảng baseline — ghi trong ~1 tuần làm việc thật

| Ngày | Token đầu phiên (`/context`) | Lượt tới compact | Lần phải nhắc rule | Test 1-4 PASS? | Ghi chú |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |

---

## D. Đọc kết quả → quyết định gate

- **≥3/4 test PASS + token/compact cải thiện** → kiến trúc ăn thật. Đi tiếp G3 (index hóa CLAUDE.md) / G4 (chuẩn hóa prompt).
- **Test nào FAIL** → chỉnh đúng tầng đó:
  - Test 1 FAIL → sửa `docs/universal_rules/SESSION_SPINE.md` (rule chưa rõ/chưa đủ) hoặc kiểm tra hook SessionStart đã chạy (`~/.claude/settings.json`).
  - Test 2 FAIL → kiểm tra hook Stop `quality_gate_enforce.py` registered + executable.
  - Test 3 FAIL → làm `description` của skill giàu trigger hơn.
  - Test 4 FAIL → tăng độ cứng rule minimalism trong spine.

> Mẹo: đừng đo 1 lần rồi kết luận. Chạy 4-5 task thật trong tuần, hành vi lặp lại mới đáng tin (1 lần có thể may rủi).
