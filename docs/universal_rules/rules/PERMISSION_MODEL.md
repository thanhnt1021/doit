# Permission Model — Cách Claude Code Quyết Định Cho Phép Tool

Tham chiếu mô hình phân quyền của Claude Code CLI: **mode + rule allow/deny/ask + thứ tự ưu tiên.**
_Lý do tồn tại: bộ rules cũ quản lý "an toàn" hoàn toàn bằng văn xuôi mệnh lệnh ("KHÔNG BAO GIỜ..."). Hiểu mô hình permission thật giúp cấu hình `settings.json` đúng và biết vì sao một hành động bị hỏi/chặn._

---

## 1. Permission modes (Shift+Tab để xoay)

| Mode | Hành vi |
|---|---|
| `default` | Mỗi tool call có rủi ro phải xin phép (prompt user). |
| `acceptEdits` | Tự cho phép sửa/ghi file trong working dir; vẫn hỏi với shell command. |
| `plan` | Read-only: chỉ explore + design, không write/edit (trừ file plan). Xem `docs/universal_rules/rules/PLAN_MODE.md`. |
| `bypassPermissions` | Tự cho phép MỌI tool (trừ vài safety check miễn nhiễm). Dùng cẩn trọng. |
| `dontAsk` | Tự **từ chối** mọi yêu cầu cần hỏi (strict). |

> Mode chỉ đổi "ai bị hỏi", **không** vượt qua được DENY rule hay safety check phá hủy.

## 2. Rule allow / deny / ask

Cú pháp trong `settings.json`: `"Tool"` hoặc `"Tool(content)"`.
- Ví dụ: `Bash(npm run test:*)`, `Bash(git push:*)`, `Read(/etc/**)`, `Edit(src/**)`.
- `Bash` hoặc `Bash(*)` cho allow **luôn bị coi là nguy hiểm** (cho phép chạy mọi lệnh) → bị strip khi vào plan/auto mode.

Ba loại rule:
- **deny** — cấm tuyệt đối.
- **ask** — luôn hỏi, kể cả mode tự động.
- **allow** — tự cho phép.

## 3. Thứ tự quyết định (quan trọng)

Khi một tool call tới, engine xét theo thứ tự — **dừng ở match đầu tiên**:

```
DENY  >  ASK  >  Tool.checkPermissions()  >  ALLOW  >  (không match → hỏi user)
```

→ **DENY luôn thắng ALLOW.** Một allow rộng không bao giờ vượt qua được một deny hẹp.

## 4. Thứ tự ưu tiên theo scope (cao → thấp)

```
policySettings (managed) > flagSettings > projectSettings
> userSettings > localSettings > cliArg > command > session
```

- Chỉ 3 scope được ghi xuống đĩa: `localSettings`, `userSettings`, `projectSettings`.
- `session`/`cliArg` chỉ tồn tại trong phiên (in-memory).
- Managed/policy settings (do tổ chức đặt) **không thể override** từ dưới.

## 5. Safety check miễn nhiễm

Một số đường dẫn/hành động **luôn bị hỏi** dù mode nào: ghi vào `.git/`, `.claude/`, shell config (`~/.bashrc`, `~/.zshrc`), credential files. Khi vào `plan`/`auto` mode, các allow rule nguy hiểm (chạy code: `python/node/bash/...`, hoặc `gh/curl/git`...) bị strip tạm thời và khôi phục khi thoát.

---

## Liên kết
- Tư duy reversibility/blast radius khi hành động: `docs/universal_rules/rules/ACTION_SAFETY.md`
- Plan mode (read-only): `docs/universal_rules/rules/PLAN_MODE.md`
- Hook can thiệp permission (`PreToolUse`, `PermissionRequest`): `docs/universal_rules/rules/HOOKS_REFERENCE.md`
- Nguồn: `utils/permissions/` trong source Claude Code.
