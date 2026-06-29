# Gap Analysis — Đối chiếu `docs/` với source code thật của Claude Code

> **Mục đích:** Liệt kê những chỗ bộ `universal_rules/` + `tdk/` đang nói chung chung/suy đoán, đối chiếu với cơ chế thật trong source code Claude Code (`src/`, 1.884 file ts/tsx). Mỗi mục kèm **con số chính xác** và **tham chiếu `file:line`** để truy vết.
>
> **Cách dùng:** Đây là checklist nâng cấp, KHÔNG phải file rule. Khi muốn làm sâu một file rule, mở mục tương ứng bên dưới, lấy số thật + dẫn chứng rồi viết lại.
>
> **Lưu ý version:** Các con số dưới đây đúng với bản source đang có trong `src/`. Source có thể đổi giữa các version Claude Code — khi nhúng vào rule nên ghi kèm `file:line` để verify lại được.

---

## Kết luận tổng

Bộ rules **mạnh về quy trình làm việc & safety**, nhưng phần **cơ chế nội bộ Claude Code** đang viết theo trí nhớ/suy đoán. Chỗ đã ghi số thì **trùng khớp source** (vd `MEMORY.md 200 dòng / 25KB` ↔ `memdir.ts:35`) — hướng đúng, chỉ thiếu độ phủ và dẫn chứng.

Phân loại docs hiện tại:
- **Viết cho user** (cách dùng Claude Code đúng) — đã tốt.
- **Viết cho hiểu cơ chế** (Claude Code thực thi thế nào) — đang thiếu, đây là phần source bổ khuyết được.

---

## Phần 1 — Nâng cấp các file rule hiện có

### 1.1 `docs/universal_rules/rules/PERMISSION_MODEL.md` — độ sâu hiện tại: NÔNG → cần SÂU

Đang mô tả 5 mode + deny/ask/allow ở mức khái niệm. Thiếu các cơ chế match thật:

| Cơ chế thật | Dẫn chứng |
|---|---|
| Prefix rule **KHÔNG** match compound command — `Bash(rm *)` không chặn `rm file && curl evil.com` (chống bypass bằng chaining) | `tools/BashTool/bashPermissions.ts:884` |
| Deny/ask rule match **mọi** subcommand trong compound; allow rule chỉ match subcommand **đầu tiên** | `bashPermissions.ts:1295` |
| Compound command > **50** subcommand → tự trả về `ask` (parse >50 starves event loop, CC-643) | `bashPermissions.ts:95` |
| `bypassPermissions` chỉ khả dụng sau khi check env (Docker/sandbox/no-internet); `--dangerously-skip-permissions` bị từ chối nếu env không thỏa | `utils/permissions/permissionSetup.ts:939` |
| Git command được normalize trước khi match — `FORCE_COLOR=1 git status` vẫn nhận diện là git | `bashPermissions.ts:2567` |
| Env var prefix bị strip khi extract command — `VAR=value git status` match như `git status` | `bashPermissions.ts:91` |
| `ToolPermissionContext` là DeepImmutable (frozen); denial tracking mutate `localDenialTracking` tại chỗ cho subagent | `Tool.ts:122` |
| **Lớp quyết định đầy đủ:** validateInput → checkPermissions → hooks → classifier (Haiku) → user prompt. Mỗi lớp chỉ bypass được theo cách có chủ đích | `utils/permissions/permissions.ts:536` |

**Đề xuất:** thêm section "Cơ chế match rule thật" + ví dụ `settings.json` cụ thể cho dev vs production.

### 1.2 `docs/universal_rules/rules/HOOKS_REFERENCE.md` — VỪA → SÂU

Đang liệt kê ~28 event + exit code 0/2. Thiếu ngữ nghĩa mutate:

| Cơ chế thật | Dẫn chứng |
|---|---|
| PreToolUse `updatedInput` mutate được input NHƯNG **không** chạy lại `validateInput` (validation đã xong) | `types/hooks.ts:73` |
| Chỉ PostToolUse mutate được **output**, qua `updatedMCPToolOutput`, và **chỉ cho MCP tool** | `types/hooks.ts:101` |
| PermissionRequest hook trả `{behavior:'allow', updatedInput}` thì `updatedInput` **override** input gốc khi execute | `types/hooks.ts:122` |
| Trường `exitCode` map từ **HTTP status**, KHÔNG phải Unix process exit code (với async/http hook: `statusCode ?? 0`) | `utils/hooks.ts:2353` |
| Path được `expandPath()` trong `backfillObservableInput()` **trước** khi hook/permission thấy → chống bypass allowlist bằng `~`/relative path | `tools/FileEditTool/FileEditTool.ts:115` |

**Đề xuất:** thêm bảng "hook nào mutate được gì" + cảnh báo exitCode ≠ process exit.

### 1.3 `docs/universal_rules/rules/TOOL_DISCIPLINE.md` — VỪA → SÂU

Đang nói "parallel calls" chung chung. Thiếu số & cơ chế:

