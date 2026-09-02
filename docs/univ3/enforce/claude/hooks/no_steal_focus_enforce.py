#!/usr/bin/env python3
"""no_steal_focus_enforce.py — CẤM TẤT ĐỊNH việc agent cướp CHUỘT / BÀN PHÍM / CỬA SỔ
của người dùng khi test app (đặc biệt iOS Simulator).

Luật founder (nguyên văn): "tại sao test emulator thì phải control chuột của tao à?
và có thể run nó bên dưới các app khác không, vẫn hiện ra nhưng hiện bên dưới, tự cho
nó ấm không được à? cứ hiện lên che các màn khác, lấy quyền dùng chuột của tao".

WHY hook chứ không thêm dòng luật markdown: lỗi này ĐÃ XẢY RA NHIỀU LẦN — agent dựng
sẵn `/tmp/tapper.swift` (CGEvent bơm click vào toạ độ MÀN HÌNH THẬT) + `osascript ...
activate` để kéo cửa sổ Simulator lên trước rồi mới bấm. Người dùng đang gõ dở thì bị
giật chuột, bị che màn hình. Markdown là xác suất, permissionDecision là cổng tất định.

WHY "deny" chứ KHÔNG "ask": thao tác này không bao giờ là thứ founder chủ động nhờ —
luôn có đường thay thế headless làm được đúng việc đó. Hỏi cũng chỉ tổ gián đoạn thêm.

  PreToolUse Bash — soi lệnh sắp chạy. CHẶN khi lệnh:
    - gọi công cụ bơm sự kiện chuột/phím hệ thống: `cliclick`, và chương trình tự biên
      dịch từ CGEvent (`.post(tap: .cghidEventTap)`);
    - `osascript` / AppleScript có `activate`, `AXRaise`, `click at`, `keystroke`,
      `key code`, `set frontmost` — tức là kéo cửa sổ lên trước hoặc gửi phím/chuột;
    - `open -a Simulator` (hoặc app bất kỳ) mà KHÔNG có cờ `-g` — mở lên trước, che màn.

  CHẶN CẢ ĐƯỜNG VÒNG: agent hay gói mấy thứ trên vào file rồi gọi file (`bash /tmp/tapv.sh`,
  `swiftc /tmp/tapper.swift -o /tmp/tapper`, rồi `/tmp/tapper 120 340`). Nên hook đọc luôn
  NỘI DUNG của file được ĐEM RA CHẠY (kể cả binary đã biên dịch — dò symbol `CGEventPost`).
  Chỉ soi file được CHẠY, không soi file bị `cat`/`grep` — nhờ vậy đọc tài liệu nói về
  `cliclick` vẫn bình thường.

  CHO QUA (đây là CÁCH ĐÚNG, chặn nhầm là nghẽn việc):
    - mọi `xcrun simctl ...` (boot/install/launch/openurl/io screenshot) — headless;
    - mọi `xcodebuild ...` kể cả `xcodebuild test` (XCUITest bấm bằng API trong
      simulator, không đụng con trỏ chuột thật);
    - `osascript` chỉ ĐỌC trạng thái (`get name of every process`, `get position of`...);
    - `open -g -a ...` (mở ở nền, không đưa lên trước).

Fail-open tuyệt đối: không parse nổi / lỗi bất kỳ -> exit 0. Thà lọt còn hơn kẹt phiên.
"""
import json
import os
import re
import shlex
import sys

# ===================== DẤU HIỆU (khai báo 1 chỗ) =====================
# 1) Công cụ bơm sự kiện chuột/phím vào MÁY THẬT. So khớp ở VỊ TRÍ LỆNH, không phải bất kỳ
#    đâu trong chuỗi — nếu không thì `grep -rn cliclick docs/` cũng bị chặn oan.
INJECT_TOOLS = {"cliclick", "xdotool"}

# 2) AppleScript kéo cửa sổ lên trước / gửi phím-chuột. Chỉ tính khi thực sự có động từ
#    GHI — `osascript` đọc trạng thái (get name of every process) là lệnh lành.
APPLESCRIPT_WRITE = re.compile(
    r"\bactivate\b"
    r"|\bAXRaise\b"
    r"|\bclick\s+at\b"
    r"|\bkeystroke\b"
    r"|\bkey\s+code\b"
    r"|\bset\s+frontmost\s+to\b"
    r"|\bperform\s+action\b",
    re.I,
)

