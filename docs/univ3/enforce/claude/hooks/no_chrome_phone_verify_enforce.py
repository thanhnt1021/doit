#!/usr/bin/env python3
"""no_chrome_phone_verify_enforce.py — CẤM TẤT ĐỊNH việc xác nhận UI/UX điện thoại
bằng chrome-devtools phone emulation. Áp cho MỌI agent, kể cả subagent.

Luật founder (đã có từ trước, dạng văn bản): "XÁC NHẬN UI/UX TRÊN PHONE / iOS APP →
BẮT BUỘC tự mở iOS Simulator. CẤM kết luận bằng chrome-devtools phone view."

WHY phải là hook PreToolUse chứ không phải chèn context:
  Luật đó đang nằm ở `mobile_sim_verify_enforce.py`, đăng ký event **UserPromptSubmit** —
  event này CHỈ bắn khi NGƯỜI DÙNG gõ prompt ở phiên chính, và `additionalContext` chỉ
  được ghép vào context của phiên chính. Subagent do Agent tool sinh ra KHÔNG hề đi qua
  UserPromptSubmit → nó không thấy một dòng luật nào → nó resize Chrome về 390px, chụp
  màn, rồi báo "đã verify mobile". Đã xảy ra thật.
  PreToolUse thì chạy TRƯỚC MỌI tool call của MỌI agent (main lẫn subagent), nên đây là
  chỗ duy nhất chặn được tất định.

CHẶN (permissionDecision="deny"):
  - `mcp__chrome-devtools__resize_page` với width <= 500 (khổ điện thoại);
  - `mcp__chrome-devtools__emulate` có `viewport` khổ điện thoại, hoặc cờ `mobile`/`touch`,
    hoặc `userAgent` giả làm iPhone/Android;
  - `take_screenshot` / `take_snapshot` NGAY SAU khi vừa bị chặn một lần giả lập điện thoại
    trong cùng phiên (cửa lách thật: bị chặn resize thì chụp đại cửa sổ hiện tại rồi vẫn
    báo "mobile OK"). Muốn chụp desktop thật thì `resize_page` về >= 501px trước — thao tác
    đó tự xoá cờ, không kẹt.

CHO QUA (chặn nhầm là nghẽn việc — mấy việc này chrome-devtools làm đúng vai):
  - `resize_page` khổ desktop/tablet (width >= 501);
  - `lighthouse_audit`, `performance_start_trace`/`stop_trace`, đo hiệu năng desktop;
  - `emulate` chỉ chỉnh cpuThrottlingRate / networkConditions / colorScheme / geolocation /
    extraHttpHeaders — không dính gì tới khổ màn điện thoại;
  - toàn bộ tool chrome-devtools còn lại (navigate, click, fill, console, network...).

Fail-open tuyệt đối: input lạ / lỗi bất kỳ -> exit 0, không kẹt phiên.
"""
import json
import os
import re
import sys
import time

# Khổ màn coi là "điện thoại". iPhone rộng nhất hiện nay ~440pt; 500 là biên rộng rãi,
# tablet/desktop nhỏ nhất người ta test là 768 nên không đụng nhau.
PHONE_MAX_WIDTH = 500

# Cờ đánh dấu "phiên này vừa thử giả lập điện thoại và đã bị chặn".
FLAG_DIR = "/tmp/claude-chrome-phone-gate"
FLAG_TTL_SEC = 15 * 60

# viewport dạng '<width>x<height>x<dpr>[,mobile][,touch][,landscape]'
VIEWPORT_RE = re.compile(r"^\s*(\d+)\s*x\s*(\d+)", re.I)
MOBILE_UA_RE = re.compile(r"iphone|ipod|android|mobile safari", re.I)

