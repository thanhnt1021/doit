#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""no_secret_in_file_enforce.py — CẤM TẤT ĐỊNH việc ghi GIÁ TRỊ BÍ MẬT THẬT vào tệp
không phải `.env`. Áp cho MỌI agent, kể cả subagent.

BÀI HỌC THẬT (phát hiện 2026-08-25, dự án nhathuocbenhvien): rule chữ
`no-hardcoded-secrets` ("secret luôn vào .env, gặp file cũ hardcode thì dọn ngay") ĐÃ CÓ
SẴN trong bộ luật, vậy mà vẫn để lọt hàng loạt:
  - mật khẩu quản trị nằm nguyên chữ trong `docs/.../admin-panel-info.md`;
  - mật khẩu FTP nằm nguyên chữ trong một tệp `*.bak-env`;
  - mật khẩu ứng dụng Gmail nằm nguyên chữ trong `docs/.../email-setup.md` và `TODO.md`;
  - token cứng trong `clone-src/deploy/_gmtest.php`.
Nguy hiểm hơn: một agent còn TỰ HẠ mức nghiêm trọng với lý do "tệp không public trên web
nên không khẩn cấp". Founder bác bỏ dứt khoát: "máy tao cũng phải rule .env" —
KHÔNG CÓ NGOẠI LỆ CHO MÁY LOCAL.

WHY phải là hook PreToolUse chứ không phải thêm dòng markdown:
  Markdown là XÁC SUẤT — agent đọc rồi vẫn quên, và subagent thì thường không thấy dòng
  luật đó (hook `UserPromptSubmit` KHÔNG bắn cho subagent). Pre-commit cũng không cứu nổi
  vì mấy tệp trên nằm ngoài git hoặc chưa từng được commit. Chỉ `PreToolUse` mới đứng
  chắn ĐÚNG khoảnh khắc nội dung sắp chạm đĩa, cho mọi agent, mọi phiên, mọi dự án.

CHẶN (permissionDecision="deny") khi Write/Edit/MultiEdit/NotebookEdit/Bash định GHI vào
tệp KHÔNG PHẢI `.env` một trong các thứ sau:
  - gán kiểu `password|passwd|pwd|secret|api_key|token|credential|passphrase|client_secret`
    `= / :` kèm một giá trị TRÔNG NHƯ THẬT (>= 8 ký tự, không phải placeholder);
  - mật khẩu ứng dụng Gmail dạng 4 cụm 4 chữ cái trên dòng có từ khoá bí mật;
  - khối khoá riêng `-----BEGIN ... PRIVATE KEY-----`;
  - token có tiền tố nhận diện được: `sk-`, `ghp_`, `github_pat_`, `AKIA`, `xoxb-`,
    `AIza`, `glpat-`, token bot Telegram;
  - chuỗi kết nối có mật khẩu: `scheme://user:<mat-khau>@host`.

CHO QUA (chặn nhầm là nghẽn việc — đây mới là cách làm ĐÚNG, không được cản):
  - ghi vào `.env`, `.env.*`, `*.env` (kể cả `.env.example`);
  - giá trị rõ ràng là placeholder: `<...>`, `xxx`, `***`, `your_...`, `changeme`,
    `example`, `TODO`, `${BIEN}`, `$BIEN`, `xem .env`, `dummy`, `redacted`...;
  - code ĐỌC secret đúng cách: `os.getenv("DB_PASSWORD")`, `process.env.TOKEN`,
    `os.environ[...]`, `config.password`;
  - mọi thao tác chỉ ĐỌC (Read/Grep/Glob/`cat`/`grep`) — hook chỉ soi hành vi GHI;
  - lệnh Bash không hề ghi ra tệp (không `>`/`>>`/`tee`/heredoc vào tệp);
  - cửa thoát có chủ đích khi founder ĐÃ ĐỒNG Ý: đặt chuỗi `univ3-secret-ok` ngay trên
    dòng đó, hoặc `SECRET_WRITE_OK=1` ở đầu lệnh Bash.

