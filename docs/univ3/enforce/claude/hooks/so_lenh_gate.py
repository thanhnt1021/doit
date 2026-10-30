#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""so_lenh_gate.py — hook bắt lệnh founder vào SỔ LỆNH (xem so_lenh.py).

Ba nhánh, mỗi nhánh làm đúng một việc:

  UserPromptSubmit  ghi NGAY nguyên văn vào goc.md (append, không cắt), cấp số L##.
                    WHY ghi ngay: phiên chết giữa chừng vẫn còn lời founder.
  Stop              (1) bóc ảnh founder dán ra anh/L##-<số>.png rồi thay dòng đặt chỗ;
                    (2) cổng: mục mới nhất bị ép mà chưa có bản dịch → chặn, tối đa 2 lần.
                    WHY để ở Stop: ảnh KHÔNG nằm trong `prompt` (đo thật) mà nằm trong
                    transcript, và lúc UserPromptSubmit dòng đó có thể chưa được ghi.
  SessionStart      dọn thư mục ngày quá 14 ngày (rẻ, một lần mỗi phiên).

FAIL-OPEN TUYỆT ĐỐI: mọi ngoại lệ → exit 0, không in gì. Founder không bao giờ bị
treo vì cái sổ. Van tắt: UNIV3_SO_LENH=0.
"""
import json
import os
import re
import sys
import time

THU_MUC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THU_MUC)
TMPDIR = "/tmp/claude_hooks"
MAX_CHAN = 2          # bằng worker_khai_xong_gate.py:56 — chặn 2 lần rồi thả


def _cach_hoi(cwd, nhanh=False):
    """Vé d991d9a878 (W301): anh vắng khỏi CLI (cờ /afk hoặc đang làm qua Telegram) → hỏi qua tin riêng,
    không bảo AskUserQuestion. `nhanh` = lượt UserPromptSubmit (anh vừa gõ CLI) → chỉ xét cờ /afk."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import afk_trang_thai as TT
        return TT.cach_hoi_anh(cwd, nhanh=nhanh)
    except Exception:
        return "AskUserQuestion"


def dem_chan(sid, ma):
    """Số lần đã chặn cho đúng mục này. Fail-open: đọc/ghi hỏng thì coi như quá hạn."""
    p = os.path.join(TMPDIR, "%s_so_lenh_chan.json" % (sid or "x"))
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    n = int(d.get(ma) or 0) + 1
    d[ma] = n
    try:
        os.makedirs(TMPDIR, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f)
    except Exception:
        return MAX_CHAN + 1
    return n


# ============================================================================
# P104 C3 — "CHỐT" PHẢI TRÍCH SỔ. Nguồn: docs/ticket/P104-siet-loi-noi-cua-main-15092026.md.
# ============================================================================
RE_P104_CHOT = re.compile(
    r"\b(?:founder|anh)\s+(?:đã\s+)?chốt\b|\bđã chốt\b(?!\s+ngày)", re.IGNORECASE)
# Hai khuôn cùng chấp nhận: đầy đủ `SL2026-09-14-L35` và rút gọn `SL14-L35` (ngày-2-chữ-số,
# tháng/năm HIỆN TẠI — đúng cách chính phiếu P104 tự trích trong toàn bộ §0.a/§9).
RE_P104_MA_SL_DAY = re.compile(r"\bSL(\d{4}-\d{2}-\d{2})-L(\d+)\b", re.IGNORECASE)
RE_P104_MA_SL_NGAN = re.compile(r"\bSL(\d{1,2})-L(\d+)\b", re.IGNORECASE)
P104_TRANG_THAI = os.path.join(THU_MUC, "p104_trang_thai.json")
P104_LOG_C3 = os.path.join(TMPDIR, "p104_nhanh.log")


def _p104_c3_bat() -> bool:
    if os.environ.get("UNIV3_P104_TAT") == "1":
        return False
    try:
        with open(P104_TRANG_THAI, encoding="utf-8") as f:
            st = json.load(f)
        return bool(st.get("C3", {}).get("bat", False))
    except Exception:
        return False


