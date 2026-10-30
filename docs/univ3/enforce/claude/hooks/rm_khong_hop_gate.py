#!/usr/bin/env python3
"""rm_khong_hop_gate.py — PreToolUse hook, matcher `Bash`.

VÌ SAO CÓ (HONGXIEM-16102026-01, anh Thành tin #263/#297 16/10/2026: «/afk thì không được có
chuyện như này. fix chưa???»): 19:47 15/10 thợ W22 (C-HX, chạy nền, phiên chính bypassPermissions)
gõ `cd /private/tmp/claude-502/w22; rm xem/*; …` → đứng chờ hộp xin quyền 3 phút tới khi bị dừng.

NGUYÊN NHÂN GỐC (đo trong mã Claude Code 2.1.x, hàm kiểm xoá `IW`/`Nw`): mọi `rm`/`rmdir` đi qua
«kiểm an toàn xoá» — kết quả `ask` loại `safetyCheck`, `classifierApprovable:false`,
`circuitBreaker:"dangerousRemoval"`. Loại này MIỄN NHIỄM với bypassPermissions và «cannot be
auto-allowed by permission rules» → thêm allow vào settings KHÔNG cứu được. Nó bật hộp khi:
  · có `cd`/`pushd` trước, đích xoá là glob TƯƠNG ĐỐI (`rm xem/*`)            ← đúng ca W22
  · đích có biến/`$(…)`/backtick, `~`, `..`
  · glob ăn sâu hơn 1 tầng (`a/*/*`, `*/x/*`)
  · đích là thư mục hệ thống/nhà/ /tmp, hoặc thư mục làm việc / thư mục cha của nó
Hook PreToolUse chạy TRƯỚC bước kiểm quyền → hook trả `deny` thì hộp không bao giờ bật.

LUẬT: khi (a) lời gọi từ THỢ (payload có agent_id — thợ nền không ai trông), hoặc (b) cờ AFK bật,
hoặc (c) anh đang làm qua Telegram → lệnh xoá rơi vào các dạng trên bị CHẶN NGAY kèm cách đổi.
Không thuộc các dạng trên → im (exit 0), lệnh chạy bình thường. Không nới quyền gì cả: chỉ biến
«đứng chờ hộp» thành «bị chặn có lời nhắn», nên không xoá được thứ gì mà trước đây xoá được.

Lối ra cho thợ: viết lại bằng ĐƯỜNG TUYỆT ĐỐI một tầng (`rm /private/tmp/claude-502/w22/xem/*.png`),
không `cd` trước `rm`; hoặc khỏi xoá — ghi ra thư mục MỚI (`…/xem-2/`).
Kiểm: `python3 rm_khong_hop_gate.py --tu-kiem`.
"""
import json
import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import afk_trang_thai as _TT
except Exception:  # thiếu mô-đun cờ → vẫn chặn cho thợ (agent_id), không làm hỏng lệnh
    _TT = None

GLOB = re.compile(r"[*?\[]")
BOC = {"sudo", "command", "builtin", "nohup", "time", "env", "exec", "nice"}
# Từ khoá shell đứng đầu đoạn sau `;` (`for …; do rm $X; done`): không bỏ qua thì đoạn bị coi là lệnh
# «do» và `rm` lọt (ca 19/10/2026 thợ soát W23, hộp xin quyền bật giữa lúc anh vắng).
TU_KHOA = {"do", "then", "else", "elif", "if", "while", "until", "!", "{", "}", "done", "fi"}
VO_SHELL = {"bash", "sh", "zsh", "dash"}
TACH = {";", "&&", "||", "|", "&", "(", ")", "|&", ";;"}
# Thư mục cấp 1 mà Claude Code coi là «critical» (danh sách yLt trong mã) + bản /private/…
CAP1 = ("bin boot dev etc home lib lib32 lib64 libx32 media mnt opt proc root run sbin srv sys tmp "
        "usr var snap nix private cores Applications Library System Users Volumes").split()


