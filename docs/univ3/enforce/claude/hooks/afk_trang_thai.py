#!/usr/bin/env python3
"""afk_trang_thai.py — MỘT nguồn trạng thái «founder đang AFK» cho mọi hook.

Ghi: `afk_mode.py` (UserPromptSubmit) — bật khi founder báo rời máy, tắt khi founder báo đã về.
Đọc: `afk_hoi_inbox_gate.py` (PreToolUse:AskUserQuestion) — đang AFK thì chặn hỏi trong CLI.

WHY cờ nằm ở thư mục người dùng chứ không theo phiên: founder rời máy là rời MỌI phiên, mọi dự án;
phiên mới mở lúc founder vắng cũng không được hỏi trong CLI (anh Thành 11/10/2026: «đã bảo /afk thì
câu hỏi gửi theo list vào inbox mà»).
WHY tự hết sau 8 tiếng: founder hay quên gõ «tao về rồi»; cờ sống mãi thì hôm sau ngồi máy vẫn bị cấm
hỏi — cổng chặn phải có lối ra.

SỬA GỐC P005 (C-HX, 18/10/2026 — lần tái phát thứ 3 «AFK mà vẫn hỏi»): «hết 8 tiếng» KHÔNG có nghĩa là
founder đã về. Ca thật: /afk 17/10 09:20, cờ hết hạn 17:20, đêm đó founder chỉ nhắn Telegram, 06:51 18/10
hộp hỏi bật trong CLI. Founder: «tao đã afk thì mày phải biết mà gửi vào tele chứ???? fix tận gốc».
Định nghĩa mới — MỘT hàm `dang_vang()` cho mọi cổng:
  · cờ còn hạn                                        → VẮNG (luật 11/10 giữ nguyên);
  · cờ hết hạn mà CHƯA có lượt GÕ CLI THẬT nào sau lúc bật (+ biên 120 giây cho chính lượt /afk) → VẮNG;
  · lời founder mới nhất đến từ Telegram, mới hơn lượt gõ CLI cuối  → VẮNG (luật W301, thêm nguồn tệp đệm
    `~/.claude/afk/moc-telegram-<dự án>.json` cho dự án tự ghi mốc — C-HX: `sep_viec.py`);
  · còn lại → có mặt. Hết hạn 8 tiếng nay chỉ còn là trần cho ca founder ĐÃ gõ CLI lại mà quên «tao về rồi».
Vì vậy cờ hết hạn KHÔNG còn bị xoá khi đọc (trước đây `dang_afk()` xoá ngay → mất dấu `bat_luc`); cờ chỉ mất
khi founder nói đã về (`afk_mode.py` → `tat()`) hoặc bị /afk mới ghi đè.
"""
import json
import os
import time

THU_MUC = os.environ.get("UNIV3_AFK_DIR") or os.path.expanduser("~/.claude/afk")   # biến môi trường: chỉ cho ca thử
TEP = os.path.join(THU_MUC, "trang-thai.json")
HAN_GIAY = 8 * 3600


def bat(trich: str = "") -> None:
    os.makedirs(THU_MUC, exist_ok=True)
    bay_gio = int(time.time())
    with open(TEP, "w", encoding="utf-8") as f:
        json.dump(
            {"bat_luc": bay_gio, "het_han": bay_gio + HAN_GIAY, "trich": trich[:200]},
            f,
            ensure_ascii=False,
        )


def tat() -> None:
    try:
        os.remove(TEP)
    except FileNotFoundError:
        pass


def doc_co():
    """dict cờ AFK thô (kể cả đã hết hạn), không có / hỏng → None. KHÔNG xoá gì (P005)."""
    try:
        with open(TEP, encoding="utf-8") as f:
            tt = json.load(f)
        return tt if isinstance(tt, dict) else None
    except Exception:
        return None


def dang_afk():
    """dict trạng thái nếu cờ AFK còn hạn, ngược lại None.

    P005: KHÔNG xoá cờ hết hạn nữa — `dang_vang()` cần `bat_luc` để biết founder đã gõ CLI lại chưa."""
    tt = doc_co()
    if not tt:
        return None
    try:
        if int(tt.get("het_han", 0)) <= int(time.time()):
            return None
    except Exception:
        return None
    return tt


