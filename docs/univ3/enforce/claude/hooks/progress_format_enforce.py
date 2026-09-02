#!/usr/bin/env python3
"""progress_format_enforce.py — cổng TẤT ĐỊNH cho khuôn báo % tiến độ worker ngầm.

Vì sao cần hook: luật markdown chỉ là xác suất — worker vẫn ghi `55|dang tai hien`
(mốc lạ + nhãn không dấu) rồi bảng % ra rác. Cổng cứng thì sai là chặn, hết đường lách.

  (A) PreToolUse Bash  -> soi lệnh sắp chạy, thấy ghi vào `*.progress` thì parse nội dung;
      sai khuôn -> permissionDecision "deny" (giống pnpm_enforce.py), kèm chỉ rõ sai gì.
  (B) SessionStart     -> đóng MỐC PHIÊN vào `<thư mục progress project>/.session`
      để bg-progress.sh biết file nào là tàn dư phiên cũ.

KHUÔN CHUẨN (SSOT của khuôn = các hằng số ngay dưới; bg-progress.sh dùng cùng bộ này):
    echo 'NN|<nhãn>' > /tmp/claude-bg-progress/<project>/<slug>.progress
    NN là số nguyên 0-100 · có dấu `|` · nhãn 1 dòng, <= 60 ký tự, tiếng Việt viết đủ dấu.
Dòng mẫu đúng:  72|đang build, chờ next build xong

VÌ SAO BỎ 5 MỐC CỨNG 20/50/70/85/100 (2026-08-26, founder):
  Bộ 5 mốc nhét TOÀN BỘ chặng deploy vào đúng một con số 85. Đo thật lúc 13:04 ngày
  26/8: BỐN worker cùng đứng 85% với bốn trạng thái khác hẳn nhau ("đã deploy demo+prod
  đang parity" · "đã LIVE prod đang dọn" · "đã commit đang đăng ký deploy" · "đang chạy
  e2e"). Một con đứng 85% suốt 1 TIẾNG vì xếp hàng chờ khoá deploy — founder và điều phối
  đều tưởng nó treo, đi giục oan. Mốc thưa thì bảng không nói được worker đang ở đâu.
  Nay: mốc là số nguyên 0-100 tuỳ ý; bộ mốc GỢI Ý dày (MOC_GOI_Y) nằm ngay dưới, tách
  riêng chặng deploy vì đó là chỗ ngốn thời gian nhất.

Fail-open: parse không nổi / lỗi bất kỳ -> exit 0, không bao giờ làm kẹt phiên.
"""
import json
import os
import re
import sys
import time
import unicodedata

