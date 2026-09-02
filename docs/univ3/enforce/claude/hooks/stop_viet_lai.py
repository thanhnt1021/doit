#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stop_viet_lai.py — MỘT nguồn duy nhất cho dòng chỉ dẫn "viết lại cho gọn".

VẤN ĐỀ GỐC (founder 29/08/2026: *"và vẫn bị lặp"* · *"PHẢI SỬA Ở TẦNG GỐC"*):
Mọi cổng ở sự kiện `Stop` chỉ chặn được SAU KHI chữ đã hiện lên màn founder (giới hạn
kiến trúc — `Stop` bắn sau render, harness không thu hồi được chữ đã in; W02 đã đo và
kết luận không chuyển sớm hơn được). Nên cái sửa được KHÔNG phải "có chặn hay không"
mà là **độ dài bản viết lại**.

ĐO THẬT (transcript `47dc9a4f-…jsonl`, 28-29/08/2026, script /tmp/w10-do-lap.py):
  · 39 cặp tin liền nhau giống ≥0,60 → **36.642 ký tự lặp** founder phải đọc lần hai.
  · Ca founder chụp ảnh: 01:35:24 (2.390 ký tự) → chặn «con đầu tiên» → 01:35:49
    (2.386, giống 0,992) → chặn LẠI đúng câu đó → 01:36:13 (2.367, giống 0,996).
    Riêng ca này **4.736 ký tự lặp**, trong đó khối bảng worker ~1.100 ký tự × 2 lần.
  · Bản viết lại chỉ khác đúng một cụm từ, nhưng main in lại NGUYÊN cả tin kèm bảng.

VÌ SAO MAIN IN LẠI CẢ TIN: không có chỗ nào bảo nó đừng. Thông điệp chặn chỉ nói
"viết lại câu đó", main hiểu là sinh lại cả lượt trả lời; còn khối bảng worker thì
`delegate_subagent_reminder.sh` ra lệnh "MỞ ĐẦU CÂU TRẢ LỜI bằng ĐÚNG khối trên" —
lệnh đó đúng cho bản 1, nhưng main áp luôn cho bản viết lại.

CÁCH SỬA (một chỗ, ăn cho MỌI cổng `Stop`): mỗi thông điệp chặn tự đính thêm khối
chỉ dẫn dưới đây. KHÔNG nới lỏng, KHÔNG tắt cổng nào — chỉ đổi CÁCH TRÌNH BÀY
lúc bị chặn.

DÒNG BẢNG WORKER CÓ ĐIỀU KIỆN: chỉ nhắc "cấm in lại bảng" khi lượt này ĐÃ in bảng
thật. Nhận biết bằng hai đường (đường nào có trước thì tính):
  1. văn bản vừa bị chặn có chứa đầu bảng `◆ Worker đang chạy`;
  2. dấu `<sid>_bang_da_in` do chính lần chặn trước đặt — cần vì main nghe lời bỏ
     bảng ở bản 2, nếu chỉ soi văn bản thì bản 3 lại được thả cho in bảng.
Dấu bị xoá ở đầu mỗi lượt founder (`delegate_subagent_reminder.sh`, UserPromptSubmit).

