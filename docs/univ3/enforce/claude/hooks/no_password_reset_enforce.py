#!/usr/bin/env python3
"""no_password_reset_enforce.py — CẤM TẤT ĐỊNH việc sửa mật khẩu / bảng người dùng
trên DB PRODUCTION để "vượt màn đăng nhập mà test".

Luật founder (nguyên văn): "nếu các app iOS hay thậm chí các web mà cần đăng nhập,
thì mày đừng reset password của tao, mày có mã nguồn, mày có thể vào thẳng xuyên qua
màn đăng nhập. chỉ để test xem từ màn đăng nhập vào có hóc gì không thôi nhé."

WHY hook chứ không thêm dòng luật: lỗi này ĐÃ XẢY RA (trí nhớ dự án ghi "reset pass =
123456"). Luật markdown là xác suất, permissionDecision là cổng tất định.

WHY "ask" chứ KHÔNG "deny": hook không biết AI khởi xướng lệnh — agent tự tiện hay
chính founder ra lệnh. "ask" đúng cho cả hai: agent tự tiện thì founder thấy câu hỏi
hiện lên bất ngờ và chặn lại được; founder chủ động ra lệnh thì bấm duyệt 1 cái là chạy,
không phải sửa hook / tắt hook / `--no-verify`. "deny" thì khoá tay luôn chính chủ.
WHY KHÔNG có cơ chế nhớ lựa chọn / file skip vĩnh viễn (khác docs_bootstrap_gate.py):
đây là thao tác đụng mật khẩu THẬT trên production, mỗi lần đều đáng hỏi lại; nhớ 1 lần
rồi im mãi là mở toang cửa.

  PreToolUse Bash — soi lệnh sắp chạy. HỎI (ask) khi hội đủ 2 điều kiện:
    (1) nhắm vào DB PRODUCTION: `--remote`, `--env production|prod`, hoặc gọi
        api.cloudflare.com/.../d1/ qua curl;
    (2) là câu lệnh GHI (UPDATE/INSERT/REPLACE/DELETE) vào bảng người dùng
        (tên bảng chứa user/account/member/auth/credential/login) HOẶC có cột mật khẩu.

  CHO QUA: SELECT (đọc thuần) · DB local (`--local`, `wrangler dev`, `.wrangler/`)
  · file .sql chỉ có CREATE/INSERT vào bảng không phải người dùng (vd db/schema.sql).

Fail-open tuyệt đối: không parse nổi / lỗi bất kỳ -> exit 0. Thà lọt còn hơn kẹt phiên,
vì cổng này chỉ là lớp chặn phản xạ xấu, không phải lớp bảo mật cuối.
"""
import json
import os
import re
import sys

# ===================== DẤU HIỆU (khai báo 1 chỗ, viết TỔNG QUÁT cho mọi project) =====================
# Production: chỉ tính khi có tín hiệu RÕ RÀNG, không suy đoán.
PROD_MARKERS = (
    re.compile(r"--remote\b"),
    re.compile(r"--env[= ]+(production|prod)\b", re.I),
    re.compile(r"api\.cloudflare\.com/\S*/d1/", re.I),
)
# Local hợp lệ: test local là việc bình thường, chặn bừa sẽ nghẽn việc.
LOCAL_MARKERS = (
    re.compile(r"--local\b"),
    re.compile(r"--preview\b"),
    re.compile(r"--persist-to\b"),
    re.compile(r"wrangler\s+dev\b"),
    re.compile(r"\.wrangler/"),
)

# Bảng "người dùng" — khớp theo NGỮ NGHĨA tên bảng, không hardcode tên của 1 project.
USER_TABLE = re.compile(r"(user|account|member|auth|credential|login|profile)", re.I)
# Cột mật khẩu thường gặp (vevoi dùng `pass_hash`, project khác dùng tên khác).
PASS_COL = re.compile(
    r"\b(pass|pass_hash|passhash|password|password_hash|hashed_password|passwd|pwd|salt)\b",
    re.I,
)
WRITE_STMT = re.compile(r"^\s*(UPDATE|INSERT|REPLACE|DELETE)\b", re.I)
# Bảng đích của từng loại câu ghi.
TARGET = (
    re.compile(r"\bUPDATE\s+(?:OR\s+\w+\s+)?[\"'`\[]?(\w+)", re.I),
    re.compile(r"\bINTO\s+[\"'`\[]?(\w+)", re.I),
    re.compile(r"\bDELETE\s+FROM\s+[\"'`\[]?(\w+)", re.I),
)

# Nguồn lấy SQL trong lệnh shell.
SQL_INLINE = (
    re.compile(r"--command[= ]+(\"[^\"]*\"|'[^']*'|\S+)", re.I),
    re.compile(r"(?<!-)-c[= ]+(\"[^\"]*\"|'[^']*')", re.I),
    re.compile(r"--data(?:-raw|-binary)?[= ]+(\"[^\"]*\"|'[^']*')", re.I),
    # `-d` dạng ngắn của curl. Chỉ tới được đây khi lệnh ĐÃ có dấu hiệu production
    # (api.cloudflare.com/.../d1/) nên không sợ đụng `-d` của lệnh khác.
    re.compile(r"(?<![\w-])-d[= ]+(\"[^\"]*\"|'[^']*')", re.I),
)
SQL_FILE = re.compile(r"--file[= ]+(\"[^\"]*\"|'[^']*'|\S+)", re.I)