# ══════ Vé d991d9a878 (W301 15/10/2026, thẻ Task-12102026-21) — ANH LÀM QUA TELEGRAM = VẮNG KHỎI CLI ══════
# Lệnh anh Thành 12/10: cấm bật hộp hỏi trong CLI khi anh đang làm qua Telegram. Đo 14/10 (W279): hai
# cổng hộp hỏi chỉ chặn khi có cờ /afk hoặc `.claude/anh-vang`; ca 19:37 gõ CLI → 19:41 Reply Telegram,
# cả hai cổng cho hộp hỏi qua. Nay coi anh VẮNG khi lời MỚI NHẤT của anh đến từ Telegram và mới hơn
# lượt anh gõ CLI cuối (mọi dự án, sổ lệnh `~/.claude/so-lenh/*/<ngày>/.so.json`).
# Mốc Telegram: dự án có bảng thẻ Việc giao Dev (ChicHub) → `task_dev.task_dev_event` trên DB SỐNG
# `chichub_bigdb`, lời của anh (`source='dev'`) mang `meta.tg_chat` (Reply / tin / /viec từ Telegram).
# Dự án khác không có nguồn → không đổi gì. Hỏng / chậm (> 3 giây) → coi như không có mốc (fail-open).
# Nhớ đệm 60 giây ở `~/.claude/afk/moc-telegram.json` để hai cổng cùng lượt không hỏi DB hai lần.
# Lùi: `UNIV3_VANG_TELEGRAM_TAT=1`.
import glob as _glob
import re as _re
import subprocess as _sp

GOC_SO_LENH = os.path.abspath(os.environ.get("UNIV3_SO_LENH_ROOT") or os.path.expanduser("~/.claude/so-lenh"))
TEP_NHO_TG = os.path.join(THU_MUC, "moc-telegram.json")
NHO_TG_GIAY = 60
SQL_TG = ("select coalesce(extract(epoch from max(at)), 0) from task_dev.task_dev_event "
          "where source = 'dev' and meta::jsonb ? 'tg_chat' and at > now() - interval '3 days'")


def luot_go_cli_cuoi():
    """Mốc epoch lượt anh GÕ TAY CLI mới nhất (mọi dự án, 2 ngày sổ gần nhất mỗi dự án); không có → None.

    WHY lọc: sổ lệnh ghi MỌI lượt UserPromptSubmit, kể cả lời nhắc theo lịch (cron phiên) — đo 15/10:
    3/8 mục sổ ChicHub (L01 01:37, L05 07:41, L06 13:37) là lời nhắc «Theo dõi thẻ…» tự bắn, không phải anh
    gõ; tính chúng là «anh vừa gõ CLI» thì mốc CLI luôn mới hơn lời Telegram → cổng mở sai."""
    cac = []
    for du_an in _glob.glob(os.path.join(GOC_SO_LENH, "*")):
        for d in sorted(_glob.glob(os.path.join(du_an, "????-??-??")))[-2:]:
            try:
                with open(os.path.join(d, ".so.json"), encoding="utf-8") as f:
                    muc = (json.load(f) or {}).get("muc", {}) or {}
            except Exception:
                continue
            for m in muc.values():
                try:
                    cac.append((float(m.get("luc")), m))
                except Exception:
                    continue
    cac.sort(key=lambda x: -x[0])
    for i, (luc, m) in enumerate(cac):
        # P005 (lỗ R2 thứ 3): trước đây mục thứ 13 được trả luôn dù CHƯA xác minh là gõ tay → nghiêng về
        # «có mặt» (đúng hướng gây hộp hỏi lúc vắng). Nay quá 12 mục toàn máy tự bắn → coi như không có mốc.
        if i >= 12:
            return None
        if _muc_so_la_go_tay(m, luc) is not False:
            return luc
    return None


def _muc_so_la_go_tay(m, luc):
    """True/False theo bản ghi phiên quanh mốc của mục sổ; không đọc được → None (giữ như cũ: tính là gõ)."""
    duong = str(m.get("transcript") or "")
    try:
        off = int(m.get("offset"))
    except Exception:
        return None
    if not duong or not os.path.isfile(duong):
        return None
    try:
        with open(duong, "rb") as f:
            f.seek(max(0, off - (1 << 20)))
            khoi = f.read(2 << 20)
    except Exception:
        return None
    tot = None
    for dong in khoi.split(b"\n"):
        lp = _phan_loai_dong(dong)
        # P005 (lỗ R2 thứ 2): mục sổ là tin kênh Telegram (`tg`) trước bị bỏ qua → None → tính là gõ tay.
        if not lp or lp[0] not in ("cli", "lich", "tg"):
            continue
        lech = abs(lp[1] - luc)
        if lech <= 10 and (tot is None or lech < tot[0]):
            tot = (lech, lp[0])
    return None if tot is None else tot[1] == "cli"