CHỐT 29/08/2026 — KHÔNG DỰNG "cổng đo độ giống giữa bản viết đầu và bản viết lại".
W10 khai còn nợ việc này; founder trả lời KHÔNG LÀM: gốc bệnh đã xử bằng luật cấm in lại
cả tin khi bị chặn (khối `_CHUNG` ngay dưới), dựng thêm một lớp đo nữa là tốn mà chưa biết
lợi gì. Ghi ở đây để lần sau không ai đào lại.
"""
import json
import os
import time

TMPDIR = "/tmp/claude_hooks"
DAU_BANG = "◆ Worker đang chạy"
# Dấu quá hạn coi như của lượt trước (phòng khi hook UserPromptSubmit không chạy).
HAN_DAU = 3 * 3600

_CHUNG = (
    "\n\n\U0001F4CE VIẾT LẠI CHO GỌN — founder ĐÃ ĐỌC bản vừa rồi:\n"
    "  · Chỉ viết lại ĐÚNG (các) câu bị bắt ở trên. CẤM in lại cả tin.\n"
    "  · CẤM chào lại, CẤM tóm tắt lại, CẤM dựng lại bố cục cũ — phần đã đúng "
    "giữ nguyên, không nhắc lại.\n"
    "  · Mở đầu thẳng bằng câu đã sửa."
)
_BANG = ("\n  · CẤM in lại khối bảng worker (```◆ Worker đang chạy…```) lần thứ hai "
         "trong cùng lượt — lượt này đã in rồi, in lại là founder đọc hai lần.")


def _duong_dan_dau(sid):
    return os.path.join(TMPDIR, "%s_bang_da_in" % sid) if sid else None


def van_ban_cuoi(transcript):
    """Nguyên văn tin assistant CUỐI CÙNG trong transcript — chính là tin vừa bị chặn.

    WHY không grep cả đuôi tệp: bảng worker của lượt TRƯỚC cũng nằm trong đuôi, grep thô
    là dương tính giả -> cấm oan main in bảng ở lượt mới.
    """
    if not transcript or not os.path.exists(transcript):
        return ""
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            dong = f.readlines()[-400:]
    except Exception:
        return ""
    for d in reversed(dong):
        d = d.strip()
        if not d:
            continue
        try:
            b = json.loads(d)
        except Exception:
            continue
        if b.get("type") != "assistant":
            continue
        noi = (b.get("message") or {}).get("content")
        if isinstance(noi, str):
            if noi.strip():
                return noi
            continue
        if isinstance(noi, list):
            manh = [k.get("text") or "" for k in noi
                    if isinstance(k, dict) and k.get("type") == "text"]
            t = "\n".join(m for m in manh if m)
            if t.strip():
                return t
    return ""


def _da_in_bang(van_ban, sid):
    """Lượt này đã in bảng worker chưa — soi văn bản trước, rồi tới dấu."""
    thay = bool(van_ban) and DAU_BANG in van_ban
    p = _duong_dan_dau(sid)
    if thay:
        if p:
            try:
                os.makedirs(TMPDIR, exist_ok=True)
                with open(p, "w") as f:
                    f.write(str(int(time.time())))
            except Exception:
                pass
        return True
    if p and os.path.exists(p):
        try:
            if time.time() - os.path.getmtime(p) <= HAN_DAU:
                return True
        except Exception:
            return False
    return False


def xoa_dau(sid):
    """Lượt founder mới bắt đầu -> quên chuyện bảng của lượt cũ."""
    p = _duong_dan_dau(sid)
    if p:
        try:
            os.remove(p)
        except Exception:
            pass


def them(ly_do, van_ban=None, sid=None, transcript=None):
    """Đính khối chỉ dẫn vào cuối thông điệp chặn của MỘT cổng `Stop` bất kỳ.

    `van_ban`    = nguyên văn lượt trả lời vừa bị chặn (cổng nào có sẵn thì truyền vào).
    `transcript` = đường dẫn transcript; thiếu `van_ban` thì tự bóc tin assistant cuối.
    `sid`        = session id, để nhớ "lượt này đã in bảng" qua nhiều lần chặn.
    """
    if van_ban is None and transcript:
        van_ban = van_ban_cuoi(transcript)
    ra = (ly_do or "").rstrip() + _CHUNG
    if _da_in_bang(van_ban, sid):
        ra += _BANG
    return ra


def _tu_kiem():
    """Bộ tự kiểm — chạy: python3 stop_viet_lai.py --tu-kiem"""
    ca = []
    sid = "TUKIEM-%d" % int(time.time())
    xoa_dau(sid)

    r1 = them("⛔ LỖI X", van_ban="một câu bình thường", sid=sid)
    ca.append(("1. luôn có khối chỉ dẫn", "VIẾT LẠI CHO GỌN" in r1))
    ca.append(("2. không in bảng -> KHÔNG có dòng bảng", "bảng worker" not in r1))
    ca.append(("3. giữ nguyên thông điệp gốc", r1.startswith("⛔ LỖI X")))

    r2 = them("⛔ LỖI Y", van_ban="```\n%s — X (3)\n```\nnội dung" % DAU_BANG, sid=sid)
    ca.append(("4. có in bảng -> CÓ dòng cấm in lại bảng", "bảng worker" in r2))

    r3 = them("⛔ LỖI Y2", van_ban="bản viết lại đã bỏ bảng", sid=sid)
    ca.append(("5. lần chặn sau vẫn nhớ đã in bảng (dấu)", "bảng worker" in r3))

    xoa_dau(sid)
    r4 = them("⛔ LỖI Z", van_ban="lượt mới, chưa in bảng", sid=sid)
    ca.append(("6. lượt mới -> quên dấu, hết nhắc bảng", "bảng worker" not in r4))

    # transcript giả: tin CŨ có bảng, tin MỚI không -> chỉ được đọc tin mới.
    import tempfile
    fd, tp = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "```\n%s — X (2)\n```" % DAU_BANG}]}}) + "\n")
        f.write(json.dumps({"type": "user", "message": {"content": "founder gõ lượt mới"}}) + "\n")
        f.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "tin mới không có bảng"}]}}) + "\n")
    sid2 = sid + "-tr"
    xoa_dau(sid2)
    r5 = them("⛔ LỖI T", sid=sid2, transcript=tp)
    ca.append(("7. đọc transcript: chỉ soi tin assistant CUỐI", "bảng worker" not in r5))
    with open(tp, "a", encoding="utf-8") as f:
        f.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "```\n%s — X (2)\n```\nnội dung" % DAU_BANG}]}}) + "\n")
    r6 = them("⛔ LỖI T2", sid=sid2, transcript=tp)
    ca.append(("8. tin cuối CÓ bảng -> nhắc cấm in lại", "bảng worker" in r6))
    xoa_dau(sid2)
    os.remove(tp)

    ca.append(("9. van_ban=None không nổ", isinstance(them("⛔ A"), str)))
    ca.append(("10. ly_do=None không nổ", isinstance(them(None), str)))

    n = sum(1 for _, ok in ca if ok)
    for ten, ok in ca:
        print("  %s %s" % ("✅" if ok else "❌", ten))
    print("stop_viet_lai --tu-kiem: %d/%d %s" % (n, len(ca), "PASS" if n == len(ca) else "FAIL"))
    return 0 if n == len(ca) else 1


if __name__ == "__main__":
    import sys
    sys.exit(_tu_kiem() if "--tu-kiem" in sys.argv else 0)
