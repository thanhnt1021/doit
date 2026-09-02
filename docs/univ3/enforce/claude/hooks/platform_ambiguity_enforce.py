#!/usr/bin/env python3
"""platform_ambiguity_enforce.py — CẤM TẤT ĐỊNH việc TỰ ĐOÁN nền tảng ở project
có CẢ app iOS native LẪN web.

SỰ CỐ THẬT (2026-08-25, repo vevoi — có `vevoi-ios/vevoi.xcodeproj` VÀ `public/`):
founder nhắn "khi up ảnh, hoặc khi edit, ... mấy cái nút bấm như lên xuống, global
gallery view gì đấy **trong app** không dùng được". Main agent tự suy "app = web",
thả worker đi verify bằng chrome-devtools → sai hoàn toàn (chrome không mô phỏng
được gì của app iOS native). Phải kill worker, làm lại từ đầu.

Rule markdown ("mơ hồ thì HỎI") ĐÃ CÓ mà vẫn bị lách → theo AGENTS.md §Rule Budget
"ép được bằng hook thì CHUYỂN xuống hook; markdown = xác suất, hook = cổng tất định".

KHÔNG chặn cứng prompt (chặn = founder không gõ được lệnh, phản tác dụng) — chỉ CHÈN
CONTEXT bắt buộc, ngôn từ mệnh lệnh tối đa. exit 0 luôn (fail-open).

Kích hoạt khi thoả CẢ BA:
  1. Project hiện tại lưỡng nền tảng: có `*.xcodeproj`/`*.xcworkspace` VÀ (`public/` hoặc `index.html`);
  2. Prompt có từ chỉ UI/app MƠ HỒ (app, màn hình, giao diện, nút, bấm, hiển thị, UI, screen...);
  3. Prompt KHÔNG nói rõ nền tảng (ios/iphone/swift/native/simulator/app store/web/browser/
     trình duyệt/cloudflare/pages...).

  UserPromptSubmit (matcher "").
"""
import json
import os
import re
import sys

# Chỉ quét nông — project lưỡng nền tảng luôn để xcodeproj/public gần gốc
# (vevoi: `vevoi-ios/vevoi.xcodeproj` + `public/`). Quét sâu = chậm, hook có timeout 5s.
MAX_DEPTH = 3
SKIP_DIRS = {
    ".git", "node_modules", "build", "Build", "DerivedData", "Pods",
    ".build", "dist", ".next", "vendor", "__pycache__", ".venv",
}

# Từ chỉ UI/app nhưng KHÔNG nói nền tảng nào. Viết cả CÓ DẤU lẫn KHÔNG DẤU
# (founder gõ cả hai kiểu). Token ASCII ngắn dùng \b để khỏi dính "minutes", "happy"...
AMBIGUOUS = (
    r"\bapp\b", r"\bứng dụng\b", r"\bung dung\b",
    r"màn hình", r"man hinh", r"\bmàn\b", r"\bscreen\b",
    r"giao diện", r"giao dien",
    r"\bnút\b", r"\bnut\b", r"\bbutton\b", r"\bnút bấm\b",
    r"\bbấm\b", r"\bbam\b", r"\bnhấn\b", r"\bnhan nut\b", r"\btap\b",
    r"\bui\b", r"\bux\b",
    r"hiển thị", r"hien thi",
    r"\bgallery\b", r"\bmàn edit\b", r"\bupload\b",
    r"\bvuốt\b", r"\bvuot\b", r"\bscroll\b",
)

# Từ nói RÕ nền tảng → prompt không còn mơ hồ, hook im lặng.
EXPLICIT = (
    # iOS native
    r"\bios\b", r"\biphone\b", r"\bipad\b", r"\bswift\b", r"\bswiftui\b",
    r"\bnative\b", r"\bsimulator\b", r"\bsimctl\b", r"\bxcode\b",
    r"app store", r"\bappstore\b", r"\btestflight\b", r"\bxcodeproj\b",
    # web
    r"\bweb\b", r"\bwebapp\b", r"\bbrowser\b", r"trình duyệt", r"trinh duyet",
    r"\bchrome\b", r"\bsafari\b", r"\bcloudflare\b", r"\bpages\b",
    r"\blocalhost\b", r"\bhtml\b", r"\bcss\b", r"\bpublic/",
)