| Cơ chế thật | Dẫn chứng |
|---|---|
| Concurrency mặc định = **10** (env `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY`) | `services/tools/toolOrchestration.ts:8` |
| An toàn song song xét theo `isConcurrencySafe()` trên **input đã parse**, KHÔNG theo tên tool — cùng 1 tool có thể safe/unsafe tùy tham số | `services/tools/toolOrchestration.ts:91` |
| Read-only batch chạy song song; non-read-only bị serialize riêng từng cái mỗi batch | `services/tools/toolOrchestration.ts:91` |
| Read tool: **2 giới hạn riêng** — byte cap 256KB (check pre-read qua `stat()`) + token cap 25k (check post-read) | `tools/FileReadTool/limits.ts` |
| Edit đọc nội dung file thật để verify `old_string` tồn tại — ngay trong `validateInput`, không phải hook | `tools/FileEditTool/FileEditTool.ts:137` |
| Streaming executor: tool được thực thi **ngay khi stream tới**, không đợi response đầy đủ | `services/tools/StreamingToolExecutor.ts:76` |

**Đề xuất:** thêm "Cơ chế song song thật" + giải thích vì sao Edit luôn cần Read trước.

### 1.4 `docs/universal_rules/rules/SUBAGENTS.md` — VỪA → SÂU

| Cơ chế thật | Dẫn chứng |
|---|---|
| Agent task tự **background sau 120s** để giải phóng main thread; user nhận notify khi xong | `tools/AgentTool/AgentTool.tsx:72` |
| Fork chia sẻ prompt cache của cha → **KHÔNG đổi model cho fork** (model khác bust cache) | `tools/AgentTool/prompt.ts:76` |
| Task **không** bị kill ở terminal — persist trong AppState với `evictAfter`; eviction tách rời khỏi status | `tasks/types.ts:12` |
| Progress tracker giữ token tích lũy + tool count + **5** activity gần nhất (ring-buffer chống GC) | `tasks/LocalAgentTask/LocalAgentTask.tsx:40` |
| AgentTool nhận `isolation: 'worktree'|'remote'`, `cwd`, `run_in_background` | `tools/AgentTool/AgentTool.tsx:82` |

**Đề xuất:** thêm ví dụ prompt giao việc + quy tắc "đừng set model cho fork".

### 1.5 `docs/universal_rules/rules/PLAN_MODE.md` — VỪA → SÂU

| Cơ chế thật | Dẫn chứng |
|---|---|
| `prePlanMode` lưu permission mode cũ để **restore khi exit** (tránh tụt quyền ngoài ý muốn) | `Tool.ts:136` |
| EnterPlanMode set mode `plan`, giới hạn Read-only tới khi ExitPlanMode | `tools/EnterPlanModeTool/EnterPlanModeTool.ts:77` |
| Plan mode **bị tắt** trong coordinator mode khi có channels (dialog duyệt cần terminal) | `tools/EnterPlanModeTool/EnterPlanModeTool.ts:56` |

**Đề xuất:** làm rõ "khi nào thoát plan mode" + cơ chế restore quyền.

### 1.6 `docs/universal_rules/rules/MEMORY_SYSTEM.md` — SÂU (số đã đúng) → bổ sung trigger

Số hiện tại khớp source: `MEMORY.md` 200 dòng / 25KB ↔ `memdir.ts:35` (`MAX_ENTRYPOINT_LINES=200`, `MAX_ENTRYPOINT_BYTES=25k`). Bổ sung:

| Cơ chế thật | Dẫn chứng |
|---|---|
| Memory extract chạy **async qua forked subagent**, chỉ kích hoạt khi **CẢ** ngưỡng token **VÀ** tool-call vượt (chi phí ngoài budget của query chính) | `services/SessionMemory/sessionMemory.ts:134` |
| Truncate theo dòng trước, rồi cắt byte tại newline cuối trước cap (tránh cắt giữa dòng); append cảnh báo nếu bị cắt | `memdir/memdir.ts:57` |
| Nested memory động: model ghi `<!-- @claude /memory/topic.md -->` để load file topic kèm MEMORY.md | `QueryEngine.ts:371` |

### 1.7 `docs/universal_rules/rules/QUALITY_GATES.md` — SÂU → bổ sung "kỳ vọng hành vi" retry

| Cơ chế thật | Dẫn chứng |
|---|---|
| Retry API: max **10** lần; recovery max-output-token: **3** chu kỳ riêng | `services/api/withRetry.ts:52`, `query.ts:164` |
| 429/529 chỉ retry ở foreground source (`repl_main_thread`, `sdk`, `agent:*`, `compact`, `auto_mode`); background bail ngay chống cascade | `services/api/withRetry.ts:62` |
| Structured output retry mặc định **5** (`MAX_STRUCTURED_OUTPUT_RETRIES`) | `QueryEngine.ts:1011` |

---

## Phần 2 — Chủ đề CHƯA có file nào (gap hoàn toàn mới)

