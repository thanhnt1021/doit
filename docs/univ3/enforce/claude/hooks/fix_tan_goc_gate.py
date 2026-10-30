#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_tan_goc_gate.py — CỔNG "FIX TẬN GỐC PHẢI HỎI TRƯỚC, CẤM NHẢ THIẾT KẾ NGAY".

LỆNH FOUNDER (nguyên văn, 07/09/2026 — history.jsonl:6479):
  "đéo tin lắm. thả RRI-T ra check, dùng ki-su và tho-xay để nghiên cứu tạo ra hệ
   thống hook chuẩn cùng các thứ chuẩn để không xung đột mà vẫn đáp ứng đủ các yếu
   tố. phải có hook bao gồm mỗi khi tao nói fix tận gốc, fix tầng gốc, fix tầng hệ
   thống, root cause, thì sẽ luôn hỏi lại là có cần ki-su tho xay challenge và
   RRI-T không? để kiểm tra chắc chắn không có gì sai."
  + "fix cái này phải đi kèm cả cái fix mà không được lập tức trả lời ngay mà phải
     phản biện nữa."

BỆNH THẬT ĐO ĐƯỢC (cùng phiên):
  founder hỏi "làm sao chữa tận gốc" -> main đọc lướt vài tên hàm rồi BẬT RA NGAY
  một thiết kế ba lớp, chưa ai phản biện, chưa chạy một lệnh kiểm chứng nào.
  Founder: "đéo tin lắm."
  => hai lỗ, phải bịt CẢ HAI:
     (1) không hỏi founder xem có cần bộ ba kiểm chứng (ki-su / tho-xay / RRI-T);
     (2) trả lời TỨC THÌ bằng phương án tự nghĩ ra — thứ founder không tin.

CƠ CHẾ — chỉ MỘT sự kiện, KHÔNG chặn tool nào:
  UserPromptSubmit -> nhận diện cụm "fix tận gốc / root cause / triệt để"...
                   -> in additionalContext ép hai thứ:
                      A. BẮT BUỘC gọi `AskUserQuestion` trước khi làm bất cứ gì,
                         đúng 3 lựa chọn (a) đủ bộ ba (b) chỉ tho-xay (c) tự làm.
                      B. CẤM nhả thiết kế / kết luận / phương án NGAY LƯỢT ĐÓ.
                   -> ghi cờ /tmp/claude_hooks/<sid>_fix_tan_goc.json (chống hỏi lặp).

VÌ SAO KHÔNG DÙNG PreToolUse deny: cổng này ép main "chỉ được HỎI". Nếu đồng thời
chặn tool thì main hết đường đi (muốn hỏi phải gọi AskUserQuestion, mà tool bị chặn).
Cổng chỉ CHÈN CHỮ + exit 0 => KHÔNG BAO GIỜ khoá chết main. Đây cũng là lý do nó an
toàn khi nổ chung với `nhai_lai_gate.py` (cổng đó mới là cổng có deny).

NGƯỠNG — CHỐNG NỔ BỪA (yêu cầu W09 §5):
  Có cụm khoá thôi CHƯA đủ. Câu KỂ CHUYỆN ("hôm qua đã fix tận gốc rồi") KHÔNG nổ.
  Luật 3 tầng, chạy theo thứ tự:
    T1. Cửa thoát/xin thôi ("khỏi hỏi", "tự làm luôn", "da-chot-cach-lam: ...") -> IM.
    T2. Có cụm khoá + có TÍN HIỆU SAI VIỆC (mệnh lệnh / câu hỏi cách làm / "cần",
        "phải", "làm sao", dấu ?) -> NỔ. Tín hiệu sai việc THẮNG tầng kể chuyện:
        "hôm qua fix tận gốc rồi mà vẫn lỗi, fix lại đi" -> vẫn phải nổ.
    T3. Có cụm khoá nhưng CHỈ là lời kể quá khứ (đã/rồi/hôm qua/vừa/lần trước bao
        quanh cụm) và không có tín hiệu sai việc -> IM.
  Vì sao chọn "tín hiệu sai việc" chứ không đếm thì quá khứ đơn thuần: founder viết
  hoa/không dấu/chửi thề tuỳ hứng, thì động từ không đáng tin; còn "việc phải làm"
  thì luôn lộ ra bằng mệnh lệnh hoặc dấu hỏi. Chấp nhận sai số: câu kể có dấu ? kiểu
  "hôm qua fix tận gốc rồi mà?" sẽ nổ oan — giá của nổ oan chỉ là main hỏi thêm 1
  câu, rẻ hơn nhiều so với bỏ sót (founder mất niềm tin, phải làm lại từ đầu).