# ── Dấu hiệu tất định TRONG PHIÊN (thẻ Task-12102026-21, lệnh anh Thành 06:14 16/10 «1A») ──
# Lời anh từ Telegram vào phiên bằng hai đường, cả hai nằm trong bản ghi phiên (`transcript_path`):
#   (a) con canh `task-dev.mjs canh` thoát → thông báo nền (origin.kind = task-notification), tệp đầu ra mở
#       đầu «🔔 CÓ CẬP NHẬT VIỆC GIAO DEV MỚI», khối sự kiện của anh có «Telegram» / «(Reply» (đo 16/10 06:10:
#       tệp b7bh0hyg5.output, 5 sự kiện, đủ ba kiểu Reply tin việc · /viec · Reply tin riêng);
#   (b) kênh Telegram của Claude Code: lượt mở đầu `<channel source="…telegram…`.
# Lượt anh gõ CLI: origin.kind / turnOrigin = "human" (cả lượt gõ chen lúc máy đang chạy = queued_command).
# Lời nhắc theo lịch: turnOrigin = "scheduled". WHY cần nguồn này: mốc Telegram trên DB hỏng khi đường hầm
# 5432 tắt (đo 06:24 16/10: psql «timeout expired» → mốc None → cổng mở, hộp hỏi bật trong lúc anh vừa Reply).
TIEU_DE_CANH = "CÓ CẬP NHẬT VIỆC GIAO DEV MỚI"
TEN_FOUNDER = os.environ.get("UNIV3_TEN_FOUNDER") or "anh Thành"
QUET_PHIEN_TOI_DA = 48 << 20     # chỉ lùi tối đa 48 MB cuối bản ghi (bản ghi ChicHub ~150 MB)
_RE_THE_TN = _re.compile(r"<output-file>([^<]+)</output-file>")
_RE_KHOI = _re.compile(r"^#\d+ ·", _re.M)