def _p104_ghi_log_c3(cau, che_do):
    try:
        with open(P104_LOG_C3, "a", encoding="utf-8") as f:
            f.write(json.dumps({"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "nhanh": "C3",
                                 "che_do": che_do, "cau": cau[:300]}, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _p104_c3_ma_ton_tai(cwd, ngay_str, so_muc) -> bool:
    import so_lenh as SL
    d = os.path.join(SL.goc_so(), SL.ten_du_an(cwd), ngay_str)
    try:
        with open(os.path.join(d, "goc.md"), encoding="utf-8") as f:
            nd = f.read()
    except Exception:
        return False
    return re.search(r"(?m)^## L0*%s\b" % int(so_muc), nd) is not None


# MIỄN TRỪ hẹp (W105, đo trên 33 câu "chốt" thật thiếu mã — §11 phiếu P104): AC5 bắt
# MỌI câu "chốt" thiếu mã SL — đo thật 33 câu lịch sử thấy hầu hết KHÔNG PHẢI khẳng
# định fabricate kiểu ca6 (dương, PHẢI chặn: "Founder đã chốt dùng phương án gộp 2
# cột...", TRẦN, không markup, không tham chiếu, khẳng định payload MỚI ngay sau
# "chốt"). 4 dạng thật tách được bằng CHỮ (không suy diễn nghĩa):
#   (i)   ĐANG XIN chốt — "cần/xin/phải X chốt" — chưa có quyết định để trích.
#   (ii)  THAM CHIẾU lại luật/quyết định ĐÃ CÓ TỪ TRƯỚC — "chốt" nằm trong mệnh đề phụ
#         xác nhận tuân theo ("như/đúng/theo...chốt", "chốt đúng", "chốt trước đó",
#         "chốt nguyên văn") — không đưa payload MỚI ngay sau chốt.
#   (iii) TỰ TRÍCH ARTIFACT kiểm được — câu tự nói đã "ghi vào brief"/"ghi vào sổ lệnh"
#         — nguồn là chính artifact đó.
#   (iv)  Payload sau "chốt" được ĐÁNH DẤU RÕ (markdown **bold**) hoặc CHÍNH CHỮ "chốt"
#         nằm trong ngoặc kép (tự trích dẫn cụm từ làm VÍ DỤ lỗi, không khẳng định).
# Đo: 0/33 câu thật khớp cả 4 vẫn còn "trần" như ca6 → 0 oan. Không nới cho câu KHÔNG
# khớp bất kỳ nhóm nào (ca6 không khớp nhóm nào — vẫn chặn).
RE_C3_XIN_CHOT = re.compile(r"\b(?:cần|xin|phải)\s+(?:founder|anh)\s+chốt\b", re.IGNORECASE)
RE_C3_THAM_CHIEU = re.compile(
    r"\b(?:như|đúng|theo)\b.{0,40}\bchốt\b|\bchốt\s+đúng\b|\bchốt\s+trước đó\b"
    r"|\bchốt\s+nguyên văn\b",
    re.IGNORECASE)
RE_C3_ARTIFACT = re.compile(r"\bbrief\b|\bsổ lệnh\b|\bso_lenh\b|\bsổ_lệnh\b", re.IGNORECASE)
RE_C3_QUOTE_CHOT = re.compile(r'"[^"\n]{0,40}chốt[^"\n]{0,15}"', re.IGNORECASE)


def _p104_c3_mien_tru(cau: str) -> bool:
    """True = câu KHÔNG cần trích mã SL (miễn trừ hẹp — xem WHY phía trên)."""
    if RE_C3_XIN_CHOT.search(cau):
        return True
    if RE_C3_THAM_CHIEU.search(cau):
        return True
    if RE_C3_ARTIFACT.search(cau):
        return True
    if RE_C3_QUOTE_CHOT.search(cau):
        return True
    m = RE_P104_CHOT.search(cau)
    if m and re.search(r"\*\*", cau[m.end():]):
        return True
    return False


def soi_c3(cwd, transcript_path):
    """C3 — câu chứa khuôn "chốt" mà KHÔNG kèm mã `SL<ngày>-L##` tồn tại thật (đã trừ
    miễn trừ hẹp `_p104_c3_mien_tru` — W105)."""
    if not transcript_path or not os.path.exists(transcript_path):
        return []
    try:
        sys.path.insert(0, THU_MUC)
        from phan_bua_gate import tach_luot, tach_cau, bo_khoi_trich
        with open(transcript_path, encoding="utf-8") as f:
            lines = f.readlines()
        ls = tach_luot(lines[-1500:])
        if not ls:
            return []
        text = "\n".join(ls[-1]["text"])
    except Exception:
        return []
    ra = []
    for cau in tach_cau(bo_khoi_trich(text)):
        if not RE_P104_CHOT.search(cau):
            continue
        if _p104_c3_mien_tru(cau):
            continue
        ma_day = RE_P104_MA_SL_DAY.search(cau)
        ma_ngan = None if ma_day else RE_P104_MA_SL_NGAN.search(cau)
        if not ma_day and not ma_ngan:
            ra.append((cau, "thiếu mã trích SL<ngày>-L## trong câu chốt"))
            continue
        if ma_day:
            ngay_str, so_muc = ma_day.group(1), ma_day.group(2)
        else:
            hom_nay = time.strftime("%Y-%m")
            ngay_str, so_muc = "%s-%02d" % (hom_nay, int(ma_ngan.group(1))), ma_ngan.group(2)
        if not _p104_c3_ma_ton_tai(cwd, ngay_str, so_muc):
            ra.append((cau, "mã sổ bịa: SL%s-L%s không có trong goc.md" % (ngay_str, so_muc)))
    return ra


def main():
    if os.environ.get("UNIV3_SO_LENH") == "0":
        return 0
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("agent_id"):          # lượt của subagent — sổ chỉ ghi lời FOUNDER
        return 0
    ev = str(data.get("hook_event_name") or "")
    cwd = str(data.get("cwd") or os.getcwd())
    sid = str(data.get("session_id") or "")
    import so_lenh as SL

    if ev == "SessionStart":
        try:
            SL.don(None, SL.GIU_NGAY)
        except Exception:
            pass
        return 0

    if ev == "UserPromptSubmit":
        prompt = str(data.get("prompt") or "")
        m = SL.ghi_goc(cwd, prompt, sid, transcript=str(data.get("transcript_path") or ""))
        if not m:
            return 0
        try:
            ep = SL.can_dich(cwd, m["so"])
        except Exception:
            ep = m.get("loai") == "LENH"
        if not ep:
            return 0
        r = {}
        try:
            r = SL.kiem_hoi(cwd, m["so"])
        except Exception:
            pass
        cach = _cach_hoi(cwd, True)
        dau_dong = ("📓 SỔ LỆNH: lượt này đã lưu NGUYÊN VĂN thành **%s** trong `goc.md` "
                    "(%d ký tự · %d gạch · %d ảnh)."
                    % (m["so"], m["so_ky_tu"], m["so_gach"], len(m["anh_cho"])))
        lenh_dich = ("   `python3 ~/.claude/universal-hooks/so_lenh.py dich --muc %s --tep <tệp>`"
                     % m["so"])
        luat_du = "\n".join([
                "→ THỨ TỰ BẮT BUỘC (founder chốt 09/09/2026): (1) ĐIỀU TRA TRƯỚC "
                "— worker trinh sát khai `GHI: -` hoặc tự Grep/Read; CHƯA được lưu bản "
                "dịch, CHƯA được nhại lại · (2) chỗ chưa rõ → hỏi bằng %s · "
                "(3) rõ rồi MỚI ghi bản dịch · (4) rồi mới thả thợ thi công." % cach,
                "→ Sau khi đã điều tra, ghi BẢN DỊCH cùng số mục:",
                lenh_dich,
                "   Khuôn: LOẠI / HIỂU LÀ / MỤC CON (%s.1 … %s.%d — ĐỦ %d gạch) / "
                "CỐ Ý KHÔNG LÀM / mỗi mục con một dòng `NGHIEM THU: url=… | phai-thay=\"…\"`."
                % (m["so"][1:].lstrip("0") or "0", m["so"][1:].lstrip("0") or "0",
                   max(m["so_gach"], 1), m["so_gach"])])
        # W21 C-HX 20/10/2026 (lệnh founder L40): phần luật THỨ TỰ + KHUÔN (~600 ký tự) là chữ
        # TĨNH, bản cũ in đủ mỗi lượt có lệnh (54 lượt/phiên). Nay dòng số mục + lệnh `dich`
        # (ĐỘNG) vẫn in mọi lượt; phần tĩnh qua nhac_gon — đủ lần đầu phiên / sau nén / khi cách
        # hỏi đổi (AFK↔có mặt) / mỗi 40 lượt. Hỏng gì cũng in đủ. Cửa tắt UNIV3_NHAC_GON=0.
        luat = luat_du
        try:
            import nhac_gon as NG
            hoi_gon = ("AskUserQuestion" if cach == "AskUserQuestion"
                       else "inbox founder (founder VẮNG — cấm AskUserQuestion)")
            luat = NG.gon(data, "so-lenh", luat_du,
                          "→ Điều tra trước → chỗ chưa rõ hỏi bằng %s → rõ rồi ghi BẢN DỊCH:\n%s\n"
                          "   (khuôn LOẠI/HIỂU LÀ/MỤC CON/CỐ Ý KHÔNG LÀM/NGHIEM THU — đủ chữ đã in "
                          "đầu phiên) → rồi mới thả thợ." % (hoi_gon, lenh_dich),
                          dau="so-lenh|" + cach)
        except Exception:
            luat = luat_du
        nhac = [dau_dong, luat]
        if r.get("bat_buoc_hoi"):
            nhac.append("⚠️ BẮT BUỘC HỎI LẠI (%s) — 1 lượt hỏi bằng %s, ≤3 câu, "
                        "rồi ghi `ĐÃ HỎI:` + `FOUNDER CHỐT:` vào bản dịch. %s"
                        % ("; ".join(r["dau_hieu"]), _cach_hoi(cwd, True), r["vi_sao"]))
        elif r.get("doi_viec"):
            d4 = ("⚠️ D4 — lượt này bị bộ phân loại xếp nhãn HỎI nhưng có từ ĐÒI "
                  "VIỆC «%s»: founder đang GIAO VIỆC, không phải hỏi thăm. Vẫn phải "
                  "ghi bản dịch (18/09 mục L14 «tao muốn edit tại cell như excel "
                  "sheet cơ … có chưa???» rơi sạch đúng vì cửa thoát này)."
                  % r["doi_viec"])
            try:      # W21: phần giải thích tĩnh in đủ một lần/phiên, sau đó 1 dòng
                import nhac_gon as NG
                d4 = NG.gon(data, "so-lenh-d4", d4,
                            "⚠️ D4 — có từ ĐÒI VIỆC «%s»: founder đang giao việc, vẫn phải ghi "
                            "bản dịch." % r["doi_viec"], dau="d4")
            except Exception:
                pass
            nhac.append(d4)
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n".join(nhac)}}, ensure_ascii=False))
        return 0

    if ev != "Stop":
        return 0

    # ── P104 C3 — "CHỐT" PHẢI TRÍCH SỔ (O1.8: hook DUY NHẤT import `so_lenh`) ──
    # Độc lập với luồng "mục chưa dịch" bên dưới -> chạy TRƯỚC, có/không mục nào
    # đang chờ dịch đều xét. Bật chặn chỉ khi qua cổng chứng minh G2 (p104_trang_thai.json).
    try:
        vi_pham_c3 = soi_c3(cwd, str(data.get("transcript_path") or ""))
    except Exception:
        vi_pham_c3 = []
    if vi_pham_c3:
        for cau, ly in vi_pham_c3:
            _p104_ghi_log_c3(cau, "bat" if _p104_c3_bat() else "dem-log")
        if _p104_c3_bat():
            cau0, ly0 = vi_pham_c3[0]
            print(json.dumps({"decision": "block", "reason": (
                '⛔ P104-C3 — chữ "chốt" phải kèm mã sổ tra được.\n'
                '  · "%s"\n    -> %s\n'
                "SỬA 1 trong 2: (1) trích đúng mã `SL<ngày>-L##` có thật trong "
                "`goc.md` · (2) đổi chữ thành \"gợi ý/đề xuất/đang nghiên cứu\" nếu "
                "founder chưa thật sự chốt.\n"
                "Không phải lời trên -> mở cờ `UNIV3_P104_TAT=1` chỉ khi khẩn cấp."
            ) % (cau0[:200], ly0)}, ensure_ascii=False))
            return 0

    d = SL.thu_muc(cwd)
    so = SL.doc_so(d)
    if not so.get("muc"):
        return 0
    ma = sorted(so["muc"])[-1]
    try:                                   # ẢNH: chỉ chạy khi mục này còn ảnh chờ
        SL.ghi_anh(cwd, ma)
    except Exception:
        pass
    if so["muc"][ma].get("dich"):
        return 0
    try:
        if not SL.can_dich(cwd, ma):
            return 0
    except Exception:
        return 0
    n = dem_chan(sid, ma)
    if n > MAX_CHAN:                       # fail-open: chặn 2 lần rồi thả
        return 0
    r = {}
    try:
        r = SL.kiem_hoi(cwd, ma)
    except Exception:
        pass
    ly = ["⛔ SỔ LỆNH: mục **%s** có BẢN GỐC nhưng CHƯA có BẢN DỊCH — "
          "chưa có bản dịch thì không có Definition of Done để nghiệm thu." % ma,
          "Bản dịch phải viết SAU khi đã điều tra (đọc code/chạy lệnh) và đã "
          "hỏi chỗ chưa rõ bằng %s — cấm dịch từ trí nhớ rồi mới đi tra." % _cach_hoi(cwd),
          "Chạy: python3 ~/.claude/universal-hooks/so_lenh.py dich --muc %s --tep <tệp>" % ma,
          "Rồi soi: python3 ~/.claude/universal-hooks/so_lenh.py doi-chieu"]
    if so["muc"][ma].get("so_gach"):
        ly.append("Bản gốc có %d gạch → bản dịch phải có ĐỦ %d mục con %s.1 … %s.%d, "
                  "thiếu là `doi-chieu` in đích danh gạch bị sót."
                  % (so["muc"][ma]["so_gach"], so["muc"][ma]["so_gach"],
                     ma[1:].lstrip("0"), ma[1:].lstrip("0"), so["muc"][ma]["so_gach"]))
    if r.get("bat_buoc_hoi") and not r.get("da_du"):
        ly.append("⚠️ %s — %s" % ("; ".join(r["dau_hieu"]), r["vi_sao"]))
    ly.append("(cổng này chặn tối đa %d lần rồi tự thả — lần %d/%d)" % (MAX_CHAN, n, MAX_CHAN))
    print(json.dumps({"decision": "block", "reason": "\n".join(ly)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