### 2.1 `COMPACTION.md` (đề xuất tách mới)
Hiện gộp sơ trong `docs/universal_rules/rules/SUBAGENTS.md`. Thực tế có **3 hệ nén cùng tồn tại**:

| Hệ | Cơ chế & số | Dẫn chứng |
|---|---|---|
| **Auto-compact** | Fire ở `effectiveWindow − 13k` token; summary ≤ 20k token (p99.99 = 17.3k); circuit-breaker dừng sau 3 lần fail liên tiếp | `services/compact/autoCompact.ts:62,30` |
| **Microcompact** | API-native; giữ 40k token cuối (`DEFAULT_TARGET_INPUT_TOKENS`), trigger ở 180k (`DEFAULT_MAX_INPUT_TOKENS`); clear thinking block cũ + tool result cũ | `services/compact/apiMicrocompact.ts:16` |
| **Snip / contextCollapse** | Feature-gated (`HISTORY_SNIP`); prune zombie message chống memory leak ở session SDK dài | `QueryEngine.ts:905` |

Công thức: `effectiveWindow = contextWindow − min(maxOutputTokens, 20k)`; `autoCompactThreshold = effectiveWindow − 13k` (`autoCompact.ts:33`).
Re-inject skill sau compact: ≤ 5k token/skill, tổng budget 25k (`services/compact/compact.ts:129`).

**Hiểu nhầm cần tránh:** tool result có content_replacement record là **vô hình** với microcompact (nó chỉ thao tác theo `tool_use_id`). Compaction KHÔNG trong suốt — là black box auto-managed, không nên tinh chỉnh thủ công.

### 2.2 `MCP_INTEGRATION.md` (đề xuất mới)
Docs hoàn toàn chưa nói Claude Code load/dùng MCP tool thế nào, schema load on-demand ra sao, hook `updatedMCPToolOutput` là đường duy nhất mutate output MCP (`types/hooks.ts:101`).

### 2.3 `TOKEN_BUDGETING.md` (đề xuất mới)
| Cơ chế thật | Dẫn chứng |
|---|---|
| Auto-continue threshold = **90%** window; dừng khi 3 lần continue mà mỗi lần tăng < **500** token (`DIMINISHING_THRESHOLD`) | `query/tokenBudget.ts:3` |
| Task budget tracking persist qua compaction (cumulative qua nhiều lần compact) | `query.ts:282` |
| Tool result budgeting chạy **trước** microcompact: result quá lớn được thay bằng disk reference | `query.ts:379` |

### 2.4 Concurrency & race
2 parallel call cùng sửa 1 file: hệ partition read-only-safe vs serialize non-read-only mỗi batch (`toolOrchestration.ts:91`) — đáng ghi 1 mục trong `docs/universal_rules/rules/TOOL_DISCIPLINE.md` hoặc file riêng.

---

## Phần 3 — Đề xuất cho bộ TDK

TDK (Tây Du Ký pipeline) thiên về vai trò/orchestration, có thể nhúng **threshold thật** để các "đệ tử" kiểm tra theo chuẩn Claude Code:

- **`RRI-T_v1.md` (QA — Bát Giới):** thêm gate cảnh báo khi context gần ngưỡng auto-compact (`window − 13k`); kiểm tra subagent có nên background (>120s).
- **`INFRA_v1.md` (Sa Tăng):** tham chiếu retry policy thật (10 retry, 429/529 foreground-only) khi thiết kế CI/healthcheck.
- **`MASTER_v1.md` (orchestrator):** khi route task nặng/đọc rộng → ưu tiên fork Explore subagent (không đổi model), đúng pattern source.

---

## Phần 4 — Bảng ưu tiên đề xuất

| Ưu tiên | Việc | Lý do |
|---|---|---|
| **P0** | Làm sâu `docs/universal_rules/rules/PERMISSION_MODEL.md` | Đang NÔNG nhất, lại là phần dễ sai nhất về an toàn |
| **P0** | Tách `COMPACTION.md` với 3 hệ + số thật | Gap lớn, ảnh hưởng trực tiếp hiệu quả session dài |
| **P1** | Làm sâu `docs/universal_rules/rules/HOOKS_REFERENCE.md`, `docs/universal_rules/rules/TOOL_DISCIPLINE.md`, `docs/universal_rules/rules/SUBAGENTS.md` | Số thật có sẵn, nhúng nhanh |
| **P1** | Thêm `TOKEN_BUDGETING.md` | Bổ khuyết hiểu biết về auto-continue/budget |
| **P2** | `MCP_INTEGRATION.md` | Hữu ích nhưng ít dùng trong project hiện tại |
| **P2** | Nhúng threshold vào TDK (RRI-T, INFRA) | Sau khi các file cơ chế đã chuẩn |

---

*Báo cáo tạo từ phân tích trực tiếp source `src/` (toàn bộ source code Claude Code). Mọi con số đều truy vết được qua `file:line` đã ghi.*
