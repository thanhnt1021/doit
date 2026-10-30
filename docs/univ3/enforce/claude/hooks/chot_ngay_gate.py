#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chot_ngay_gate.py — CHẶN gửi BÁO CÁO NGÀY khi việc của ngày còn nợ.

VÌ SAO CÓ TỆP NÀY (ca thật 03/09/2026 — báo cáo ngày gửi NON HAI LẦN trong một ngày):
  · Lần 1 (W54): gửi lúc W55 còn đang chạy. Founder mắng, phải xoá tin.
  · Lần 2 (W57): chờ đúng — W55 xong 22:52, W56 xong 23:00, W59 xong 23:13 — kết luận
    sạch rồi gửi lúc 23:16 (`message_id 1869`). Nhưng **W60 và W61 sinh lúc 23:10–23:11**
    từ chính phát hiện của W56. W57 tự biện hộ trong báo cáo: *"W60/W61 chỉ khởi động
    23:10–23:11 nên nằm ở mục D/F, không tính vào ngày"* → SAI: việc sinh trong ngày là
    việc của ngày. Và main còn nói một câu sai logic: *"W60/W61 chưa được thả — hàng chờ
    trống, không worker nào sống, nên nó viết báo cáo đúng theo brief"*. **Việc chưa có vé
    cũng là việc còn nợ**; "bảng trống" chỉ nghĩa là chưa ai ghi vé.

BA LỖ CỦA ĐỊNH NGHĨA "XONG" CŨ (skill `chot-ngay` Bước 1 bản trước):
  1. Ảnh chụp MỘT thời điểm — kiểm 23:00 rồi gửi 23:16, giữa hai mốc worker mới sinh ra.
  2. Không tính việc CHƯA CÓ VÉ — worker xong để lại việc (`ĐỂ LẠI:` trong báo cáo cuối),
     main chưa kịp đẻ vé → bảng trống nhưng việc còn nợ.
  3. Cho worker TỰ PHÁN "coi như đã sạch" → nó tự biện hộ được. Markdown là xác suất,
     cổng này là tất định.

CHẶN CÁI GÌ: đúng một loại lệnh — gửi Telegram **tài liệu/tin báo cáo ngày** vào nhóm
"Hệ thống Fulfill TheChic" (`-5449057497`). Nhận diện = có `sendDocument`/`sendMessage`
+ có chat id đó + có `BAO-CAO-NGAY` hoặc tên báo cáo ngày trong lệnh. Mọi lệnh khác KHÔNG
bị soi (xoá tin `deleteMessage`, gửi nhóm khác, gửi tài liệu khác đều đi thẳng).

CHẶN KHI còn thoả MỘT trong ba:
  (1) còn worker SỐNG THẬT trong dự án (trừ chính con đang gửi);
  (2) hàng chờ `~/.claude/worker-queue/<dự án>/` còn vé chưa chạy (vé diện *chờ founder
      quyết* KHÔNG chặn — thả ra worker cũng ngồi đợi; nhưng cổng nhắc phải nêu ở mục E);
  (3) còn dòng `ĐỂ LẠI:` trong `/tmp/w*-bao-cao*.md` của ngày mà chưa có vé tương ứng.