def _epoch_iso(chu):
    try:
        import datetime as _dt
        return _dt.datetime.fromisoformat(str(chu).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def canh_co_loi_telegram_cua_anh(chu):
    """Đầu ra con canh có ít nhất một sự kiện CỦA ANH đến qua Telegram."""
    if TIEU_DE_CANH not in (chu or ""):
        return False
    vt = [m.start() for m in _RE_KHOI.finditer(chu)] + [len(chu)]
    for a, b in zip(vt, vt[1:]):
        khoi = chu[a:b]
        dau = khoi.split("\n", 1)[0]
        if TEN_FOUNDER in dau and ("Telegram" in khoi or "(Reply" in khoi):
            return True
    return False


def _chu_luot(j):
    c = (j.get("message") or {}).get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        if c and all(isinstance(x, dict) and x.get("type") == "tool_result" for x in c):
            return None
        return " ".join(str(x.get("text") or "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    return None


def _phan_loai_dong(dong):
    """(loại, epoch) cho một dòng bản ghi: cli · tg · lich; dòng khác → None."""
    if b'"user"' not in dong and b"queued_command" not in dong:
        return None
    try:
        j = json.loads(dong)
    except Exception:
        return None
    luc = _epoch_iso(j.get("timestamp"))
    if luc is None:
        return None
    if j.get("type") == "attachment":
        a = j.get("attachment") or {}
        if a.get("type") != "queued_command":
            return None
        nguon = (a.get("origin") or {}).get("kind") if isinstance(a.get("origin"), dict) else None
        chu = a.get("prompt") if isinstance(a.get("prompt"), str) else ""
    elif j.get("type") == "user":
        # P005 (lỗ R2 thứ 1): dòng tóm tắt nén ngữ cảnh mang `turnOrigin: "human"` mà không có `origin` (đo bản
        # ghi C-HX 18/10 06:51:30) → trước bị tính là founder gõ CLI. Dòng máy chèn (meta / chỉ hiện trong bản ghi)
        # không bao giờ là người gõ.
        # (Lời nhắc theo lịch cũng mang isMeta → nhận diện «lich» TRƯỚC để sổ lệnh vẫn loại được nó.)
        if j.get("turnOrigin") == "scheduled":
            return ("lich", luc)
        if j.get("isCompactSummary") or j.get("isMeta") or j.get("isVisibleInTranscriptOnly"):
            return None
        chu = _chu_luot(j)
        if chu is None:
            return None
        nguon = (j.get("origin") or {}).get("kind") or j.get("turnOrigin")
        if j.get("turnOrigin") == "scheduled":
            nguon = "scheduled"
    else:
        return None
    if chu.lstrip().startswith("<channel source=") and "telegram" in chu[:200].lower():
        return ("tg", luc)
    if nguon == "human":
        return ("cli", luc)
    if nguon == "scheduled":
        return ("lich", luc)
    if nguon == "task-notification" and "<output-file>" in chu:
        m = _RE_THE_TN.search(chu)
        try:
            with open(m.group(1).strip(), encoding="utf-8", errors="replace") as f:
                dau = f.read(64 << 10)
        except Exception:
            return None
        if canh_co_loi_telegram_cua_anh(dau):
            return ("tg", luc)
    return None


def moc_trong_phien(transcript):
    """{'cli': epoch|None, 'tg': epoch|None} — lượt gõ CLI và lời Telegram MỚI NHẤT trong bản ghi phiên."""
    kq = {"cli": None, "tg": None}
    if not transcript or not os.path.isfile(transcript):
        return kq
    try:
        with open(transcript, "rb") as f:
            f.seek(0, 2)
            cuoi = f.tell()
            du = b""
            da_doc = 0
            while cuoi > 0 and da_doc < QUET_PHIEN_TOI_DA and kq["cli"] is None:
                buoc = min(4 << 20, cuoi)
                cuoi -= buoc
                f.seek(cuoi)
                khoi = f.read(buoc) + du
                da_doc += buoc
                dong = khoi.split(b"\n")
                du = dong[0] if cuoi > 0 else b""
                for d in reversed(dong[1:] if cuoi > 0 else dong):
                    lp = _phan_loai_dong(d)
                    if not lp or lp[0] == "lich":
                        continue
                    if kq[lp[0]] is None:
                        kq[lp[0]] = lp[1]
                    if kq["cli"] is not None:
                        break
    except Exception:
        pass
    return kq


def _goc_task_dev(cwd):
    p = os.path.abspath(cwd or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(p, "src", "lib", "task-dev")) and os.path.isfile(os.path.join(p, ".env")):
            return p
        cha = os.path.dirname(p)
        if cha == p:
            return ""
        p = cha


def _url_db_song(goc):
    """DATABASE_URL của dự án, ÉP tên DB sống `chichub_bigdb` (`.env` trần trỏ DB dev), bỏ ?schema=…"""
    try:
        with open(os.path.join(goc, ".env"), encoding="utf-8") as f:
            for dong in f:
                m = _re.match(r'\s*DATABASE_URL\s*=\s*"?([^"\n]+)"?', dong)
                if m:
                    url = m.group(1).split("?", 1)[0]
                    return _re.sub(r"/[A-Za-z0-9_]+$", "/chichub_bigdb", url)
    except Exception:
        pass
    return ""


def moc_telegram_cuoi(cwd=""):
    """Mốc epoch lời mới nhất của anh đến từ Telegram (dự án có bảng thẻ); không có / hỏng → None."""
    gia = os.environ.get("UNIV3_MOC_TELEGRAM_ANH")      # ca thử
    if gia is not None:
        try:
            return float(gia) or None
        except Exception:
            return None
    tep = moc_telegram_tep(cwd)
    goc = _goc_task_dev(cwd)
    if not goc:
        return tep
    db = _moc_telegram_db(goc)
    return max([x for x in (tep, db) if x] or [0]) or None


# ── P005 — nguồn mốc Telegram CẮM ĐƯỢC theo dự án (tệp đệm, hook không gọi mạng) ──
# Dự án nào có bot Telegram tự ghi `~/.claude/afk/moc-telegram-<tên thư mục dự án>.json` = {"moc": epoch giây
# lời founder mới nhất trên Telegram, "nguon": "..."}. C-HX: `scripts/sep-viec/sep_viec.py` (lệnh `moc-founder`,
# mỗi lượt `canh`, và khi `moi`/`canh` thấy tin của chủ nhà). Tệp cũ / hỏng / thiếu → bỏ qua (H2 vẫn phủ).
def _ten_du_an_len(cwd):
    p = os.path.abspath(cwd or os.getcwd())
    ra = []
    for _ in range(12):
        ten = os.path.basename(p)
        if ten:
            ra.append(ten)
        cha = os.path.dirname(p)
        if cha == p:
            break
        p = cha
    return ra


def moc_telegram_tep(cwd=""):
    """Mốc epoch từ tệp đệm của dự án (thư mục đang đứng hoặc thư mục cha); không có / hỏng → None."""
    for ten in _ten_du_an_len(cwd):
        p = os.path.join(THU_MUC, "moc-telegram-%s.json" % ten)
        if not os.path.isfile(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                moc = float((json.load(f) or {}).get("moc") or 0)
            return moc if moc > 0 else None
        except Exception:
            return None
    return None


def _moc_telegram_db(goc):
    """Đường cũ ChicHub (giữ nguyên hành vi — A13/R7 phiếu P005): psql bảng task_dev, nhớ đệm 60 giây."""
    try:
        with open(TEP_NHO_TG, encoding="utf-8") as f:
            nho = json.load(f)
        if nho.get("goc") == goc and time.time() - float(nho.get("luc", 0)) < NHO_TG_GIAY:
            return float(nho.get("moc") or 0) or None
    except Exception:
        pass
    url = _url_db_song(goc)
    if not url:
        return None
    try:
        r = _sp.run(["psql", url, "-At", "-c", SQL_TG], capture_output=True, text=True, timeout=3.0,
                    env=dict(os.environ, PGCONNECT_TIMEOUT="2"))
        moc = float((r.stdout or "").strip() or 0) if r.returncode == 0 else None
    except Exception:
        moc = None
    if moc is None:
        return None
    try:
        os.makedirs(THU_MUC, exist_ok=True)
        with open(TEP_NHO_TG, "w", encoding="utf-8") as f:
            json.dump({"goc": goc, "luc": time.time(), "moc": moc}, f)
    except Exception:
        pass
    return moc or None


def vang_qua_telegram(cwd="", cli=None, tg=None, transcript=""):
    """dict {tg, cli} nếu lời mới nhất của anh đến từ Telegram, mới hơn lượt gõ CLI cuối; ngược lại None.

    Hai nguồn mỗi mốc, lấy cái MỚI hơn: Telegram = DB thẻ (`moc_telegram_cuoi`) + bản ghi phiên;
    CLI = sổ lệnh mọi dự án (đã lọc lời nhắc theo lịch) + bản ghi phiên. `transcript` = `transcript_path`
    của payload hook; bỏ trống thì như cũ (chỉ DB + sổ)."""
    if os.environ.get("UNIV3_VANG_TELEGRAM_TAT") == "1":
        return None
    phien = moc_trong_phien(transcript) if transcript else {"cli": None, "tg": None}
    if cli is None:
        cli = max([x for x in (luot_go_cli_cuoi(), phien["cli"]) if x] or [0]) or None
    if tg is None:
        # Bản ghi phiên đã đủ kết luận VẮNG thì khỏi hỏi DB: đường hầm tắt làm psql treo ~3 giây, cổng
        # chỉ có 5 giây (settings.json) — quá hạn là cổng mở (đo 06:24 16/10: 3–4 giây/lượt).
        if phien["tg"] and (cli is None or phien["tg"] > cli):
            tg = phien["tg"]
        else:
            tg = max([x for x in (moc_telegram_cuoi(cwd), phien["tg"]) if x] or [0]) or None
    if not tg:
        return None
    if cli is not None and cli >= tg:
        return None
    return {"tg": tg, "cli": cli}


# ══════ P005 (C-HX 18/10/2026) — MỘT định nghĩa «founder đang vắng» cho MỌI cổng ══════
BIEN_VE_GIAY = 120          # lượt gõ ≤ bat_luc + 120 giây là chính lượt /afk (sổ C-HX 18/10: L02 07:03:32 = bat_luc)
TIEN_TO_MAY = ("<task-notification", "<cross-session-message", "<agent-message", "[SYSTEM NOTIFICATION",
               "<system-reminder", "<local-command-", "<user-prompt-submit-hook", "<bash-std", "<channel source=")


def la_loi_may(prompt):
    """Lượt UserPromptSubmit do máy chèn (thông báo nền, tin liên phiên, kênh Telegram…), không phải người gõ."""
    return str(prompt or "").lstrip().startswith(TIEN_TO_MAY)


def dang_vang(cwd="", transcript="", nhanh=False, prompt=None):
    """(vắng?, lý do, chi tiết) — nguồn sự thật DUY NHẤT cho mọi cổng đẩy việc hỏi founder.

    Lý do: «co-con-han» · «co-het-han-chua-go-cli» · «telegram» · «vua-go-cli» · «co-mat».
    `nhanh=True` (gọi từ UserPromptSubmit, founder vừa gõ CLI): chỉ xét cờ còn hạn, không quét sổ/phiên —
    TRỪ KHI `prompt` là lời máy chèn (thông báo nền cũng đi qua UserPromptSubmit) → xét đủ.
    Không bao giờ ném lỗi: hỏng chỗ nào thì nghiêng về VẮNG khi đã có cờ (R2), có mặt khi không có cờ."""
    bay_gio = time.time()
    tt = doc_co()
    try:
        bat_luc = float((tt or {}).get("bat_luc") or 0)
        het_han = float((tt or {}).get("het_han") or 0)
    except Exception:
        bat_luc, het_han = 0.0, 0.0
    ct = {"bat_luc": bat_luc or None, "het_han": het_han or None, "cli": None, "tg": None}
    if tt and het_han > bay_gio:
        return True, "co-con-han", ct
    if nhanh and prompt is not None and la_loi_may(prompt):
        nhanh = False
    if nhanh:
        return False, "vua-go-cli", ct
    try:
        phien = moc_trong_phien(transcript) if transcript else {"cli": None, "tg": None}
    except Exception:
        phien = {"cli": None, "tg": None}
    try:
        so = luot_go_cli_cuoi()
    except Exception:
        so = None
    cli = max([x for x in (so, phien.get("cli")) if x] or [0]) or None
    ct["cli"] = cli
    if tt and (cli is None or cli <= bat_luc + BIEN_VE_GIAY):
        return True, "co-het-han-chua-go-cli", ct
    if os.environ.get("UNIV3_VANG_TELEGRAM_TAT") == "1":
        return False, "co-mat", ct
    tg = phien.get("tg")
    if not (tg and (cli is None or tg > cli)):
        try:
            tg = max([x for x in (moc_telegram_cuoi(cwd), phien.get("tg")) if x] or [0]) or None
        except Exception:
            tg = phien.get("tg")
    ct["tg"] = tg
    if tg and (cli is None or tg > cli):
        return True, "telegram", ct
    return False, "co-mat", ct


def anh_vang(cwd="", transcript=""):
    """Một câu hỏi cho mọi cổng: anh có VẮNG khỏi CLI không. P005: đi qua `dang_vang()`."""
    try:
        return dang_vang(cwd, transcript)[0]
    except Exception:
        return bool(dang_afk())


def _goc_du_an(cwd):
    """Thư mục dự án chứa `.claude/afk-inbox.txt` (đi ngược lên từ cwd); không có → ''."""
    p = os.path.abspath(cwd or os.getcwd())
    for _ in range(12):
        if os.path.isfile(os.path.join(p, ".claude", "afk-inbox.txt")):
            return p
        cha = os.path.dirname(p)
        if cha == p:
            return ""
        p = cha
    return ""


def khai_inbox(cwd=""):
    """(tên dự án, nơi khai, chữ lệnh) — dự án tự khai kênh inbox. Không có → (tên thư mục, '', '').

    Hai nơi khai, nơi đầu thắng:
      1. `<dự án>/.claude/afk-inbox.txt` (dự án có quyền ghi .claude của mình);
      2. `~/.claude/afk/inbox-<tên thư mục dự án>.txt` — do chính công cụ inbox của dự án tự ghi (C-HX:
         `scripts/sep-viec/sep_viec.py` ghi mỗi lần chạy, vì `.claude/` của C-HX bị .gitignore — đo 18/10)."""
    goc = _goc_du_an(cwd)
    if goc:
        try:
            with open(os.path.join(goc, ".claude", "afk-inbox.txt"), encoding="utf-8") as f:
                chu = f.read().strip()
            if chu:
                return os.path.basename(goc), ".claude/afk-inbox.txt", chu
        except Exception:
            pass
    for ten in _ten_du_an_len(cwd):
        tep = os.path.join(THU_MUC, "inbox-%s.txt" % ten)
        if not os.path.isfile(tep):
            continue
        try:
            with open(tep, encoding="utf-8") as f:
                chu = f.read().strip()
            if chu:
                return ten, tep.replace(os.path.expanduser("~"), "~"), chu
        except Exception:
            pass
    return os.path.basename(os.path.abspath(cwd or os.getcwd()).rstrip("/")) or "du-an", "", ""


def kenh_inbox(cwd=""):
    """Khối chữ «gửi câu hỏi founder qua đâu» cho dự án đang đứng (H5 phiếu P005).

    Thứ tự: dự án tự khai (`khai_inbox`) → ChicHub (gắn cứng, giữ nguyên) → `~/.claude/afk/cau-hoi-<dự án>.md`."""
    cwd = str(cwd or os.getcwd())
    try:
        ten, noi, chu = khai_inbox(cwd)
    except Exception:
        ten, noi, chu = "du-an", "", ""
    if chu:
        return ("  %s → kênh inbox founder của dự án (khai ở %s):\n" % (ten, noi)
                + "".join("    " + d + "\n" for d in chu.splitlines()))
    if "EtsyFulfillChichub" in cwd or _goc_task_dev(cwd):
        return (
            "  ChicHub → MỘT tin riêng anh Thành (chạy --thu trước, rồi bỏ --thu gửi thật):\n"
            "    TASK_DEV_URL=https://fulfill.thechic.site node scripts/task-dev.mjs tin --rieng \\\n"
            "      --loai hoi --ma <Task-… của việc>   (chưa có thẻ: --loai khong-task --ly-do-khong-task \"…\") \\\n"
            "      --tieu-de \"Câu hỏi chờ anh quyết (đang AFK)\" \\\n"
            "      --da-lam $'1. <câu 1>\\n1A · <đề xuất> (đề xuất) · 1B · <khác>\\n2. …' \\\n"
            "      --xem-o \"<link màn hoặc: không có màn — chạy ngầm>\" \\\n"
            "      --can-lam \"**anh Thành** — trả lời kiểu 1A, 2B (Reply tin này)\" --thu\n"
        )
    return (
        "  Dự án này chưa khai kênh inbox (.claude/afk-inbox.txt hoặc ~/.claude/afk/inbox-%s.txt) → ghi danh sách vào\n"
        "    ~/.claude/afk/cau-hoi-%s.md và nhắc lại đầu tiên khi founder gõ «tao về rồi».\n" % (ten, ten)
    )


def mo_ta_vang(ly_do, ct):
    """Một dòng người đọc được: vì sao coi founder đang vắng."""
    gio = lambda x: time.strftime("%H:%M %d/%m", time.localtime(x)) if x else "chưa có"
    if ly_do == "co-con-han":
        con = max(0, int((ct.get("het_han") or 0) - time.time()))
        return "cờ /afk còn %d giờ %d phút" % (con // 3600, (con % 3600) // 60)
    if ly_do == "co-het-han-chua-go-cli":
        return ("cờ /afk bật lúc %s đã quá 8 tiếng nhưng từ đó founder CHƯA gõ CLI lượt nào (lượt gõ cuối %s) "
                "— hết hạn KHÔNG có nghĩa là đã về" % (gio(ct.get("bat_luc")), gio(ct.get("cli"))))
    if ly_do == "telegram":
        return ("lời mới nhất của founder đến từ Telegram (%s), mới hơn lượt gõ CLI cuối (%s)"
                % (gio(ct.get("tg")), gio(ct.get("cli"))))
    return ly_do


def loi_khi_vang(cwd="", transcript="", nhanh=False, prompt=None):
    """Khối chữ chèn vào lời của MỌI cổng đang bảo «gọi AskUserQuestion» — '' khi founder có mặt."""
    try:
        vang, ly_do, ct = dang_vang(cwd, transcript, nhanh=nhanh, prompt=prompt)
    except Exception:
        return ""
    if not vang:
        return ""
    return ("⛔ FOUNDER ĐANG VẮNG (%s) → chỗ nào ở trên bảo hỏi founder thì CẤM AskUserQuestion, "
            "CẤM hỏi bằng chữ trong CLI rồi đứng chờ (cổng afk_hoi_inbox_gate chặn). Làm thay:\n"
            "  gom câu thành danh sách 1. 2., lựa chọn mã 1A · 1B, đề xuất đặt đầu, gửi MỘT tin vào inbox:\n"
            % mo_ta_vang(ly_do, ct)
            + kenh_inbox(cwd)
            + "  rồi KHÔNG CHỜ: chọn phương án đề xuất, ghi `CHỐT: … — vì …`, chạy tiếp. "
              "Hết vắng khi founder gõ một lượt CLI thật hoặc nói «tao về rồi».")


def cach_hoi_anh(cwd="", nhanh=False, transcript="", prompt=None):
    """Cụm chữ «hỏi bằng gì» cho lời nhắc của cổng: anh ở máy → hộp hỏi; anh vắng → inbox dự án.

    `nhanh=True` (gọi từ UserPromptSubmit): anh VỪA gõ CLI nên chắc chắn mới hơn lời Telegram —
    chỉ xét cờ /afk, không hỏi DB (mỗi lần hỏi DB qua đường hầm ~2 giây, không được cộng vào mọi lượt gõ).
    P005: đi qua `dang_vang()`; thông báo nền đi qua UserPromptSubmit thì xét đủ (`prompt`)."""
    try:
        vang = dang_vang(cwd, transcript, nhanh=nhanh, prompt=prompt)[0]
    except Exception:
        vang = bool(dang_afk())
    if vang:
        if _goc_task_dev(cwd):
            return ("tin riêng anh qua `node scripts/task-dev.mjs tin --rieng --loai hoi` "
                    "(anh đang VẮNG khỏi CLI — cấm AskUserQuestion)")
        try:
            dong = (khai_inbox(cwd)[2].splitlines() or [""])[0].split("#")[0].strip()
        except Exception:
            dong = ""
        if dong:
            return "inbox founder qua `%s` (founder đang VẮNG — cấm AskUserQuestion)" % dong
        return ("inbox founder của dự án (không có thì ghi `~/.claude/afk/cau-hoi-<dự án>.md`) — "
                "founder đang VẮNG, cấm AskUserQuestion")
    return "`AskUserQuestion`"


def _ca_thu():
    """python3 afk_trang_thai.py --ca-thu — ca gốc vé d991d9a878: gõ CLI 19:37, Reply Telegram 19:41."""
    import calendar
    import tempfile
    vn = lambda hm: calendar.timegm(time.strptime("2026-10-14 " + hm, "%Y-%m-%d %H:%M")) - 7 * 3600
    tong, sai = 0, 0

    def ca(ten, dung):
        nonlocal tong, sai
        tong += 1
        sai += 0 if dung else 1
        print("%s %s" % ("PASS" if dung else "FAIL", ten))

    ca("1. CLI 19:37, Telegram 19:41 → VẮNG", vang_qua_telegram("/x", cli=vn("19:37"), tg=vn("19:41")) is not None)
    ca("2. Telegram 19:41, CLI 19:45 → có mặt", vang_qua_telegram("/x", cli=vn("19:45"), tg=vn("19:41")) is None)
    ca("3. chưa từng gõ CLI, có lời Telegram → VẮNG", vang_qua_telegram("/x", cli=0.0, tg=vn("19:41")) is not None)
    ca("4. dự án không có nguồn Telegram → có mặt (không đổi gì)", moc_telegram_cuoi(tempfile.gettempdir()) is None
       if os.environ.get("UNIV3_MOC_TELEGRAM_ANH") is None else True)
    os.environ["UNIV3_VANG_TELEGRAM_TAT"] = "1"
    ca("5. công tắc lùi UNIV3_VANG_TELEGRAM_TAT=1 → tắt", vang_qua_telegram("/x", cli=vn("19:37"), tg=vn("19:41")) is None)
    os.environ.pop("UNIV3_VANG_TELEGRAM_TAT")
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "A", "2026-10-14"))
        with open(os.path.join(d, "A", "2026-10-14", ".so.json"), "w", encoding="utf-8") as f:
            json.dump({"muc": {"L01": {"luc": str(vn("19:37"))}, "L02": {"luc": "hỏng"}}}, f)
        global GOC_SO_LENH
        cu, GOC_SO_LENH = GOC_SO_LENH, d
        try:
            ca("6. sổ lệnh: lấy lượt gõ mới nhất, bỏ dòng hỏng", luot_go_cli_cuoi() == vn("19:37"))
        finally:
            GOC_SO_LENH = cu
    print("\n%d/%d ca đúng" % (tong - sai, tong))
    return 1 if sai else 0


if __name__ == "__main__":
    import sys as _sys
    if "--ca-thu" in _sys.argv:
        _sys.exit(_ca_thu())
