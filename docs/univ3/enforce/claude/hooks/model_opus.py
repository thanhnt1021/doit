#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""model_opus.py — MỘT bản luật model cho mọi lệnh thả Agent (W102, 09/10/2026).

LỆNH FOUNDER (anh Thành 09/10/2026, chọn «Khoá gốc + sửa cổng»): mặc định toàn máy CHỈ
Opus 5.5 Medium; Fable chỉ khi anh bảo đặc biệt. Fix gốc trong hệ thống, không phải luật chữ.

WHY một module riêng: trước đây luật model nằm rải — `nhai_lai_gate.soi_c7a` ÉP việc phiếu
phải Fable (luật cũ SL14-L08), skill ui-ux khuyên Fable, còn cổng đó lại ĐÃ TẮT từ 18/09 nên
không ai chặn được lệnh thả `model: "fable"` nào. Giờ một hàm `soi_model` dùng cho:
  · `subagent_background_enforce.py` CỔNG 5 — cổng SỐNG ở matcher Agent, chặn thật;
  · `nhai_lai_gate.soi_c7a` — vế model của C7a (corpus ca thử P104 vẫn import).

LUẬT:
  · `model` bỏ trống -> CHO QUA (kế thừa mặc định máy = opus, settings.json + frontmatter
    3 thợ đã đặt opus/medium).
  · `model` bắt đầu bằng "opus" -> CHO QUA.
  · `model` = "fable" -> CHỈ cho khi brief có dòng `ANH-CHO-FABLE: <nguyên văn anh ≥5 ký tự>`.
  · model khác (sonnet/haiku/…) -> CHẶN.
  · `subagent_type` = "fork" -> CHO QUA (harness bỏ qua `model` của fork, luôn dùng model cha).
"""
import re

RX_ANH_CHO_FABLE = re.compile(r"^\s*ANH-CHO-FABLE\s*:\s*(\S.{4,})$", re.MULTILINE)


def anh_cho_fable(prompt: str) -> str:
    """Nguyên văn anh cho Fable ('' = không có)."""
    m = RX_ANH_CHO_FABLE.search(str(prompt or ""))
    return m.group(1).strip() if m else ""


def soi_model(ti: dict):
    """None = cho qua. Chuỗi = lý do CHẶN."""
    ti = ti or {}
    if str(ti.get("subagent_type") or "").strip().lower() == "fork":
        return None
    model = str(ti.get("model") or "").strip().lower()
    if not model or model.startswith("opus"):
        return None
    if model == "fable":
        if anh_cho_fable(ti.get("prompt")):
            return None
        return ("model 'fable' khi brief KHÔNG có dòng `ANH-CHO-FABLE: <nguyên văn anh>` — "
                "mặc định toàn máy chỉ Opus Medium (anh Thành 09/10/2026), Fable chỉ khi anh "
                "bảo đặc biệt.")
    return ("model '%s' — mặc định toàn máy chỉ Opus Medium (anh Thành 09/10/2026). "
            "Bỏ trường model (kế thừa opus) hoặc đặt model: \"opus\"." % model)