def _bo_heredoc(cmd: str) -> str:
    """Bỏ thân heredoc (mã python/js trong `<<'EOF'` không phải lệnh shell)."""
    return re.sub(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?\n\s*\2\s*(?=\n|$)", " ", cmd, flags=re.S)


def _tach_doan(cmd: str):
    s = _bo_heredoc(cmd).replace("\n", " ; ")
    try:
        lx = shlex.shlex(s, posix=True, punctuation_chars=";&|()")
        lx.whitespace_split = True
        tok = list(lx)
    except ValueError:
        tok = s.split()
    doan, cur = [], []
    for t in tok:
        if t in TACH:
            if cur:
                doan.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        doan.append(cur)
    return doan


def _lenh(seg):
    i = 0
    while i < len(seg) and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", seg[i]) or seg[i] in BOC or seg[i] in TU_KHOA):
        i += 1
    return (os.path.basename(seg[i]) if i < len(seg) else ""), seg[i + 1:]


def _nguy_hiem_tuyet_doi(p: str, cwd: str) -> str:
    """p: đường tuyệt đối đã bỏ glob đuôi. Trả lý do nếu là thư mục hệ thống/nhà/làm việc."""
    p = os.path.normpath(p)
    home = os.path.expanduser("~")
    if p == "/":
        return "đích là thư mục gốc /"
    parts = [x for x in p.split("/") if x]
    if len(parts) == 1 and parts[0] in CAP1:
        return f"đích là thư mục hệ thống {p}"
    if len(parts) == 2 and parts[0] == "private" and parts[1] in CAP1:
        return f"đích là thư mục hệ thống {p}"
    if p == home or home.startswith(p + "/"):
        return f"đích là thư mục nhà hoặc thư mục cha của nó ({p})"
    c = os.path.normpath(cwd) if cwd else ""
    if c and (p == c or c.startswith(p + "/")):
        return f"đích là thư mục làm việc hoặc thư mục cha của nó ({p})"
    return ""


def phan_tich(cmd: str, cwd: str, sau: int = 0):
    """Trả danh sách lý do (rỗng = lệnh xoá này không bật hộp)."""
    return [chu for _ma, chu, _dich in phan_tich_ma(cmd, cwd, sau)]


def phan_tich_ma(cmd: str, cwd: str, sau: int = 0):
    """Như phan_tich nhưng mỗi lý do kèm MÃ LOẠI + đường đích tuyệt đối (nếu biết) — để tin gửi anh
    dịch được sang lời thường và phân biệt «thợ tự viết lại được» với «đích nguy hiểm thật»."""
    ly_do = []
    da_cd = False
    for seg in _tach_doan(cmd):
        ten, args = _lenh(seg)
        if ten in ("cd", "pushd", "popd"):
            da_cd = True
            continue
        if ten in VO_SHELL and "-c" in args and sau < 2:
            k = args.index("-c")
            if k + 1 < len(args):
                ly_do += phan_tich_ma(args[k + 1], cwd, sau + 1)
            continue
        if ten not in ("rm", "rmdir"):
            continue
        dich, het_co = [], False
        for a in args:
            if not het_co and a == "--":
                het_co = True
            elif not het_co and a.startswith("-") and a != "-":
                continue
            else:
                dich.append(a)
        for d in dich:
            if re.search(r"[$`]", d):
                ly_do.append(("bien", f"`{ten} {d}`: đích có biến/$(…)/backtick — máy không đọc trước được", ""))
                continue
            if d.startswith("~"):
                ly_do.append(("nga", f"`{ten} {d}`: đích bắt đầu bằng ~", ""))
                continue
            if re.search(r"(^|/)\.\.(/|$)", d):
                ly_do.append(("cha", f"`{ten} {d}`: đích có `..`", ""))
                continue
            tuyet = d.startswith("/")
            co_glob = bool(GLOB.search(d))
            if da_cd and not tuyet and co_glob:
                ly_do.append(("cd_glob", f"`{ten} {d}`: có `cd` trước rồi xoá glob TƯƠNG ĐỐI — đúng ca W22 bật hộp", ""))
                continue
            thanh = [x for x in d.split("/") if x not in ("", ".")]
            duoi = 0
            while thanh and set(thanh[-1]) == {"*"}:
                thanh.pop()
                duoi += 1
            glob_giua = sum(1 for x in thanh if GLOB.search(x))
            if duoi + glob_giua > 1 or (thanh[:-1] and any(GLOB.search(x) for x in thanh[:-1])):
                ly_do.append(("glob_sau", f"`{ten} {d}`: glob ăn sâu hơn một tầng thư mục", ""))
                continue
            if co_glob and duoi == 0 and not GLOB.search(d.rsplit("/", 1)[-1]):
                ly_do.append(("glob_giua", f"`{ten} {d}`: glob nằm ở tầng giữa đường dẫn", ""))
                continue
            if tuyet:
                goc = "/" + "/".join(thanh)
            elif da_cd:
                continue  # đích tương đối không glob sau cd: không phải kiểm xoá bật hộp
            else:
                goc = os.path.join(cwd or os.getcwd(), *thanh) if thanh else (cwd or os.getcwd())
            if not GLOB.search(goc):
                ld = _nguy_hiem_tuyet_doi(goc, cwd)
                if ld:
                    ma = "he_thong" if ld.startswith(("đích là thư mục gốc", "đích là thư mục hệ thống")) else (
                        "nha" if ld.startswith("đích là thư mục nhà") else "lam_viec")
                    ly_do.append((ma, f"`{ten} {d}`: {ld}", os.path.normpath(goc)))
    return ly_do


def _vang(data, cwd):
    if data.get("agent_id"):
        return "lời gọi từ THỢ chạy nền (không ai trông hộp xin quyền)"
    if _TT is None:
        return ""
    try:
        if _TT.dang_afk():
            return "anh Thành đang AFK"
    except Exception:
        pass
    try:
        if _TT.vang_qua_telegram(cwd):
            return "anh Thành đang làm qua Telegram"
    except Exception:
        pass
    return ""


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    cmd = str((data.get("tool_input") or {}).get("command") or "")
    if not re.search(r"\brm(dir)?\b", cmd):
        return 0
    cwd = str(data.get("cwd") or os.getcwd())
    ds = phan_tich_ma(cmd, cwd)
    ly_do = [chu for _ma, chu, _d in ds]
    if not ly_do:
        return 0
    vi_sao = _vang(data, cwd)
    if not vi_sao:
        return 0  # anh đang ngồi máy → để hộp của Claude Code bật như cũ, anh tự bấm
    # Task-20102026-02 (anh Thành 20/10): việc xoá THẬT SỰ cần quyền (đích là thư mục hệ thống / nhà /
    # thư mục làm việc, không phải chỗ nháp, không viết lại được) → hỏi anh qua Telegram 1A/1B, chờ ≤ 10
    # phút. 1A → ghi dấu đã duyệt rồi thả lệnh đi: PreToolUse `allow` KHÔNG vượt được hộp kiểm xoá (đo
    # 20/10 trên 2.1.304), nên để hộp bật, hook PermissionRequest thấy dấu thì cho qua. Kênh chưa dựng /
    # 1B / hết giờ → chặn như cũ.
    ket = ""
    try:
        import hop_quyen_vang_gate as HQ
        if HQ.phan_loai(data, ds) == "that":
            kq = HQ.xin_phep(data, vi_sao, ds)
            if kq == "allow":
                HQ.ghi_da_duyet(data)
                return 0
            ket = kq or ""
    except Exception:
        pass
    msg = (
        f"⛔ Lệnh xoá này sẽ bật HỘP XIN QUYỀN của Claude Code (kiểm an toàn xoá — bypass cũng không qua, "
        f"allow trong settings cũng không qua) mà {vi_sao} → không ai bấm, thợ đứng chờ. Đã chặn trước.\n"
        + "\n".join("  · " + x for x in ly_do)
        + "\nĐỔI CÁCH (chọn một):\n"
        "  1. Viết lại bằng ĐƯỜNG TUYỆT ĐỐI, KHÔNG `cd` trước `rm`, glob chỉ ở tầng cuối, không biến/~/..\n"
        "     vd `rm /private/tmp/claude-502/w22/xem/*.png` (một lệnh riêng).\n"
        "  2. Khỏi xoá: ghi ra thư mục MỚI (vd …/xem-2/) — tệp nháp trong /tmp tự dọn.\n"
        "  3. Cần xoá thư mục hệ thống/nhà/thư mục dự án → KHÔNG tự làm, ghi vào danh sách câu hỏi inbox."
    )
    if ket in ("1B", "het-gio"):
        msg = (f"⛔ Anh Thành {'trả lời 1B — KHÔNG cho' if ket == '1B' else 'không trả lời trong giờ chờ — coi như KHÔNG cho'} "
               "lệnh xoá này (hỏi qua Telegram). Đừng thử lại cùng lệnh; làm phần khác, ghi việc này vào ĐỂ LẠI.\n" + msg)
    try:  # mọi lần chặn đều nhắn anh (anh Thành 19/10: «nếu deny thì cũng phải báo tao vào telegram»)
        from hop_quyen_vang_gate import bao_tu_choi
        bao_tu_choi(data, vi_sao, "; ".join(ly_do), ly_do_ma=ds, ket=ket)
    except Exception:
        pass
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": "deny",
                                             "permissionDecisionReason": msg}}, ensure_ascii=False))
    return 0