Fail-open tuyệt đối: input lạ / lỗi bất kỳ -> exit 0, không kẹt phiên.
"""
import json
import os
import re
import sys

MARKER = "univ3-secret-ok"          # cửa thoát khi founder đã đồng ý
BASH_ESCAPE = re.compile(r"(?<![\w./-])SECRET_WRITE_OK\s*=\s*1\b")
SELF = "no_secret_in_file_enforce.py"   # tệp hook này chứa sẵn mẫu -> tự miễn trừ

# ── nhận diện tệp .env (được phép chứa secret thật) ──────────────────────────
ENV_FILE = re.compile(r"(^|/)\.env(\.|$)|\.env$", re.I)

# tệp SINH RA (không phải nơi con người viết secret) -> bỏ qua cho đỡ chặn nhầm
GENERATED = re.compile(
    r"(^|/)(node_modules|\.next|\.open-next|dist|build|out|vendor|coverage|\.venv)(/|$)"
    r"|\.min\.(js|css)$|(^|/)(package-lock\.json|pnpm-lock\.yaml|yarn\.lock)$", re.I)

# ── mẫu 1: gán khoá-bí-mật = giá trị ─────────────────────────────────────────
KEY_ASSIGN = re.compile(r"""(?ix)
    (?<![A-Za-z0-9])
    ( pass(?:word|wd)? | pwd | secret | api[_-]?key | apikey | passphrase
    | access[_-]?token | auth[_-]?token | refresh[_-]?token | bearer | token
    | credentials? | client[_-]?secret | private[_-]?key
    | mat[_\s-]?khau | mật[_\s-]?khẩu )
    [A-Za-z0-9_\-]{0,24}
    \s* (?: := | == | = | : ) \s*
    (?: " ([^"\n]{0,200}) " | ' ([^'\n]{0,200}) ' | ` ([^`\n]{0,200}) ` | ([^\s\n,;)\]}]{1,200}) )
