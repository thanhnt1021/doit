#!/usr/bin/env python3
"""sim_one_device_enforce.py — CẤM TẤT ĐỊNH việc boot NHIỀU iOS Simulator cùng lúc.

BÀI HỌC THẬT (2026-08-24, máy founder, 14:43): 4 worker UI chạy song song, brief con nào
cũng ghi "verify bằng iOS Simulator, test 1 device rộng + 1 device vừa". Kết quả đo được:

    load average: 566.37 623.43 479.56
    5 device booted cùng lúc (agent-NHATRANGdream, agent-banner-hero, agent-banner-max,
        agent-drawer, agent-NHATRANGdream-max)
    708 tiến trình CoreSimulator
    Pages free: 3943 (page 16KB) -> chỉ còn ~63MB RAM trống

Máy founder gần đơ. Nguyên văn founder: "ý là không dồn các task simulator vào test chung
hoặc phân tích cùng nhau xong cuối cùng chỉ test 1 con thôi à? để đỡ lag?" -> kiến trúc
đúng là TÁCH THI CÔNG KHỎI KIỂM THỬ: worker thi công KHÔNG boot simulator, một worker QA
duy nhất boot ĐÚNG 1 device và gom kiểm thử toàn bộ trong một lượt.

WHY hook chứ không thêm dòng markdown: brief đã ghi rõ quy trình simulator mà 4 worker vẫn
mỗi con boot 1-2 device — markdown là xác suất, mỗi worker chỉ thấy brief của nó và không
hề biết 3 con kia đang boot cái gì. Chỉ có hook mới NHÌN ĐƯỢC trạng thái toàn máy
(`simctl list devices booted`) tại đúng khoảnh khắc trước khi lệnh boot chạy.

  PreToolUse Bash — soi lệnh sắp chạy. CHẶN khi:
    lệnh có ý định BOOT (`xcrun simctl boot ...` hoặc `sim-headless.sh boot`)
    VÀ trên máy đang có >= 1 device tên `agent-*` ở trạng thái Booted
    VÀ device sắp boot KHÔNG phải chính con đang booted đó.

  CHO QUA (chặn nhầm là nghẽn việc):
    - máy chưa có device `agent-*` nào booted -> boot con đầu tiên: bình thường;
    - boot lại ĐÚNG con đang booted (lệnh idempotent, `sim-headless.sh boot` chạy 2 lần);
    - mọi lệnh simctl khác: create / install / launch / openurl / io screenshot /
      bootstatus / shutdown / delete — không con nào làm tăng số máy ảo đang chạy;
    - device người dùng tự mở (tên KHÔNG bắt đầu bằng `agent-`) không bị tính -> founder
      đang xem Simulator của mình thì agent vẫn boot được device riêng;
    - cửa thoát có chủ đích: đặt `SIM_MULTI_OK=1` ngay trong lệnh khi founder ĐÃ ĐỒNG Ý
      chạy song song (vd `SIM_MULTI_OK=1 xcrun simctl boot <udid>`).

Fail-open tuyệt đối: không parse nổi / `simctl` lỗi / quá 8 giây -> exit 0. Thà lọt còn hơn kẹt phiên.
"""
import json
import os
import re
import shlex
import subprocess
import sys

AGENT_PREFIX = "agent-"

ESCAPE = re.compile(r"(?<![\w./-])SIM_MULTI_OK\s*=\s*1\b")

# Ranh giới câu lệnh khi tách token — `simctl` ở nhánh này không dính lệnh con ở nhánh kia.
SHELL_OPS = {";", "&&", "||", "|", "&", "(", ")", "{", "}"}


def tokens(cmd: str):
    """Tách token kiểu shell. WHY tokenize thay vì regex trên cả chuỗi: lệnh chỉ NHẮC TÊN
    `simctl` bên trong một chuỗi trích dẫn (echo payload JSON để tự thử hook, grep tài liệu)
    bị regex thô chặn oan — đã dính thật. shlex gộp nguyên chuỗi trích dẫn thành 1 token nên
    `simctl` không còn đứng riêng -> không chặn. Không tách nổi (heredoc...) -> [] = cho qua."""
    try:
        return shlex.split(cmd, posix=True)
    except Exception:
        return []


def boot_intent(toks):
    """(có_ý_định_boot, tên-hoặc-udid-đích). `bootstatus`/`shutdown`/`io`/`create` không tính."""
    for i, t in enumerate(toks):
        base = t.rsplit("/", 1)[-1]
        is_simctl = base == "simctl"
        is_headless = base == "sim-headless.sh"
        if not (is_simctl or is_headless):
            continue
        for j in range(i + 1, len(toks)):
            nxt = toks[j]
            if nxt in SHELL_OPS:
                break
            if nxt.startswith("-"):
                continue
            if nxt == "boot":
                if is_headless:
                    return True, ""
                for k in range(j + 1, len(toks)):
                    if toks[k] in SHELL_OPS:
                        break
                    if not toks[k].startswith("-"):
                        return True, toks[k]
                return True, ""
            if is_headless:
                break  # sim-headless.sh <lệnh khác> (shot/url/stop/udid...)
    return False, ""