# 3) `open -a <App>` không có `-g`. `-g` có thể đứng bất cứ đâu trong cụm cờ.
OPEN_APP = re.compile(r"(?<![\w./-])open\s+((?:-{1,2}[\w-]+\s+)*)-a\s+(\"[^\"]+\"|'[^']+'|\S+)", re.I)
OPEN_BG_FLAG = re.compile(r"(?<![\w-])-(g|-background|j|-hide)\b")

# 4) Dấu hiệu tìm trong NỘI DUNG script shell / binary được đem ra chạy.
#    Cố ý chỉ lấy dấu hiệu MẠNH: `source venv/bin/activate` trong script build không được
#    phép bị chặn oan, nên `activate` chỉ tính khi đi cùng `tell application`.
FILE_MARKERS = (
    re.compile(rb"cghidEventTap"),
    re.compile(rb"CGEventPost"),
    re.compile(rb"CGEventCreate(?:Mouse|Keyboard)Event"),
    re.compile(rb"CGWarpMouseCursorPosition"),
    re.compile(rb"(?<![\w./-])cliclick\b"),
    re.compile(rb"tell\s+application[^\n]{0,80}\bactivate\b", re.I),
    re.compile(rb"\bAXRaise\b"),
    re.compile(rb"\bclick\s+at\b", re.I),
    re.compile(rb"\bkeystroke\b", re.I),
)
# Shell chạy 1 file script: file cần soi là ĐỐI SỐ đứng sau, không phải chính nó.
# WHY chỉ shell (không python3/node/swiftc): script python/node hay CHỨA mấy chữ cấm dưới
# dạng chuỗi vì nó đang VIẾT TÀI LIỆU về luật này — soi nội dung là chặn oan. Còn mã bơm
# chuột thật thì lúc ĐEM RA CHẠY (`./tapper`) vẫn bị tóm.
SHELLS = {"bash", "sh", "zsh", "ksh", "dash"}
SEGMENT_SPLIT = re.compile(r"(?:\|\||&&|[;|\n&])")

# Heredoc: `python3 - <<'PY' ... PY` — phần thân là DỮ LIỆU đưa vào stdin, không phải lệnh.
# Không bóc ra thì viết tài liệu có ví dụ `open -a Simulator` cũng bị chặn oan.
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

HOW_TO = (
    "CÁCH ĐÚNG (làm được đúng việc đó mà KHÔNG đụng chuột / màn hình của người dùng):\n"
    "  • Tạo device riêng cho agent, đừng dùng chung device người dùng đang xem:\n"
    "      UDID=$(xcrun simctl create agent-lab 'iPhone 17 Pro' <runtime>)\n"
    "      xcrun simctl boot \"$UDID\"\n"
    "  • Cài / chạy / mở link / chụp ảnh — tất cả headless, không cần cửa sổ:\n"
    "      xcrun simctl install \"$UDID\" <App>.app\n"
    "      xcrun simctl launch  \"$UDID\" <bundle-id>\n"
    "      xcrun simctl openurl \"$UDID\" \"http://127.0.0.1:8788/...\"\n"
    "      xcrun simctl io      \"$UDID\" screenshot /tmp/sim.png   # rồi ĐỌC ảnh\n"
    "  • Cần TỰ BẤM trong app: XCUITest — bấm bằng API trong simulator, không dùng con trỏ thật:\n"
    "      xcodebuild test -scheme <Scheme> -destination \"id=$UDID\"\n"
    "  • Web trong Safari simulator: bơm `PointerEvent`/`dispatchEvent` bằng JS, đừng bấm chuột thật.\n"
    "  • Bắt buộc phải có GUI thì mở ở NỀN, không đưa lên trước:  open -g -a Simulator\n"
    "  • Xong việc thì dọn:  xcrun simctl shutdown \"$UDID\" && xcrun simctl delete \"$UDID\"\n"
    "CẤM tuyệt đối: cliclick / CGEvent bơm chuột-phím / osascript activate / AXRaise — "
    "người dùng đang làm việc trên chính cái máy này."
)
# =====================================================================