""")

# ── mẫu 2: mật khẩu ứng dụng Gmail: 4 cụm 4 chữ cái (chỉ tính trên dòng có từ khoá) ──
APP_PASSWORD = re.compile(
    r"(?i)(?:pass\w*|pwd|mat\s?khau|mật\s?khẩu|app[_\s-]?password)[^\n]{0,24}[:=]\s*"
    r"(?<![A-Za-z])([a-z]{4}[ \-][a-z]{4}[ \-][a-z]{4}[ \-][a-z]{4})(?![A-Za-z])")
MAX_LINE = 400     # dòng dài hơn = dữ liệu/bundle rút gọn -> BỎ QUA cả dòng.
                   # Vừa chống chặn nhầm (file JSON danh mục), vừa giữ hook chạy nhanh:
                   # quét regex trên dòng minified dài hàng trăm KB tốn hàng chục giây.
MAX_CHARS = 2_000_000   # nội dung to hơn -> chỉ soi phần đầu, tránh treo phiên

# ── mẫu 3: khối khoá riêng ───────────────────────────────────────────────────
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z0-9 ]{0,40}PRIVATE KEY-----")

# ── mẫu 4: token có tiền tố nhận diện được ───────────────────────────────────
PREFIXED = [
    ("khoá API OpenAI/Anthropic (sk-…)",    re.compile(r"(?<![A-Za-z0-9_/-])sk-(?:ant-)?[A-Za-z0-9_\-]{16,}")),
    ("token GitHub (ghp_/gho_/github_pat_)", re.compile(r"(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")),
    ("khoá truy cập AWS (AKIA…)",            re.compile(r"(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}(?![A-Za-z0-9])")),
    ("token Slack (xox…)",                   re.compile(r"(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("khoá API Google (AIza…)",              re.compile(r"(?<![A-Za-z0-9_])AIza[A-Za-z0-9_\-]{30,}")),
    ("token GitLab (glpat-…)",               re.compile(r"(?<![A-Za-z0-9_])glpat-[A-Za-z0-9_\-]{15,}")),
    ("token bot Telegram",                   re.compile(r"(?<![0-9])\d{8,12}:AA[A-Za-z0-9_\-]{30,}")),
]

# ── mẫu 5: chuỗi kết nối có mật khẩu ─────────────────────────────────────────
CONN_URL = re.compile(r"(?i)\b[a-z][a-z0-9+.\-]{1,20}://[^\s:@/]{1,64}:([^\s:@/\"']{6,64})@[^\s\"']+")

# ── placeholder: thấy là CHO QUA ─────────────────────────────────────────────
PLACEHOLDER_SUB = (
    "<", ">", "${", "$(", "%s", "%d", "{{", "}}", "xxx", "***", "...", "___",
    "your_", "your-", "your ", "yourpass", "changeme", "change-me", "change_me",
    "example", "placeholder", "dummy", "redacted", "masked", "sample", "fake",
    "todo", "tbd", "n/a", "notset", "not_set", "no_secret",
    ".env", "getenv", "environ", "process.env", "dotenv", "secrets.", "vault",
    "xem ", "dat ", "đặt ", "điền", "dien ", "thay ", "bí mật", "bi mat",
    "mật khẩu", "mat khau", "không", "khong", "bắt buộc", "bat buoc", "ở đây",
)
PLACEHOLDER_EQ = {
    "true", "false", "null", "none", "nil", "undefined", "required", "optional",
    "string", "str", "boolean", "bool", "number", "integer", "int", "object",
    "array", "any", "unknown", "empty", "hidden", "secret", "password", "pass",
    "token", "apikey", "api_key", "credential", "credentials", "hash", "hashed",
    "bcrypt", "argon2", "encrypted", "plaintext", "removed", "deleted", "unset",
    "same-origin", "include", "omit", "cors", "no-cors", "anonymous",
    "use-credentials", "bearer", "basic", "digest",
}
# biểu thức code (đọc secret đúng cách) -> cho qua
CODE_EXPR = re.compile(r"""(?x)
    ^[\$&*@(\[{]                               # $var, (string)(...), [..], {..}, @annotation
  | ^[A-Za-z_][A-Za-z0-9_]*\s*[\(\[]           # getenv(...), config[...]
  | ^[A-Za-z_][A-Za-z0-9_]*[?!]?\.[A-Za-z_]   # process.env.X, self.password, env?.SECRET
  | ^(await|new|require|import|typeof|def|function|lambda|return)\b
""")


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z_]*$")      # chữ cái + gạch dưới, KHÔNG chữ số
CAMEL = re.compile(r"^[a-z_]+[A-Z]")
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)+$")  # TÊN BIẾN: ADMIN_PASSWORD, SSH_KEY
TEMPLATE_MARK = re.compile(r"^(__.*__|%%.*%%|@@.*@@|<%.*%>)$")   # ô trống của bản mẫu
PATH_LIKE = ("/", "./", "../", "~/", "http://", "https://", "www.")
PATH_RE = re.compile(r"^[a-z0-9_.\-]+(/[a-z0-9_.\-]*)+$")   # docs/research/ — đường dẫn thường


def looks_placeholder(val: str, quoted: bool = True) -> bool:
    """True = giá trị này KHÔNG phải secret thật -> cho qua.

    `quoted=False` (giá trị trần, không nằm trong dấu nháy): thêm một cửa cho qua cho
    ĐỊNH DANH code — `TOKEN = auth_token`, `pwd = userPassword` là gán biến, không phải
    mật khẩu. Chỉ áp khi giá trị toàn chữ cái/gạch dưới (KHÔNG có chữ số) và trông đúng
    kiểu tên biến (`snake_case` hoặc `camelCase`); `abc123xyz` hay `Matkhau2026` không
    lọt cửa này."""
    v = (val or "").strip().strip("\"'`,;")
    if len(v) < 8:
        return True
    low = v.lower()
    if low in PLACEHOLDER_EQ:
        return True
    if any(p in low for p in PLACEHOLDER_SUB):
        return True
    if len(set(v)) <= 2:                      # ****, xxxxxxxx, --------
        return True
    if any(ord(c) > 127 for c in v):          # có dấu tiếng Việt -> văn xuôi, không phải secret
        return True
    if ENV_NAME.match(v):                     # đúng cách làm: tài liệu chỉ ghi TÊN BIẾN
        return True
    if TEMPLATE_MARK.match(v):                # __SMTP_PASS__ = ô trống chờ điền từ .env
        return True
    if v.startswith(PATH_LIKE) or PATH_RE.match(v):   # đường dẫn / URL, không phải secret
        return True
    if CODE_EXPR.search(v):                   # os.getenv(...), process.env.TOKEN
        return True
    if not quoted and IDENTIFIER.match(v) and ("_" in v or CAMEL.match(v) or len(v) <= 10):
        return True                           # tên biến / từ văn xuôi: auth_token, dropdown
    return False


def mask(val: str) -> str:
    v = (val or "").strip()
    return (v[:2] + "…" + "*" * 6) if len(v) > 3 else "***"


def scan_text(text: str, where: str) -> str:
    """Trả lý do chặn (rỗng = sạch). KHÔNG BAO GIỜ in nguyên giá trị bí mật."""
    if not text:
        return ""
    for ln, line in enumerate(text[:MAX_CHARS].splitlines(), 1):
        if MARKER in line or len(line) > MAX_LINE:
            continue
        stripped = line.strip()

        m = PRIVATE_KEY.search(line)
        if m:
            return f"{where} dòng {ln}: có khối KHOÁ RIÊNG `{m.group(0)[:32]}…`"

        for label, rx in PREFIXED:
            mm = rx.search(line)
            if mm and not looks_placeholder(mm.group(0)):
                return f"{where} dòng {ln}: có {label} — `{mask(mm.group(0))}`"

        mc = CONN_URL.search(line)
        if mc and not looks_placeholder(mc.group(1)):
            return (f"{where} dòng {ln}: chuỗi kết nối nhúng thẳng MẬT KHẨU "
                    f"(`scheme://user:{mask(mc.group(1))}@host`)")

        for ma in KEY_ASSIGN.finditer(line):
            key = ma.group(1)
            quoted = (ma.group(2) or ma.group(3) or ma.group(4)) is not None
            val = (ma.group(2) or ma.group(3) or ma.group(4) or ma.group(5) or "")
            val = val.strip().strip("\"'`,;")
            if looks_placeholder(val, quoted):
                continue
            return (f"{where} dòng {ln}: gán `{key}` = một GIÁ TRỊ THẬT "
                    f"(`{mask(val)}`, {len(val)} ký tự)")

        mg = APP_PASSWORD.search(stripped)
        if mg and not looks_placeholder(mg.group(1)):
            return (f"{where} dòng {ln}: trông như MẬT KHẨU ỨNG DỤNG Gmail "
                    f"(4 cụm 4 chữ cái) — `{mask(mg.group(1))}`")
    return ""


HOW_TO = """CÁCH ĐÚNG (rules/GATES.md §Env — secrets):
  1. Giá trị thật CHỈ nằm trong `.env` của máy/máy chủ đó:
        printf '%s\\n' 'ADMIN_PASSWORD=<dán giá trị thật>' >> .env
        chmod 600 .env            # và `.gitignore` phải có `.env*`
  2. Trong TÀI LIỆU (`.md`, `TODO.md`, ghi chú) chỉ ghi TÊN BIẾN, không ghi giá trị:
        Mật khẩu quản trị: xem biến `ADMIN_PASSWORD` trong `.env` (không chép ra đây)
  3. Trong CODE đọc từ biến môi trường, không viết thẳng:
        os.getenv("ADMIN_PASSWORD")   ·   process.env.ADMIN_PASSWORD
  4. `.env.example` chỉ chứa TÊN BIẾN + placeholder (`ADMIN_PASSWORD=<đặt trong .env>`).
  5. Giá trị vừa định ghi mà TỪNG bị lộ ở đâu đó -> đổi (rotate) ngay tại nguồn.

KHÔNG CÓ NGOẠI LỆ CHO MÁY LOCAL. Nguyên văn founder: "máy tao cũng phải rule .env".
Lý do "tệp này không public trên web nên không sao" đã bị bác bỏ dứt khoát — tệp local
vẫn bị chép vào backup, vào `*.bak-*`, vào script deploy quét cả thư mục, vào transcript
của agent. Đừng tự hạ mức nghiêm trọng.

Đây thật sự là placeholder / dữ liệu giả và founder ĐÃ ĐỒNG Ý ghi -> thêm chuỗi
`univ3-secret-ok` ngay trên dòng đó (hoặc `SECRET_WRITE_OK=1` ở đầu lệnh Bash)."""


# ── Bash: chỉ soi khi lệnh THẬT SỰ ghi ra tệp ────────────────────────────────
REDIR = re.compile(r"(?<![0-9<>&])>>?\s*(?![&|(])([^\s;&|<>()]+)")
TEE = re.compile(r"(?<![\w./-])tee\s+(?:-[a-zA-Z]+\s+)*([^\s;&|<>()]+)")
HEREDOC = re.compile(r"<<-?\s*['\"]?[A-Za-z_][A-Za-z0-9_]*")


def bash_targets(cmd: str):
    """(có_ghi_tệp, [tệp đích]). /dev/null, /dev/stderr... không tính là tệp."""
    out = []
    for rx in (REDIR, TEE):
        for m in rx.finditer(cmd):
            t = m.group(1).strip("\"'")
            if t.startswith("/dev/") or t in ("-",):
                continue
            out.append(t)
    return (bool(out) or bool(HEREDOC.search(cmd))), out


def check(tool: str, ti: dict) -> str:
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        path = str(ti.get("file_path") or ti.get("notebook_path") or "")
        if ENV_FILE.search(path) or GENERATED.search(path) or os.path.basename(path) == SELF:
            return ""
        parts = []
        if tool == "Write":
            parts.append(("nội dung sắp ghi", ti.get("content")))
        elif tool == "Edit":
            parts.append(("nội dung mới", ti.get("new_string")))
        elif tool == "NotebookEdit":
            parts.append(("ô notebook mới", ti.get("new_source")))
        else:
            for i, e in enumerate(ti.get("edits") or [], 1):
                if isinstance(e, dict):
                    parts.append((f"sửa #{i}", e.get("new_string")))
        for label, txt in parts:
            why = scan_text(str(txt or ""), label)
            if why:
                return f"`{tool}` vào `{path or '?'}` — {why}"
        return ""

    if tool == "Bash":
        cmd = str(ti.get("command") or "")
        if not cmd or BASH_ESCAPE.search(cmd):
            return ""
        writes, targets = bash_targets(cmd)
        if not writes:
            return ""            # chỉ đọc / grep / chạy chương trình -> không phải việc của hook
        if targets and all(ENV_FILE.search(t) for t in targets):
            return ""            # ghi thẳng vào .env -> ĐÚNG, cho qua
        if targets and all(os.path.basename(t) == SELF for t in targets):
            return ""
        why = scan_text(cmd, "lệnh Bash")
        if why:
            dest = ", ".join("`%s`" % t for t in targets[:3]) or "một tệp (heredoc)"
            return f"lệnh Bash ghi ra {dest} — {why}"
    return ""


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    if str(data.get("hook_event_name") or "") != "PreToolUse":
        return 0
    try:
        tool = str(data.get("tool_name") or "")
        ti = data.get("tool_input") or {}
        if not isinstance(ti, dict):
            return 0
        why = check(tool, ti)
        if not why:
            return 0
        reason = ("CHẶN GHI THÔNG TIN BÍ MẬT — " + why +
                  ".\n\nLUẬT FOUNDER: secret THẬT chỉ được nằm trong `.env` (chmod 600), "
                  "tài liệu và code chỉ được nhắc TÊN BIẾN.\n\n" + HOW_TO)
    except Exception:
        return 0

    json.dump(
        {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }},
        sys.stdout, ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
