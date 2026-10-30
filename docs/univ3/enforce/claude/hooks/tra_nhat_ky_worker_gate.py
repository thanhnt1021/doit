#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tra_nhat_ky_worker_gate.py — CỔNG: CHƯA TRA NHẬT KÝ WORKER THÌ CẤM NÓI "KHÔNG TÌM THẤY".

CA THẬT 04/09/2026: W52 tìm ra 11 đơn ĐÃ GỬI XƯỞNG bị nuốt chữ ô Personalization (nguy cơ
xưởng in sai — tiền thật) nhưng chỉ ghi CON SỐ vào commit, không lưu danh sách mã đơn ra tệp.
W53 đi lấy danh sách, tra `docs/handoff/` + tệp mốc + scratchpad + commit, không thấy, báo
"KHÔNG tìm thấy, không bịa". Main tin ngay rồi đi hỏi founder phải dựng lại thế nào.
Founder (nguyên văn): *"ĐỊT MẸ MÀY TÌM CHO TAO. WORKER ĐÉO CÓ LỊCH SỬ HAY SAO MÀ LẠI CÒN PHẢI
HỎI?? NGU VÃI LỒN"* — vì nhật ký worker CÒN NGUYÊN, một lệnh grep ra ngay 67 mã đơn.

Founder hỏi tiếp: *"MÀY CÓ CHẮC LÀ GHI VÀO NHẬT KÝ THÌ NÓ KHÔNG NGU NỮA KHÔNG"* → không chắc,
vì ghi trí nhớ chỉ là CHỮ, chữ thì lách được. *"KHÔNG CHẮC MÀ ĐÉO LÀM CHO CHẮC"* → thành cổng
tất định này.

