#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""giao_viec_moi.py — MODULE DÙNG CHUNG: `SendMessage` này có phải GIAO VIỆC THI CÔNG MỚI không?

LỖ HỔNG THẬT (07/09/2026, đo trong phiên):
  · main gọi `Agent` để thả worker thi công mà chưa chạy lệnh tra nào
    -> `nhai_lai_gate.py` CHẶN ĐÚNG ("CHƯA TRA GÌ MÀ ĐÃ ĐỊNH THẢ WORKER THI CÔNG").
  · ngay sau đó main giao thêm 2 việc cho worker ĐANG CHẠY bằng `SendMessage`,
    cũng chưa tra dòng nào -> cổng KHÔNG nổ, việc lọt thẳng xuống worker.
  Founder: *"hình như mày lại trả lời mà chưa suy nghĩ???? tao tưởng có hook rồi???"*

NGUYÊN NHÂN ĐO ĐƯỢC (không đoán):
  1) `settings.json`: `nhai_lai_gate.py` đăng ký `PreToolUse` với matcher **'Agent'** duy nhất.
  2) `nhai_lai_gate.py:147` `AGENT_TOOLS = {"Agent", "Task"}`; `nhanh_tool()` trả 0 ngay
     khi `tool_name` không nằm trong tập đó.
  -> `SendMessage` là ĐƯỜNG VÒNG KHÔNG BỊ CANH, dù bản chất cũng là giao việc thi công.

VÌ SAO KHÔNG CHẶN BỪA MỌI `SendMessage`:
  Điều phối sống bằng SendMessage — hỏi trạng thái, trả lời, bảo chờ worker khác, bảo dừng.
  Chặn hết = nghẽn điều phối = phản tác dụng. Nên module này chỉ trả True khi tin nhắn
  **thật sự là một việc thi công MỚI**.

BA CỬA, XÉT THEO THỨ TỰ:
  (0) Khai CHỈ ĐỌC / trinh sát        -> False (tra cứu là bước 1, không phải việc thi công).
  (1) TIÊU ĐỀ giao việc tường minh    -> True  ("THÊM VIỆC", "NẠP THÊM", "VIỆC 4 —", "task mới"…).
  (2) ĐỘNG TỪ thi công + tin ĐỦ DÀI   -> True  (brief thật luôn dài; "deploy lại đi" là điều phối).
  còn lại                             -> False.
"""
import re
import unicodedata

# Brief thi công thật luôn dài. Ngưỡng này chỉ áp cho cửa (2) — cửa (1) không cần dài.
NGUONG_DAI = 400


def _bo_dau(s: str) -> str:
    s = (s or "").lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)


# ── (0) khai chỉ đọc -> KHÔNG phải việc thi công ──────────────────────────────
RE_CHI_DOC = re.compile(
    r"chi doc|chi tra|khong sua gi|khong ghi gi|read-?only|"
    r"trinh sat|vung: ?chi doc|doc thoi|khong dong vao code"
)

# ── (1) tiêu đề giao việc tường minh (một mình đã đủ chặn) ────────────────────
RE_TIEU_DE = re.compile(
    r"them viec"                       # "THÊM VIỆC 4"
    r"|nap them"                       # "NẠP THÊM"
    r"|viec moi|task moi|nhiem vu moi"
    r"|viec bo sung|bo sung viec"
    r"|giao them|lam them viec"
    r"|yeu cau moi"
    r"|viec \d+ *[-—:]"                # "VIỆC 2 —" / "VIỆC 2:"
    r"|viec thu \d+"
)

# ── (2) động từ thi công (phải kèm tin đủ dài) ────────────────────────────────
RE_DONG_TU = re.compile(
    r"sua file|sua lai file|chinh sua file|viet lai|tao file moi|xoa file"
    r"|thi cong|trien khai"
    r"|deploy|build lai|dung lai ban|commit|push len"
    r"|them tinh nang|them man hinh|them cot|them bang|them endpoint"
    r"|refactor|migration|chuyen doi luoc do"
    r"|va loi|fix loi|sua loi"
)


def la_giao_viec_moi(message: str, summary: str = "") -> tuple:
    """(True/False, lý do) — tin `SendMessage` này có phải giao việc THI CÔNG MỚI không."""
    tho = f"{summary}\n{message}"
    t = _bo_dau(tho)

    if RE_CHI_DOC.search(t):
        return False, "khai chỉ đọc / trinh sát"

    m = RE_TIEU_DE.search(t)
    if m:
        return True, f"tiêu đề giao việc mới: «{m.group(0)}»"

    m = RE_DONG_TU.search(t)
    if m and len(message or "") >= NGUONG_DAI:
        return True, (f"brief dài {len(message)} ký tự + động từ thi công «{m.group(0)}»")

    return False, "điều phối / hỏi trạng thái / trả lời — không phải việc thi công mới"