THỨ TỰ ƯU TIÊN KHI NHIỀU CỔNG CÙNG NỔ (ghi rõ vì 3 cổng ép 3 hướng khác nhau):
  1) fix_tan_goc_gate  (cổng này) — HỎI TRƯỚC, cấm nhả thiết kế. Ưu tiên cao nhất
     vì nó CẤM ĐẦU RA; hai thứ kia chỉ định dạng/định tuyến đầu ra.
  2) nhai_lai_gate     — khối NHẠI LẠI viết SAU khi founder đã chốt cách làm, ngay
     trước lúc thả worker (nó deny ở PreToolUse:Agent, không deny AskUserQuestion).
  3) "main trống, thả worker rồi dừng" — áp cuối, lúc thi công.
  KHÔNG khoá chết: (a) cổng này không deny tool nào; (b) `nhai_lai_gate` đòi main
  phải CHẠY LỆNH ĐỌC trước khi thả worker — đọc/verify KHÔNG phải "nhả thiết kế",
  nên vẫn làm được trong lượt bị cổng này gác; (c) `AskUserQuestion` không nằm
  trong danh sách tool bị `nhai_lai_gate` chặn.

CHỐNG HỎI LẶP: đã hỏi trong TRAN_PHUT phút gần đây -> lượt sau chỉ nhắc nhẹ (bám
lựa chọn founder đã chốt), KHÔNG bắt hỏi lại. Tránh vòng lặp hỏi vô tận.
"""
import json
import os
import re
import sys
import time
import unicodedata

TMPDIR = "/tmp/claude_hooks"
TRAN_PHUT = 90            # trong 90' đã hỏi rồi -> không bắt hỏi lại
CUA_THOAT = "da-chot-cach-lam"   # + lý do >= 15 ký tự

# Tên THẬT của agent trong hệ (đã kiểm `ls ~/.claude/agents/` 07/09/2026):
#   ki-su (Ki-su.md) · tho-xay (Tho-xay.md) · tho-fulfill (tho-fulfill.md)
# RRI-T = skill `qa-multipass`, tài liệu docs/univ3/skills/qa-multipass/references/RRI-T_v1.md
AGENT_KYSU = "ki-su"
AGENT_THOXAY = "tho-xay"
RRIT_DOC = "docs/univ3/skills/qa-multipass/references/RRI-T_v1.md"


def bo_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt + hạ chữ thường -> khớp cả khi founder gõ không dấu."""
    s = s.lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# ── Cụm khoá (viết ở dạng ĐÃ BỎ DẤU — prompt cũng được bỏ dấu trước khi khớp) ──
# Nhờ bo_dau(), "fix tận gốc" và "fix tan goc" thành CÙNG một chuỗi -> một mẫu lo cả hai.
RE_CUM = re.compile(
    r"(fix|sua|chua|xu ly|giai quyet|tri)\s+(lai\s+)?(tan|tang)\s+goc"
    r"|(fix|sua|chua|xu ly|giai quyet|tri)\s+(tang\s+)?he\s+thong"
    r"|root\s*[- ]?\s*cause"
    r"|\btan\s+goc\b"
    r"|\btang\s+goc\b"
    r"|\btriet\s+de\b"
    r"|\bnguyen\s+nhan\s+goc\b",
    re.I,
)

# Tín hiệu SAI VIỆC — có cái này thì nổ, kể cả câu có dạng kể chuyện.
RE_SAI_VIEC = re.compile(
    r"\bhay\b|\bcan\b|\bphai\b|\bnen\b|\byeu cau\b"
    r"|\blam sao\b|\blam the nao\b|\bthe nao\b|\bcach nao\b|\btai sao\b|\bvi sao\b"
    r"|\bdi\b\s*[.!?]?\s*$|\bdi\b\s*[,.!?]"          # "fix lại đi", "làm đi,"
    r"|\bngay\b|\bluon\b|\bgio\b|\bbay gio\b"
    r"|\bfix lai\b|\blam lai\b|\bsua lai\b|\bxu ly\b|\bkiem tra\b|\bcheck\b|\bra soat\b"
    r"|\bthiet ke\b|\bphuong an\b|\bke hoach\b|\bplan\b|\bde xuat\b"
    r"|\?",
    re.I,
)

