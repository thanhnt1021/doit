# Quality Gates

Checklist BẮT BUỘC trước mỗi commit. Không pass → không commit.
_Lý do tồn tại: commit broken code vào repo nghĩa là mọi người pull về đều bị broken. Production deploy từ broken code là sự cố thật._

## 0. Verify Before Done & Báo Cáo Trung Thực — BẮT BUỘC

Áp dụng cho MỌI task, không chỉ trước commit. **Chưa verify thì chưa được nói "xong".**

**A. Verify trước khi báo hoàn thành**
- Trước khi nói một task đã xong → **thực sự kiểm chứng nó chạy**: chạy test, execute script, xem output thật. Không suy đoán "chắc là chạy được".
- Nếu **không thể** verify (chưa có test, không chạy được code ở đây) → **nói thẳng là chưa verify**, đừng tuyên bố thành công.

**B. Báo cáo trung thực — ZERO che giấu**
- Test fail → **nói rõ là fail**, kèm output. KHÔNG bao giờ nói "all tests pass" khi output có failure.
- KHÔNG suppress / đơn giản hóa / bỏ qua check đang fail cho "đẹp báo cáo".
- KHÔNG mô tả việc dở dang hoặc hỏng là "đã hoàn thành". Bước nào bị skip → ghi rõ là đã skip.
- Khi đã xong và đã verify → nói thẳng, không vòng vo, không "có lẽ".

**C. Verify đối kháng (task lớn: ≥3 file, backend/API, infra)**
- Sau khi tự làm xong, rà lại với tâm thế **"thử làm nó vỡ"**, không phải "xác nhận nó chạy": edge case, input rỗng/sai, concurrency, regression ở tính năng cũ liên quan.
- Ghi lại lệnh đã chạy để verify (để user tự kiểm chứng được).

_Lý do: báo "xong" mà chưa chạy là cái bẫy tốn kém nhất — user tin tưởng deploy/build tiếp dựa trên một lời tuyên bố sai. Một lần nói dối kết quả (dù vô tình) phá vỡ toàn bộ độ tin cậy. Thà nói "tôi chưa verify được phần X" còn hơn "all good" rồi vỡ ở production._

## 1. Type / Lint Check

> Lệnh dưới dùng `pnpm` cho project MỚI (mặc định), `npm` cho project legacy có `package-lock.json` — xem `docs/universal_rules/rules/NEW_PROJECT_SETUP.md`. Thay `pnpm`↔`npm` theo lock file thực tế của repo.

```bash
# TypeScript
pnpm exec tsc --noEmit      # legacy: npx tsc --noEmit

# ESLint (nếu có)
pnpm exec eslint . --ext .ts,.tsx   # legacy: npx eslint ...
```

→ **Zero errors.** Warnings có thể chấp nhận nếu không ảnh hưởng runtime (ví dụ: unused import warning thì OK, `any` type trên critical data flow thì không OK).

_Lý do: TypeScript errors là bug chắc chắn sẽ xảy ra ở runtime — compiler đã phát hiện ra rồi, không có lý do để ignore._

## 2. Build Pass

```bash
pnpm run build   # Next.js / React (legacy: npm run build)
# hoặc tương đương theo stack
```

→ Build thành công, không có error.

_Lý do: type-check pass không đảm bảo build pass. Next.js có thể lỗi ở bước bundle/optimization dù TypeScript OK. Build fail = deploy fail._

## 3. Runtime Test

- Chạy `test demo` (quick deploy) và verify tính năng mới hoạt động trên browser thật
- Kiểm tra không có regression ở tính năng cũ liên quan

_Lý do: build pass không đảm bảo app chạy đúng. Runtime errors (API sai, UI vỡ, logic lỗi) chỉ phát hiện được khi chạy thật._

## 4. MD Files Updated

- [ ] `docs/MD_FILES_TO_UPDATE.md` đã được populate với đúng files cần update
- [ ] Tất cả files trong list đã được update
- [ ] `docs/MD_FILES_TO_UPDATE.md` đã được clear sau khi update xong
- [ ] Nếu có env var / service / dependency mới → `docs/REQUIREMENTS_CHECK.md` đã update
- [ ] Nếu commit này hoàn thành milestone → `docs/GOAL.md` đã được update (tick `[x]`, cập nhật "Hiện tại đang ở đâu")
- [ ] Nếu thay đổi thuộc 4 loại catalog-level (Removed/Renamed/Contract changed/Constitution change) → `docs/CHANGELOG.md` đã có entry (xem `docs/universal_rules/rules/CHANGELOG_RULES.md`)

_Lý do: đây là quality gate vì code và docs phải đi cùng nhau trong một commit. Nếu merge code mà docs cũ, người deploy server mới sau này sẽ thiếu thông tin và app sẽ crash._

## 5. Environment Sync Check

- [ ] `.env.example` tồn tại và đồng bộ với `.env` (cùng keys, khác values)
- [ ] `.gitignore` chứa `.env*` (không commit secrets)
- [ ] Không có file `.env` trong staged changes

> Chi tiết: `docs/universal_rules/rules/ENV_RULES.md`

_Lý do: `.env.example` là tài liệu duy nhất cho team biết cần setup biến nào. Thiếu sync = deploy server mới thiếu biến → app crash._

