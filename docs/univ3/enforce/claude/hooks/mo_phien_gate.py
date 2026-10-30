#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mo_phien_gate.py — MỞ PHIÊN: HOOK TỰ CHẠY (lớp 1) + LƯỚI AN TOÀN (lớp 2).

VÌ SAO CÓ TỆP NÀY (nguyên văn founder 07/09/2026):
  *"vá thì phải fix để session sau bố mày còn làm được. lần lồn nào cũng vá vá."*
  *"đây là fix tầng gốc hay fix vá kiểu ngu học từng cái? 1 by 1??"*
  *"đéo biết. làm sao để nó chắc chắn chạy là được."*

BỆNH ĐO ĐƯỢC (07/09/2026, không đoán):
  · founder gõ "đầu-ngày, thả watchdog:" -> main KHÔNG gọi `Skill(dau-ngay)` -> mốc
    `~/.claude/worker-counter/EtsyFulfillChichub.dau-ngay` không được ghi -> sổ `.seq` vẫn
    ghi ngày cũ, số worker không reset -> worker mang W151/W153/W155 thay vì W01…
  · cùng buổi sáng main bị chặn 6 lần bởi 5 cổng khác nhau, phải mở cửa thoát 1 lần.

CÁCH CŨ SAI Ở ĐÂU: mọi bản vá trước đều là CỔNG — chặn main rồi bắt main tự chạy. Cổng
là XÁC SUẤT theo hai nghĩa: (a) main phải đọc lời chặn và làm đúng, (b) cổng chỉ nổ khi
main tình cờ gọi đúng tool bị canh. Thêm cổng = thêm chỗ để quên.

CÁCH MỚI — HAI LỚP:
  LỚP 1 (đường chính, `SessionStart`): hook TỰ THỰC THI chuỗi mở phiên rồi nhét kết quả
      vào `additionalContext`. Main mở mắt ra là đã có sẵn số liệu — KHÔNG còn khâu nào
      để quên, vì không còn khâu nào giao cho main.
  LỚP 2 (lưới, `PreToolUse`): chỉ nổ khi lớp 1 KHÔNG để lại dấu (hook không chạy, máy
      chậm, lệnh lỗi). Lớp 1 trót lọt -> lớp 2 im hoàn toàn.

BA RÀNG BUỘC CỨNG:
  · RẺ: trần `TRAN_GIAY` giây cho cả chuỗi; quá hạn -> bỏ phần chậm, in cảnh báo, KHÔNG
    treo phiên founder. Mỗi lệnh con có timeout riêng.
  · IDEMPOTENT: gọi lại giữa phiên KHÔNG reset số (chỉ gọi `wseq dau-ngay` khi mốc ghi
    ngày KHÁC hôm nay theo giờ VN) và KHÔNG đẻ watchdog thứ hai (dùng `ensure`, không
    `start`).
  · FAIL-OPEN: mọi lỗi -> im lặng cho qua, không bao giờ làm chết phiên.

