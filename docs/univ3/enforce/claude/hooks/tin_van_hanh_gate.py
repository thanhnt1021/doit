#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tin_van_hanh_gate.py — CHẶN CỨNG tin gửi NHÓM NGƯỜI VẬN HÀNH mà còn dính chữ kỹ thuật.

CA THẬT 07/09/2026. Một worker gửi tin vào nhóm "Hệ thống Fulfill TheChic" (Phương, My,
Hạnh — KHÔNG ai là lập trình viên), cuối tin viết:

    "Chi tiết đầy đủ (có cả món đã tới xưởng để đối chiếu) nằm ở tệp trong kho mã nguồn:
     docs/handoff/DON-NUOT-MON-CAN-DAY-BU-07092026.md"

Founder: *"những tin nhắn như này, mày nhắc tới tệp kho mã nguồn làm gì? chỉ 1 mình tao là
Dev hiểu thôi. ngu vãi lồn. fix tận gốc để sau này gửi chuẩn."*

GỐC BỆNH: model quen viết cho lập trình viên nên tin gửi người vận hành cũng chèn đường dẫn
tệp, mã commit, tên nhánh, tên hàm, tên cột DB — thứ người đọc KHÔNG mở được, chỉ làm tin rối.
Đây là lỗi LẶP theo phản xạ, không phải sơ sẩy một lần -> markdown là xác suất, phải là cổng.

CỔNG NÀY CHẶN GÌ (đủ CẢ HAI mới chặn):
  (1) Lệnh Bash đang GỬI TIN RA NGOÀI (Bot API `sendMessage`/`sendDocument`/`sendPhoto`,
      `tg-notify.sh`, `chichub-tg.sh`), VÀ
  (2) Đích đến là NHÓM NGƯỜI VẬN HÀNH — nhận diện bằng chat_id THẬT hoặc `--loai=`, KHÔNG
      suy đoán, VÀ
  (3) Trong NỘI DUNG TIN có yếu tố kỹ thuật vô dụng với người đọc.

CỔNG NÀY KHÔNG CHẶN (chặn bừa còn tệ hơn không có cổng — founder nói thẳng):
  · Nhóm KỸ THUẬT "Nhật Ký Bóc Lột" (`-1003849385640`, `--loai=ky-thuat`) — nơi tin kỹ thuật
    ĐÚNG chỗ. `tg-notify.sh`/`claude_notify.sh` mặc định bắn vào đây.
  · Chat riêng của founder (chat_id DƯƠNG = chat 1-1) và mọi đích KHÔNG nhận ra được.
  · Mã đơn `A67-4163738170`, mã hàng/SKU, tên xưởng, phần cá nhân hoá, đường dẫn Drive/Etsy,
    link web `fulfill.thechic.site` — team CẦN đúng những thứ này, bị bóc trước khi soi.

BẢN ĐỒ NHÓM (đo 04/09/2026, `docs/handoff/backup-w53/NGUON-PHAT-TELEGRAM.md`):
    -4826531949    Loa Phường Etsy            don-hang   VẬN HÀNH -> soi
    -5449057497    Hệ thống Fulfill TheChic   tai-lieu   VẬN HÀNH -> soi
    -5239336952    TheChic - nhóm nhận noti   noti-csv   VẬN HÀNH -> soi
    -1003849385640 Nhật Ký Bóc Lột            ky-thuat   KỸ THUẬT -> CHO QUA

