# File Ownership — file này CỦA AI, push ĐI ĐÂU, con khác PULL KIỂU GÌ?

> Trả lời 3 câu trước khi commit/push bất kỳ file nào: **(1) chung hay riêng? (2) push lên repo nào? (3) agent/máy khác lấy về bằng đường nào?**
> Sinh từ sự cố thật 7/2026: 7 bản univ2 drift vì rule chung kẹt lại project; C-HX có file Canva riêng nằm lẫn trong `universal_rules/` suýt bị đẩy nhầm lên SSOT/xoá nhầm khi sync; doit có file cá nhân untracked mà nếu "tiện tay commit" là lộ dữ liệu riêng tư lên GitHub.

## 1. Bốn loại file — nhận diện bằng máy trước, hỏi người sau

| Loại | Nhận diện | Push đi đâu | Con khác pull về kiểu gì |
|---|---|---|---|
| **1. Chung (universal)** | Nằm trong `docs/universal_rules/` **VÀ có trong `MANIFEST.txt`** | SSOT `thanhnt1021/universal-workflow` (chiều PUSH — WORKFLOWS.md) rồi fan-out | `sync uni` |
| **2. Riêng project** | Code app, docs project (`GOAL/PROJECT_SUMMARY/CHANGELOG/DESIGN...`), asset | Repo GitHub **của project đó** | clone/pull repo project |
| **3. Riêng-nhưng-nằm-trong-`universal_rules/`** | KHÔNG có trong `MANIFEST.txt` **và** được khai trong `LOCAL_ONLY.txt` | Repo project (nếu project track docs) — **TUYỆT ĐỐI KHÔNG đẩy lên SSOT** | Không pull — của riêng project đó |
| **4. Cá nhân / nhạy cảm** | Secret, `.env`, token, tài liệu cá nhân không liên quan code | **KHÔNG push đi đâu** — `.gitignore` | Không |

## 2. `LOCAL_ONLY.txt` — khai báo loại 3

- Vị trí: `docs/universal_rules/LOCAL_ONLY.txt`, mỗi dòng 1 đường dẫn tương đối (trong folder universal_rules).
- **`sync uni` chiều PULL** (bước xoá file thừa): file trong LOCAL_ONLY → **giữ nguyên, không xoá**.
- **Chiều PUSH**: file trong LOCAL_ONLY → **không bao giờ copy lên SSOT**.
- File này mỗi project mỗi khác → **không nằm trong MANIFEST** (gen_manifest.sh loại nó ra). Project không có file riêng thì không cần tạo.
- Ví dụ thật (C-HX): `CANVA_EXACT_PLAYBOOK.md`, `canva-measure.py`, `canva-spec.py`, `hooks/canva_crosscheck_enforce.py`.

## 3. Decision tree khi COMMIT/PUSH — chạy theo thứ tự

1. **File có trong `MANIFEST.txt`?** → loại 1. Sửa nó = sửa rule chung → bắt buộc chiều PUSH: bump `VERSION` + `gen_manifest.sh` + push SSOT + fan-out (WORKFLOWS.md).
2. **File MỚI bên trong `docs/universal_rules/`?** → mặc định KHÔNG RÕ → **AskUserQuestion BẮT BUỘC trước khi commit**:
   - **A. Của chung** → đưa vào SSOT (chiều PUSH); project khác nhận qua `sync uni`.
   - **B. Riêng project này** → thêm dòng vào `LOCAL_ONLY.txt` rồi mới commit.
   - **C. Cá nhân/nhạy cảm** → `.gitignore`, không push.
3. **File ngoài `docs/universal_rules/`** → loại 2, push repo project như thường. **Ngoại lệ:** nội dung chứa BÀI HỌC dùng được mọi project (fix hook, luồng deploy mới, pattern mới) → hỏi user có trích phần chung về SSOT không (đừng để bài học kẹt lại — đúng bệnh drift 7/2026).
4. **File lạ mình KHÔNG tạo ra** (user/tool khác bỏ vào working tree) → **KHÔNG tự commit**. AskUserQuestion: track vào repo / gitignore / bỏ qua. _Ví dụ thật: PDF cá nhân trong doit._

## 4. Bất biến

- `MANIFEST.txt` = ranh giới máy-đọc-được của "chung". `LOCAL_ONLY.txt` = ý định người-khai-báo của "riêng". `AskUserQuestion` = chốt chặn cuối khi 2 cái trên chưa phân xử được.
- Mọi commit vào SSOT phải qua `gen_manifest.sh` — file chung mới sinh sẽ TỰ vào MANIFEST, từ đó hết mơ hồ cho các lần sau.
- KHÔNG commit secret/token vào bất kỳ repo nào, kể cả SSOT (ENV_RULES.md).