HOW_TO = (
    "Cần vượt màn đăng nhập để test thì làm 1 trong 3 cách:\n"
    "  (1) Tự ký session token hợp lệ từ secret có sẵn trong mã nguồn.\n"
    "  (2) Tạo tài khoản TEST riêng, không đụng user thật.\n"
    "  (3) Chạy backend local với D1 local (`--local`) và dữ liệu giả.\n"
    "Mật khẩu tài khoản thật của chủ dự án là BẤT KHẢ XÂM PHẠM."
)
# =====================================================================================


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def is_production(cmd: str) -> bool:
    """`--remote` thắng tuyệt đối; ngoài ra có dấu hiệu local thì coi là local."""
    if re.search(r"--remote\b", cmd):
        return True
    if any(p.search(cmd) for p in LOCAL_MARKERS):
        return False
    return any(p.search(cmd) for p in PROD_MARKERS)


def collect_sql(cmd: str) -> str:
    """Gom SQL từ --command / --data / --file. File đọc không nổi -> bỏ qua (fail-open):
    thà lọt còn hơn chặn oan một lệnh mà hook không nhìn thấy nội dung."""
    parts = []
    for pat in SQL_INLINE:
        for m in pat.finditer(cmd):
            parts.append(_unquote(m.group(1)))
    # Payload API D1 là JSON (`{"sql": "..."}`) — bóc câu SQL ra, nếu không thì câu lệnh
    # không nằm ở ĐẦU chuỗi và bộ dò theo-từng-câu bên dưới sẽ trượt.
    for raw in list(parts):
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if isinstance(obj, dict):
            parts.extend(v for v in obj.values() if isinstance(v, str))
    for m in SQL_FILE.finditer(cmd):
        path = _unquote(m.group(1))
        try:
            if os.path.getsize(path) <= 1_000_000:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    parts.append(fh.read())
        except OSError:
            pass
    return "\n".join(parts)


def db_name(cmd: str) -> str:
    """Tên DB đứng ngay sau `d1 execute` — để câu hỏi nói rõ đang đụng DB nào."""
    m = re.search(r"\bd1\s+execute\s+([\w.-]+)", cmd, re.I)
    return m.group(1) if m else ""


def offending(sql: str) -> str:
    """Trả câu lệnh GHI đầu tiên đụng bảng người dùng / cột mật khẩu ('' nếu sạch).

    Tách theo `;` rồi soi TỪNG câu — nhờ vậy file schema (CREATE TABLE users ... pass_hash
    + INSERT vào bảng khác) không bị chặn oan: câu CREATE không phải câu ghi, còn câu
    INSERT thì không nhắm bảng người dùng.
    """
    for chunk in sql.split(";"):
        # Câu ghi có thể không nằm ở ĐẦU chunk (payload JSON `{"sql": "..."}`, hay SQL
        # nhiều dòng) -> dò theo TỪNG DÒNG, thấy dòng nào mở đầu câu ghi thì lấy từ đó
        # tới hết chunk làm câu lệnh. Vẫn giữ được tính "theo từng câu" nên file schema
        # (CREATE TABLE users ... pass_hash) không bị chặn oan.
        lines = chunk.splitlines()
        start = next((i for i, ln in enumerate(lines) if WRITE_STMT.search(ln)), -1)
        if start < 0:
            continue
        stmt = "\n".join(lines[start:])
        table = ""
        for pat in TARGET:
            m = pat.search(stmt)
            if m:
                table = m.group(1)
                break
        if (table and USER_TABLE.search(table)) or PASS_COL.search(stmt):
            return " ".join(stmt.split())[:200]
    return ""


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0

    if str(data.get("hook_event_name") or "") != "PreToolUse":
        return 0
    if str(data.get("tool_name") or "") != "Bash":
        return 0

    try:
        cmd = (data.get("tool_input") or {}).get("command", "") or ""
        if not cmd or not is_production(cmd):
            return 0
        sql = collect_sql(cmd)
        if not sql:
            return 0
        bad = offending(sql)
        if not bad:
            return 0
        dbname = db_name(cmd)
        reason = (
            "XÁC NHẬN — lệnh này sắp GHI vào bảng người dùng / mật khẩu trên DB PRODUCTION.\n"
            f"  DB: {dbname or '(không rõ tên)'}  ·  môi trường: PRODUCTION\n"
            f"  Sắp ghi: {bad}\n\n"
            "Nếu chỉ để VƯỢT MÀN ĐĂNG NHẬP mà test thì KHÔNG cần reset mật khẩu — "
            "ký session token / tạo user test / chạy D1 local là đủ.\n\n"
            + HOW_TO
        )
    except Exception:
        return 0

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