NGUỒN ĐẾM — DÙNG LẠI, KHÔNG TỰ ĐẾM KIỂU KHÁC (hai nguồn lệch nhau là sinh bệnh mới):
  · worker sống  → `worker_queue.agent_song()` (chính nó gọi `worker_board.gom_theo_agent`
    + `worker_board.ket_thuc_cua` + hằng `SONG_PHUT` — đúng bộ mà `bg-progress.sh` in ra).
    Trả `None` = KHÔNG ĐO ĐƯỢC → bỏ qua kiểm (1), không chặn oan.
  · hàng chờ     → `worker_queue.doc()` + `worker_queue.cho_founder()`.
  · dòng ĐỂ LẠI  → `worker_de_lai.RX_DE_LAI` / `RX_RONG` / `_la_dieu_phoi` (TẦNG A, khuôn
    máy đọc được). CỐ Ý KHÔNG dùng tầng B (lưới vớt văn xuôi): đo thật trên 24 bản báo
    cáo worker ngày 03/09, tầng B bắt 33 dòng mà phần lớn là TIÊU ĐỀ MỤC ("Phần chưa làm
    được", "PHẦN CHƯA LÀM ĐƯỢC / ĐỂ LẠI") — chặn bằng nó là chặn oan mỗi tối.
    `worker_de_lai` cũng đã hạ tầng B xuống "chỉ báo, không đẻ vé" từ 30/08 vì lý do này.

KHÔNG TỰ CHẶN CHÍNH MÌNH: con đang gửi báo cáo LUÔN là một worker sống. Loại nó ra bằng
hai đường tất định: `agent_id` trong payload (đo thật 27/08: payload PreToolUse của worker
có `agent_id`), và mô tả/slug thuộc lớp *worker gửi báo cáo* (chốt ngày / báo cáo ngày).

KHÔNG CÓ CỬA THOÁT THỜI GIAN (P121, lệnh founder 06/10/2026: *"treo qua đêm đéo sao cả.
sang ngày mới tao đéo thích báo cáo thì tao chạy skill đầu ngày reset ngày mới luôn"*).
Còn nợ thì CHỜ, bao lâu cũng được. Bản cũ có trần chờ theo phút + một chuỗi thần chú nhét vào lệnh
nên báo cáo gửi đi với việc đang chạy bị gắn nhãn "bỏ dở" — sai sự thật.
Hai ca gốc 07/10/2026 00:01 (báo cáo ngày 06/10 bay khi còn việc nợ):
  · cổng KHÔNG ĐƯỢC GỌI: worker gửi bằng `node scripts/task-dev.mjs tin … --tep
    BAO-CAO-NGAY-….pdf` (không có `sendDocument`, không có mã nhóm) -> `la_lenh_gui_bao_cao`
    trả False. Nay soi cả đường này.
  · điều kiện ③ MÙ: nguồn của nó là `/tmp/w*-bao-cao*.md`, mà worker không còn ghi tệp đó
    (báo cáo cuối chỉ nằm trong transcript) -> dòng ĐỂ LẠI "hỏi anh Thành 12 câu chốt (main)"
    không bao giờ được thấy. Nay đọc báo cáo cuối từ transcript worker đã xong.
Ngày mới đã mở (`wseq.sh dau-ngay` ghi mốc) thì báo cáo của ngày CŨ hơn mốc bị CHẶN: founder
chạy đầu ngày = bỏ báo cáo cũ, thợ chốt ngày còn sống không gửi lọt được.

FAIL-OPEN tuyệt đối: lỗi bất kỳ → exit 0, không bao giờ làm vỡ phiên.

CHẠY TAY:
  python3 chot_ngay_gate.py --hien-trang    # in hiện trạng 3 điều kiện (skill Bước 1/4 gọi)
"""
import glob
import json
import os
import re
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 05/10/2026 nhóm lên supergroup: mã mới -1004466820523; giữ mã cũ để lệnh chép từ tài liệu cũ vẫn bị soi.
NHOM_HE_THONG = ("4466820523", "5449057497")  # nhóm "Hệ thống Fulfill TheChic"
LOG = "/tmp/claude_hooks/chot_ngay_gate.log"

# Mốc "ngày mới đã mở": `wseq.sh dau-ngay` ghi dòng 1 = "YYYY-MM-DD HH:MM:SS" (giờ VN).
COUNTER = os.path.expanduser(os.environ.get("WSEQ_ROOT", "~/.claude/worker-counter"))
MOC_DAU_NGAY = None   # None -> `<COUNTER>/<tên dự án>.dau-ngay`; ca thử ghi đè bằng đường tệp


def _moc_dau_ngay_cua(cwd):
    """Ngày (YYYY-MM-DD) của mốc đầu-ngày gần nhất của dự án, hoặc ''."""
    p = MOC_DAU_NGAY
    if not p:
        try:
            import mo_phien_gate as MP
            ten = MP.ten_scope(cwd)
        except Exception:
            ten = os.path.basename(os.path.abspath(cwd or ".").rstrip("/"))
        p = os.path.join(COUNTER, "%s.dau-ngay" % ten)
    try:
        with open(p, encoding="utf-8") as fh:
            d = (fh.readline() or "").split()
        return d[0] if d and re.match(r"^\d{4}-\d{2}-\d{2}$", d[0]) else ""
    except OSError:
        return ""


RX_NGAY_BAO_CAO = re.compile(
    r"BAO-CAO-NGAY-(\d{2})(\d{2})(\d{4})|b[aá]o c[aá]o ng[aà]y\s+(\d{1,2})/(\d{1,2})/(\d{4})", re.I)


def ngay_cua_bao_cao(cmd):
    """Ngày (YYYY-MM-DD) mà lệnh nói là báo cáo của ngày nào, hoặc ''."""
    m = RX_NGAY_BAO_CAO.search(cmd or "")
    if not m:
        return ""
    g = m.groups()
    d, mo, y = (g[0], g[1], g[2]) if g[0] else (g[3], g[4], g[5])
    return "%s-%02d-%02d" % (y, int(mo), int(d))


def bao_cao_ngay_cu(cmd, cwd):
    """Câu giải thích nếu báo cáo này là của ngày CŨ hơn ngày đã mở bằng đầu-ngày, else ''."""
    ngay_bc = ngay_cua_bao_cao(cmd)
    moc = _moc_dau_ngay_cua(cwd)
    if ngay_bc and moc and ngay_bc < moc:
        return ("⛔ NGÀY MỚI ĐÃ MỞ — báo cáo ngày %s KHÔNG được gửi nữa.\n"
                "Founder đã chạy đầu-ngày cho %s (mốc `wseq dau-ngay`): chạy đầu-ngày nghĩa là "
                "BỎ báo cáo của ngày cũ. Thợ chốt ngày còn sống thì DỪNG, báo main, không gửi.\n"
                "Muốn gửi bù thật thì founder tự nói rõ; máy không tự cho qua."
                % (ngay_bc[8:] + "/" + ngay_bc[5:7], moc[8:] + "/" + moc[5:7]))
    return ""


# Báo cáo cuối của worker nằm ở `/tmp/w<NN>-bao-cao.md` (luật báo cáo của mọi worker W##).
BAOCAO_GLOB = os.environ.get("UNIV3_BAOCAO_GLOB", "/tmp/w*-bao-cao*.md")
# Sổ việc-để-lại ĐÃ XỬ LÝ / đã chốt là không làm được: main ghi mỗi việc một dòng.
SO_DA_XU_LY = ".de-lai-da-xu-ly"
# Mục ĐỂ LẠI ngắn hơn ngần này TỪ thì không phải một việc (ca thật: worker khai
# "ĐỂ LẠI: … · B45 · B51" — B45/B51 là mã shop, không phải việc) → bỏ, không chặn.
TOI_THIEU_TU = 3
# Đoạn khớp để coi "đã có vé": 8 từ đầu của mục, đủ đặc trưng mà vẫn chịu được việc vé
# ghi tên rút gọn ở phần sau.
DAI_KHOP = 8

# Mục ĐANG CHỜ MỘT NGƯỜI (đã hỏi/đã nhờ, bóng ở sân người đó) — không đẻ vé được, chỉ phải nêu
# ở mục E. KHÁC `hỏi anh Thành …` (việc CỦA MAIN, chưa ai hỏi): cái đó phải CHẶN (ca gốc
# 07/10 00:01). Soi trên văn bản đã bỏ dấu (`chuan`). Đo 07/10: 54 mục ĐỂ LẠI của 33 báo
# cáo trong ngày, 22 mục là chờ-người/xoá-tay, 32 còn lại là việc nợ thật.
RX_CHO_NGUOI = re.compile(
    r"\b(?:cho|doi|nho|tuy)\s+(?:anh|chi|em|founder|phuong|thanh|quynh|flowdy|huu anh|lenh|"
    r"mot nguoi)\b"
    r"|\bxin\s+(?:tai khoan|anh|chi|founder|file|tep)\b|\bcan anh\b|\banh\s+(?:tu\s+)?"
    r"(?:xoa|don|chot|duyet|gat|bam|gui|keo|doc|nap|xac nhan|tra loi)\b"
    r"|\bkhi\s+(?:huu anh|may mo khoa|flowdy|phuong)\b|xoa tay|don tay|xoa tuy y|tuy anh"
    r"|\.next-w\d+|chan rm|chan xoa|lenh xoa bi tu choi|chua push \(cho lenh\)")
RX_GUI = re.compile(r"send(?:Document|Message)", re.I)
# Neo ĐẦU lệnh (sau `cd …;` tuỳ chọn): lệnh chép đoạn mã đó trong thông điệp commit / heredoc
# ghi tài liệu KHÔNG được bị coi là lệnh gửi (đã vấp 2 lần ngày 07/10).
RX_TASK_DEV_TIN = re.compile(
    r"^\s*(?:cd\s+[^;&|\n]+(?:;|&&)\s*)?(?:[A-Z_]+=\S+\s+)*node\s+\S*task-dev\.mjs\s+tin\b")
# Tên tệp/caption của báo cáo ngày, soi trên văn bản đã bỏ dấu.
RX_TEN_BAO_CAO = re.compile(r"bao[-_ ]?cao[-_ ]?ngay")
# Worker gửi báo cáo — mô tả/slug của CHÍNH NÓ, không được tự chặn mình.
RX_NGUOI_GUI = re.compile(r"chot.?ngay|bao.?cao.?ngay|\beod\b")


def bo_dau(s):
    s = unicodedata.normalize("NFD", (s or "").replace("Đ", "D").replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def chuan(s):
    """'Xin founder file A1N' -> 'xin founder file a1n' (chỉ chữ + số + khoảng trắng)."""
    return re.sub(r"[^a-z0-9]+", " ", bo_dau(s)).strip()


def ghi_log(dong):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dong))
    except Exception:
        pass


def la_lenh_gui_bao_cao(cmd):
    """Đúng loại lệnh cần soi: gửi báo cáo ngày vào nhóm Hệ thống."""
    if not cmd:
        return False
    if RX_TASK_DEV_TIN.search(cmd):
        # Đường thứ hai (ca gốc 07/10 00:01): `task-dev.mjs tin` luôn đi vào nhóm Hệ thống.
        # `--thu` = chỉ soạn + đo, không gửi -> không soi.
        if re.search(r"(?:^|\s)--thu(?:\s|$)", cmd):
            return False
        return bool(RX_TEN_BAO_CAO.search(bo_dau(cmd)))
    if not RX_GUI.search(cmd):
        return False
    if not any(n in cmd for n in NHOM_HE_THONG):
        return False
    return bool(RX_TEN_BAO_CAO.search(bo_dau(cmd)))


RX_THO_CHOT_NGAY = re.compile(r"^\s*(?:w\d+\s+)?(?:chot.?ngay|bao.?cao.?ngay|eod)\b")


def tho_chot_ngay_dang_song(cwd):
    """[{'so','mo_ta','id'}] thợ lớp CHỐT NGÀY còn sống — đầu-ngày dùng để bảo main TaskStop (R1 P121)."""
    try:
        import worker_queue as WQ
        ds = WQ.agent_song(cwd)
    except Exception:
        return []
    ra = []
    for a in ds or []:
        mo_ta = str(a.get("mo_ta") or "")
        # CHỈ thợ có mô tả BẮT ĐẦU bằng "chốt ngày" — thợ sửa chính cổng chốt ngày (mô tả
        # có chữ đó ở giữa) không được bị bảo tắt oan.
        if RX_THO_CHOT_NGAY.match(bo_dau(mo_ta)):
            ra.append({"so": a.get("so") or "W??", "mo_ta": mo_ta[:60], "id": str(a.get("id") or "")})
    return ra




# ── (1) worker còn sống ─────────────────────────────────────────────────────

def worker_song(cwd, self_aid=""):
    """([{'so','ten','id'}], do_duoc). do_duoc=False -> KHÔNG đo được, không chặn."""
    try:
        import worker_queue as WQ
    except Exception:
        return [], False
    try:
        ds = WQ.agent_song(cwd)
    except Exception:
        ds = None
    if ds is None:
        return [], False
    ra = []
    for a in ds:
        aid = str(a.get("id") or "")
        if self_aid and (aid == self_aid or aid.startswith(self_aid) or self_aid.startswith(aid)):
            continue                      # chính con đang gửi
        mo_ta = str(a.get("mo_ta") or "")
        if RX_NGUOI_GUI.search(bo_dau(mo_ta)) or RX_NGUOI_GUI.search(bo_dau(a.get("slug") or "")):
            continue                      # lớp worker gửi báo cáo (chốt ngày) — là người gửi
        ten = mo_ta
        try:
            import worker_board as WB
            ten = WB.ten_sach(mo_ta, a.get("slug") or "")
        except Exception:
            pass
        try:
            im = float(a.get("im"))
        except (TypeError, ValueError):
            im = -1.0
        ra.append({"so": a.get("so") or "W??", "ten": (ten or "(không rõ tên việc)")[:70],
                   "id": aid, "im": im})
    return ra, True


# ── (2) hàng chờ ────────────────────────────────────────────────────────────

def ve_hang_cho(cwd):
    """(vé CHẶN, vé chờ founder) — cùng nguồn với bảng worker.

    W69 (04/09/2026): vé nằm ở SỔ PHỤ (thư mục con / worktree của cùng dự án) trước đây
    cổng KHÔNG thấy -> báo cáo ngày "sạch" trong khi việc còn nợ. `WQ.doc()` nay quét cả
    sổ phụ; ở đây ghi thêm TÊN SỔ vào mỗi vé để người đọc biết vé nằm ở đâu mà gỡ.
    """
    try:
        import worker_queue as WQ
    except Exception:
        return [], []
    try:
        ves = WQ.doc(cwd)
    except Exception:
        return [], []
    try:
        so_chinh = WQ.thu_muc(cwd)
    except Exception:
        so_chinh = ""
    chan, founder = [], []
    for v in ves:
        # P103 H3 (15/09/2026): vé HOÃN "có chỗ đứng" nhưng KHÔNG tính nợ chốt ngày —
        # ca gốc W91 (14/09 22:49:05): hệ thiếu trạng thái hoãn nên main phải `xoa` (mất
        # vé) để chốt ngày im; nay `worker_queue.py hoan` giữ vé, chốt ngày chỉ bỏ qua.
        if v.get("trang_thai") == "hoan":
            continue
        try:
            ten = WQ.ten_ve(v)
        except Exception:
            ten = str(v.get("description") or "")
        ten = ten[:70]
        so_cua_ve = os.path.dirname(str(v.get("_path") or ""))
        if so_cua_ve and so_chinh and so_cua_ve != so_chinh:
            # Không cắt lại sau khi ghép: cắt là mất đúng cái nhãn vừa thêm.
            ten = "%s  [SỔ PHỤ %s]" % (ten, os.path.basename(so_cua_ve)[-38:])
        muc = {"so": v.get("so") or "W??", "ten": ten}
        try:
            la_founder = WQ.cho_founder(v)
        except Exception:
            la_founder = False
        (founder if la_founder else chan).append(muc)
    return chan, founder


# ── (3) dòng `ĐỂ LẠI:` chưa có vé ───────────────────────────────────────────

def _ngay_cua_ngay():
    """Tập ngày (theo giờ máy) được tính là 'của ngày' — trước 06:00 thì tính cả hôm qua.

    WHY nới về hôm qua khi còn sớm: chốt ngày thường chạy 23:xx–01:xx; bản báo cáo viết
    lúc 22:50 hôm trước vẫn là việc của CÙNG một ngày làm việc.
    """
    bay_gio = time.time()
    ra = {time.strftime("%Y-%m-%d", time.localtime(bay_gio))}
    if int(time.strftime("%H", time.localtime(bay_gio))) < 6:
        ra.add(time.strftime("%Y-%m-%d", time.localtime(bay_gio - 86400)))
    return ra


def _blob_ve(cwd):
    """Toàn văn CHUẨN HOÁ của mọi tệp vé (kể cả `.da-chay`) + sổ đã-xử-lý.

    WHY đọc cả vé đã chạy: vé xong bị đổi tên thành `*.json.da-chay` chứ không mất — nếu
    chỉ đọc vé đang chờ thì mọi việc ĐỂ LẠI đã làm xong đều hiện thành "chưa có vé" và
    cổng chặn vĩnh viễn.
    """
    ra = []
    try:
        import worker_queue as WQ
        d = WQ.thu_muc(cwd)
    except Exception:
        return ra
    for p in glob.glob(os.path.join(d, "*.json*")) + [os.path.join(d, SO_DA_XU_LY)]:
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                ra.append(chuan(fh.read()))
        except Exception:
            pass
    return ra


def _bao_cao_tu_transcript(cwd, ngay):
    """[(nhãn, văn bản)] báo cáo CUỐI của worker đã xong trong ngày, đọc từ transcript.

    WHY (ca gốc 07/10/2026 00:01): nguồn cũ `/tmp/w*-bao-cao*.md` không còn tệp nào — báo cáo
    cuối của worker chỉ nằm trong transcript — nên điều kiện ③ mù, dòng `ĐỂ LẠI: hỏi anh
    Thành 12 câu chốt (main)` không bao giờ bị thấy. Cùng nguồn với `worker_de_lai.quet`
    (`bao_cao_cuoi`). Bỏ qua worker thuộc lớp gửi báo cáo (chốt ngày): báo cáo của nó là
    báo cáo ngày, không phải việc nợ.
    """
    ra = []
    try:
        import worker_board as WB
        import worker_de_lai as WDL
        import worker_relapse as WR
        goc = WB.thu_muc_du_an(cwd)
        if not goc:
            return ra
        for jl in sorted(glob.glob(os.path.join(goc, "*", "subagents", "agent-*.jsonl"))):
            try:
                if time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(jl))) not in ngay:
                    continue
                if not WR.da_tra_bao_cao(jl):
                    continue                  # còn chạy / chết giữa chừng — không phải báo cáo cuối
                meta = {}
                try:
                    meta = json.load(open(jl[:-len(".jsonl")] + ".meta.json", encoding="utf-8"))
                except Exception:
                    pass
                mo_ta = str(meta.get("description") or "")
                if RX_NGUOI_GUI.search(bo_dau(mo_ta)):
                    continue
                m = re.match(r"^\s*(W\d+)\b", mo_ta, re.I)
                nhan = "%s-bao-cao" % (m.group(1).lower() if m else os.path.basename(jl)[6:14])
                txt = WDL.bao_cao_cuoi(jl)
                if txt:
                    ra.append((nhan, txt))
            except Exception:
                continue
    except Exception:
        pass
    return ra


def de_lai_con_no(cwd):
    """(chưa có vé, diện chờ founder) — mỗi mục {'tep','muc'}."""
    try:
        import worker_de_lai as WDL
    except Exception:
        return [], []
    try:
        import worker_queue as WQ
    except Exception:
        WQ = None
    ngay = _ngay_cua_ngay()
    blobs = _blob_ve(cwd)
    song_txt = ""
    try:
        ds, _ = worker_song(cwd)
        song_txt = chuan(" ".join(x["ten"] for x in ds))
    except Exception:
        pass
    thieu, founder = [], []
    nguon = []
    for f in sorted(glob.glob(BAOCAO_GLOB)):
        try:
            if time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(f))) not in ngay:
                continue
            nguon.append((os.path.basename(f), open(f, encoding="utf-8", errors="replace").read()))
        except Exception:
            continue
    nguon += _bao_cao_tu_transcript(cwd, ngay)
    for ten_nguon, txt in nguon:
        f = ten_nguon
        for m in WDL.RX_DE_LAI.finditer(txt):
            v = m.group(1).strip(" `*_")
            if WDL.RX_RONG.match(WDL._bo_dau(v).strip()):
                continue                       # worker khai "không có" — sạch
            for p in re.split(r"\s·\s|\s\|\s|;\s", v):
                p = p.strip(" `*_-")
                if len(p) < 3:
                    continue
                try:
                    if WDL._la_dieu_phoi(p):
                        continue               # chuyện điều phối vé, không phải việc
                except Exception:
                    pass
                n = chuan(p)
                tu = n.split()
                if len(tu) < TOI_THIEU_TU:
                    continue
                frag = " ".join(tu[:DAI_KHOP])
                if any(frag in b for b in blobs) or (song_txt and frag in song_txt):
                    continue                   # đã có vé / đang có worker làm
                muc = {"tep": f, "muc": p[:90]}
                # Diện CHỜ FOUNDER: dùng ĐÚNG regex của sổ vé (`worker_queue._CHO_NGUOI`)
                # — chữ "founder" đi kèm động từ xin/chờ/quyết/duyệt/nạp. CỐ Ý KHÔNG gọi
                # `cho_founder()` cả hàm: hàm đó coi MỌI việc để lại KHÔNG NÊU VÙNG là
                # chờ founder, mà mục ĐỂ LẠI bóc từ báo cáo thì phần lớn không có đường
                # dẫn → gọi cả hàm là mọi mục đều thành "chờ founder" và điều kiện ③
                # không bao giờ chặn được ai (đo thật: 8/8 mục lọt).
                la_founder = bool(RX_CHO_NGUOI.search(n))
                if not la_founder and WQ is not None:
                    try:
                        la_founder = bool(WQ._CHO_NGUOI.search(WQ._khong_dau(p)))
                    except Exception:
                        la_founder = False
                (founder if la_founder else thieu).append(muc)
    return thieu, founder


# ── tổng hợp ────────────────────────────────────────────────────────────────

def dau_viec_khong_tho(cwd):
    """[{ma, tieu_de}] đầu việc đã dịch hôm nay mà không mang nhãn thợ (W11, 19/09/2026).

    Sổ lệnh và sổ thợ là hai tệp không nói chuyện với nhau — không lệnh nào trả lời được
    "đầu việc nào đã dịch mà chưa có thợ", nên việc dịch xong rồi bỏ đó chỉ lòi ra ở lượt
    rà nhiều ngày sau. CỐ Ý không tự đếm kiểu khác: gọi thẳng `viec_vs_tho`."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import viec_vs_tho as VT
        return VT.doi_chieu(cwd)["thieu"]
    except Exception:
        return []


def luot_roi_khoi_so(cwd):
    """[{gio, trich}] lượt founder gõ hôm nay mà KHÔNG có trong `goc.md` (W11)."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import so_lenh as SL
        return SL.dem_doi_chieu(cwd).get("thieu") or []
    except Exception:
        return []


def do_hien_trang(cwd, self_aid=""):
    song, do_duoc = worker_song(cwd, self_aid)
    ve, ve_founder = ve_hang_cho(cwd)
    thieu, dl_founder = de_lai_con_no(cwd)
    return {"song": song, "do_duoc_song": do_duoc, "ve": ve, "ve_founder": ve_founder,
            "de_lai_thieu": thieu, "de_lai_founder": dl_founder,
            "so_phu": so_phu_con_ve(cwd),
            "viec_khong_tho": dau_viec_khong_tho(cwd),
            "luot_roi": luot_roi_khoi_so(cwd)}


def so_phu_con_ve(cwd):
    """[(tên sổ phụ, số vé sống)] — sổ phụ CÙNG dự án còn vé, tính trong lúc chuyển tiếp.

    W69: `ve_hang_cho` đã đếm những vé này vào mục ②, nên đây KHÔNG phải điều kiện chặn
    thứ hai; nó chỉ để câu "✅ SẠCH" nói được là sạch CẢ sổ phụ, khỏi ai phải tự đi `ls`.
    """
    try:
        import glob as _g
        import worker_queue as WQ
        return [(os.path.basename(d), len(_g.glob(os.path.join(d, "*.json"))))
                for d in WQ.so_phu(cwd)]
    except Exception:
        return []


def ly_do_chan(ht):
    """Thông điệp chặn — ĐÍCH DANH con nào / vé nào / dòng nào."""
    if not (ht["song"] or ht["ve"] or ht["de_lai_thieu"] or ht.get("viec_khong_tho")
            or ht.get("luot_roi")):
        return ""
    d = ["⛔ CHỐT NGÀY — CHƯA ĐƯỢC GỬI BÁO CÁO NGÀY. Việc của ngày còn nợ:", ""]
    if ht["song"]:
        d.append("① Còn %d worker SỐNG THẬT:" % len(ht["song"]))
        for a in ht["song"]:
            d.append("   · %s — %s" % (a["so"], a["ten"]))
    if ht["ve"]:
        d.append("② Hàng chờ còn %d vé CHƯA CHẠY:" % len(ht["ve"]))
        for v in ht["ve"]:
            d.append("   · %s — %s" % (v["so"], v["ten"]))
    if ht["de_lai_thieu"]:
        d.append("③ Còn %d dòng `ĐỂ LẠI:` chưa có vé (bảng trống KHÔNG bằng hết việc):"
                 % len(ht["de_lai_thieu"]))
        for m in ht["de_lai_thieu"]:
            d.append("   · %s → «%s»" % (m["tep"], m["muc"]))
    if ht.get("viec_khong_tho"):
        d.append("④ Còn %d ĐẦU VIỆC đã dịch mà KHÔNG ai nhận (sổ lệnh ↔ sổ thợ lệch):"
                 % len(ht["viec_khong_tho"]))
        for v in ht["viec_khong_tho"]:
            d.append("   · %s — %s" % (v["ma"], v["tieu_de"]))
    if ht.get("luot_roi"):
        d.append("⑤ Còn %d LƯỢT founder gõ hôm nay KHÔNG có trong `goc.md`:"
                 % len(ht["luot_roi"]))
        for x in ht["luot_roi"]:
            d.append("   · %s — «%s»" % (x.get("gio"), x.get("trich")))
    if ht["ve_founder"] or ht["de_lai_founder"]:
        d.append("")
        d.append("⚠ Ngoài ra %d việc diện CHỜ FOUNDER — không đẻ vé được, nhưng PHẢI nêu ở mục E:"
                 % (len(ht["ve_founder"]) + len(ht["de_lai_founder"])))
        for v in ht["ve_founder"]:
            d.append("   · %s — %s" % (v["so"], v["ten"]))
        for m in ht["de_lai_founder"]:
            d.append("   · %s → «%s»" % (m["tep"], m["muc"]))
    d += [
        "",
        "PHẢI LÀM (skill `chot-ngay` Bước 1 — LUẬT A/B/C):",
        "  1. Chờ ĐÍCH DANH mấy con ở ① xong (xác treo đã trả báo cáo cuối + im >5 phút thì không tính là sống).",
        "  2. Vé ở ② → báo main thả nốt. Dòng `ĐỂ LẠI:` ở ③ → báo main đẻ vé và thả; việc đã làm hoặc không làm được thì ghi một dòng vào `<hàng chờ>/%s`." % SO_DA_XU_LY,
        "  3. Việc sinh TRONG ngày là việc CỦA ngày — cấm lý lẽ 'sinh sau nên xếp mục D/F'.",
        "  3b. Đầu việc ở ④ → ghi `Giao W##.` vào đúng mục con trong `dich.md` (hoặc "
        "`MAIN TỰ LÀM` / `CỐ Ý KHÔNG GIAO`); soi lại bằng `python3 "
        "~/.claude/universal-hooks/viec_vs_tho.py`. Lượt ở ⑤ → ghi bù vào sổ gốc, soi "
        "bằng `so_lenh.py dem-doi-chieu`.",
        "  4. Viết bổ sung rồi KIỂM LẠI SÁT LÚC GỬI (`--hien-trang`), sạch mới gửi.",
        "",
        "Không có trần thời gian: chờ tiếp cho tới khi sạch, qua đêm không sao. Sang ngày mới mà "
        "founder không muốn báo cáo cũ thì founder tự chạy đầu-ngày (đầu-ngày tự bỏ báo cáo cũ).",
    ]
    return "\n".join(d)


def in_hien_trang(cwd):
    ht = do_hien_trang(cwd)
    ly = ly_do_chan(ht)
    if ly:
        print(ly)
        if not ht["do_duoc_song"]:
            print("\n(⚠ không đo được worker sống — điều kiện ① bị bỏ qua)")
        return 1
    print("✅ SẠCH — không worker sống, hàng chờ không vé chặn, không dòng `ĐỂ LẠI:` nào thiếu vé.")
    if ht.get("so_phu"):
        print("   (đã soi thêm %d sổ phụ cùng dự án, đều KHÔNG còn vé sống: %s)"
              % (len(ht["so_phu"]), ", ".join(t for t, _ in ht["so_phu"])))
    if ht["ve_founder"] or ht["de_lai_founder"]:
        print("⚠ %d việc diện CHỜ FOUNDER phải nêu ở mục E:"
              % (len(ht["ve_founder"]) + len(ht["de_lai_founder"])))
        for v in ht["ve_founder"]:
            print("   · %s — %s" % (v["so"], v["ten"]))
        for m in ht["de_lai_founder"]:
            print("   · %s → «%s»" % (m["tep"], m["muc"]))
    if not ht["do_duoc_song"]:
        print("(⚠ không đo được worker sống — điều kiện ① bị bỏ qua)")
    return 0


def main():
    if "--hien-trang" in sys.argv:
        cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        sys.exit(in_hien_trang(cwd))
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)
    try:
        cmd = str((data.get("tool_input") or {}).get("command") or "")
        if not la_lenh_gui_bao_cao(cmd):
            sys.exit(0)
        cwd = str(data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        # 07/10/2026 (việc 20261007-L20): báo cáo ngày vào nhóm Hệ thống là luật CHICHUB —
        # điều kiện dự án dùng chung ở pham_vi_chichub.py (lỗi import -> vẫn soi như cũ).
        try:
            import pham_vi_chichub
            if not pham_vi_chichub.thuoc_chichub(cmd, cwd):
                sys.exit(0)
        except ImportError:
            pass
        cu = bao_cao_ngay_cu(cmd, cwd)
        if cu:
            ghi_log("CHAN NGAY CU | %s" % cmd[:120].replace("\n", " "))
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": cu,
            }}, sys.stdout, ensure_ascii=False)
            sys.exit(0)
        ht = do_hien_trang(cwd, str(data.get("agent_id") or ""))
        ly = ly_do_chan(ht)
        if not ly:
            ghi_log("CHO QUA (sach) | %s" % cmd[:120].replace("\n", " "))
            sys.exit(0)
        ghi_log("CHAN | song=%d ve=%d de_lai=%d | %s"
                % (len(ht["song"]), len(ht["ve"]), len(ht["de_lai_thieu"]),
                   cmd[:120].replace("\n", " ")))
        json.dump({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": ly,
        }}, sys.stdout, ensure_ascii=False)
        sys.exit(0)
    except Exception as e:
        # W64 04/09/2026 — VẪN cho qua (chặn ở đây thì một lỗi vặt trong hook là founder
        # không chốt ngày được), nhưng THÔI IM. Bản cũ `except: sys.exit(0)` khiến cổng
        # hỏng và cổng đạt trông y hệt nhau: founder tưởng đã kiểm worker/vé/việc-để-lại
        # trong khi thật ra chưa kiểm gì. Không đo được ≠ đạt — đo được thì chặn, không đo
        # được thì ít nhất phải khai là mình mù.
        try:
            ghi_log("CONG HONG (fail-open) | %s: %s" % (type(e).__name__, e))
        except Exception:
            pass
        try:
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "cổng chốt ngày lỗi — cho qua nhưng CHƯA kiểm",
                "additionalContext":
                    ("⚠️ CỔNG CHỐT NGÀY HỎNG (%s: %s) — lượt này KHÔNG kiểm được worker còn "
                     "chạy / vé chờ / việc để lại. Đừng đọc im lặng thành «sạch»: tự chạy "
                     "`python3 %s --hien-trang` rồi hãy gửi báo cáo."
                     % (type(e).__name__, str(e)[:120], os.path.abspath(__file__)))}},
                sys.stdout, ensure_ascii=False)
        except Exception:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