TỰ KIỂM: python3 mo_phien_gate.py --ca-thu
CHẠY TAY (lớp 2 chỉ dẫn đúng lệnh này): python3 mo_phien_gate.py chay
"""
import json
import os
import re
import subprocess
import sys
import time

HOOKS = os.environ.get("UNIV3_MOPHIEN_HOOKS") or os.path.dirname(os.path.abspath(__file__))
TMPDIR = os.environ.get("UNIV3_MOPHIEN_TMP", "/tmp/claude_hooks")
COUNTER = os.path.expanduser(os.environ.get("WSEQ_ROOT", "~/.claude/worker-counter"))
NHAT_KY = os.path.expanduser("~/.claude/logs/mo-phien.log")

TRAN_GIAY = float(os.environ.get("UNIV3_MOPHIEN_TRAN", "22"))   # trần cả chuỗi
TRAN_LENH = float(os.environ.get("UNIV3_MOPHIEN_TRAN_LENH", "14"))
# WHY 22/14 (15/09/2026): `bảng worker` đọc transcript của MỌI worker trong ngày, đo thật
# 9.4s trên máy này — trần cũ 6s làm nó LUÔN "hỏng"; mà nó TRỌNG YẾU nên dấu mở phiên luôn
# `xong=false` -> lớp 2 chặn sạch tool, và lệnh cứu chạy lại đúng chuỗi đó nên cũng không
# gỡ được. Đây là ca khoá cứng thật lúc 01:35 ngày 15/09.
MAX_CHAN = int(os.environ.get("UNIV3_MOPHIEN_MAX_CHAN", "8"))   # van an toàn chống kẹt cứng
VN_LECH = 7 * 3600                                              # Asia/Ho_Chi_Minh, không DST
GIAO_CA_GIO = int(os.environ.get("UNIV3_GIAO_CA_GIO", "6"))      # cùng ngưỡng `wseq.sh`

LENH_CUU = "python3 ~/.claude/universal-hooks/mo_phien_gate.py chay"
# Dấu MÁY ĐỌC ĐƯỢC của một mắt xích hỏng. WHY không bắt exception: `_chay` cố tình
# nuốt lỗi để không làm chết phiên -> nếu không có dấu này thì chuỗi "hỏng sạch" vẫn
# đếm là 0 lỗi và lớp 2 không bao giờ nổ (ca thử 07/09 bắt đúng lỗ này).
DAU_LOI = "\u27ea L\u1ed6I \u27eb"


# ── tiện ích ────────────────────────────────────────────────────────────────
def _ghi(dong: str):
    try:
        os.makedirs(os.path.dirname(NHAT_KY), exist_ok=True)
        with open(NHAT_KY, "a", encoding="utf-8") as fh:
            fh.write("%s\t%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dong))
    except OSError:
        pass


def hom_nay_vn() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(time.time() + VN_LECH))


def goc_repo(cwd: str) -> str:
    try:
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=3)
        t = (r.stdout or "").strip()
        if t:
            return t
    except Exception:
        pass
    return cwd


def ten_scope(cwd: str) -> str:
    return os.path.basename(goc_repo(cwd).rstrip("/")) or "khong-ten"


def _chay(cmd, cwd=None, han=None, env=None) -> str:
    """Chạy một lệnh, trả stdout+stderr đã cắt. Lỗi/timeout -> chuỗi báo lỗi, KHÔNG ném."""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=han or TRAN_LENH,
                           env=(dict(os.environ, **env) if env else None))
        ra = ((r.stdout or "") + (r.stderr or "")).strip()
        # Mã thoát khác 0 = mắt xích HỎNG. WHY phải xét: `subprocess.run` không ném khi
        # lệnh chạy nhưng trượt (script mất, script lỗi) -> ca thử 07/09 ép HOOKS trỏ sai
        # đường mà chuỗi vẫn báo "0 lỗi", lớp 2 không bao giờ nổ.
        if r.returncode != 0:
            return "%s mã thoát %d — %s" % (DAU_LOI, r.returncode, ra[:300])
        return ra
    except subprocess.TimeoutExpired:
        return "%s quá hạn %ss" % (DAU_LOI, han or TRAN_LENH)
    except Exception as e:
        return "%s %s" % (DAU_LOI, e)


def _cat(s: str, n: int) -> str:
    d = [x for x in (s or "").splitlines() if x.strip()]
    if len(d) <= n:
        return "\n".join(d)
    return "\n".join(d[:n] + ["… (còn %d dòng)" % (len(d) - n)])


# ── các mắt xích của chuỗi mở phiên ─────────────────────────────────────────
def buoc_ngay_lam_viec(cwd: str) -> tuple:
    """Mốc ngày làm việc — TỰ MỞ khi đã sang ngày mới và qua giờ giao ca (W305).

    LỊCH SỬ: 09/09/2026 gỡ nhánh tự mở theo đồng hồ (bệnh 4, 04/09 — qua nửa đêm về W01
    giữa lúc chốt ngày cũ; founder: *"tao đã bảo reset sang ngày mới đâu???"*), chỉ còn
    NHẮC gõ "đầu ngày". Hệ quả đo được 15/10/2026: không ai gõ thì mốc kẹt 12/10, số thợ
    leo tới W306. Anh Thành 07:20 15/10 (Task-15102026-04): *"reset cách đánh số worker
    khi sang ngày mới nhé. hiện không đổi nên chạy đến mấy trăm."* — lệnh mới THẮNG.
    NAY: hỏi `wseq.sh tu-mo` (MỘT cửa quyết, cùng luật với lần cấp số `next/adopt`):
    trước GIAO_CA_GIO (6h sáng VN) giữ ngày cũ, từ đó trở đi tự mở dãy mới.

    Chốt F3 vẫn giữ: chung cho TẤT CẢ dự án, CẤM cờ riêng theo tên dự án (AC24a).
    """
    scope = ten_scope(cwd)
    nay = hom_nay_vn()
    out = _chay(["bash", os.path.join(HOOKS, "wseq.sh"), "tu-mo"], cwd=cwd,
                env={"WSEQ_ROOT": COUNTER, "WSEQ_PROJECT": scope, "WSEQ_HOM_NAY_VN": nay})
    dong = (out.splitlines() or [""])[0].split()
    ma = dong[0] if dong else ""
    if ma == "TU-MO" and len(dong) >= 3:
        _ghi("TU-MO NGAY %s cho %s (ngay cu %s)" % (dong[1], scope, dong[2]))
        return ("ngày làm việc: đã tự mở ngày làm việc %s (ngày cũ %s) — dãy số về W01"
                % (dong[1], dong[2])) + _nhac_tat_tho_chot_ngay_cu(cwd), True
    if ma == "DA-MO" and len(dong) >= 2:
        cach = "máy tự mở" if dong[2:3] == ["tu-mo"] else "founder gõ đầu ngày"
        return ("ngày làm việc: đã mở %s (%s — không đụng, giữ nguyên dãy số)"
                % (dong[1], cach)), False
    if ma == "CHUA" and len(dong) >= 2:
        return ("ngày làm việc: còn %s — chưa tới %dh sáng nên giữ dãy số cũ; "
                "từ %dh lần cấp số đầu tiên tự mở dãy mới"
                % (dong[1], GIAO_CA_GIO, GIAO_CA_GIO)), False
    _ghi("TU-MO HONG cho %s: %r" % (scope, out[:200]))
    return ("⚠ không hỏi được sổ số để tự mở ngày (%s) — chạy tay: "
            "bash ~/.claude/universal-hooks/wseq.sh tu-mo" % out.replace("\n", " | ")[:160]), False


def buoc_watchdog(cwd: str) -> str:
    _chay(["bash", os.path.join(HOOKS, "worker-watchdog.sh"), "ensure"], cwd=cwd)
    st = _chay(["bash", os.path.join(HOOKS, "worker-watchdog.sh"), "status"], cwd=cwd)
    return "con canh worker: " + (st.splitlines() or ["%s không đọc được" % DAU_LOI])[0]


def buoc_bang_worker(cwd: str) -> str:
    return _cat(_chay(["bash", os.path.join(HOOKS, "bg-progress.sh")], cwd=cwd), 24)


def buoc_hang_cho(cwd: str) -> str:
    """Sổ vé + (P094 mục 6.2) MỒI HÀNH ĐỘNG cho vé thả lại được ngay.

    WHY: mở phiên sau khi tắt máy, bản cũ chỉ IN danh sách vé — điều phối phải tự dò brief
    nằm đâu rồi tự dựng lệnh. Dữ liệu đã có sẵn trong vé, nên in thẳng một dòng bấm được:
    mã vé + số + tệp chứa brief nguyên văn. KHÔNG tự thả hộ (thả là hành động, phải do điều
    phối quyết), KHÔNG đổi điều kiện lọc: dùng đúng `ve_tha_duoc` mà cổng Stop đang dùng.
    """
    # W08 17/10/2026 (Task-17102026-03) — RÀ THỢ CHẾT THEO PHIÊN CŨ TRƯỚC KHI IN HÀNG CHỜ.
    # Mở phiên sau khi máy đơ/tắt là lúc chắc chắn có thợ chết theo phiên cha (harness không
    # kịp ghi thông báo kết thúc). Bản cũ chỉ in sổ vé có sẵn -> W01/W03 sáng 17/10 không có
    # vé nên không hiện ở đâu cả. `worker_relapse.quet` dựng vé + sổ bàn giao ngay tại đây.
    hoi = []
    try:
        sys.path.insert(0, HOOKS)
        import worker_relapse as _WR
        hoi = _WR.quet(cwd) or []
    except Exception:
        hoi = []
    ra = _cat(_chay(["python3", os.path.join(HOOKS, "worker_queue.py"), "liet-ke"], cwd=cwd), 20)
    if hoi:
        ra = ("⚠ %d thợ chết giữa chừng theo phiên trước — đã đưa vào hàng chờ kèm sổ bàn giao: %s\n"
              % (len(hoi), " · ".join("%s «%s» dừng ở %s" % (v[0], str(v[1])[:40],
                                       ("%s%%" % v[2]) if v[2] is not None else "?")
                                       for v in hoi[:6]))) + (ra or "")
    try:
        sys.path.insert(0, HOOKS)
        import worker_queue as WQ
        san = WQ.ve_tha_duoc(cwd) or []
        if san:
            d = WQ.thu_muc(cwd)
            mo = ["", "➜ THẢ LẠI ĐƯỢC NGAY (%d vé) — brief nguyên văn nằm trong tệp vé:" % len(san)]
            for v in san[:8]:
                ma = str(v.get("ma") or "")
                tep = ""
                try:
                    tep = (WQ._tim_ve_theo_ma(cwd, ma) or ("", False))[0]
                except Exception:
                    tep = ""
                if not tep and ma:
                    import glob as _g
                    ds = sorted(_g.glob(os.path.join(d, "*-%s.json" % ma)))
                    tep = ds[0] if ds else ""
                mo.append("   LÀM NGAY: thả lại vé %s — %s «%s»%s"
                          % (ma, v.get("so") or "W??", WQ.ten_ve(v)[:60],
                             (" — brief: %s" % tep) if tep else ""))
            ra = (ra or "") + "\n" + "\n".join(mo)
    except Exception:
        pass
    return ra


def buoc_git(cwd: str) -> str:
    g = goc_repo(cwd)
    st = _cat(_chay(["git", "-C", g, "status", "--short"], han=4), 12)
    lg = _cat(_chay(["git", "-C", g, "log", "--oneline", "-5"], han=4), 5)
    br = _chay(["git", "-C", g, "rev-parse", "--abbrev-ref", "HEAD"], han=3)
    return "nhánh %s\n-- git status --short --\n%s\n-- 5 commit gần nhất --\n%s" % (br, st or "(sạch)", lg)


def buoc_tunnel(cwd: str) -> str:
    """Kiểm cầu DB. Chết mà dự án có `.claude/ensure-tunnel.sh` -> tự dựng lại (đã có luật
    `auto-start-tunnel`: tunnel tắt thì TỰ bật, KHÔNG hỏi founder)."""
    def song() -> bool:
        try:
            return subprocess.call(["nc", "-z", "-G", "2", "localhost", "5432"],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, timeout=4) == 0
        except Exception:
            return False
    if song():
        return "cầu DB localhost:5432: SỐNG"
    sh = os.path.join(goc_repo(cwd), ".claude", "ensure-tunnel.sh")
    if os.path.exists(sh):
        _chay(["bash", sh], cwd=cwd, han=8)
        return ("cầu DB localhost:5432: %s (đã tự chạy ensure-tunnel.sh)"
                % ("SỐNG" if song() else "VẪN CHẾT"))
    return "cầu DB localhost:5432: CHẾT — chạy `npm run tunnel`"


RE_TREO = re.compile(r"^\s*[-*]?\s*(\[ \]|\[~\]|🔲|⏳|❌|TODO|CHƯA|ĐANG)", re.I)


def buoc_tai_lieu(cwd: str) -> str:
    """GOAL + TODO: CHỈ trích mục còn treo. WHY không nhét cả file: mỗi ký tự ở đây ăn
    context của MỌI phiên (luật Rule Budget trong SPINE)."""
    g = goc_repo(cwd)
    ra = []
    for ten, tran in (("docs/GOAL.md", 12), ("docs/TODO.md", 14)):
        p = os.path.join(g, ten)
        if not os.path.exists(p):
            continue
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                dong = fh.read().splitlines()
        except Exception:
            continue
        treo = [d.strip()[:150] for d in dong if RE_TREO.match(d)]
        ra.append("-- %s (%d dòng, %d mục còn treo) --\n%s"
                  % (ten, len(dong), len(treo),
                     "\n".join(treo[:tran]) or "(không có mục nào còn treo)"))
    return "\n".join(ra) or "(dự án không có docs/GOAL.md hay docs/TODO.md)"


# (tên, hàm, TRỌNG YẾU?) — TRỌNG YẾU = hỏng cái này thì coi như lớp 1 THẤT BẠI, lớp 2 nổ.
# Vì sao chỉ ba cái này trọng yếu: chúng quyết định SỐ worker đúng, AI đang chạy, VIỆC nào
# còn xếp hàng — thiếu là main điều phối mù. git/cầu DB/GOAL hỏng thì chỉ mất thông tin
# tham khảo, chặn sạch tool vì mấy cái đó là biến lưới an toàn thành cổng nhiễu.
CHUOI = [
    ("ngày làm việc + số worker", buoc_ngay_lam_viec, True),
    ("con canh worker",           buoc_watchdog,      True),
    ("bảng worker",               buoc_bang_worker,   True),
    ("hàng chờ",                  buoc_hang_cho,      False),
    ("git",                       buoc_git,           False),
    ("cầu DB",                    buoc_tunnel,        False),
    ("GOAL + TODO còn treo",      buoc_tai_lieu,      False),
]
TRONG_YEU = {t for t, _f, q in CHUOI if q}


def chay_chuoi(cwd: str) -> tuple:
    """Chạy cả chuỗi trong trần thời gian. Trả (văn bản, danh sách lỗi, giây)."""
    t0 = time.time()
    khoi, loi = [], []
    for ten, fn, _qt in CHUOI:
        con = TRAN_GIAY - (time.time() - t0)
        if con <= 0.5:
            loi.append("%s: BỎ QUA (hết trần %.0fs)" % (ten, TRAN_GIAY))
            khoi.append("### %s\n(bỏ qua — hết trần thời gian mở phiên)" % ten)
            continue
        try:
            r = fn(cwd)
            if isinstance(r, tuple):
                r = r[0]
        except Exception as e:
            r = "%s %s" % (DAU_LOI, e)
        if DAU_LOI in str(r):
            loi.append("%s: hỏng" % ten)
        khoi.append("### %s\n%s" % (ten, r))
    return "\n\n".join(khoi), loi, time.time() - t0


# ── dấu "đã chạy xong chuỗi mở phiên" ───────────────────────────────────────
def duong_dau(sid: str) -> str:
    return os.path.join(TMPDIR, "%s_mo_phien.json" % (sid or "nosid"))


def ghi_dau(sid: str, cwd: str, loi: list, giay: float, ep_xong: bool = False):
    """Ghi dấu "đã chạy xong chuỗi mở phiên".

    `xong` KHÔNG đòi 100% mắt xích chạy được — một mắt xích chậm (git ở repo to, cầu DB
    chết) mà bắt lớp 2 chặn sạch tool là biến lưới an toàn thành cổng nhiễu, đúng thứ
    founder đang chửi. Ngưỡng: chỉ HỎNG MẮT XÍCH TRỌNG YẾU (xem `TRONG_YEU`) mới coi là
    lớp 1 thất bại -> lớp 2 nổ.
    """
    # `ep_xong` = lệnh cứu chạy TAY. Cổng sinh ra để ÉP chuỗi chạy và ÉP main đọc, không
    # phải để đòi mọi mắt xích xanh. Không có cửa này thì mắt xích trọng yếu hỏng =
    # khoá cứng: chạy lệnh cứu bao nhiêu lần cũng vẫn bị chặn (ca 15/09/2026).
    xong = ep_xong or not any(l.split(":")[0] in TRONG_YEU for l in loi)
    try:
        os.makedirs(TMPDIR, exist_ok=True)
        with open(duong_dau(sid), "w", encoding="utf-8") as fh:
            json.dump({"xong": xong, "luc": time.time(), "cwd": cwd,
                       "loi": loi, "giay": round(giay, 2)}, fh, ensure_ascii=False)
    except OSError:
        pass


def da_chay(sid: str) -> bool:
    try:
        with open(duong_dau(sid), encoding="utf-8") as fh:
            return bool(json.load(fh).get("xong"))
    except Exception:
        return False



# ── ÉP `Skill(chot-ngay)` — phần DUY NHẤT còn giữ của "mảng 1" ───────────────
# VÌ SAO ĐẦU-NGÀY KHÔNG CÒN CẦN CỔNG mà CHỐT-NGÀY thì CÒN:
#   · "đầu ngày" = reset số + dựng con canh -> LỚP 1 tự làm được, không cần main.
#   · "chốt ngày" = chờ mọi worker xong + gom báo cáo PDF + GỬI TELEGRAM cho cả nhà.
#     Hook KHÔNG được tự gửi tin ra ngoài (luật Action-Safety: gửi mail/Slack/Telegram là
#     hành động khó đảo ngược, phải có người quyết). Nên chốt-ngày vẫn phải do main gọi
#     skill -> vẫn cần cổng ép.
import unicodedata as _ud


def _bo_dau(t: str) -> str:
    t = (t or "").lower().replace("đ", "d")
    t = _ud.normalize("NFD", t)
    return "".join(c for c in t if _ud.category(c) != "Mn")


RE_CHOT_NGAY = re.compile(r"(?:^|[^a-z0-9])(chot[ -]?ngay|/eod|/chot-ngay|end of day)(?:[^a-z0-9]|$)")
# Câu KỂ LẠI, không phải câu ra lệnh -> không chặn.
RE_KE_CHUYEN = re.compile(
    r"(hom qua|hom truoc|luc nay|khi nao|ve viec|noi ve|da chot ngay|chot ngay xong|"
    r"sau khi chot ngay|truoc khi chot ngay|neu chot ngay|chot ngay la gi|lenh chot ngay)")
SKILL_CHOT = {"chot-ngay", "eod"}

# ── P085 mảng B — BỘ NHẬN DIỆN LỆNH ĐẦU-NGÀY (đối xứng với chốt-ngày) ───────────────
# Sáng 09/09/2026 founder gõ "việc hôm nay, skill đầu ngày: …" lúc 09:18 mà dãy số worker
# KHÔNG reset: `SessionStart` không bắn lại (phiên mở 23:08 hôm trước), còn `UserPromptSubmit`
# thì chỉ biết chốt-ngày, không biết đầu-ngày. Ba worker cùng buổi mang W130 · W131 · W01.
#
# ☠️ VÌ SAO PHỦ ĐỊNH PHẢI NEO VÀO TỪ KHOÁ, CẤM QUÉT TOÀN CÂU: prompt gốc 09:18 (589 ký tự)
# chứa 5 trong 7 từ chặn — `?`, `nếu` ×4, `không`, `chưa`, `hôm qua` — nằm ở THÂN câu.
# Quét toàn câu là bộ nhận diện KHÔNG BẮN cho chính ca đẻ ra luật này.
RE_DAU_NGAY = re.compile(r"(?:^|[^a-z0-9])(dau[ -]?ngay|/dau-ngay|/sod)(?:[^a-z0-9]|$)")
RE_SOD_LENH = re.compile(r"^\s*sod(?:[^a-z0-9]|$)")     # `sod` trần chỉ tính khi ở ĐẦU câu
PHU_DINH_DN = ("chua", "mai", "hom qua", "hom truoc", "se ", "neu", "khong")
CUA_SO_PHU_DINH = 20        # ký tự mỗi bên quanh từ khoá


def can_dau_ngay(prompt: str) -> bool:
    """Câu founder có phải LỆNH mở ngày làm việc mới không (bỏ dấu, không phân biệt hoa thường)."""
    t = _bo_dau(prompt)
    m = RE_DAU_NGAY.search(t) or RE_SOD_LENH.search(t)
    if not m:
        return False
    # (2) VỊ TRÍ, không phải "nghĩa ra lệnh" — đúng cách chốt-ngày đang phân biệt lệnh với kể.
    if not (m.start() <= 80 or len(t) <= 200):
        return False
    # (3) phủ định NEO quanh từ khoá: "chưa đầu ngày", "mai đầu ngày", "đầu ngày hôm qua".
    a = max(0, m.start() - CUA_SO_PHU_DINH)
    b = min(len(t), m.end() + CUA_SO_PHU_DINH)
    quanh = t[a:b]
    return not any(x in quanh for x in PHU_DINH_DN)



def _duong_co_chot(sid: str) -> str:
    return os.path.join(TMPDIR, "%s_chot_ngay_cho" % (sid or "nosid"))


def can_chot_ngay(prompt: str) -> bool:
    """Câu founder có phải LỆNH chốt ngày không (bỏ dấu, không phân biệt hoa thường)."""
    t = _bo_dau(prompt)
    m = RE_CHOT_NGAY.search(t)
    if not m:
        return False
    if RE_KE_CHUYEN.search(t):
        return False
    # Lệnh thật nằm ở ĐẦU câu hoặc câu ngắn; nằm giữa một đoạn dài = đang kể.
    return m.start() <= 80 or len(t) <= 200



def _moc_dau_ngay(cwd: str):
    """(ngày mốc, epoch của mốc). Không có mốc -> ("", 0.0)."""
    f = os.path.join(COUNTER, "%s.dau-ngay" % ten_scope(cwd))
    try:
        with open(f, encoding="utf-8") as fh:
            d1 = (fh.readline() or "").strip()
    except OSError:
        return "", 0.0
    p = d1.split()
    if not p:
        return "", 0.0
    try:
        ep = time.mktime(time.strptime(" ".join(p[:2]), "%Y-%m-%d %H:%M:%S")) if len(p) > 1 else 0.0
    except ValueError:
        ep = 0.0
    return p[0], ep


def da_chot_ngay_sau(cwd: str, moc_epoch: float) -> bool:
    """Có dấu CHỐT NGÀY của CHÍNH dự án này, SAU thời điểm mở ngày, và là vế SKILL CHẠY THẬT.

    Hai biến thể trong nhật ký, mỗi cái sai một chiều: `dat co ep Skill(chot-ngay)` ghi
    NGAY LÚC founder gõ (dương tính giả — gõ rồi đổi ý), `da goi dung skill, go co` ghi
    KHI SKILL CHẠY THẬT. Lấy vế thứ hai. Không thấy dòng nào -> KHÔNG suy "chưa chốt":
    số 0 không làm bằng chứng phủ định, người gọi phải HỎI.
    """
    dich = os.path.abspath(cwd or os.getcwd())
    try:
        with open(NHAT_KY, encoding="utf-8", errors="replace") as fh:
            cac = fh.readlines()
    except OSError:
        return False
    for d in reversed(cac[-4000:]):
        if "CHOT-NGAY" not in d or "da goi dung skill" not in d:
            continue
        if ("cwd=%s" % dich) not in d:
            continue
        try:
            t = time.mktime(time.strptime(d.split("\t")[0].strip(), "%Y-%m-%d %H:%M:%S"))
        except Exception:
            continue
        if t >= moc_epoch:
            return True
    return False


def _nhac_tat_tho_chot_ngay_cu(cwd: str) -> str:
    """P121 (R1): đầu-ngày = BỎ báo cáo ngày cũ -> thợ chốt ngày hôm trước còn sống phải bị TaskStop.

    Cổng `chot_ngay_gate` đã chặn tất định việc nó gửi báo cáo ngày cũ (mốc `.dau-ngay` mới
    hơn ngày báo cáo); câu này bảo main tắt hẳn cho khỏi treo danh sách."""
    try:
        import chot_ngay_gate as CG
        ds = CG.tho_chot_ngay_dang_song(cwd)
    except Exception:
        return ""
    if not ds:
        return ""
    return ("\n⛔ CÒN THỢ CHỐT NGÀY CỦA NGÀY CŨ ĐANG CHỜ: %s.\n"
            "   Founder vừa mở ngày mới = bỏ báo cáo cũ. main PHẢI `TaskStop` các thợ này NGAY "
            "(cổng đã chặn chúng gửi báo cáo ngày cũ, nhưng đừng để treo)."
            % ", ".join("%s «%s» (id %s)" % (d["so"], d["mo_ta"], d["id"][:12]) for d in ds))


def xu_ly_dau_ngay(cwd: str) -> str:
    """Cây quyết định khi trúng lệnh đầu-ngày (P085 §7B.5). Trả về câu in cho founder."""
    scope = ten_scope(cwd)
    nay = hom_nay_vn()
    moc, moc_ep = _moc_dau_ngay(cwd)
    if moc != nay:
        out = _chay(["bash", os.path.join(HOOKS, "wseq.sh"), "dau-ngay"], cwd=cwd,
                    env={"WSEQ_ROOT": COUNTER, "WSEQ_PROJECT": scope})
        if DAU_LOI in out:
            return "⚠ KHÔNG mở được ngày mới: %s" % out.replace("\n", " | ")[:200]
        _ghi("DAU-NGAY cwd=%s MO NGAY %s (moc cu %r)" % (os.path.abspath(cwd), nay, moc))
        return out.strip() + _nhac_tat_tho_chot_ngay_cu(cwd)
    if da_chot_ngay_sau(cwd, moc_ep):
        out = _chay(["bash", os.path.join(HOOKS, "wseq.sh"), "dau-ngay"], cwd=cwd,
                    env={"WSEQ_ROOT": COUNTER, "WSEQ_PROJECT": scope})
        _ghi("DAU-NGAY cwd=%s MO DAY MOI (phien 2+) sau chot ngay" % os.path.abspath(cwd))
        return out.strip() + _nhac_tat_tho_chot_ngay_cu(cwd)
    # W305: ngày hôm nay do MÁY tự mở, đây là lần gõ ĐẦU TIÊN của founder -> dãy đang chạy
    # CHÍNH LÀ dãy của hôm nay, không mở phiên 2 (mở là đè W01… vừa cấp). Không hỏi lại.
    if _da_tu_mo_hom_nay(cwd):
        _ghi("DAU-NGAY cwd=%s DA TU MO %s — giu nguyen day" % (os.path.abspath(cwd), moc))
        return ("ngày làm việc %s đã được máy tự mở lúc %s — giữ nguyên dãy số đang chạy.\n"
                "   Thật sự muốn mở phiên 2 trong ngày: bash ~/.claude/universal-hooks/wseq.sh dau-ngay"
                % (moc, moc_dau_ngay_gio_cua(cwd) or "?"))
    # Gõ lần hai trong ngày mà CHƯA có dấu chốt ngày -> HỎI LẠI, cấm tự xử (chốt C2).
    _ghi("DAU-NGAY cwd=%s HOI LAI (da mo %s, chua thay dau chot ngay)"
         % (os.path.abspath(cwd), moc))
    return ("⚠ ĐÃ MỞ NGÀY LÀM VIỆC HÔM NAY LÚC %s mà CHƯA thấy dấu chốt ngày cho dự án này.\n"
            "   KHÔNG tự reset. Hỏi lại founder bằng AskUserQuestion, đúng hai lựa chọn:\n"
            "     (a) mở dãy mới, coi như phiên 2 trong ngày\n"
            "     (b) giữ nguyên dãy — vừa gõ nhầm\n"
            "   Founder chọn (a) thì chạy: bash ~/.claude/universal-hooks/wseq.sh dau-ngay"
            % (moc_dau_ngay_gio_cua(cwd) or "?"))


def _da_tu_mo_hom_nay(cwd: str) -> bool:
    """Mốc hiện hành do `wseq.sh tu_mo_ngay_moi` ghi (dòng 1 tệp `.tu-mo` khớp dòng 1 `.dau-ngay`)."""
    s = ten_scope(cwd)
    try:
        with open(os.path.join(COUNTER, "%s.dau-ngay" % s), encoding="utf-8") as fh:
            a = (fh.readline() or "").strip()
        with open(os.path.join(COUNTER, "%s.tu-mo" % s), encoding="utf-8") as fh:
            b = (fh.readline() or "").strip()
    except OSError:
        return False
    return bool(a) and a == b


def moc_dau_ngay_gio_cua(cwd: str) -> str:
    f = os.path.join(COUNTER, "%s.dau-ngay" % ten_scope(cwd))
    try:
        with open(f, encoding="utf-8") as fh:
            p = (fh.readline() or "").split()
        return p[1] if len(p) > 1 else ""
    except OSError:
        return ""


def nhanh_prompt(data: dict) -> int:
    sid = str(data.get("session_id") or "")
    if not sid:
        return 0
    if can_chot_ngay(str(data.get("prompt") or "")):
        try:
            os.makedirs(TMPDIR, exist_ok=True)
            open(_duong_co_chot(sid), "w").write(str(time.time()))
        except OSError:
            pass
        # `cwd=` là BẮT BUỘC: máy này chạy ≥5 dự án chung một tệp nhật ký, dòng chốt-ngày
        # cũ chỉ có `sid=` nên câu hỏi "đã chốt ngày CHO DỰ ÁN NÀY chưa" không trả lời được.
        _ghi("CHOT-NGAY sid=%s cwd=%s — dat co ep Skill(chot-ngay)"
             % (sid[:8], str(data.get("cwd") or os.getcwd())))
        return 0
    # CỬA MỞ NGÀY LÀM VIỆC DUY NHẤT: founder GÕ LỆNH (chốt C1). Không phụ thuộc phiên mở
    # lúc nào — ca 09/09/2026 phiên mở 23:08 hôm trước, `SessionStart` không bắn lại,
    # founder gõ lúc 09:18 mà dãy số vẫn là của hôm qua.
    if can_dau_ngay(str(data.get("prompt") or "")):
        cau = xu_ly_dau_ngay(str(data.get("cwd") or os.getcwd()))
        if cau:
            json.dump({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                              "additionalContext": cau}},
                      sys.stdout, ensure_ascii=False)
    return 0


def chan_chot_ngay(data: dict) -> bool:
    """Còn cờ chốt-ngày mà main gọi tool khác -> DENY. Gọi đúng skill -> gỡ cờ, cho qua."""
    # Worker con chung session_id với main nên thấy cùng cờ; W45 (worker chốt ngày) bị
    # chặn oan nhiều lượt 06/10/2026. Cờ chỉ ép MAIN gọi Skill, worker luôn cho qua.
    if data.get("agent_id"):
        return False
    sid = str(data.get("session_id") or "")
    if not sid or not os.path.exists(_duong_co_chot(sid)):
        return False
    ten = str(data.get("tool_name") or "")
    ti = data.get("tool_input") or {}
    if ten == "Skill" and _bo_dau(str(ti.get("skill") or "")).strip("/") in SKILL_CHOT:
        try:
            os.remove(_duong_co_chot(sid))
        except OSError:
            pass
        _ghi("CHOT-NGAY sid=%s cwd=%s — da goi dung skill, go co"
             % (sid[:8], str(data.get("cwd") or os.getcwd())))
        return False
    dem = os.path.join(TMPDIR, "%s_chot_ngay_chan" % sid)
    try:
        n = int(open(dem).read().strip()) + 1
    except Exception:
        n = 1
    try:
        open(dem, "w").write(str(n))
    except OSError:
        pass
    if n > MAX_CHAN:
        try:
            os.remove(_duong_co_chot(sid))
        except OSError:
            pass
        _ghi("CHOT-NGAY sid=%s VAN AN TOAN — chan %d lan, tha ra" % (sid[:8], n))
        return False
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason":
            "⛔ FOUNDER GÕ LỆNH CHỐT NGÀY MÀ CHƯA GỌI `Skill(chot-ngay)`.\n"
            "Chốt ngày KHÔNG phải mấy lệnh lẻ: nó chờ mọi worker + hàng chờ sạch, gom báo "
            "cáo PDF theo nhóm, rồi GỬI nhóm Telegram Hệ thống. Làm tay là thiếu bước.\n"
            "LÀM: gọi `Skill(chot-ngay)` trước, xong rồi muốn làm gì thì làm."}},
        sys.stdout, ensure_ascii=False)
    return True


# ── LỚP 1 — SessionStart ────────────────────────────────────────────────────
def nhanh_session_start(data: dict) -> int:
    cwd = str(data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    sid = str(data.get("session_id") or "")
    van, loi, giay = chay_chuoi(cwd)
    ghi_dau(sid, cwd, loi, giay)
    _ghi("LOP1 sid=%s cwd=%s %.2fs loi=%d" % (sid[:8], ten_scope(cwd), giay, len(loi)))
    dau = ("## Mở phiên — hook ĐÃ TỰ CHẠY, số liệu dưới đây là THẬT (%.1fs)\n"
           "Đọc rồi trả lời thẳng; KHÔNG chạy lại mấy lệnh này chỉ để \"cho chắc\".\n\n"
           % giay)
    if loi:
        dau += "⚠ mắt xích lỗi/bỏ qua: %s\n\n" % "; ".join(loi)
    json.dump({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                      "additionalContext": dau + van}},
              sys.stdout, ensure_ascii=False)
    return 0


# ── LỚP 2 — PreToolUse (chỉ nổ khi lớp 1 không để lại dấu) ──────────────────
def nhanh_pre_tool(data: dict) -> int:
    if data.get("agent_id"):
        return 0                                  # worker con, không phải main
    sid = str(data.get("session_id") or "")
    if not sid:
        return 0                                  # không định danh được -> fail-open
    if da_chay(sid):
        return 0                                  # lớp 1 trót lọt -> IM HOÀN TOÀN

    # Lệnh cứu phải luôn lọt, nếu không là kẹt cứng.
    if str(data.get("tool_name") or "") == "Bash":
        lenh = str((data.get("tool_input") or {}).get("command") or "")
        if "mo_phien_gate.py" in lenh:
            return 0

    dem = os.path.join(TMPDIR, "%s_mo_phien_chan" % sid)
    try:
        n = int(open(dem).read().strip()) + 1
    except Exception:
        n = 1
    try:
        os.makedirs(TMPDIR, exist_ok=True)
        with open(dem, "w") as fh:
            fh.write(str(n))
    except Exception:
        pass
    if n > MAX_CHAN:
        _ghi("LOP2 sid=%s VAN AN TOAN — da chan %d lan, tha ra de khong ket cung" % (sid[:8], n))
        return 0                                  # van an toàn: thà lọt còn hơn kẹt cứng

    _ghi("LOP2 sid=%s CHAN lan=%d tool=%s" % (sid[:8], n, data.get("tool_name")))
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason":
            "⛔ CHUỖI MỞ PHIÊN CHƯA CHẠY — hook `SessionStart` không để lại dấu "
            "(máy chậm / lệnh lỗi / hook chưa nạp).\n"
            "CHẠY ĐÚNG MỘT LỆNH NÀY rồi làm tiếp (nó in luôn bảng worker, hàng chờ, git, "
            "cầu DB, GOAL/TODO còn treo — không phải chạy thêm gì):\n"
            "    " + LENH_CUU + "\n"
            "Chưa chạy xong thì mọi tool khác đều bị chặn."}},
        sys.stdout, ensure_ascii=False)
    return 0


# ── CLI ─────────────────────────────────────────────────────────────────────
def cli_chay() -> int:
    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    sid = os.environ.get("CLAUDE_SESSION_ID") or ""
    van, loi, giay = chay_chuoi(cwd)
    print("## Mở phiên (chạy tay) — %.1fs" % giay)
    if loi:
        print("⚠ mắt xích lỗi/bỏ qua: %s" % "; ".join(loi))
    print(van)
    if sid:
        ghi_dau(sid, cwd, loi, giay, ep_xong=True)
        print("\n(đã ghi dấu mở phiên cho phiên %s%s)"
              % (sid[:8], " — CÓ mắt xích hỏng, xem dòng ⚠ ở trên" if loi else ""))
    else:
        # Không biết session_id -> ghi dấu cho MỌI phiên đang bị chặn, nếu không main
        # chạy đúng lệnh được bảo mà vẫn bị chặn tiếp = kẹt cứng.
        n = 0
        try:
            for t in os.listdir(TMPDIR):
                if t.endswith("_mo_phien_chan"):
                    ghi_dau(t[:-len("_mo_phien_chan")], cwd, loi, giay, ep_xong=True)
                    n += 1
        except OSError:
            pass
        print("\n(đã ghi dấu mở phiên cho %d phiên đang bị chặn)" % n)
    return 0


def _ca_thu() -> int:
    """Tự kiểm — 7 ca, in PASS/FAIL, không đụng sổ thật (dùng thư mục tạm).

    W07 22/09/2026 — thân hàm dựng hộp cát bằng `mkdtemp` mà KHÔNG xoá: đếm được 13
    thư mục `mophien-cathu-*` mồ côi. Bọc `finally` để ca trượt hay văng lỗi vẫn dọn,
    và chỉ dọn ĐÍCH DANH hộp lượt này tạo (không quét theo khuôn tên).
    """
    import shutil
    import tempfile
    td = tempfile.mkdtemp(prefix="mophien-cathu-")
    try:
        return _ca_thu_than(td)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def _ca_thu_than(td) -> int:
    ok = True
    global TMPDIR
    cu = TMPDIR
    TMPDIR = td
    # ca 1: chưa có dấu -> LỚP 2 CHẶN
    r = _bat_stdout(nhanh_pre_tool, {"hook_event_name": "PreToolUse", "session_id": "ca1",
                                     "tool_name": "Read", "tool_input": {}})
    c1 = '"deny"' in r
    print("ca1 chưa có dấu -> lớp 2 chặn: %s" % ("PASS" if c1 else "FAIL " + r[:80])); ok &= c1
    # ca 2: có dấu -> lớp 2 im
    ghi_dau("ca2", "/tmp", [], 0.1)
    r = _bat_stdout(nhanh_pre_tool, {"hook_event_name": "PreToolUse", "session_id": "ca2",
                                     "tool_name": "Read", "tool_input": {}})
    c2 = r.strip() == ""
    print("ca2 có dấu -> lớp 2 im: %s" % ("PASS" if c2 else "FAIL " + r[:80])); ok &= c2
    # ca 3: lệnh cứu luôn lọt
    r = _bat_stdout(nhanh_pre_tool, {"hook_event_name": "PreToolUse", "session_id": "ca3",
                                     "tool_name": "Bash",
                                     "tool_input": {"command": LENH_CUU}})
    c3 = r.strip() == ""
    print("ca3 lệnh cứu lọt: %s" % ("PASS" if c3 else "FAIL " + r[:80])); ok &= c3
    # ca 4: worker con (agent_id) -> không bao giờ chặn
    r = _bat_stdout(nhanh_pre_tool, {"hook_event_name": "PreToolUse", "session_id": "ca4",
                                     "agent_id": "a123", "tool_name": "Read", "tool_input": {}})
    c4 = r.strip() == ""
    print("ca4 worker con không bị chặn: %s" % ("PASS" if c4 else "FAIL " + r[:80])); ok &= c4
    # ca 6+7: cờ chốt ngày — worker (agent_id) không bị chặn, main chưa gọi Skill vẫn chặn
    open(_duong_co_chot("ca6"), "w").write("1")
    r = _bat_stdout(chan_chot_ngay, {"session_id": "ca6", "agent_id": "a456",
                                     "tool_name": "Bash", "tool_input": {"command": "ls"}})
    c6 = r.strip() == ""
    print("ca6 chốt ngày: worker không bị chặn: %s" % ("PASS" if c6 else "FAIL " + r[:80])); ok &= c6
    r = _bat_stdout(chan_chot_ngay, {"session_id": "ca6",
                                     "tool_name": "Bash", "tool_input": {"command": "ls"}})
    c7 = '"deny"' in r
    print("ca7 chốt ngày: main chưa gọi Skill vẫn chặn: %s" % ("PASS" if c7 else "FAIL " + r[:80])); ok &= c7
    # ca 5: van an toàn sau MAX_CHAN lần
    for _ in range(MAX_CHAN + 1):
        r = _bat_stdout(nhanh_pre_tool, {"hook_event_name": "PreToolUse", "session_id": "ca5",
                                         "tool_name": "Read", "tool_input": {}})
    c5 = r.strip() == ""
    print("ca5 van an toàn sau %d lần: %s" % (MAX_CHAN, "PASS" if c5 else "FAIL " + r[:80])); ok &= c5
    TMPDIR = cu
    print("\n%s" % ("TẤT CẢ PASS" if ok else "CÓ CA FAIL"))
    return 0 if ok else 1


def _bat_stdout(fn, data):
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(data)
    return buf.getvalue()


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("chay", "--chay"):
        return cli_chay()
    if len(sys.argv) > 1 and sys.argv[1] == "--ca-thu":
        return _ca_thu()
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    ev = str(data.get("hook_event_name") or "")
    if ev == "SessionStart":
        return nhanh_session_start(data)
    if ev == "UserPromptSubmit":
        return nhanh_prompt(data)
    if ev == "PreToolUse":
        if chan_chot_ngay(data):
            return 0
        return nhanh_pre_tool(data)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)                                # fail-open tuyệt đối