HOW_TO = """CÁCH ĐÚNG — chụp Safari THẬT trong iOS Simulator (headless, không chiếm chuột/màn của người dùng):
  1. bash ~/.claude/universal-hooks/sim-headless.sh boot
  2. python3 -m http.server 8080 --bind 127.0.0.1 & SRV=$!; trap 'kill $SRV 2>/dev/null' EXIT
     (bước 2-4 để CÙNG 1 lệnh Bash; xong `kill $SRV`. CẤM `kill %1` ở lệnh sau — shell khác, job control chết)
  3. bash ~/.claude/universal-hooks/sim-headless.sh url "http://localhost:8080/..."
  4. bash ~/.claude/universal-hooks/sim-headless.sh shot /tmp/sim.png   # rồi ĐỌC ảnh đó
  App iOS native: sim-headless.sh install <App>.app -> launch <bundle_id> -> shot /tmp/sim.png

VÌ SAO CẤM chrome-devtools phone view: nó BỎ SÓT thanh URL Safari (dưới) + status bar +
bottom-nav -> "vừa 1 màn" giả, lên iPhone thật thì tràn/scroll. Với app native thì
chrome-devtools không mô phỏng được gì cả.

VẪN ĐƯỢC DÙNG chrome-devtools cho: đo hiệu năng desktop, Lighthouse desktop, xem console/
network, thao tác trang ở khổ desktop (resize_page width >= 501)."""


def flag_path(session_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "nosession")[:64]
    return os.path.join(FLAG_DIR, safe + ".flag")


def set_flag(session_id: str) -> None:
    try:
        os.makedirs(FLAG_DIR, exist_ok=True)
        with open(flag_path(session_id), "w") as fh:
            fh.write(str(int(time.time())))
    except Exception:
        pass


def clear_flag(session_id: str) -> None:
    try:
        os.remove(flag_path(session_id))
    except Exception:
        pass


def flag_fresh(session_id: str) -> bool:
    try:
        with open(flag_path(session_id)) as fh:
            return (time.time() - int(fh.read().strip() or 0)) < FLAG_TTL_SEC
    except Exception:
        return False


def check(tool: str, ti: dict, session_id: str) -> str:
    """Trả lý do chặn (rỗng = cho qua). Có side effect đặt/xoá cờ phiên."""
    short = tool.rsplit("__", 1)[-1]

    if short == "resize_page":
        try:
            width = float(ti.get("width"))
        except (TypeError, ValueError):
            return ""
        if width <= PHONE_MAX_WIDTH:
            set_flag(session_id)
            return (f"`resize_page` width={int(width)}px là khổ MÀN ĐIỆN THOẠI — "
                    "đây là giả lập phone bằng Chrome, không phải điện thoại thật")
        clear_flag(session_id)   # đã về desktop -> mở lại cửa chụp màn
        return ""

    if short == "emulate":
        vp = str(ti.get("viewport") or "")
        if vp:
            low = vp.lower()
            m = VIEWPORT_RE.match(vp)
            width = int(m.group(1)) if m else None
            if "mobile" in low or "touch" in low:
                set_flag(session_id)
                return (f"`emulate viewport=\"{vp}\"` bật chế độ thiết bị di động "
                        "(mobile/touch) — đây là giả lập phone bằng Chrome")
            if width is not None and width <= PHONE_MAX_WIDTH:
                set_flag(session_id)
                return (f"`emulate viewport=\"{vp}\"` có bề rộng {width}px = khổ màn "
                        "ĐIỆN THOẠI — đây là giả lập phone bằng Chrome")
        ua = str(ti.get("userAgent") or "")
        if ua and MOBILE_UA_RE.search(ua):
            set_flag(session_id)
            return ("`emulate userAgent` giả làm trình duyệt điện thoại — "
                    "đây là giả lập phone bằng Chrome")
        return ""

    if short in ("take_screenshot", "take_snapshot"):
        if flag_fresh(session_id):
            return ("vừa có một lần giả lập màn hình điện thoại bị chặn trong phiên này, "
                    f"nên `{short}` lúc này bị coi là chụp lại đúng cái phone view đó. "
                    "Cần chụp DESKTOP thật thì gọi `resize_page` width >= 501 trước "
                    "(thao tác đó tự mở lại cửa chụp màn)")
        return ""

    return ""


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0

    if str(data.get("hook_event_name") or "") != "PreToolUse":
        return 0

    tool = str(data.get("tool_name") or "")
    if not tool.startswith("mcp__chrome-devtools__"):
        return 0

    try:
        ti = data.get("tool_input") or {}
        if not isinstance(ti, dict):
            return 0
        why = check(tool, ti, str(data.get("session_id") or ""))
        if not why:
            return 0
        reason = (f"CHẶN — {why}.\n\nLUẬT FOUNDER: xác nhận UI/UX trên điện thoại PHẢI "
                  f"dùng iOS Simulator, CẤM kết luận bằng chrome-devtools phone view.\n\n{HOW_TO}")
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