def _tu_kiem() -> int:
    cwd = "/Users/buddhy/PycharmProjects/C-HX"
    ca = [
        # (lệnh, phải chặn?)
        ("cd /private/tmp/claude-502/w22; rm xem/*; pdftoppm -r 65 -png a.pdf xem/t", True),
        ("rm /private/tmp/claude-502/w22/xem/*.png", False),
        ("rm /private/tmp/claude-502/w22/xem/*", False),
        ("rm -f /private/tmp/claude-502/w01-16/thu/a.png", False),
        ("rm -rf /tmp/claude-x/abc", False),
        ("rm build/tmp.txt", False),
        ("rm -rf $OUT/*", True),
        ("rm -rf ~/x", True),
        ("rm -rf ../x/*", True),
        ("rm -rf /private/tmp/*/*", True),
        ("rm -rf /tmp", True),
        ("rm -rf /private/tmp", True),
        ("rm -rf /Users/buddhy", True),
        ("rm -rf /Users/buddhy/PycharmProjects/C-HX", True),
        ("rm -rf .", True),
        ("bash -c 'cd /tmp/a && rm b/*'", True),
        ("python3 - <<'EOF'\nimport os\nos.system('rm -rf $X')\nEOF", False),
        ("git rm --cached a.txt", False),
        ("S=/tmp/a; for d in x y; do rm -f $S/$d/node_modules; done", True),
        ("if true; then rm -rf $X; fi", True),
        ("while read f; do rm \"$f\"; done < l.txt", True),
        ("for f in a b; do rm -f /private/tmp/claude-502/w1/$f.png; done", True),
        ("for f in a b; do echo $f; done", False),
        ("echo rm", False),
    ]
    sai = 0
    for c, can in ca:
        ld = phan_tich(c, cwd)
        ok = bool(ld) == can
        sai += not ok
        print(("OK  " if ok else "SAI ") + ("CHẶN" if ld else "qua ") + " | " + c.replace("\n", "⏎")[:70])
    sai += _tu_kiem_xin_phep()
    print("tổng sai:", sai)
    return 1 if sai else 0