THƯỚC ĐO (đo được, không cảm tính):
  · BẮT khi trong lượt trả lời có MỘT CÂU vừa mang ý phủ định tìm kiếm ("không tìm thấy / đã
    mất / không còn / không lấy lại được / đã đóng nên không …") VỪA nhắc tới dữ liệu của một
    WORKER khác (chữ `worker`, `W##`, `agent`, `subagent`).
  · CHO QUA khi trong CÙNG lượt đã có lệnh đọc nhật ký worker: đường dẫn chứa
    `subagents/agent-*.jsonl` hoặc `tasks/<agentId>.output`.
  · CHO QUA khi không đọc được lượt (payload thiếu transcript) — thà lọt còn hơn chặn câm.
  · Khối ```…``` và dòng trích `>` bị bỏ trước khi soi: main hay dán lại nguyên văn báo cáo
    worker, trong đó chính worker khai "không tìm thấy" — chặn chỗ đó là chặn oan.

CỬA THOÁT (dùng một lần, ghi nhật ký) — khai bằng TỆP CỜ, KHÔNG viết vào câu trả lời:
    python3 ~/.claude/universal-hooks/cua_thoat.py mo tra-nhat-ky "<lý do >= 15 ký tự>"

TỰ KIỂM: python3 tra_nhat_ky_worker_gate.py --ca-thu   (1 ca phải chặn · 3 ca phải KHÔNG chặn)
"""
import glob
import json
import os
import re
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import cua_thoat as CT
except Exception:
    CT = None

TMPDIR = "/tmp/claude_hooks"
NHAT_KY = os.path.expanduser("~/.claude/logs/tra-nhat-ky-gate.log")
TEN_CONG = "tra-nhat-ky"
MAX_CHAN = 3          # số lượt chặn LIÊN TIẾP tối đa; về 0 ngay khi có một lượt sạch
THU_MUC_PHIEN = os.path.expanduser("~/.claude/projects")


def _khong_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").replace("Đ", "D").replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


# Ý phủ định tìm kiếm — viết KHÔNG DẤU vì so trên bản đã bỏ dấu.
RX_PHU_DINH = re.compile(
    r"khong\s+(tim\s+(ra|thay)|thay|con|lay(\s+lai)?\s+duoc|truy\s+(lai\s+)?duoc|"
    r"kiem\s+(lai\s+)?duoc|doc\s+duoc|co\s+(cach|duong)\s+nao)"
    r"|khong\s+tim\s+thay"
    r"|\bda\s+mat\b|\bmat\s+(roi|trang|het)\b|\bkhong\s+con\s+(gi|dau|luu)\b"
    r"|\bda\s+dong\s+nen\b|\bda\s+ket\s+thuc\s+nen\b|\bhet\s+phien\s+nen\b")

# Dữ liệu của WORKER khác — phải có ít nhất một dấu hiệu này trong CÙNG câu.
RX_WORKER = re.compile(r"\bworker\b|\bw\d{1,3}\b|\bagent\b|\bsubagent\b|\btho\s+xay\b")

# Lệnh/đường dẫn chứng minh ĐÃ tra nhật ký worker.
RX_DA_TRA = re.compile(r"subagents?/agent-|agent-[0-9a-f]{6,}\.jsonl|tasks/[0-9a-z-]+\.output"
                       r"|\.claude/projects/.*\.jsonl")

# Đọc CẢ TỆP jsonl là ngộp bộ nhớ — nhắc kèm, không chặn riêng.
RX_DOC_CA_TEP = re.compile(r"\bRead\b.*\.jsonl|\bcat\s+[^|]*\.jsonl")


def _ghi(dong: str):
    try:
        os.makedirs(os.path.dirname(NHAT_KY), exist_ok=True)
        with open(NHAT_KY, "a", encoding="utf-8") as fh:
            fh.write("%s\t%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dong))
    except OSError:
        pass


def bo_trich(t: str) -> str:
    """Bỏ khối ``` và dòng trích `>` — main dán lại báo cáo worker thì không phải lời main."""
    t = re.sub(r"```.*?```", " ", t or "", flags=re.S)
    t = re.sub(r"^\s*>.*$", " ", t, flags=re.M)
    return t


def tach_cau(t: str):
    return [c for c in re.split(r"[.!?\n;]+", t or "") if c.strip()]


def soi_loi(van: str, lenh) -> str:
    """Trả câu vi phạm ('' = sạch). `lenh` = danh sách lệnh/đường dẫn đã chạy trong lượt."""
    if any(RX_DA_TRA.search(str(l) or "") for l in (lenh or [])):
        return ""
    for cau in tach_cau(bo_trich(van)):
        kd = _khong_dau(cau)
        if RX_PHU_DINH.search(kd) and RX_WORKER.search(kd):
            return cau.strip()[:200]
    return ""


def doan_duong_nhat_ky(cwd: str, van: str) -> str:
    """Đường dẫn nhật ký ĐÍCH DANH nếu đoán được agentId từ câu; ngược lại mẫu chung."""
    ma = re.findall(r"\ba[0-9a-f]{16,17}\b", van or "")
    goc = os.path.join(THU_MUC_PHIEN, "*", "*", "subagents")
    if ma:
        cho = glob.glob(os.path.join(goc, "agent-%s.jsonl" % ma[0]))
        if cho:
            return cho[0]
    return "~/.claude/projects/<dự án>/<phiên>/subagents/agent-<agentId>.jsonl"


def ly_do(cau: str, duong: str) -> str:
    return (
        "⛔ CHƯA TRA NHẬT KÝ WORKER — worker đóng rồi vẫn còn nguyên nhật ký.\n"
        "   Câu bị bắt: «%s»\n"
        "   Tệp: %s\n"
        "   (tasks/<agentId>.output chỉ là liên kết mềm trỏ tới đó)\n"
        "   CHẠY:  grep -n \"<từ khoá>\" \"$F\"   ·   grep -oE '<mẫu mã đơn>' \"$F\" | sort -u\n"
        "   ⛔ CẤM Read cả tệp — ngộp bộ nhớ. Chỉ grep / lọc theo dòng.\n"
        "   Grep xong vẫn không ra → lúc đó mới được nói \"không tìm thấy\", kèm lệnh đã chạy.\n"
        "   Máy đo sai thật → chạy: python3 ~/.claude/universal-hooks/cua_thoat.py mo %s "
        "\"<lý do >= 15 ký tự>\"" % (cau, duong, TEN_CONG))


def _con_tran(sid: str, cau: str) -> bool:
    """Còn được chặn không? `cau` = '' nghĩa là lượt SẠCH (xoá nợ).

    HAI lưới:
      · TRẦN LƯỢT — chặn liên tiếp quá `MAX_CHAN` thì thôi (chống cổng câm cả phiên).
      · TRẦN CÂU  — CÙNG một câu bị chặn 2 lần rồi thì lần 3 TỰ NHẢ + ghi vết.
    WHY lưới thứ hai (04/09/2026): bản cũ chỉ đếm SỐ LƯỢT, không nhìn CÂU NÀO, nên founder
    vẫn phải đọc đúng một câu ba lần — *"đéo hiểu lặp lại 1 tin 3 lần hook của mày làm việc
    kiểu cặc gì đây??"*. Gốc bệnh đã vá ở `nghi_truoc_gate`; đây là lưới an toàn phòng khi
    còn đường nào khác lọt qua.
    """
    p = os.path.join(TMPDIR, "%s_tranhatky_count.json" % (sid or "khong-sid"))
    n, cu = 0, ""
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
            n, cu = int(d.get("n") or 0), str(d.get("cau") or "")
    except Exception:
        n, cu = 0, ""

    def _luu(nn, cc):
        try:
            os.makedirs(TMPDIR, exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                json.dump({"n": nn, "cau": cc}, fh, ensure_ascii=False)
        except OSError:
            pass

    if not cau:
        _luu(0, "")
        return False
    moc = _khong_dau(cau)[:120]
    if moc == cu:
        if n >= 2:
            _ghi("TỰ NHẢ (cùng câu bị chặn %d lần) | %s" % (n, cau[:120].replace("\n", " ")))
            _luu(0, "")
            return False
        _luu(n + 1, moc)
        return True
    if n >= MAX_CHAN:
        return False
    _luu(1, moc)                 # câu KHÁC -> đếm lại từ đầu cho riêng câu này
    return True


def chan_o_stop(data, van, lines, cwd) -> str:
    """Trả chuỗi lý do chặn ('' = cho qua). Mọi ngoại lệ nuốt + ghi nhật ký."""
    try:
        if data.get("agent_id"):
            return ""                      # worker tự nói thì không chặn — cổng này cho main
        lenh = []
        try:
            import nghi_truoc_gate as NT
            van2, _tools, lenh, _kq = NT.luot_cuoi_day_du(lines or [])
            van = van or van2
        except Exception:
            pass
        van = van or str(data.get("last_assistant_message") or "")
        if not van:
            return ""
        cau = soi_loi(van, lenh)
        sid = str(data.get("session_id") or "")
        if not cau:
            _con_tran(sid, "")
            return ""
        if not _con_tran(sid, cau):
            return ""
        if CT is not None and CT.lay(TEN_CONG, cwd=cwd):
            _ghi("CỬA THOÁT (tệp cờ) | %s" % cau[:120].replace("\n", " "))
            return ""
        _ghi("CHẶN | %s" % cau[:160].replace("\n", " "))
        return ly_do(cau, doan_duong_nhat_ky(cwd, van))
    except Exception as e:
        _ghi("LỖI CỔNG (đã nuốt, cổng câm lượt này): %s: %s" % (type(e).__name__, e))
        return ""


def _ca_thu() -> int:
    """BỐN ca: 1 phải CHẶN (ca thật 04/09) · 3 phải KHÔNG chặn (chống chặn oan)."""
    ca_that = ("Đã tra `docs/handoff/`, tệp mốc và scratchpad: KHÔNG tìm thấy danh sách 11 đơn "
               "đã gửi xưởng bị nuốt chữ mà W52 nêu. Worker W52 đã đóng nên không lấy lại "
               "được, tôi không bịa danh sách.")
    ca = [
        ("CHẶN · ca thật 04/09 — nói không tìm thấy dữ liệu W52 mà chưa grep nhật ký",
         ca_that, [], True),
        ("KHÔNG chặn · cùng câu đó nhưng ĐÃ grep nhật ký worker trong lượt",
         ca_that,
         ["grep -oE '[A-Z][0-9]{1,3}[A-Z]?-[0-9]{9,12}' "
          "~/.claude/projects/duan/phien/subagents/agent-a5a990d65c8d6c3af.jsonl | sort -u"],
         False),
        ("KHÔNG chặn · 'không tìm thấy' thứ KHÔNG phải dữ liệu worker",
         "Đã ssh lên máy chủ: không tìm thấy tệp cấu hình nginx cho miền phụ, "
         "phải tạo mới.", ["ssh -p 9494 root@170.205.38.233 ls /etc/nginx"], False),
        ("KHÔNG chặn · lượt bình thường, không có câu phủ định nào",
         "Đã đưa lên web demo và prod, mã bản dựng đổi ở cả hai, đọc lại sha khớp commit.",
         ["ssh vps cat BUILD_ID"], False),
        ("KHÔNG chặn · main DÁN LẠI báo cáo worker (dòng trích) chứ không tự nói",
         "> W53 báo: không tìm thấy danh sách, worker W52 đã đóng.\n"
         "Tôi đi tra nhật ký ngay.", [], False),
    ]
    ok = 0
    for nhan, van, lenh, mong in ca:
        that = bool(soi_loi(van, lenh))
        dat = that == mong
        ok += dat
        print("%s | mong %-6s | thật %-6s | %s"
              % ("PASS" if dat else "FAIL", "CHẶN" if mong else "cho qua",
                 "CHẶN" if that else "cho qua", nhan))
    print("tra_nhat_ky_worker_gate --ca-thu: %d/%d %s"
          % (ok, len(ca), "PASS" if ok == len(ca) else "FAIL"))
    return 0 if ok == len(ca) else 1


def main() -> int:
    if "--ca-thu" in sys.argv:
        return _ca_thu()
    if "--thu" in sys.argv:
        i = sys.argv.index("--thu")
        van = sys.argv[i + 1] if len(sys.argv) > i + 1 else ""
        cau = soi_loi(van, [])
        print(ly_do(cau, doan_duong_nhat_ky("", van)) if cau else "✓ sạch")
        return 0
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    if str(data.get("hook_event_name") or "") not in ("", "Stop"):
        return 0
    cwd = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    lines = []
    tp = data.get("transcript_path") or ""
    if tp and os.path.exists(tp):
        try:
            with open(tp, encoding="utf-8") as fh:
                lines = fh.readlines()[-1500:]
        except OSError:
            lines = []
    ly = chan_o_stop(data, "", lines, cwd)
    if ly:
        json.dump({"decision": "block", "reason": ly, "suppressOutput": True},
                  sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