AMBIGUOUS_RE = [re.compile(p, re.I) for p in AMBIGUOUS]
EXPLICIT_RE = [re.compile(p, re.I) for p in EXPLICIT]

WARNING = """\
⚠️ PROJECT LƯỠNG NỀN TẢNG — CẤM TỰ ĐOÁN "app" LÀ CÁI NÀO.
  Repo này có CẢ HAI: app iOS NATIVE (SwiftUI, `*.xcodeproj`) VÀ web (`public/`).
  Prompt vừa rồi nói tới UI/app nhưng KHÔNG nói rõ nền tảng.

  Sự cố thật (2026-08-25): founder nói "mấy nút trong app không dùng được", agent tự suy
  "app = web", thả worker verify bằng chrome-devtools → sai hoàn toàn, phải kill worker làm lại.
  chrome-devtools KHÔNG mô phỏng được gì của app iOS native.

  BẮT BUỘC LÀM ĐÚNG THỨ TỰ:
  1. Dùng tool `AskUserQuestion` hỏi thẳng "iOS native hay web?" — TRƯỚC khi spawn worker,
     TRƯỚC khi sửa bất kỳ file nào, TRƯỚC khi mở tool verify. CẤM đoán, CẤM "chắc là".
  2. Có câu trả lời rồi mới đi tiếp:
     · iOS native → sửa `.swift`, verify bằng iOS Simulator
       (`bash ~/.claude/universal-hooks/sim-headless.sh boot|install|launch|shot`).
       CẤM chrome-devtools — hook `no_chrome_phone_verify_enforce.py` chặn tất định.
     · web → sửa `public/`, verify bằng Safari THẬT trong iOS Simulator nếu là view điện thoại;
       chrome-devtools chỉ dùng cho khổ desktop / console / network.
  3. Brief giao cho worker PHẢI ghi rõ nền tảng đã chốt + cách verify tương ứng.

  Ngoại lệ DUY NHẤT không cần hỏi: founder đã nói rõ nền tảng ngay trong lượt này,
  hoặc việc đang làm không đụng UI (git/log/docs/hạ tầng).
"""


def _project_dir(data: dict) -> str:
    """Thư mục gốc project: ưu tiên env của harness, sau đó leo lên từ cwd tìm .git."""
    env = os.environ.get("CLAUDE_PROJECT_DIR") or ""
    if env:
        return env.rstrip("/")
    cur = os.path.abspath(str(data.get("cwd") or os.getcwd()))
    while True:
        if os.path.isdir(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.abspath(str(data.get("cwd") or os.getcwd()))
        cur = parent


def _dual_platform(root: str) -> bool:
    """True khi project có CẢ xcodeproj/xcworkspace LẪN thư mục web."""
    has_ios = False
    has_web = os.path.isdir(os.path.join(root, "public")) or os.path.isfile(
        os.path.join(root, "index.html"))
    root = root.rstrip("/")
    base_depth = root.count(os.sep)
    for cur, dirs, files in os.walk(root):
        if cur.count(os.sep) - base_depth >= MAX_DEPTH:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for d in dirs:
            if d.endswith(".xcodeproj") or d.endswith(".xcworkspace"):
                has_ios = True
            elif d == "public" and cur != root:
                has_web = True
        if not has_web and "index.html" in files:
            has_web = True
        if has_ios and has_web:
            return True
    return False


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
    prompt = str(data.get("prompt") or "")
    if not prompt:
        return 0
    if not any(r.search(prompt) for r in AMBIGUOUS_RE):
        return 0
    if any(r.search(prompt) for r in EXPLICIT_RE):
        return 0
    try:
        if not _dual_platform(_project_dir(data)):
            return 0
    except Exception:
        return 0
    emit(WARNING)
    return 0


if __name__ == "__main__":
    sys.exit(main())