SIM_NAME_ENV = re.compile(r"(?<![\w./-])SIM_NAME\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s;&|]+)")

HOW_TO = """KIẾN TRÚC ĐÚNG — TÁCH THI CÔNG KHỎI KIỂM THỬ (rules/AGENTS-ORCH.md §QA-tập-trung):
  1. Worker THI CÔNG: KHÔNG boot simulator. Tự xác minh không cần trình duyệt — đọc lại
     file:dòng vừa sửa, grep, đếm bằng script, tính contrast bằng script, đọc thẳng giá trị
     CSS (font-size, padding, opacity). Kết thúc báo cáo bằng mục "CẦN QA KIỂM".
  2. MỘT worker QA duy nhất chạy sau cùng: boot ĐÚNG 1 device, gom kiểm thử toàn bộ các
     mảng trong một lượt, đọc ảnh chụp bằng tool Read.
  3. Cần so 2 cỡ màn -> TUẦN TỰ: `xcrun simctl shutdown <udid-1>` xong mới boot con thứ hai.
  4. Xong việc: `xcrun simctl shutdown` + tắt http server nền, không bỏ tiến trình rác.

CÁCH ĐI TIẾP NGAY BÂY GIỜ (chọn 1):
  a. DÙNG LẠI device đang booted thay vì boot con mới:
       xcrun simctl list devices booted
       xcrun simctl openurl <udid-đang-booted> "http://localhost:8080/..."
       xcrun simctl io <udid-đang-booted> screenshot /tmp/sim.png
  b. Việc trên con kia đã xong -> tắt trước rồi mới boot con này:
       xcrun simctl shutdown <udid-đang-booted>
  c. Founder ĐÃ đồng ý chạy song song -> thêm SIM_MULTI_OK=1 vào đầu lệnh.

Luật KHÔNG đổi: vẫn BẮT BUỘC verify UI mobile bằng Safari trong iOS Simulator, vẫn CẤM kết
luận bằng chrome-devtools phone view. Chỉ đổi AI ĐƯỢC BOOT BAO NHIÊU CON (đáp án: 1)."""


def booted_devices():
    """[(udid, name)] các device đang Booted. Lỗi/timeout -> None (fail-open)."""
    try:
        out = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "booted", "-j"],
            capture_output=True, text=True, timeout=8,
        )
        if out.returncode != 0:
            return None
        data = json.loads(out.stdout or "{}")
    except Exception:
        return None
    devs = []
    for lst in (data.get("devices") or {}).values():
        for d in lst or []:
            if str(d.get("state") or "") == "Booted":
                devs.append((str(d.get("udid") or ""), str(d.get("name") or "")))
    return devs


def boot_target(cmd: str, cwd: str, arg: str) -> str:
    """Tên hoặc UDID của device sắp boot. Chuỗi rỗng = không xác định được."""
    m = SIM_NAME_ENV.search(cmd)
    if m:
        return m.group(1).strip("\"'")
    if arg:
        return arg
    # sim-headless.sh mặc định SIM_NAME=agent-<tên thư mục hiện tại>
    return AGENT_PREFIX + os.path.basename(cwd or os.getcwd())


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
        if not cmd or ESCAPE.search(cmd):
            return 0
        want_boot, arg = boot_intent(tokens(cmd))
        if not want_boot:
            return 0

        devs = booted_devices()
        if devs is None:
            return 0
        agents = [(u, n) for (u, n) in devs if n.lower().startswith(AGENT_PREFIX)]
        if not agents:
            return 0

        target = boot_target(cmd, str(data.get("cwd") or ""), arg)
        if target and any(target in (u, n) for (u, n) in agents):
            return 0  # boot lại đúng con đang chạy = idempotent, cho qua

        dsx = "\n".join(f"    - {n}  ({u})" for (u, n) in agents)
        reason = (
            "CHẶN — máy đang có {} iOS Simulator của agent ở trạng thái Booted, lệnh này "
            "boot THÊM con nữa:\n{}\n\nMỗi simulator ngốn hàng trăm tiến trình CoreSimulator. "
            "Lần trước 5 con cùng lúc đẩy load average lên 566 và chỉ còn ~63MB RAM trống — "
            "máy founder gần đơ.\n\n{}"
        ).format(len(agents), dsx, HOW_TO)
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