# ========================= HẰNG SỐ KHUÔN (chỉ khai báo 1 chỗ) =========================
PROGRESS_ROOT = "/tmp/claude-bg-progress"
# Mốc = số nguyên 0-100 tuỳ ý (không còn danh sách trắng). Chỉ chặn khi ngoài khoảng.
STEP_MIN, STEP_MAX = 0, 100
# Bộ mốc GỢI Ý — KHÔNG ép, chỉ in ra khi worker ghi sai để nó biết nên dùng số nào.
# Chặng deploy (80-98) tách dày vì đo thật cho thấy đó là chỗ worker nằm lâu nhất.
MOC_GOI_Y = [
    (10, "nhận việc, đã đọc luật + brief"),
    (20, "đang điều tra / đọc code"),
    (35, "đã tìm ra nguyên nhân"),
    (50, "đang sửa"),
    (65, "sửa xong, đang tự kiểm (tsc/lint)"),
    (72, "đang build"),
    (78, "build xanh, đã commit local"),
    (85, "đã đăng ký vé đẩy — BÀN GIAO chặng deploy"),
    (95, "đã dọn tiến trình nền, đang viết báo cáo"),
    (100, "xong phần thi công — đã bàn giao vé đẩy"),
    # --- dưới đây CHỈ dành cho worker/lượt CHẠY LÔ ĐẨY, không phải worker thi công ---
    (86, "[lô] có khoá rồi, đang deploy demo"),
    (90, "[lô] đã lên demo, đang smoke test"),
    (93, "[lô] đang deploy prod"),
    (97, "[lô] đã lên prod, đang verify parity"),
]
# VÌ SAO CẮT CHẶNG ĐẨY RA KHỎI THANG MỐC CỦA WORKER THI CÔNG (29/08/2026, W187):
# đêm 29/8 ba worker chết đúng ở khúc 82-95 (chặng đẩy) — W144 92% «Smoke demo + prod»,
# W165 84% «Đăng ký lô deploy», W175 92%. Việc thi công của chúng đã xong và đã commit,
# nhưng vì thang mốc bắt chúng "chưa xong khi chưa deploy" nên công thi công bị tính là
# dở dang, phải thả con khác làm lại từ đầu. Nay HAI CUỐN SỔ:
#   sổ thi công = tệp `.progress` này, đóng ở 100 NGAY KHI đăng ký được vé đẩy;
#   sổ đẩy      = `~/.claude/deploy-queue/<project>/pending/*.json`, đóng khi lô chạy xong.
# Chết ở chặng đẩy chỉ mất chặng đẩy. Quên đăng ký vé -> `deploy_ban_giao_gate.py` kêu.
LABEL_MAX = 60
SESSION_MARKER_NAME = ".session"
GOOD_EXAMPLE = "echo '72|đang build, chờ next build xong' > /tmp/claude-bg-progress/<project>/<slug>.progress"
# Nhãn thiếu dấu: DÙNG LẠI bộ pattern của viet_diacritics_check.py (cùng thư mục,
# import-safe) — KHÔNG tự chế luật mới.
# WHY bỏ luật cũ "nhãn phải chứa >=1 ký tự có dấu": nó bắt nhầm hàng loạt nhãn viết
# ĐÚNG chính tả mà vốn không có dấu (`xong`, `commit`, `deploy`, `build`, `push`,
# `ghi log`) -> bảng % đầy cảnh báo giả, mà cảnh báo giả thì người ta học cách bơ đi.
# Đúng bản chất là bắt chữ tiếng Việt BỊ VIẾT THIẾU DẤU, không phải bắt "vắng dấu".
try:
    from viet_diacritics_check import BAD_PATTERNS as _SHARED_BAD
except Exception:
    _SHARED_BAD = []
# Bổ sung riêng cho nhãn tiến độ (add-on-failure): 3 từ này đã lọt lưới bộ chung
# trong ca thật `dang tai hien tren simulator`. Để ở đây chứ không nhét vào bộ chung
# để phạm vi ảnh hưởng chỉ là nhãn progress, không đụng gate Write/Edit toàn máy.
_EXTRA_BAD = [
    (r"\bdang\b", "đang"),
    (r"\btren\b", "trên"),
    (r"\btai hien\b", "tái hiện"),
]
BAD_DIACRITICS = list(_SHARED_BAD) + _EXTRA_BAD
# Mốc phiên bị lùi lại vài giây: `-nt` là "mới hơn HẲN", worker ghi trong cùng giây với
# mốc sẽ bị coi là cũ và biến mất khỏi bảng nếu không lùi.
MARKER_BACKDATE_SEC = 2
# =====================================================================================

# ===== CẤM GỘP CÂU GHI MỐC VÀO LỆNH CÓ THỂ BỊ TỪ CHỐI (thêm 29/08/2026, W187) =====
# Đo thật đêm 29/8 — ba worker liên tiếp "đứng phần trăm" ở chặng deploy, cùng một cơ chế:
#   W144 00:06:42  `rm -f .w144-*.mjs && echo '100|…' > …progress`   -> data-guard DENY
#   W165 00:22:46  `rm -rf .w165 /tmp/w165 && echo '100|…' > …`      -> data-guard DENY
#   W175 00:23:44  `git commit … && echo '100|…' > …`                -> pre-commit exit 1
# Hook `deny` giết CẢ lệnh Bash, nên câu ghi mốc trong cùng lệnh KHÔNG BAO GIỜ chạy.
# Worker vẫn làm tiếp và khai "xong", còn vạch % đứng lại -> điều phối tưởng nó chết.
# Vì thế: ghi mốc phải là MỘT lệnh Bash RIÊNG, không dính lệnh nào có thể bị chặn.
# Không xét thứ tự (deny giết cả lệnh, đứng trước hay sau đều mất).
RUI_RO_CUNG_LENH = [
    (re.compile(r"(^|[\s;&|(])rm\s"), "`rm` (data-guard hay chặn)"),
    (re.compile(r"\bgit\s+commit\b"), "`git commit` (pre-commit hay exit 1)"),
    (re.compile(r"\bgit\s+push\b"), "`git push` (cổng push hay deny)"),
    (re.compile(r"\bdeploy-(batch|promote|zd|remote)\b"), "kịch bản deploy"),
    (re.compile(r"\b(pnpm|npm|yarn)\s+(run\s+)?build\b"), "lệnh build"),
]
# Tên tệp mốc PHẢI mở đầu bằng mã worker `w<số>-`. WHY: mọi cổng ghép mốc với worker
# (worker_khai_xong_gate, worker_relapse, worker_board) dùng mã W làm mối nối tất định;
# tệp đặt tên khác quy ước rơi về đường đoán-theo-transcript và bị ghép NHẦM sang con
# khác — đúng ca W173 tự bắt được ngày 29/8 (nó bị gán nhãn của W165).
RX_TEN_MOC = re.compile(r"^w\d{1,4}-[a-z0-9-]+\.progress$")