# Dấu KỂ CHUYỆN quá khứ bao quanh cụm khoá.
RE_KE_CHUYEN = re.compile(
    r"\bda\b|\broi\b|\bxong\b|\bhom qua\b|\bhom truoc\b|\blan truoc\b|\btuan truoc\b"
    r"|\bvua\b|\btruoc day\b|\bhoi nay\b|\btung\b",
    re.I,
)

# Founder chủ động xin thôi -> cổng im.
RE_XIN_THOI = re.compile(
    r"kh[oô]?ng c[aâ]?n h[oỏ]i|kho?i h[oỏ]i|dung h[oỏ]i|tu lam luon|lam luon di"
    r"|kho?i challenge|kh[oô]?ng c[aâ]?n challenge|kh[oô]?ng c[aâ]?n rri",
    re.I,
)
RE_CUA_THOAT = re.compile(re.escape(CUA_THOAT) + r"\s*:\s*(.{15,})", re.I)

# Lượt do hệ thống bơm vào (không phải founder gõ) -> bỏ qua.
RE_HE_THONG = re.compile(
    r"<system-reminder|<command-name>|<local-command|Caveat: The messages below",
    re.I,
)


def duong_dan_co(sid: str) -> str:
    return os.path.join(TMPDIR, f"{sid}_fix_tan_goc.json")


def da_hoi_gan_day(sid: str) -> bool:
    try:
        with open(duong_dan_co(sid), encoding="utf-8") as f:
            ts = float(json.load(f).get("ts", 0))
        return (time.time() - ts) < TRAN_PHUT * 60
    except Exception:
        return False


def ghi_co(sid: str, ly_do: str, prompt: str) -> None:
    try:
        os.makedirs(TMPDIR, exist_ok=True)
        with open(duong_dan_co(sid), "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "ly_do": ly_do, "dau": prompt[:200]},
                      f, ensure_ascii=False)
    except Exception:
        pass


def can_hoi(prompt: str) -> tuple:
    """Trả (True/False, mã lý do). Ba tầng — xem docstring đầu file."""
    if RE_HE_THONG.search(prompt):
        return False, "luot-he-thong"

    p = bo_dau(prompt)

    m = RE_CUM.search(p)
    if not m:
        return False, "khong-co-cum-khoa"

    # T1 — founder chủ động miễn
    if RE_XIN_THOI.search(p):
        return False, "founder-xin-thoi"
    if RE_CUA_THOAT.search(p):
        return False, "cua-thoat-da-chot-cach-lam"

    # T2 — có tín hiệu sai việc -> nổ (thắng cả tầng kể chuyện)
    if RE_SAI_VIEC.search(p):
        return True, "co-cum-khoa+sai-viec"

    # T3 — chỉ là lời kể quanh cụm khoá -> im
    lo, hi = max(0, m.start() - 60), min(len(p), m.end() + 60)
    if RE_KE_CHUYEN.search(p[lo:hi]):
        return False, "chi-ke-chuyen-qua-khu"

    # Có cụm khoá, không kể chuyện, không mệnh lệnh rõ -> vẫn nổ (an toàn hơn bỏ sót)
    return True, "co-cum-khoa"