def strip_heredocs(cmd: str) -> str:
    """Bỏ THÂN heredoc — trừ khi chính shell đọc nó (`bash <<EOF` là chạy thật)."""
    lines = cmd.splitlines()
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = HEREDOC.search(line)
        i += 1
        if not m:
            continue
        head = line.strip().split()[0] if line.strip() else ""
        if os.path.basename(head) in SHELLS:   # `bash <<EOF` -> thân là lệnh thật, giữ lại
            continue
        delim = m.group(2)
        while i < len(lines) and lines[i].strip() != delim:
            i += 1
        i += 1                                  # bỏ luôn dòng kết thúc heredoc
    return "\n".join(out)


def segments(cmd: str):
    """Tách lệnh thành từng đoạn rồi tokenize. Nhờ vậy phân biệt được TÊN LỆNH
    (`cliclick c:1,2`) với ĐỐI SỐ chỉ nhắc tới tên đó (`grep -rn cliclick docs/`)."""
    out = []
    for seg in SEGMENT_SPLIT.split(strip_heredocs(cmd)):
        seg = seg.strip()
        if not seg:
            continue
        try:
            toks = shlex.split(seg)
        except ValueError:
            toks = seg.split()
        if toks:
            out.append(toks)
    return out


def head_index(toks):
    """Vị trí TÊN LỆNH thật — bỏ qua `VAR=1`, `sudo`, `env`, `nohup`, `time`."""
    i = 0
    while i < len(toks):
        t = toks[i]
        if re.fullmatch(r"[A-Za-z_][\w]*=.*", t) or t in ("sudo", "env", "nohup", "time", "command", "exec"):
            i += 1
            continue
        return i
    return -1


def script_arg(toks, i):
    """File nguồn mà trình thông dịch/biên dịch sắp chạy — đối số đầu không phải cờ."""
    skip = False
    for t in toks[i + 1:]:
        if skip:
            skip = False
            continue
        if t.startswith("-"):
            skip = t in ("-e", "-c", "-o", "-l", "-module-name")
            continue
        return t
    return ""


def scan_file(path: str) -> str:
    """Tên dấu hiệu tìm thấy trong file ('' nếu sạch / không đọc được -> fail-open)."""
    try:
        if not os.path.isfile(path) or os.path.getsize(path) > 20_000_000:
            return ""
        with open(path, "rb") as fh:
            blob = fh.read()
    except OSError:
        return ""
    for pat in FILE_MARKERS:
        m = pat.search(blob)
        if m:
            return m.group(0).decode("utf-8", "replace")
    return ""


def offending(cmd: str) -> str:
    """Trả lý do bị chặn ('' nếu lệnh sạch)."""
    for toks in segments(cmd):
        i = head_index(toks)
        if i < 0:
            continue
        head = toks[i]
        base = os.path.basename(head)
        seg = " ".join(toks[i:])

        if base in INJECT_TOOLS:
            return (
                f"lệnh bơm sự kiện chuột/bàn phím vào MÁY THẬT (`{base}`) — "
                "nó giật con trỏ khỏi tay người dùng đang gõ dở"
            )

        if base == "osascript":
            m = APPLESCRIPT_WRITE.search(seg)
            if m:
                return (
                    f"AppleScript `{m.group(0)}` — kéo cửa sổ lên trước / gửi phím-chuột, "
                    "che mất màn hình người dùng đang dùng"
                )

        if base == "open":
            m = OPEN_APP.search(seg)
            if m and not OPEN_BG_FLAG.search(m.group(1) or ""):
                app = m.group(2).strip("\"'")
                return (
                    f"`open -a {app}` không có cờ `-g` — mở app ĐÈ lên trên, "
                    "che màn hình người dùng đang làm việc"
                )

        # File đem ra CHẠY (không phải file bị cat/grep đọc) -> soi nội dung.
        path = script_arg(toks, i) if base in SHELLS else (head if ("/" in head or head.startswith(".")) else "")
        if path:
            hit = scan_file(path)
            if hit:
                return (
                    f"file đem ra chạy `{path}` có mã cướp chuột/cửa sổ (`{hit}`) — "
                    "gói vào script/binary rồi gọi vẫn là giật con trỏ của người dùng"
                )
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
        if not cmd:
            return 0
        why = offending(cmd)
        if not why:
            return 0
        reason = f"CHẶN — {why}.\n\n{HOW_TO}"
    except Exception:
        return 0

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
