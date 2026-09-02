#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""worker_vi_tri_gate.py — CỔNG: gọi worker phải bằng MÃ `W###`, cấm gọi theo VỊ TRÍ.

CA GỐC (27/08/2026, đo được trong transcript phiên
`e4d8e154-b072-479e-9ca5-c79227bd0a55.jsonl`, bản ghi lúc 08:44:30Z):
  main viết: *"W147 và W150 đang nghẽn cùng một lô deploy."* — sau đó rút gọn thành
  *"Ba con đầu đang nghẽn cùng một lô deploy"*.
  Founder (nguyên văn): *"đừng có nói ba con đầu. tao đéo biết đâu là đầu đâu là cuối
  cả. exactly W"*.

VÌ SAO VỊ TRÍ LUÔN SAI: bảng worker sắp theo mã (`dong.sort` trong `worker_board.py`) và
DANH SÁCH ĐỔI MỖI LƯỢT — con xong thì biến mất, con mới chen vào. "Con đầu" của lượt này
là con khác của lượt sau. Founder đọc bảng ở một thời điểm, main viết câu ở thời điểm
khác -> không bao giờ trỏ về cùng một worker. Mã `W###` thì bất biến, cấp một lần trong sổ
`~/.claude/worker-counter/<dự án>.map` và giữ nguyên kể cả khi vé bị xếp hàng rồi thả lại.

CÙNG LỚP LUẬT ĐÃ CÓ của dự án: nhắc ĐƠN bằng mã `{shop_code}-{etsy_order_id}`, nhắc THẺ
bằng mã thẻ, cấm lộ id nội bộ tự tăng (memory `goi-don-theo-ma-order`, có pre-commit chặn).
Nay mở rộng sang worker.

CƠ CHẾ: hook `Stop` — đọc lượt trả lời vừa xong, thấy cụm vị trí thì `decision: block`,
in đúng cụm bị bắt và bắt viết lại bằng mã. Chặn tối đa 2 lần/lượt rồi thả (fail-open),
KHÔNG treo founder.

CHỐNG CHẶN OAN — ba lớp, phải qua CẢ BA mới bắt:
  1. Chỉ nhận lượng từ + `con/thằng/đứa` + từ chỉ vị trí. "Nó", "cái kia" không tính.
  2. Loại danh từ ghép có sẵn chữ `con`: con số, con người, con trỏ, con dấu, con đường…
  3. Câu chứa cụm đó PHẢI có tín hiệu worker (worker/agent/W###/thả/xếp hàng/deploy/
     build/nghẽn/TaskStop/bảng). Nói "ba con đầu" về đơn hàng, file, dòng, thẻ -> cho qua.
