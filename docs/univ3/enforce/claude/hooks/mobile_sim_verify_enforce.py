#!/usr/bin/env python3
"""mobile_sim_verify_enforce.py — hook ENFORCE verify UI/UX bằng iOS Simulator.

Rule founder chốt (GLOBAL, mọi dự án): xác nhận UI/UX cho (a) WEB MOBILE lẫn (b) iOS APP NATIVE
PHẢI dùng iOS Simulator (model TỰ nhìn qua screenshot simulator), CẤM kết luận bằng
chrome-devtools phone emulation. Lý do: chrome-devtools phone view bỏ sót thanh URL Safari
(dưới) + status bar + bottom-nav -> tưởng fit nhưng Safari iPhone thật thì tràn/scroll;
với iOS app native thì chrome-devtools KHÔNG mô phỏng được gì cả.

AI ĐƯỢC BOOT (sửa 2026-08-24 sau sự cố thật): worker THI CÔNG **không** tự boot simulator;
chỉ MỘT worker QA duy nhất boot ĐÚNG 1 device và gom kiểm thử toàn bộ trong một lượt. Lý do:
4 worker UI song song, con nào cũng "verify bằng simulator" -> 5 device booted, 708 tiến trình
CoreSimulator, load average 566, còn ~63MB RAM trống, máy founder gần đơ. Cổng tất định:
hook `sim_one_device_enforce.py` (PreToolUse Bash) chặn lệnh boot con thứ hai.

Rule ở markdown = xác suất (model hay quên). Chuyển thành CHÈN CONTEXT tất định:
khi lượt có ngữ cảnh XÁC NHẬN UI/UX trên phone / iOS app (keyword bên dưới) -> in cảnh báo
BẮT BUỘC mở iOS Simulator + how-to simctl + danh sách "chỉ escalate user khi device-only".
Chỉ chèn context (không block cứng để khỏi kẹt) nhưng ngôn từ mệnh lệnh tối đa. exit 0 luôn (fail-open).

  UserPromptSubmit (matcher "") — chỉ bắn khi prompt trúng keyword phone/mobile-verify/iOS-app.
"""
import json
import sys

# Keyword (vi+en) báo hiệu đang XÁC NHẬN / KIỂM TRA view trên điện thoại HOẶC iOS app native.
KEYWORDS = (
    "iphone", "ios simulator", "simulator", "simctl", "safari",
    "phone view", "mobile view", "screenshot phone", "chrome-devtools",
    "chrome devtools", "devtools phone", "phone emulation",
    "vừa màn", "vừa 1 màn", "vừa một màn", "1 màn", "một màn", "fit màn",
    "responsive", "vừa khít", "tràn màn", "vừa điện thoại", "trên điện thoại",
    "xem trên phone", "verify mobile", "verify ui mobile", "test mobile",
    # iOS app native
    "ios app", "app ios", "swiftui", "native app", "app native", "giao diện app",
    "ui app", "ux app", "layout app", "app trên iphone",
)

