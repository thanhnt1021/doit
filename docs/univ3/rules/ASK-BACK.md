# ASK-BACK — hỏi ngược trước khi thực thi

Tự chạy trong `feature:` Phase 1 (Track A). Dùng standalone bằng prefix `ask back`. Bỏ qua khi mọi thứ rõ ràng (message ngắn, không ambiguity) hoặc user nói `just do`.

## Luật CỨNG (luôn áp dụng, KHÔNG chỉ trong feature/ask-back)
**Bất kỳ khi nào cần chủ nhà chốt giữa các lựa chọn RỜI RẠC → PHẢI gọi `AskUserQuestion`. CẤM liệt kê option bằng văn bản rồi bắt user tự gõ trả lời.** Áp dụng ở MỌI ngữ cảnh, kể cả:
- Ngoài flow `feature:`/`ask back` — hội thoại thường, giữa chừng một việc.
- Khi tổng hợp câu hỏi mở / "Cần quyết định" do subagent (Kỹ sư/Thợ xây) trả về → chuyển THẲNG thành các câu `AskUserQuestion`, đừng chép ra prose.
- Chỉ có **1 câu**, hoặc câu **Yes/No · A/B · giữ/bỏ** → vẫn gọi tool (đừng viết prose vì "chỉ 1 câu / đơn giản").

**Chỉ được** dùng prose cho câu hỏi mở KHÔNG có tập lựa chọn xác định (vd "đặt tên gì?", "dán link/khóa API vào đây"). Có ≥2 phương án đặt tên được → là lựa chọn rời rạc → dùng tool.

**Anti-pattern phải tránh** (dấu hiệu đang dùng SAI): trong message xổ danh sách "Quyết định 1…N / Câu hỏi 1…N" kèm option rồi hỏi "bạn chốt cái nào?". Thấy mình sắp viết kiểu đó → DỪNG, gọi `AskUserQuestion`.

**GOM VỀ ĐẦU NGÀY:** mọi thứ cần chủ nhà chốt — nhất là **hook mới / nới hook** cho việc
sửa dữ liệu hoặc đụng tệp dùng chung — phải dồn vào **một lượt `AskUserQuestion` buổi
sáng** trước khi bắt tay làm. Founder xả task xong là đi vắng; hỏi giữa chừng = phiên đứng
im. Chi tiết: `rules/WORKFLOWS.md` §Buổi-sáng.

## FOUNDER HỎI ≠ FOUNDER RA LỆNH (cổng `founder_lenh_gate.py`)
Lượt founder chỉ **hỏi / góp ý / cung cấp thông tin** thì việc phải làm là **TRẢ LỜI**, không phải
tự sinh ra việc rồi thi hành. Ba ca thật 27/08/2026:

| Founder nói | Main tự làm | Đúng ra phải |
|---|---|---|
| "tao tưởng có cơ chế gộp để deploy tiết kiệm rồi nhỉ?" | thả worker chạy lô deploy | trả lời có/không, xong |
| "báo cáo kiểu này rất ngu vì làm tao hoảng" | đi tạo vé | sửa cách báo cáo |
| "nói chung mỗi shop sẽ có listing id unique" | dựng thêm nhánh dự phòng | ghi nhận, hỏi lại nếu cần |

Nghĩ việc đó **cần** làm → hỏi bằng `AskUserQuestion` (founder duyệt là cổng tự mở). Đang tiếp lệnh
founder ra ở lượt TRƯỚC → vượt cổng bằng `founder-ra-lenh-ok` **kèm** `LENH FOUNDER: "<nguyên văn>"`.

## Quy trình
Đọc plan + đọc codebase hiện tại → so "plan nói gì vs code thực tế có gì" → phân loại findings → hỏi ngược bằng options → nhận trả lời → thực thi.

## Phân loại findings (6 loại)
| | Loại | Nghĩa | Hỏi? |
|---|---|---|---|
| 🔴 | CONFLICT | Plan mâu thuẫn code hiện tại | BẮT BUỘC |
| 🟡 | AMBIGUITY | Plan hiểu được 2+ cách | BẮT BUỘC |
| 🟠 | RISK | Làm được nhưng có thể break thứ khác | Nên hỏi |
| 🔵 | GAP | Plan thiếu thông tin để implement | Nên hỏi |
| ⚪ | ASSUMPTION | Claude sẽ giả định X nếu không nói | Hỏi nếu critical |
| 🟢 | CLEAR | Rõ ràng | KHÔNG hỏi |

**Chỉ hỏi 🔴🟡🟠🔵⚪ — KHÔNG hỏi 🟢. Mọi thứ 🟢 → skip ask-back, làm luôn.**

## Cách hỏi
- **Claude Code**: dùng `AskUserQuestion` tool (UI option, tự có "Other"). **Codex/harness khác**: output danh sách câu hỏi + option đánh số, chờ user chọn.
- Trước khi hỏi, output 1-3 dòng tóm tắt: "Hiểu mày muốn [X]. Ảnh hưởng [Y file]. Phát hiện [N] điểm cần xác nhận."
- Tối đa **7 câu**, ưu tiên 🔴>🟡>🟠>🔵>⚪. Claude giới hạn **4 câu/lần gọi** → >4 thì chia nhiều lần (nhóm critical trước).
- Mỗi câu: `header` ≤12 ký tự + 2-4 option, mỗi option có `label` ngắn + `description` (hệ quả cụ thể). **Recommended đặt ĐẦU tiên** + ghi "(Recommended)" cuối description.
- `multiSelect` khi câu hỏi cho chọn nhiều.

Sau khi user chọn → tạo execution plan cuối (plan gốc + câu trả lời) → thực thi. Gặp vấn đề mới critical giữa chừng → dừng hỏi tiếp.

> Kết hợp goal-check: nếu plan lệch `docs/GOAL.md` → thêm 1 câu 🔴 "Plan vs Goal" (options: plan đúng-update goal / goal đúng-sửa plan / làm cả hai). Xem `rules/DOCS.md` §GOAL.