KHOI_EP = f"""\
⛔ CỔNG "FIX TẬN GỐC" NỔ ({{ly_do}}) — founder vừa dùng ngôn ngữ TẦNG GỐC.
Đây đúng chỗ main từng hỏng: đọc lướt vài tên hàm rồi BẬT RA NGAY một thiết kế,
chưa ai phản biện. Founder nguyên văn: "đéo tin lắm."

LƯỢT NÀY MÀY BỊ CẤM HAI THỨ:
  1. CẤM nhả THIẾT KẾ / PHƯƠNG ÁN / KIẾN TRÚC / KẾT LUẬN nguyên nhân gốc.
     Không "tôi đề xuất 3 lớp", không "cách chữa là...", không bảng so sánh phương án.
  2. CẤM thả worker THI CÔNG trước khi founder chốt cách kiểm chứng.
  Được phép: ĐỌC/GREP/chạy lệnh kiểm chứng (đọc là thu bằng chứng, không phải vẽ
  giải pháp) và MÔ TẢ TRIỆU CHỨNG ĐO ĐƯỢC (file:dòng, output lệnh).

VIỆC PHẢI LÀM NGAY — gọi `AskUserQuestion`, đúng 3 lựa chọn dưới đây:
  Câu hỏi: "Việc này mày gọi là fix tận gốc. Cần bộ kiểm chứng tới đâu?"
  (a) ĐỦ BỘ BA (3 bước, KHÔNG có bước 4) — thả `{AGENT_KYSU}` viết phiếu
      (docs/ticket/P###.md) → `{AGENT_THOXAY}` phản biện bằng CODE THẬT (CHALLENGE mode,
      mọi objection kèm file:dòng) **dùng luôn RRI-T làm bộ tiêu chí soi phiếu** — RRI-T
      đã nằm SẴN trong `{AGENT_THOXAY}` (tài liệu `{RRIT_DOC}`, skill `qa-multipass`) →
      phiếu qua cửa thì chính `{AGENT_THOXAY}` thi công.
      CẤM đẻ con thứ ba "rà độc lập chạy RRI-T sau khi xong", CẤM chạy RRI-T song song:
      để RRI-T ở cuối = bắt được sai lúc đã code xong = phải thả lại cả bộ ba.
  (b) CHỈ THỢ XÂY — bỏ kỹ sư, thả thẳng `{AGENT_THOXAY}` phản biện bằng code thật
      rồi thi công. Nhanh hơn, không có phiếu để đối chiếu về sau.
  (c) KHÔNG CẦN — tự làm luôn, founder chịu rủi ro không ai phản biện.

Phương án chỉ được nói ra SAU KHI có phiếu của `{AGENT_KYSU}` hoặc phản biện của
`{AGENT_THOXAY}`. Trước đó mà mở miệng vẽ giải pháp = đúng lại lỗi founder vừa mắng.

THỨ TỰ KHI NHIỀU CỔNG CÙNG NỔ: (1) cổng này HỎI trước · (2) `nhai_lai_gate` — khối
NHẠI LẠI viết sau khi founder chốt, ngay trước lúc thả worker · (3) "main trống, thả
worker rồi dừng". Cổng này KHÔNG chặn tool nào nên không khoá chết đường nào.

CỬA THOÁT nếu thật sự đã chốt cách làm: founder viết `{CUA_THOAT}: <lý do >= 15 ký tự>`.
"""

NHAC_NHE = """\
🔁 Cổng "fix tận gốc" ĐÃ hỏi trong phiên này (còn hiệu lực {con} phút) — KHÔNG hỏi lại.
Bám đúng lựa chọn founder đã chốt. Vẫn giữ nguyên luật: cấm nhả thiết kế/kết luận
nguyên nhân gốc khi chưa có phiếu `ki-su` hoặc phản biện `tho-xay` kèm file:dòng.
"""


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0                       # fail-open: hỏng gì cũng không chặn founder

    # Lời gọi phát ra TỪ WORKER -> cho qua (bất biến, học từ nhai_lai_gate.py)
    if data.get("agent_id"):
        return 0
    if str(data.get("hook_event_name") or "") != "UserPromptSubmit":
        return 0

    prompt = str(data.get("prompt", ""))
    sid = str(data.get("session_id") or "nosid")

    can, ly_do = can_hoi(prompt)
    if not can:
        return 0

    if da_hoi_gan_day(sid):
        con = TRAN_PHUT
        try:
            with open(duong_dan_co(sid), encoding="utf-8") as f:
                ts = float(json.load(f).get("ts", 0))
            con = max(1, int(TRAN_PHUT - (time.time() - ts) / 60))
        except Exception:
            pass
        text = NHAC_NHE.format(con=con)
    else:
        ghi_co(sid, ly_do, prompt)
        text = KHOI_EP.format(ly_do=ly_do)
        # P005 (C-HX 18/10/2026): founder đang VẮNG (cờ /afk còn hạn — lệnh có thể gõ từ điện thoại; hoặc lượt
        # này là lời máy chèn) → câu 3 lựa chọn gửi inbox, không bật hộp hỏi. Nguồn duy nhất: afk_trang_thai.
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import afk_trang_thai as _TT
            _vang = _TT.loi_khi_vang(str(data.get("cwd") or os.getcwd()), str(data.get("transcript_path") or ""),
                                     nhanh=True, prompt=prompt)
        except Exception:
            _vang = ""
        if _vang:
            text = text + "\n" + _vang + "\n  (Lúc vắng: tự chọn (a) theo đề xuất, ghi CHỐT, gửi câu hỏi vào inbox ở trên.)\n"

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": text,
    }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