WARNING = """\
📱 XÁC NHẬN UI/UX TRÊN PHONE / iOS APP → BẮT BUỘC tự mở iOS Simulator (xcrun simctl) chụp xem. CẤM kết luận bằng chrome-devtools phone view.
  Lý do: chrome-devtools phone emulation BỎ SÓT thanh URL Safari (dưới) + status bar + bottom-nav → "vừa 1 màn" giả; với iOS app native thì chrome-devtools KHÔNG mô phỏng được gì.

  ⚠️ AI ĐƯỢC BOOT — 1 DEVICE TẠI 1 THỜI ĐIỂM (bài học thật 2026-08-24: 4 worker UI song song, con nào cũng tự boot → 5 simulator, 708 tiến trình CoreSimulator, load average 566, còn ~63MB RAM trống, máy gần đơ):
    · Worker THI CÔNG **KHÔNG boot** simulator — tự xác minh bằng grep / đọc lại file:dòng / đếm bằng script / tính contrast bằng script / đọc thẳng giá trị CSS; kết thúc báo cáo bằng mục **"CẦN QA KIỂM"** (trang nào · soi điểm gì · so ảnh nào).
    · **MỘT worker QA duy nhất** chạy sau cùng, boot ĐÚNG 1 device, gom kiểm toàn bộ các mảng trong MỘT lượt.
    · Cần cỡ màn thứ hai → TUẦN TỰ: `xcrun simctl shutdown <udid-1>` xong mới boot con sau. CẤM boot song song.
    · Xong việc → `xcrun simctl shutdown` + **tự tắt http server** (`kill $SRV`), báo cáo ghi rõ đã tắt PID nào.
      CẤM `kill %1` ở lệnh Bash SAU — mỗi lệnh là shell riêng, job control chết → server sống mãi thành rác.
      Chụp bằng Playwright: `browser.close()` để trong `try/finally`, KHÔNG đặt cuối script.
    · Trước khi boot LUÔN chạy `xcrun simctl list devices booted` — có sẵn device thì DÙNG LẠI. Hook `sim_one_device_enforce.py` chặn tất định lệnh boot con thứ hai. Chi tiết điều phối: `rules/AGENTS-ORCH.md` §QA-tập-trung.

  (a) WEB MOBILE — chụp Safari THẬT trong simulator:
    1. bash ~/.claude/universal-hooks/sim-headless.sh boot   # DEVICE RIÊNG của agent, tái dùng nếu đã có, KHÔNG mở cửa sổ, KHÔNG chiếm chuột
    2. python3 -m http.server 8080 --bind 127.0.0.1 & SRV=$!; trap 'kill $SRV 2>/dev/null' EXIT   # bước 2-4 CÙNG 1 lệnh Bash
       (trang auth-gate thì STUB, vẫn nhúng nav để có topbar+bottom-nav thật)
    3. bash ~/.claude/universal-hooks/sim-headless.sh url "http://localhost:8080/..."
    4. bash ~/.claude/universal-hooks/sim-headless.sh shot /tmp/sim.png   # rồi ĐỌC ảnh, xem có tràn/scroll không
    CSS: dùng `100svh` KHÔNG `100dvh`. Test trên device người dùng thực dùng (Pro/Pro Max đời hiện tại — hỏi/known device); KHÔNG ép optimize cho iPhone SE nếu user không dùng SE (màn nhỏ ép co dúm layout). How-to: skill mobile-webapp §15.

  (b) iOS APP NATIVE — cài app vào simulator rồi tự xem:
    1. build → bash ~/.claude/universal-hooks/sim-headless.sh install <App>.app
    2. bash ~/.claude/universal-hooks/sim-headless.sh launch <bundle_id>
    3. bash ~/.claude/universal-hooks/sim-headless.sh shot /tmp/sim.png   # ĐỌC ảnh: layout/luồng/spacing/safe-area. How-to: skill ios-native-app.

  CẤM chiếm máy người dùng: không đưa cửa sổ Simulator lên trước, không AppleScript activate/AXRaise,
  không cliclick/CGEvent bơm chuột thật (hook no_steal_focus_enforce.py chặn tất định).
  Cần tự bấm -> XCUITest (`xcodebuild test -destination "id=<udid>"`) hoặc bơm PointerEvent bằng JS.

  CHỈ nhờ user mở iPhone THẬT cho tính năng device-only simulator KHÔNG kiểm được:
  Face ID/Touch ID · camera thật · push notification thật · haptics/gesture tinh vi ·
  share sheet gửi sang app thật · hiệu năng thiết bị thật · ký/cài App Store/provisioning thật.
  NGOÀI các mục đó → PHẢI tự verify bằng simulator, KHÔNG đẩy cho user.
"""


def emit(text: str) -> None:
    print(json.dumps(
        {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}},
        ensure_ascii=False))


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if str(data.get("hook_event_name") or "") != "UserPromptSubmit":
        return 0
    prompt = str(data.get("prompt") or "").lower()
    if any(k in prompt for k in KEYWORDS):
        emit(WARNING)
    return 0


if __name__ == "__main__":
    sys.exit(main())
