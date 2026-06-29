# Minimalism — Làm Vừa Đủ, Không Làm Thừa

Nguyên tắc đối trọng với checklist/quality-gate: **đủ thì dừng, không gold-plate.**
_Lý do tồn tại: phần lớn rule trong bộ này nói "làm cho đủ" (checklist, milestone, gate). Thiếu đối trọng "làm cho VỪA đủ" thì Claude có xu hướng thêm code/comment/abstraction/validation thừa — khó đọc, khó maintain, dễ sinh bug ở chỗ không ai yêu cầu._

---

## 1. Minimum complexity — phạm vi đúng bằng yêu cầu

- **KHÔNG thêm tính năng, refactor, hay "cải thiện"** ngoài phạm vi được giao. Fix 1 bug thì sửa đúng bug đó — không dọn dẹp code xung quanh. Thêm 1 tính năng đơn giản thì không kèm theo cấu hình/option dư thừa.
- **KHÔNG thêm error handling / fallback / validation cho tình huống không thể xảy ra.** Tin tưởng code nội bộ và đảm bảo của framework. Chỉ validate ở **ranh giới hệ thống** (user input, external API, webhook).
- **KHÔNG dùng feature flag hay backwards-compat shim** khi có thể sửa thẳng code. Nếu chắc chắn một thứ không còn dùng → xóa hẳn, không để lại `// removed`, không rename thành `_unused`, không re-export "cho chắc".

_Lý do: mỗi dòng code thừa là một dòng phải đọc, test, và có thể hỏng. Code không viết ra là code không bao giờ bug._

## 2. Không abstraction non — "rule of three"

- **3 dòng lặp lại còn tốt hơn 1 abstraction non.** Chỉ tách helper/utility/class khi đã thấy pattern lặp **≥ 3 lần** và thực sự cùng bản chất.
- KHÔNG tạo helper cho thao tác chỉ dùng 1 lần.

_Lý do: abstraction sai sớm tốn kém hơn lặp code. Gỡ một abstraction sai khó hơn gộp 3 dòng giống nhau._

## 3. Comment policy — mặc định KHÔNG comment

- **Mặc định không viết comment.** Chỉ thêm khi **WHY** không hiển nhiên: một ràng buộc ẩn, một invariant tinh tế, một workaround cho bug cụ thể, hành vi gây bất ngờ cho người đọc.
- KHÔNG giải thích **WHAT** code làm — tên hàm/biến tốt đã nói điều đó.
- KHÔNG viết comment tham chiếu task/fix/caller hiện tại ("dùng cho X", "thêm cho flow Y") — những thứ đó thuộc về PR description và sẽ mục theo thời gian.
- **KHÔNG xóa comment có sẵn** trừ khi xóa luôn code nó mô tả, hoặc chắc chắn nó sai. Một comment trông vô nghĩa có thể đang mã hóa một bài học từ bug cũ.
- KHÔNG thêm docstring / comment / type annotation vào code bạn **không** chỉnh sửa.

_Lý do: comment thừa nhiễu loạn, và comment sai còn tệ hơn không có — nó nói dối người đọc sau này._

## 4. Đọc trước khi sửa

- **Không đề xuất thay đổi code chưa đọc.** User hỏi/nhờ sửa file nào → đọc file đó trước, hiểu code hiện có rồi mới đề xuất.
- Trước khi dùng một thư viện → kiểm tra nó đã có trong project (`package.json` / `requirements.txt` / import lân cận) chưa. Không giả định một lib có sẵn.
- Code mới phải **bắt chước style xung quanh**: cách đặt tên, mật độ comment, idiom, format hiện có của file.

_Lý do: code đọc giống code xung quanh thì người review lướt qua được; code lạc quẻ buộc người ta dừng lại._

## 5. Vài rule nhỏ (hành vi mặc định)

- **KHÔNG đưa ước lượng thời gian** ("việc này mất 2 ngày") trừ khi user hỏi.
- **KHÔNG dùng emoji** trong code/file trừ khi user yêu cầu.
- **KHÔNG tự tạo file tài liệu** (`*.md`, README) trừ khi user yêu cầu rõ ràng. Ưu tiên sửa file có sẵn hơn tạo file mới.

---

## Liên kết
- Đối trọng cứng về an toàn hành động: `docs/universal_rules/rules/ACTION_SAFETY.md`
- Verify trước khi báo xong: `docs/universal_rules/rules/QUALITY_GATES.md` §0
- Gốc tư tưởng: chính system prompt của Claude Code (`# Doing tasks` — "minimum complexity", "default to writing no comments").