_REDIR = re.compile(r'(?P<op>>>?)\s*(?P<path>"[^"]*"|\'[^\']*\'|[^\s;&|<>]+)')
_EMIT = re.compile(
    r"""(?:echo|printf)\s+(?:-[a-zA-Z]+\s+)*(?P<payload>'[^']*'|"[^"]*"|[^\s;&|<>]+)"""
)
_SEP = re.compile(r"&&|\|\||[;&\n(]")

# Thân heredoc KHÔNG phải lệnh — nó là DỮ LIỆU. Bỏ đi trước khi soi.
# WHY (đo ngay ngày làm, 29/08/2026): cổng vừa thêm ở trên chặn oan chính W187 hai lần
# liên tiếp — `git commit -F` với thông điệp NHẮC TỚI `.progress`, và `python3 - <<PY`
# vá chính file này. Cả hai đều không ghi mốc, chỉ là chữ nằm trong thân heredoc.
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1[^\n]*\n.*?^\s*\2\s*$",
                      re.S | re.M)


def _bo_than_heredoc(cmd: str) -> str:
    return _HEREDOC.sub(lambda m: m.group(0).split("\n", 1)[0] + "\n", cmd)


def _unquote(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    return text


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


def _check(payload: str, path: str, expect_dir: str) -> list:
    """Trả về danh sách lỗi khuôn (rỗng = hợp lệ)."""
    errors = []

    # 1. Đúng thư mục progress của project hiện tại
    real_dir = os.path.dirname(path.rstrip("/"))
    if real_dir != expect_dir:
        errors.append(
            f"• Sai thư mục: `{path}`.\n"
            f"  Phải nằm ngay trong `{expect_dir}/` (thư mục progress của project hiện tại)."
        )

    # 1b. Tên tệp phải mở đầu bằng mã worker `w<số>-` (mối nối tất định, xem RX_TEN_MOC)
    ten = os.path.basename(path.rstrip("/"))
    if not RX_TEN_MOC.match(ten):
        errors.append(
            f"• Tên tệp mốc `{ten}` sai quy ước — phải là `w<số>-<slug-có-gạch>.progress`\n"
            f"  (ví dụ `w187-tach-chang-deploy.progress`). Mã W ở đầu tên là thứ DUY NHẤT "
            f"cho cổng ghép mốc về đúng worker; thiếu nó thì mốc bị gán nhầm sang con khác."
        )

    line = unicodedata.normalize("NFC", payload).strip("\n")

    # 2. Chỉ 1 dòng
    if "\n" in line:
        errors.append("• Nhãn phải nằm gọn 1 dòng, không xuống dòng.")
        line = line.splitlines()[0]

    # 3. Có dấu `|`
    if "|" not in line:
        errors.append(
            f"• Thiếu dấu `|` ngăn giữa mốc và nhãn — bạn đang ghi `{line}`."
        )
        return errors

    raw_step, label = line.split("|", 1)
    raw_step = raw_step.strip()
    label = label.strip()

    # 4. Mốc là số nguyên trong khoảng 0-100 (không còn danh sách trắng 5 giá trị)
    if not raw_step.isdigit() or not (STEP_MIN <= int(raw_step) <= STEP_MAX):
        errors.append(
            f"• Mốc `{raw_step}` không hợp lệ — phải là SỐ NGUYÊN {STEP_MIN}-{STEP_MAX}."
        )

    # 5. Nhãn không rỗng, không quá dài
    if not label:
        errors.append("• Nhãn rỗng — phải mô tả bước vừa xong.")
    elif len(label) > LABEL_MAX:
        errors.append(f"• Nhãn dài {len(label)} ký tự — tối đa {LABEL_MAX}.")

    # 6. Nhãn có chữ tiếng Việt bị viết THIẾU DẤU (không phải "vắng dấu" là sai)
    missing = []
    for pat, correct in BAD_DIACRITICS:
        m = re.search(pat, label, re.IGNORECASE)
        if m:
            missing.append(f"`{m.group()}` -> `{correct}`")
    if missing:
        errors.append(
            "• Nhãn có chữ tiếng Việt thiếu dấu: " + ", ".join(missing[:5])
        )

    return errors


def _co_ghi_moc(cmd: str) -> bool:
    """Lệnh có THỰC SỰ chuyển hướng vào một tệp `*.progress` không (không chỉ nhắc tên)."""
    for m in _REDIR.finditer(cmd):
        if _unquote(m.group("path")).endswith(".progress"):
            return True
    return False


def _gop_lenh_rui_ro(cmd: str) -> list:
    """Câu ghi mốc bị gộp chung lệnh với thứ có thể bị `deny`/exit 1 -> kể tên thủ phạm."""
    if not _co_ghi_moc(cmd):
        return []
    return [ten for rx, ten in RUI_RO_CUNG_LENH if rx.search(cmd)]


def _scan(cmd: str, expect_dir: str) -> list:
    """Soi lệnh Bash, trả về lỗi của MỌI lần ghi vào *.progress."""
    findings = []
    for m in _REDIR.finditer(cmd):
        path = _unquote(m.group("path"))
        if not path.endswith(".progress"):
            continue
        head = cmd[: m.start()]
        seg = _SEP.split(head)[-1]
        emit = None
        for e in _EMIT.finditer(seg):
            emit = e
        if emit is None:
            continue  # không phải echo/printf -> không parse nổi, cho qua (fail-open)
        findings.extend(_check(_unquote(emit.group("payload")), path, expect_dir))
    return findings


# ===== THƯ MỤC TIẾN ĐỘ CHỈ CHỨA *.progress (thêm 27/08/2026) =====
# Đo thật hôm nay: `/tmp/claude-bg-progress/EtsyFulfillChichub/` chứa HƠN 80 tệp rác lẫn
# với 6 tệp tiến độ thật — build*.log, deploy*.log, tsc*.log, e2e.log, doisup-*.png,
# thư mục shots/, q.mjs, cookies.txt, commit-msg.txt… Luật markdown bảo worker "tự dọn
# rác" mà KHÔNG con nào dọn. Đây là thư mục dành riêng cho tệp trạng thái; log/ảnh/script
# tạm phải nằm trong thư mục nháp của phiên (scratchpad).
RX_GHI_VAO = re.compile(
    r"""(?:>>?|\btee\b\s+(?:-a\s+)?|\b-o\s+|\b-O\s+|\b(?:cp|mv|rsync|mkdir|touch)\b[^|;&\n]*?\s)"""
    r"""\s*["']?(/tmp/claude-bg-progress/[^\s"'|;&)>]+)""")
CHO_PHEP_DUOI = (".progress",)
CHO_PHEP_TEN = (".session", "done")


def _rac_vao_thu_muc_tien_do(cmd: str) -> list:
    """Lệnh ghi tệp KHÔNG PHẢI .progress vào thư mục tiến độ -> chặn, chỉ chỗ khác mà đổ."""
    xau = []
    for m in RX_GHI_VAO.finditer(cmd):
        duong = m.group(1).rstrip("/")
        ten = os.path.basename(duong)
        if duong.endswith(CHO_PHEP_DUOI) or ten in CHO_PHEP_TEN or "/done/" in duong:
            continue
        if duong.count("/") <= 3:      # chính thư mục gốc/thư mục project -> mkdir, cho qua
            continue
        xau.append(duong)
    return xau


def _stamp_session(data: dict) -> None:
    """Đóng mốc phiên để bg-progress.sh lọc tàn dư phiên cũ.

    WHY đánh mốc chứ không xoá thư mục: ẩn thì không mất gì — worker còn sống ghi bước
    kế tiếp là file mới hơn mốc, tự hiện lại; còn xoá là không đảo ngược được và thổi
    bay luôn file của phiên khác đang chạy song song trên cùng project.
    Chỉ đóng mốc khi phiên thực sự MỚI (startup/clear) — resume/compact là phiên cũ
    chạy tiếp, đóng mốc lại sẽ giấu mất worker đang chạy.
    """
    if str(data.get("source") or "startup") not in ("startup", "clear"):
        return
    project = os.path.basename(_project_dir(data))
    if not project:
        return
    d = os.path.join(PROGRESS_ROOT, project)
    os.makedirs(d, exist_ok=True)
    marker = os.path.join(d, SESSION_MARKER_NAME)
    with open(marker, "w", encoding="utf-8") as fh:
        fh.write(f"{data.get('session_id') or '?'}\n{int(time.time())}\n")
    t = time.time() - MARKER_BACKDATE_SEC
    os.utime(marker, (t, t))


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0

    event = str(data.get("hook_event_name") or "")

    if event == "SessionStart":
        try:
            _stamp_session(data)
        except Exception:
            pass
        return 0

    if event != "PreToolUse" or str(data.get("tool_name") or "") != "Bash":
        return 0

    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    cmd = _bo_than_heredoc(cmd)            # thân heredoc là DỮ LIỆU, không phải lệnh

    # Cổng 2: đổ rác vào thư mục tiến độ (log, ảnh, script tạm) -> chặn thẳng.
    rac = _rac_vao_thu_muc_tien_do(cmd)
    if rac:
        nhap = os.environ.get("CLAUDE_SCRATCHPAD_DIR") or "<thư mục nháp của phiên>"
        json.dump({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason":
                "CHẶN — `/tmp/claude-bg-progress/<project>/` CHỈ chứa tệp `*.progress`.\n"
                "Tệp định ghi: %s\n\n"
                "Log build/deploy, ảnh chụp, script tạm, backup JSON… đổ vào THƯ MỤC NHÁP "
                "của phiên (%s) hoặc `/tmp/` — đừng trộn vào thư mục trạng thái worker.\n"
                "WHY: bảng worker đọc thư mục này; 27/8 nó đã ngập 80+ tệp rác lẫn với 6 "
                "tệp tiến độ thật, không ai dọn."
                % (", ".join(rac[:4]), nhap)}}, sys.stdout, ensure_ascii=False)
        return 0

    if ".progress" not in cmd:
        return 0

    project = os.path.basename(_project_dir(data))
    expect_dir = os.path.join(PROGRESS_ROOT, project)

    # Cổng 3: gộp câu ghi mốc vào lệnh dễ bị chặn -> mốc không bao giờ được ghi.
    gop = _gop_lenh_rui_ro(cmd)
    if gop:
        json.dump({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason":
                "CHẶN — câu ghi mốc `.progress` đang GỘP CHUNG một lệnh với: %s\n\n"
                "Cổng nào từ chối lệnh này thì nó giết CẢ lệnh, nên câu ghi mốc cũng "
                "không chạy: worker vẫn làm tiếp và khai «xong», còn vạch %% đứng lại "
                "-> điều phối tưởng nó chết giữa chừng.\n"
                "ĐO THẬT đêm 29/08/2026, ba ca liên tiếp đúng kiểu này: W144 (`rm` + ghi "
                "100) đứng ở 92 · W165 (`rm -rf` + ghi 100) đứng ở 84 · W175 (`git commit` "
                "+ ghi 100) đứng ở 92.\n\n"
                "SỬA: tách làm HAI lệnh Bash. Chạy việc kia trước, rồi ghi mốc bằng đúng "
                "một lệnh riêng:\n  %s"
                % (", ".join(gop), GOOD_EXAMPLE)}}, sys.stdout, ensure_ascii=False)
        return 0

    errors = _scan(cmd, expect_dir)
    if not errors:
        return 0

    goi_y = "  ".join("%d=%s" % (n, t) for n, t in MOC_GOI_Y)
    reason = (
        "CHẶN — báo tiến độ SAI KHUÔN:\n"
        + "\n".join(errors)
        + f"\n\nKhuôn duy nhất được chấp nhận: `NN|<nhãn>` — NN là số nguyên "
        + f"{STEP_MIN}-{STEP_MAX}, nhãn 1 dòng <= {LABEL_MAX} ký tự, tiếng Việt phải viết đủ dấu.\n"
        + f"Ví dụ đúng:\n  {GOOD_EXAMPLE}\n"
        + "Mốc GỢI Ý (không ép, dùng cho khớp nhau giữa các worker):\n  "
        + goi_y
    )
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