"""
import json
import os
import re
import sys
import time

# ── Khối chỉ dẫn "viết lại cho gọn" — MỘT nguồn: stop_viet_lai.py ──────────────
# WHY: cổng `Stop` chặn SAU khi chữ đã hiện lên màn founder; không giấu được bản 1
# (giới hạn harness). Thứ sửa được là ĐỘ DÀI bản viết lại — đo 28-29/08: 39 cặp tin
# giống nhau ≥0,60 = 36.642 ký tự founder đọc hai lần.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import stop_viet_lai as _SVL
except Exception:
    _SVL = None


def _viet_lai(ly_do, sid=None, transcript=None, van_ban=None):
    if _SVL is None:
        return ly_do
    try:
        return _SVL.them(ly_do, van_ban=van_ban, sid=sid, transcript=transcript)
    except Exception:
        return ly_do



TMPDIR = "/tmp/claude_hooks"
NHAT_KY = os.path.join(TMPDIR, "worker_vi_tri_gate.log")
MAX_BLOCKS = 2

VI_TRI = r"(?:đầu\s+tiên|cuối\s+cùng|thứ\s+(?:nhất|nhì|hai|ba|tư|bốn|năm|mấy|\d+)|đầu|cuối|trên|dưới|giữa)"
LUONG = r"(?:hai|ba|bốn|bon|năm|sáu|bảy|mấy|vài|các|những|mọi|\d+)"
# `con/thằng/đứa` = lượng từ người Việt hay dùng cho worker ("ba con đầu", "hai con dưới").
RE_BAT = re.compile(
    r"(?:\b%s\s+)?\b(con|thằng|đứa)\s+(?:%s\s+)?%s\b" % (LUONG, LUONG, VI_TRI),
    re.I)
# Danh từ ghép có sẵn chữ `con` — không phải lượng từ, bắt vào là oan.
RE_OAN = re.compile(r"\bcon\s+(?:số|người|trỏ|dấu|đường|em|cái|gái|trai|mắt|tim)\b", re.I)
TIN_HIEU_WORKER = re.compile(
    r"\bW\d{1,4}\b|worker|agent|subagent|thả\b|xếp hàng|hàng chờ|TaskStop|deploy|build|"
    r"nghẽn|khoá deploy|bảng worker|đang chạy|báo cáo|kill|dừng|chết|xác\b|tiến độ|vé\b|"
    r"mốc|trần|bỏ dở|\d+%", re.I)
# Trích dẫn thì THA: main nhắc lại chính cụm sai để bàn về luật ("không có gì cấm em viết
# \"ba con đầu\"") là đang SỬA lỗi, chặn nó là chặn oan — ca thật trong transcript 27/8.
RE_TRICH = re.compile(r"\"[^\"]{0,200}\"|«[^»]{0,200}»|“[^”]{0,200}”|`[^`]{0,200}`")


def cau_cua(van_ban):
    """Cắt thành câu — cụm vị trí và tín hiệu worker phải NẰM CÙNG MỘT CÂU mới tính."""
    return [c for c in re.split(r"(?<=[.!?\n·])\s+|\n", van_ban or "") if c.strip()]


def soi(van_ban):
    """[(câu, cụm bị bắt)] — rỗng nghĩa là sạch.

    Ngữ cảnh xét trên CỬA SỔ 3 câu (câu trước + câu chứa cụm + câu sau): ca thật 27/8
    *"Con thứ ba báo không tìm thấy vì nó đã tự biến mất trước khi em kịp kill"* nằm ngay
    dưới một đoạn nói về worker, nhưng bản thân câu đó không có chữ nào trong danh sách
    tín hiệu -> xét đúng một câu là lọt.
    """
    ra = []
    cac = cau_cua(RE_TRICH.sub(" ", van_ban or ""))
    for i, c in enumerate(cac):
        m = RE_BAT.search(c)
        if not m:
            continue
        if RE_OAN.search(m.group(0)):
            continue
        cua_so = " ".join(cac[max(0, i - 1):i + 2])
        if not TIN_HIEU_WORKER.search(cua_so):
            continue
        ra.append((c.strip()[:200], m.group(0).strip()))
    return ra


def luot_cuoi(cac_dong):
    """Văn bản assistant của lượt CUỐI (từ sau bản ghi user gần nhất)."""
    mo = 0
    for i, d in enumerate(cac_dong):
        try:
            b = json.loads(d)
        except Exception:
            continue
        if b.get("type") == "user" and not b.get("isMeta"):
            mo = i
    manh = []
    for d in cac_dong[mo:]:
        try:
            b = json.loads(d)
        except Exception:
            continue
        if b.get("type") != "assistant":
            continue
        noi = (b.get("message") or {}).get("content")
        if isinstance(noi, str):
            manh.append(noi)
        elif isinstance(noi, list):
            for k in noi:
                if isinstance(k, dict) and k.get("type") == "text":
                    manh.append(k.get("text") or "")
    return "\n".join(manh)


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--soi-transcript":
        cham_transcript(sys.argv[2])
        return
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)
    tp = data.get("transcript_path", "")
    sid = data.get("session_id", "")
    if not tp or not os.path.exists(tp):
        sys.exit(0)
    os.makedirs(TMPDIR, exist_ok=True)
    dem_file = os.path.join(TMPDIR, "%s_vitri_count" % sid)
    time.sleep(0.2)
    try:
        with open(tp, encoding="utf-8", errors="replace") as f:
            cac_dong = f.readlines()
    except Exception:
        sys.exit(0)
    bat = soi(luot_cuoi(cac_dong[-1500:]))
    if not bat:
        try:
            os.remove(dem_file)
        except Exception:
            pass
        sys.exit(0)
    try:
        n = int(open(dem_file).read().strip()) + 1
    except Exception:
        n = 1
    try:
        open(dem_file, "w").write(str(n))
    except Exception:
        pass
    if n > MAX_BLOCKS:
        try:
            os.remove(dem_file)
        except Exception:
            pass
        sys.exit(0)
    dong = ["  · CỤM BỊ BẮT: «%s»\n    TRONG CÂU: \"%s\"" % (cum, cau) for cau, cum in bat[:4]]
    ly_do = (
        "⛔ GỌI WORKER THEO VỊ TRÍ — founder không đọc được.\n\n"
        + "\n".join(dong)
        + "\n\nCA GỐC (27/08/2026): main viết \"Ba con đầu đang nghẽn cùng một lô deploy\". "
          "Founder: \"đừng có nói ba con đầu. tao đéo biết đâu là đầu đâu là cuối cả. exactly W\".\n"
          "Bảng worker đổi mỗi lượt (con xong thì biến mất) -> \"con đầu\" lượt này là con khác "
          "lượt sau. Mã W### thì bất biến.\n\n"
          "SỬA: viết lại chính câu đó bằng MÃ đích danh, đúng như bảng đang in — "
          "\"W147 và W150 đang nghẽn cùng một lô deploy\". Không nhớ mã thì đọc lại khối "
          "◆ Worker đang chạy ở đầu lượt."
    )
    try:
        with open(NHAT_KY, "a", encoding="utf-8") as f:
            f.write(json.dumps({"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "session": sid,
                                "lan": n, "bat": [{"cau": c, "cum": u} for c, u in bat]},
                               ensure_ascii=False) + "\n")
    except Exception:
        pass
    print(json.dumps({"decision": "block",
                      "reason": _viet_lai(ly_do, sid=sid, transcript=tp),
                      "suppressOutput": True}, ensure_ascii=False))
    sys.exit(0)


def cham_transcript(duong_dan):
    """`--soi-transcript <file.jsonl>` — chạy cổng trên transcript THẬT, in từng ca bắt được.

    Dùng để đo tỉ lệ bắt oan trước khi bật cổng (luật: oan > 5% thì phải siết lại).
    """
    tong_cau = 0
    ca = []
    with open(duong_dan, encoding="utf-8", errors="replace") as f:
        for d in f:
            try:
                b = json.loads(d)
            except Exception:
                continue
            if b.get("type") != "assistant":
                continue
            noi = (b.get("message") or {}).get("content")
            manh = []
            if isinstance(noi, str):
                manh.append(noi)
            elif isinstance(noi, list):
                for k in noi:
                    if isinstance(k, dict) and k.get("type") == "text":
                        manh.append(k.get("text") or "")
            vb = "\n".join(manh)
            tong_cau += len(cau_cua(vb))
            for cau, cum in soi(vb):
                ca.append((b.get("timestamp", ""), cum, cau))
    print("Tổng câu assistant đã soi: %d" % tong_cau)
    print("Số ca BẮT: %d" % len(ca))
    for ts, cum, cau in ca:
        print("  [%s] «%s» ← %s" % (ts, cum, cau))


if __name__ == "__main__":
    main()