## 6. Dependency Security Audit — BẮT BUỘC MỌI PROJECT

- [ ] `npm audit --audit-level=high` — zero high/critical (Node.js)
- [ ] `pip audit` — zero known vulnerabilities (Python)
- [ ] Lock file đã được commit cùng với code thay đổi

> Chi tiết: `docs/universal_rules/rules/SECURITY_CHECKLIST.md` §0.C

_Lý do: supply chain attack — package inject mã độc sau khi publish lên npm/PyPI. Server production đã bị compromise qua attack chain có liên quan. Không audit = deploy code có known vulnerability = rủi ro không cần thiết._

## 7. Vietnamese Diacritics Check (Dự án tiếng Việt)

- [ ] Grep tất cả strings tiếng Việt trong files vừa sửa
- [ ] Mọi user-facing string đều có dấu đầy đủ (messages, buttons, captions, image labels, AI prompts)
- [ ] Không có string nào dạng "Trai bai", "Quay lai", "Khach hang" (thiếu dấu)

→ **ZERO TOLERANCE.** Chi tiết: xem `docs/universal_rules/rules/BOT_COMMAND_RULES.md` mục 7.

_Lý do: Tiếng Việt không dấu là lỗi phổ biến nhất khi AI viết code. Mỗi commit phải verify -- không tin vào "đã viết đúng từ đầu"._

## 8. Commit Message

Format:
```
type: short description (imperative, present tense)

Longer explanation if needed — tập trung vào WHY, không phải WHAT.

Co-Authored-By: Claude <model> <noreply@anthropic.com>
```

Thay `<model>` bằng model đang dùng (giữ dạng placeholder, không hardcode version để tránh lỗi thời).

Types và ý nghĩa:
| Type | Dùng khi |
|------|----------|
| `feat` | Thêm tính năng mới hoàn toàn |
| `fix` | Sửa bug |
| `docs` | Chỉ thay đổi file tài liệu (.md) |
| `chore` | Config, dependencies, scripts — không ảnh hưởng logic |
| `refactor` | Tái cấu trúc code, không thêm feature không fix bug |
| `style` | Format, whitespace, CSS thuần — không ảnh hưởng logic |
| `test` | Thêm/sửa tests |

## Per Project Type

### [WEB/Next.js]
- [ ] `npx tsc --noEmit` pass
- [ ] `npm run build` pass
- [ ] Test trên mobile browser thật (nếu có UI thay đổi) — DevTools không đủ, iOS Safari có nhiều quirks

### [MOBILE]
- [ ] Build debug pass
- [ ] Test trên device thật — emulator không reproduce được hết lỗi hardware/OS

### [BOT/API — Node]
- [ ] Unit tests pass (nếu có)
- [ ] Health check endpoint respond 200
- [ ] **Command Registration Check:** Mọi CommandHandler đều có BotCommand tương ứng trong menu (xem `docs/universal_rules/rules/BOT_COMMAND_RULES.md` mục 1 + 4). Số handler phải khớp số menu command (trừ /start).

### [BOT/API — Python]
- [ ] `python -m py_compile <main_file>` pass (syntax check)
- [ ] `pip install -r requirements.txt` thành công trong venv
- [ ] Service restart thành công: `sudo systemctl restart <service> && sudo systemctl status <service>`
- [ ] **Command Registration Check:** Tương tự Node — xem `docs/universal_rules/rules/BOT_COMMAND_RULES.md` mục 1 + 4.

## 9. RRI-T Quality Audit (Khi user yêu cầu)

Khi user gọi `check quality` hoặc `check RRI-T` → chạy kiểm thử toàn diện theo **TDK Pipeline**:

1. **Đọc** `docs/universal_rules/skills/tdk-master/references/RRI-T_v1.md` (skill **qa-multipass**) — nắm methodology + multi-pass protocol
2. **Chọn mode:** Lite (solo dev, 3 personas) hoặc Full (5 personas)
3. **MULTI-PASS bắt buộc** (không chạy gộp personas):
   - Pass 0: Phase 1.5 Code-Path Analysis → output Code-Path Map → user review
   - Pass 1: 👤 End User (D1 UI/UX + D7 Edge) → output test cases
   - Pass 2: 🔍 QA Destroyer (D2 API + D7 Edge) → output test cases
   - Pass 3: 🔒 Security Auditor (D4 Security) → output test cases
   - [Full mode: Pass 4-5 thêm 📋 BA + 🔧 DevOps]
   - Pass Final: Self-Check (Common Misses checklist per dimension)
4. **Output:** Test suite by pass, scoring dashboard, P0-P3 priority, recommended fixes

_Lý do: RRI-T bổ sung cho unit test bằng cách kiểm thử từ góc nhìn người dùng thật + phá hệ thống + security + infrastructure. Multi-pass đảm bảo mỗi persona được 100% focus, không bị lướt._

> **File cũ `RRI-T_METHODOLOGY.md` đã được thay thế bởi `docs/universal_rules/skills/tdk-master/references/RRI-T_v1.md`** (skill **qa-multipass**) — bản mới có multi-pass enforcement, common misses registry, và self-check protocol.