Fail-open tuyệt đối: parse không nổi / lỗi bất kỳ -> exit 0. Cổng này lọc VĂN PHONG, không
phải lớp bảo mật; thà lọt một tin còn hơn khoá chết đường báo tin cho team.
"""
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LOG = os.environ.get("UNIV3_TIN_VAN_HANH_LOG", "/tmp/claude_hooks/tin_van_hanh_gate.log")
TEN_CUA_THOAT = "tin-van-hanh"

# ── (1) NHÓM ĐÍCH ────────────────────────────────────────────────────────────────────
NHOM_VAN_HANH = {
    "-4826531949": "Loa Phường Etsy (đơn hàng)",
    "-1004466820523": "Hệ thống Fulfill TheChic",
    "-5449057497": "Hệ thống Fulfill TheChic (mã cũ trước supergroup 05/10/2026)",
    "-5239336952": "TheChic - nhóm nhận noti",
}
NHOM_KY_THUAT = {"-1003849385640": "Nhật Ký Bóc Lột (nhóm kỹ thuật)"}
LOAI_VAN_HANH = {"don-hang": "Loa Phường Etsy (đơn hàng)",
                 "tai-lieu": "Hệ thống Fulfill TheChic",
                 "noti-csv": "TheChic - nhóm nhận noti"}
# Tên BIẾN chat trong cấu hình cổng một cửa — dùng khi lệnh viết `chat_id=$CHAT_TAI_LIEU`.
BIEN_VAN_HANH = {"CHAT_DON_HANG": "Loa Phường Etsy (đơn hàng)",
                 "CHAT_TAI_LIEU": "Hệ thống Fulfill TheChic",
                 "CHAT_HE_THONG": "Hệ thống Fulfill TheChic",
                 "CHAT_NOTI": "TheChic - nhóm nhận noti"}

RX_GUI = re.compile(
    r"api\.telegram\.org|/bot[0-9A-Za-z:_\-]+/(send|edit)\w+"
    r"|\bsendMessage\b|\bsendDocument\b|\bsendPhoto\b"
    r"|tg-notify\.sh|chichub-tg\.sh", re.I)
RX_LOAI = re.compile(r"--loai[= ]+([a-z-]+)")
RX_CHAT_ID = re.compile(r"chat_id[=:\s\"']+(-?\d{6,})")
RX_TG_CHAT_ENV = re.compile(r"TG_CHAT_ID[=\s\"']+(-?\d{6,})")


def dich_den(cmd):
    """('van-hanh'|'ky-thuat'|'khong-ro', tên nhóm) — ĐO trong lệnh, cấm suy đoán."""
    for so, ten in NHOM_KY_THUAT.items():
        if so in cmd:
            return "ky-thuat", ten
    for so, ten in NHOM_VAN_HANH.items():
        if so in cmd:
            return "van-hanh", ten
    m = RX_LOAI.search(cmd)
    if m:
        if m.group(1) == "ky-thuat":
            return "ky-thuat", NHOM_KY_THUAT["-1003849385640"]
        if m.group(1) in LOAI_VAN_HANH:
            return "van-hanh", LOAI_VAN_HANH[m.group(1)]
    for bien, ten in BIEN_VAN_HANH.items():
        if re.search(r"\$\{?%s\b" % bien, cmd):
            return "van-hanh", ten
    # chat_id DƯƠNG = chat 1-1 với một người (founder) -> việc riêng, không phải nhóm team.
    for rx in (RX_CHAT_ID, RX_TG_CHAT_ENV):
        m = rx.search(cmd)
        if m and not m.group(1).startswith("-"):
            return "ky-thuat", "chat riêng 1-1"
    return "khong-ro", ""


# ── (2) RÚT NỘI DUNG TIN (KHÔNG soi cả lệnh — đường dẫn tg-notify.sh là của MÁY) ──────
RX_HEREDOC = re.compile(r"<<-?\s*[\"']?([A-Za-z_][A-Za-z0-9_]*)[\"']?\s*\n(.*?)\n\s*\1\s*$",
                        re.S | re.M)
RX_TRUONG = re.compile(
    r"(?:--data-urlencode|--data-raw|--data-binary|--data|-d|-F)\s+"
    r"(?:\"(?:text|caption)=((?:[^\"\\]|\\.)*)\"|'(?:text|caption)=([^']*)'|(?:text|caption)=(\S+))")
RX_ECHO = re.compile(r"(?:^|[|;&]\s*)(?:echo(?:\s+-e)?|printf(?:\s+'%s\\?n?')?)\s+"
                     r"(?:\"((?:[^\"\\]|\\.)*)\"|'([^']*)')")
RX_SENDER_ARG = re.compile(r"(?:tg-notify\.sh|chichub-tg\.sh)((?:\s+(?:--\S+|\"(?:[^\"\\]|\\.)*\"|'[^']*'|\$\w+))*)")
RX_ARG_Q = re.compile(r"\"((?:[^\"\\]|\\.)*)\"|'([^']*)'")
RX_CAT = re.compile(r"(?:^|[|;&]\s*)cat\s+(?:-\S+\s+)*([^\s|;&<>]+)")


def _gom(m):
    for g in m.groups():
        if g:
            return g
    return ""


def rut_noi_dung(cmd):
    """[(nguồn, chữ)] — chỉ phần NGƯỜI ĐỌC sẽ thấy. Rỗng -> cổng không chặn (fail-open)."""
    ra = []
    for m in RX_HEREDOC.finditer(cmd):
        ra.append(("thân heredoc <<%s" % m.group(1), m.group(2)))
    for m in RX_TRUONG.finditer(cmd):
        t = _gom(m)
        if t:
            ra.append(("trường text=/caption=", t))
    for m in RX_SENDER_ARG.finditer(cmd):
        for q in RX_ARG_Q.finditer(m.group(1) or ""):
            t = _gom(q)
            if t:
                ra.append(("tham số nội dung của script gửi", t))
    for m in RX_ECHO.finditer(cmd):
        t = _gom(m)
        if t:
            ra.append(("echo/printf đẩy vào ống", t))
    # `cat <tệp> | ...gửi` — nội dung nằm trong tệp, đọc thẳng tệp ra mà soi.
    for m in RX_CAT.finditer(cmd):
        p = os.path.expanduser(m.group(1).strip("\"'"))
        try:
            if os.path.isfile(p) and os.path.getsize(p) <= 200_000:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    ra.append(("nội dung tệp %s" % os.path.basename(p), fh.read()))
        except OSError:
            pass
    return ra


# ── (3) BÓC THỨ TEAM CẦN (chặn nhầm mấy thứ này là hỏng việc thật) ───────────────────
BOC = [
    re.compile(r"\b[A-Z]{1,3}\d{1,3}-\d{6,}\b"),          # mã đơn A67-4163738170
    re.compile(r"\b\d{9,}\b"),                             # số đơn Etsy trần
    # link team BẤM ĐƯỢC (Drive, Etsy, web app...). Link github giữ lại -> vẫn bị bắt.
    re.compile(r"https?://(?!\S*github\.com)\S+"),
]


def boc_phan_team_can(s):
    for rx in BOC:
        s = rx.sub(" ", s)
    return s


# ── (4) YẾU TỐ KỸ THUẬT VÔ DỤNG VỚI NGƯỜI VẬN HÀNH ───────────────────────────────────
DUOI_MA = "md|ts|tsx|js|jsx|mjs|cjs|py|sh|bash|json|sql|yml|yaml|toml|env|prisma|gs"
THU_MUC_MA = "docs|src|scripts|prisma|e2e|workers|reference|public|app|lib|components|migrations|hooks"

BAT = [
    ("đường dẫn thư mục mã nguồn",
     re.compile(r"(?<![\w/])(?:%s)/[\w./-]{2,}" % THU_MUC_MA)),
    ("tên tệp mã nguồn / tài liệu kho",
     re.compile(r"(?<![\w/])[\w.-]+\.(?:%s)\b" % DUOI_MA, re.I)),
    ("mã commit",
     re.compile(r"(?<![\w/])(?=[0-9a-f]{7,40}(?![\w/]))(?=[0-9a-f]*[a-f])(?=[0-9a-f]*\d)"
                r"[0-9a-f]{7,40}(?![\w/])")),
    ("tên nhánh git",
     re.compile(r"\b(?:origin|staging|upstream)/[\w.-]+\b")),
    ("tên hàm / lời gọi hàm",
     re.compile(r"\b[a-zA-Z_]\w*\(\)")),
    ("tên bảng / cột kỹ thuật trong CSDL",
     re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+){2,}\b"
                r"|\b[a-z][a-z0-9]*_(?:id|at|vnd|usd|url|status|hash|key|token|json|uuid)\b")),
    ("từ ngữ nhà nghề người vận hành không dùng",
     re.compile(r"kho\s*m[aã]\s*ngu[oồ]n|m[aã]\s*ngu[oồ]n|\brepo\b|\bcommit\b|\bbranch\b"
                r"|\bbuild\b|\bdeploy\b|BUILD_ID|\bmerge\b|pull\s*request|\bPR\s*#"
                r"|\bmigration\b|\bschema\b|\bendpoint\b|\bgit\b|\bpm2\b|\brollback\b"
                r"|\bstack\s*trace\b|\bhotfix\b", re.I)),
]


def soi(chu):
    """[(nhãn, cụm bị bắt)] — đã bóc phần team cần trước khi soi."""
    sach = boc_phan_team_can(chu)
    ra, da_co = [], set()
    for nhan, rx in BAT:
        for m in rx.finditer(sach):
            cum = m.group(0).strip()
            if not cum or (nhan, cum.lower()) in da_co:
                continue
            da_co.add((nhan, cum.lower()))
            ra.append((nhan, cum))
            if len(ra) >= 12:
                return ra
    return ra


def ghi_log(dong):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(dong.rstrip() + "\n")
    except OSError:
        pass


GOI_Y = (
    "CÁCH VIẾT LẠI (người đọc là Phương / My / Hạnh — KHÔNG ai mở được kho mã nguồn):\n"
    "  · Cần đưa chi tiết -> DÁN THẲNG bảng/danh sách vào tin, hoặc gửi tệp đính kèm\n"
    "    (`sendDocument`), hoặc thêm câu: «cần bản đầy đủ thì nhắn lại nhóm, em gửi».\n"
    "  · Cần chỉ chỗ trên web -> đưa LINK BẤM ĐƯỢC (fulfill.thechic.site/...), không đưa\n"
    "    đường dẫn tệp.\n"
    "  · Cần nói việc đã sửa xong -> nói bằng HIỆN TƯỢNG NGƯỜI DÙNG THẤY («từ giờ đơn thiếu\n"
    "    món sẽ hiện cảnh báo đỏ»), không nói commit / build / deploy.\n"
    "  · Tin thuần kỹ thuật -> gửi nhóm kỹ thuật (`--loai=ky-thuat`), đúng chỗ thì không bị chặn."
)


def dung_ly_do(nhom, bat_duoc):
    d = ["CHẶN — tin này gửi NHÓM NGƯỜI VẬN HÀNH «%s» mà còn dính chữ kỹ thuật." % nhom,
         "Người đọc không phải lập trình viên: họ không mở được kho mã nguồn, không tra được",
         "mã commit, không biết tên hàm / tên cột. Những cụm này với họ là rác, chỉ làm tin rối.",
         "", "CỤM BỊ BẮT (nguồn: phần nội dung tin, không phải phần lệnh):"]
    for nguon, nhan, cum in bat_duoc:
        d.append("  · «%s»  — %s   [%s]" % (cum[:90], nhan, nguon))
    d += ["", GOI_Y]
    return "\n".join(d)


# W05 29/09/2026 — SOẠN TỆP KHÔNG PHẢI GỬI. Lệnh `cat > gui-tin.mjs <<EOF … EOF` có chữ
# `sendMessage` / `chat_id` trong THÂN TỆP đang viết ra, chưa ai bấm gửi; chặn ở đây thì
# không viết nổi bộ gửi tin (đo thật 29/09: lệnh soạn tin nối tiếp bị chặn vì mấy chữ
# trong chính mã nguồn của bộ gửi). Chỉ bỏ qua khi heredoc ĐỔ VÀO MỘT TỆP (`> tệp <<EOF`);
# dạng gửi thật `curl --data @- <<EOF` KHÔNG có phần `> tệp` nên vẫn bị soi như cũ, và lúc
# THỰC THI tệp vừa soạn thì `tin_nhom_trung_thuc_gate` bắt được.
RX_SOAN_TEP = re.compile(r">{1,2}\s*[^\s|;&]+[^\n]*<<-?\s*[\"\']?\w+")


# W45 01/10/2026 — CHỈ LỆNH THẬT SỰ GỬI TIN (cùng cách W39 chữa `xung_ho_gate.py`
# `chu_se_gui` và W44 chữa `.claude/xung-ho-enforce.py` `chu_gui_cua_lenh`).
# CA THẬT 01/10 (`/tmp/claude_hooks/tin_van_hanh_gate.log`, dòng CHẶN cuối): W44 chạy
# `python3 - <<'PY' … PY` chỉ để SỬA ca thử trong tệp cổng — thân heredoc có chuỗi
# `api.telegram.org/…/sendMessage` + mã nhóm NẰM TRONG CHUỖI dữ liệu, không ai gửi gì.
# Bản cũ thấy chữ `sendMessage` ở bất kỳ đâu trong lệnh là coi như đang gửi.
# Nay "đang gửi" chỉ khi MỘT VẾ lệnh là: script gửi (`chichub-tg.sh`/`tg-notify.sh`) ·
# `curl`/`wget`/`ssh` có dấu Telegram · trình thông dịch chạy MÃ TẠI CHỖ (heredoc/-c/-e)
# hoặc chạy KỊCH BẢN mà PHẦN MÃ (đã bỏ chuỗi + chú thích) có lời gọi mạng/tiến trình và
# toàn khối có dấu Telegram. Vế còn lại (grep, cat, echo, python sửa tệp) không tính.
TEP_GUI = ("chichub-tg.sh", "tg-notify.sh")
TRINH_SHELL = {"bash", "sh", "zsh"}
TRINH_MA = {"python", "python3", "node", "deno", "bun", "tsx", "ts-node", "npx"}
DUOI_KB = (".sh", ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx")
TIEN_TO = {"env", "sudo", "time", "exec", "nohup", "command", "then", "do", "else", "!"}
RX_HD = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_]\w*)\1")
RX_GOI_MANG = re.compile(
    r"urlopen|urllib|\brequests\b|httpx|http\.client|aiohttp|subprocess|os\.system|os\.popen"
    r"|\bfetch\s*\(|axios|https?\.request|child_process|execSync|spawn|\bexec\s*\(")
RX_CHUOI_JS = re.compile(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"|`(?:[^`\\]|\\.)*`")


def _don_vi(cmd):
    """(dòng, thân heredoc của dòng đó). Nối dòng kết bằng `\\`."""
    dong = (cmd or "").replace("\\\n", " ").split("\n")
    i = 0
    while i < len(dong):
        d = dong[i]
        i += 1
        than = []
        for m in RX_HD.finditer(d):
            while i < len(dong) and dong[i].strip() != m.group(2):
                than.append(dong[i])
                i += 1
            i += 1
        yield d, "\n".join(than)


def _ma_khong_chuoi(ma):
    """Mã nguồn đã bỏ chuỗi + chú thích — chuỗi là DỮ LIỆU, không phải lời gọi."""
    try:
        import io
        import tokenize
        bo = (tokenize.STRING, tokenize.COMMENT)
        bo += tuple(getattr(tokenize, t) for t in ("FSTRING_START", "FSTRING_MIDDLE",
                                                     "FSTRING_END") if hasattr(tokenize, t))
        return " ".join(t.string for t in tokenize.generate_tokens(io.StringIO(ma).readline)
                        if t.type not in bo)
    except Exception:
        return RX_CHUOI_JS.sub(" ", ma or "")      # không phải Python (JS…) -> bỏ chuỗi thô


def _ma_goi_gui(ma, khoi):
    return bool(RX_GOI_MANG.search(_ma_khong_chuoi(ma)) and RX_GUI.search(khoi))


def _doc_kb(p):
    try:
        if os.path.getsize(p) > 400_000:
            return ""
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def co_gui_that(cmd, cwd=""):
    """True = có ít nhất một vế lệnh THẬT SỰ gửi tin. Mù thì True (giữ hành vi cũ)."""
    try:
        import shlex
        cwd = cwd or os.getcwd()
        for dong, than in _don_vi(cmd):
            khoi = dong + "\n" + than
            for ve in re.split(r"&&|\|\||[;|&()]|\$\(|`", dong):
                try:
                    tu = shlex.split(ve)
                except ValueError:
                    tu = ve.split()
                while tu and (tu[0] in TIEN_TO or re.match(r"^[A-Za-z_]\w*=", tu[0])):
                    tu.pop(0)
                if not tu:
                    continue
                dau = os.path.basename(tu[0])
                if dau == "cd" and len(tu) > 1:
                    cwd = os.path.join(cwd, os.path.expanduser(tu[1]))
                    continue
                if dau in TEP_GUI:
                    return True
                if dau in ("curl", "wget", "ssh") and RX_GUI.search(khoi):
                    return True
                if dau in TRINH_SHELL | TRINH_MA:
                    kb = next((t for t in tu[1:] if t.endswith(DUOI_KB)), "")
                    if kb:
                        noi = _doc_kb(os.path.join(cwd, os.path.expanduser(kb)))
                        if dau in TRINH_SHELL:
                            if RX_GUI.search(noi or ""):
                                return True
                        elif _ma_goi_gui(noi, noi + "\n" + khoi):
                            return True
                        continue
                    ma = than or " ".join(tu[1:])     # heredoc hoặc `-c`/`-e` tại chỗ
                    if dau in TRINH_SHELL:
                        if RX_GUI.search(ma) and co_gui_that(ma, cwd):
                            return True
                    elif _ma_goi_gui(ma, khoi):
                        return True
                    continue
                if tu[0].endswith(DUOI_KB) and "/" in tu[0]:
                    noi = _doc_kb(os.path.join(cwd, os.path.expanduser(tu[0])))
                    if tu[0].endswith(".sh"):
                        if RX_GUI.search(noi or ""):
                            return True
                    elif _ma_goi_gui(noi, noi + "\n" + khoi):
                        return True
        return False
    except Exception:
        return True


def kiem(cmd, cwd=""):
    """(có chặn?, lý do) — tách khỏi main để ca thử gọi thẳng được."""
    if not cmd or not RX_GUI.search(cmd):
        return False, ""
    if RX_SOAN_TEP.search(cmd):
        return False, ""
    if not co_gui_that(cmd, cwd):
        return False, ""
    loai, nhom = dich_den(cmd)
    if loai != "van-hanh":
        return False, ""
    manh = rut_noi_dung(cmd)
    if not manh:
        ghi_log("KHÔNG SOI ĐƯỢC (không rút được nội dung) | %s" % cmd[:200].replace("\n", " "))
        return False, ""
    bat_duoc = []
    for nguon, chu in manh:
        for nhan, cum in soi(chu):
            bat_duoc.append((nguon, nhan, cum))
    if not bat_duoc:
        return False, ""
    return True, dung_ly_do(nhom, bat_duoc[:12])


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    try:
        if str(data.get("tool_name") or "") != "Bash":
            return 0
        cmd = (data.get("tool_input") or {}).get("command", "") or ""
        # 07/10/2026 (việc 20261007-L20): nhóm vận hành là nhóm CHICHUB — dự án khác (vd Hồng
        # Xiêm, loại tin "tài liệu" qua hx-tg.sh) im lặng. Điều kiện ở pham_vi_chichub.py.
        try:
            import pham_vi_chichub
            if not pham_vi_chichub.thuoc_chichub(cmd, str(data.get("cwd") or "")):
                return 0
        except Exception:
            pass
        chan, ly_do = kiem(cmd, str(data.get("cwd") or ""))
        if not chan:
            return 0
        try:
            import cua_thoat
            mo = cua_thoat.lay(TEN_CUA_THOAT, ai=str(data.get("agent_id") or "main"))
            if mo:
                ghi_log("CỬA THOÁT | %s" % mo[:200])
                return 0
            ly_do += "\n\n" + cua_thoat.loi_khuyen(TEN_CUA_THOAT)
        except Exception:
            pass
        ghi_log("CHẶN | %s" % cmd[:300].replace("\n", " "))
    except Exception:
        return 0
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": ly_do,
    }}, sys.stdout, ensure_ascii=False)
    return 0


# ── CA THỬ (chạy: python3 tin_van_hanh_gate.py --tu-kiem) ────────────────────────────
CA_THU = [
    ("1. tin vận hành + trỏ tệp trong kho mã nguồn -> CHẶN", True,
     '''/root/chichub-tg.sh --loai=tai-lieu "Cả nhà ơi, đơn A67-4163738170 bị nuốt món.
Chi tiết đầy đủ nằm ở tệp trong kho mã nguồn: docs/handoff/ABC.md"'''),
    ("2. tin vận hành chỉ có mã đơn / xưởng / cá nhân hoá -> QUA", False,
     '''/root/chichub-tg.sh --loai=don-hang "Đơn A67-4163738170 đã gửi xưởng Zootopbear.
Phần cá nhân hoá: «To my dearest Mom - 2026». Mã hàng ZTB-MUG-11OZ-WHT, số lượng 2."'''),
    ("3. tin vận hành có mã commit -> CHẶN", True,
     '''curl -s -X POST https://api.telegram.org/bot$T/sendMessage -d chat_id=-5449057497 \\
  --data-urlencode "text=Đã sửa xong lỗi thiếu món, bản 1e79e3b0 nhé cả nhà."'''),
    ("4. tin vận hành bình thường -> QUA", False,
     '''~/.claude/universal-hooks/tg-notify.sh "Cả nhà nhớ chốt đơn trước 5h chiều nay.
Đơn nào xưởng báo hết hàng thì nhắn lại nhóm để em đổi mẫu."'''.replace(
         "tg-notify.sh", "tg-notify.sh") .replace("~/.claude", "TG_CHAT_ID=-5449057497 ~/.claude")),
    ("5. tin KỸ THUẬT gửi nhóm kỹ thuật -> QUA (không chặn bừa)", False,
     '''/root/chichub-tg.sh --loai=ky-thuat "Deploy prod xong, commit 1e79e3b0, BUILD_ID đã đổi.
Sửa ở src/lib/orders/actions.ts, chạy migration add_missing_items."'''),
    ("6. tin vận hành có tên hàm + tên cột DB -> CHẶN", True,
     '''/root/chichub-tg.sh --loai=noti-csv "Bảng daily_stats cột revenue_daily_vnd đã đúng,
hàm tinhLaiRong() chạy lại rồi nhé."'''),
    ("7. tin vận hành có link web bấm được -> QUA", False,
     '''/root/chichub-tg.sh --loai=tai-lieu "Xem danh sách đơn thiếu món tại
https://fulfill.thechic.site/orders?filter=missing — bấm vào là ra, không cần làm gì thêm."'''),
    ("9. SOAN tep gui tin (heredoc do vao tep) -> QUA (chua gui gi)", False,
     "cat > /tmp/gui-tin.mjs <<'XX'\n"
     "const api = 'https://api.telegram.org/bot' + token\n"
     "await fetch(api + '/sendMessage', {body: JSON.stringify({chat_id: '-5449057497',\n"
     "  text: 'Cả nhà mở thử giúp nhé', reply_to_message_id: 3683})})\nXX"),
    ("8. chat riêng 1-1 với founder -> QUA", False,
     '''curl -s -X POST https://api.telegram.org/bot$T/sendMessage -d chat_id=123456789 \\
  --data-urlencode "text=Đã push docs/handoff/ABC.md, commit 1e79e3b0, nhánh origin/main."'''),
    # W45 01/10/2026 — chuỗi Telegram nằm trong DỮ LIỆU của lệnh sửa tệp, không ai gửi gì.
    ("10. python heredoc chỉ SỬA tệp cổng, chuỗi gửi tin nằm trong dữ liệu -> QUA", False,
     "python3 - <<'PY'\np='x.py'\ns=open(p).read()+'''urllib.request.urlopen('https://api.telegram.org/"
     "botT/sendMessage?chat_id=-5449057497&text=docs/handoff/A.md')'''\nopen(p,'w').write(s)\nPY"),
    ("11. python heredoc GỌI Telegram thật tới nhóm, tin trỏ tệp -> CHẶN", True,
     "python3 - <<'PY'\nimport urllib.request, urllib.parse\nq=urllib.parse.urlencode({'chat_id': "
     "'-5449057497', 'text': 'Chi tiết ở docs/handoff/A.md'})\n"
     "urllib.request.urlopen('https://api.telegram.org/botT/sendMessage?'+q)\nPY"),
    ("12. grep đọc phiếu + echo nhắc mã nhóm, không gửi -> QUA", False,
     "grep -n 'sendMessage' docs/ticket/P114.md; echo \"chat_id=-5449057497 docs/handoff/A.md\""),
]


def tu_kiem():
    loi = 0
    for ten, mong, cmd in CA_THU:
        chan, ly_do = kiem(cmd)
        ok = (chan == mong)
        loi += 0 if ok else 1
        print("%s %s" % ("PASS" if ok else "FAIL", ten))
        if chan:
            for dong in ly_do.splitlines():
                if dong.strip().startswith("·") and "—" in dong:
                    print("        %s" % dong.strip())
        if not ok:
            print("        (mong %s, ra %s)" % ("CHẶN" if mong else "QUA",
                                                "CHẶN" if chan else "QUA"))
    print("\n%d/%d ca đúng" % (len(CA_THU) - loi, len(CA_THU)))
    return 1 if loi else 0


if __name__ == "__main__":
    if "--tu-kiem" in sys.argv:
        sys.exit(tu_kiem())
    sys.exit(main())