def _tu_kiem_xin_phep() -> int:
    """Ca Task-20102026-02: tin chặn lời thường; xoá thật cần quyền → hỏi 1A/1B (Telegram giả)."""
    import io
    import tempfile
    import hop_quyen_vang_gate as HQ
    d0 = tempfile.mkdtemp(prefix="rm-gate-tu-kiem-")
    HQ.THU_MUC, HQ.SO_DOI, HQ.SO_DUYET = d0, d0 + "/doi.json", d0 + "/duyet.json"
    HQ.SO_TIN, HQ.KHOA_TIN = d0 + "/tin.json", d0 + "/khoa"
    os.environ["UNIV3_XIN_QUYEN_CHO"] = "2"
    os.environ["VIEC_TAY_DIR"] = d0 + "/viec-tay"     # sổ việc tay GIẢ — không ghi vào sổ thật của anh
    gui, tra = [], {"chu": None, "mid": 700}
    HQ._gui_tele = lambda chu: gui.append(chu)

    def gia_tg(tok, method, params, timeout=10):
        if method == "sendMessage":
            if "reply_parameters" not in params:
                tra["mid"] += 1     # Telegram cấp mã tin mới cho mỗi câu hỏi
            return {"ok": True, "result": {"message_id": tra["mid"]}}
        if method == "getUpdates" and tra["chu"]:
            c, tra["chu"] = tra["chu"], None
            return {"ok": True, "result": [{"update_id": tra["mid"], "message": {
                "chat": {"id": 111}, "from": {"id": 111}, "text": c, "reply_to_message": {"message_id": tra["mid"]}}}]}
        return {"ok": True, "result": []}
    HQ._tg = gia_tg

    def chay(d):
        cu_in, cu_out = sys.stdin, sys.stdout
        sys.stdin, sys.stdout = io.StringIO(json.dumps(d)), io.StringIO()
        try:
            main()
            return sys.stdout.getvalue()
        finally:
            sys.stdin, sys.stdout = cu_in, cu_out

    sai = 0

    def chk(ten, dk):
        nonlocal sai
        sai += not dk
        print(("OK  " if dk else "SAI ") + ten)

    tho = {"agent_id": "a1", "agent_type": "tho-fulfill", "tool_name": "Bash"}
    nhap = "/private/tmp/claude-502/-Users-buddhy-PycharmProjects-LOYTeam-EtsyFulfillChichub/s/scratchpad"
    HQ._cau_hinh_xin = lambda: {"tok": "T", "anh": "111", "chat": "111"}
    ra = chay({**tho, "session_id": "n1", "tool_input": {"command": f"cd {nhap} && rm z-A-*"}, "cwd": nhap})
    chk("xoá nháp sau cd → chặn ngay, KHÔNG hỏi anh", '"deny"' in ra and len(gui) == 1 and "tệp nháp" in gui[-1])
    viec = {**tho, "tool_input": {"command": "rm -rf /Users/u/P/X"}, "cwd": "/Users/u/P/X"}
    tra["chu"] = "1A"
    ra = chay({**viec, "session_id": "t1"})
    chk("xoá thư mục dự án, anh 1A → không chặn ở cổng", ra.strip() == "")
    o = HQ.quyet({**viec, "session_id": "t1"})
    chk("… rồi hộp bật thì hook xin quyền cho qua (dấu đã duyệt)", o["hookSpecificOutput"]["decision"]["behavior"] == "allow")
    tra["chu"] = "1B"
    ra = chay({**viec, "session_id": "t2"})
    chk("anh 1B → chặn, tin báo «theo trả lời 1B»", '"deny"' in ra and "1B" in ra and "1B" in gui[-1])
    ra = chay({**viec, "session_id": "t3"})
    chk("hết giờ → chặn, tin báo hết giờ", '"deny"' in ra and "hết 10 phút" in gui[-1])
    HQ._cau_hinh_xin = lambda: None
    ra = chay({**viec, "session_id": "t4"})
    chk("chưa dựng kênh → chặn như cũ", '"deny"' in ra and "mở máy bấm cho phép" in gui[-1])

    # Task-28102026-28 — chặn lúc anh vắng: xoá thật cần anh → vào sổ việc tay; xoá nháp → chỉ đếm.
    so_md, chan = d0 + "/viec-tay/danh-sach.md", d0 + "/viec-tay/chan.jsonl"
    doc = lambda p: open(p, encoding="utf-8").read() if os.path.exists(p) else ""  # noqa: E731
    if os.path.exists(os.environ.get("UNIV3_VIEC_TAY_MJS") or HQ.VIEC_TAY_MJS) and HQ._node():
        for p in (so_md, chan):
            if os.path.exists(p):
                os.remove(p)
        chay({**tho, "session_id": "s1", "tool_input": {"command": "rm -rf /Users/u/P/Y"}, "cwd": "/Users/u/P/Y"})
        chk("xoá thư mục dự án bị chặn → có mục trong sổ giả", doc(so_md).count("· chờ") == 1 and "xoá tệp / thư mục" in doc(so_md))
        chk("… tin chặn nói đã vào sổ nhắc", "Đã vào sổ nhắc việc tay 20:00/22:00" in gui[-1])
        chay({**tho, "session_id": "s2", "tool_input": {"command": f"cd {nhap} && rm y-*"}, "cwd": nhap})
        chk("xoá nháp (thợ tự viết lại) → KHÔNG thêm mục sổ, có dòng đếm",
            doc(so_md).count("· chờ") == 1 and doc(chan).count('"tu-viet-lai"') == 1)
        chk("… tin chặn nói không vào sổ, không cần anh làm gì", "Không vào sổ nhắc — không cần anh làm gì" in gui[-1])
    else:
        print("     (máy này không có viec-tay.mjs / node — bỏ ca sổ việc tay)")
    return sai


if __name__ == "__main__":
    if "--tu-kiem" in sys.argv:
        sys.exit(_tu_kiem())
    sys.exit(main())
