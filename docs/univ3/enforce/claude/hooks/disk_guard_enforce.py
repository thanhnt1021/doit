#!/usr/bin/env python3
"""Cổng tự kiểm ĐĨA MÁY ĐANG DÙNG — chạy đều, im khi an toàn, kêu khi thật sự căng.

WHY (W192, 29/08/2026): sáng 29/08 máy local đầy 98% (còn 12 GB) mà không ai biết;
founder phải tự hỏi "có phải đầy bộ nhớ không" thì mới có người đi đo. Đo đĩa tốn
~5 mili giây — không có lý do gì để đợi người hỏi.

WHY ba mức chứ không một ngưỡng: cùng ngày, cảnh báo đĩa máy chủ bị chạy thử với
ngưỡng 1% nên bắn tin lúc đĩa mới 40% — founder đọc xong coi cảnh báo là nhiễu.
Bài học: cảnh báo kêu sai một lần là mất niềm tin. Nên dưới ngưỡng an toàn phải IM
TUYỆT ĐỐI, mức chớm căng chỉ nhắc MỘT LẦN mỗi 12 tiếng, chỉ mức nguy hiểm mới nhắc
mỗi lượt.

WHY đọc ổ dữ liệu: trên macOS `df /` là ổ hệ thống chỉ-đọc (báo 57% trong khi ổ dữ
liệu thật đã 98%). Đọc nhầm ổ = báo an toàn lúc sắp hết chỗ.

Chạy ở: UserPromptSubmit (mỗi lượt founder gõ) và PreToolUse matcher Agent (trước
khi thả worker). KHÔNG chặn việc — chỉ chèn cảnh báo vào ngữ cảnh.
"""
import json
import os
import platform
import shutil
import subprocess
import sys
import time

STATE = os.path.expanduser("~/.claude/disk-guard.state")

# Ngưỡng phần trăm đã dùng. Dưới AN_TOAN: không nói gì.
AN_TOAN = int(os.environ.get("DISK_GUARD_AN_TOAN", "85"))
NGUY_HIEM = int(os.environ.get("DISK_GUARD_NGUY_HIEM", "93"))
# Mức chớm căng chỉ nhắc lại sau bấy nhiêu giờ (chống lặp mỗi lượt).
CACH_NHAC_GIO = float(os.environ.get("DISK_GUARD_CACH_NHAC_GIO", "12"))


def o_du_lieu() -> str:
    """Ổ chứa dữ liệu người dùng — KHÔNG phải ổ hệ thống chỉ-đọc."""
    if platform.system() == "Darwin" and os.path.isdir("/System/Volumes/Data"):
        return "/System/Volumes/Data"
    return "/"


def do_dia():
    gia = os.environ.get("DISK_GUARD_GIA_LAP_PCT")  # chỉ dùng khi tự kiểm cổng
    duong = o_du_lieu()
    tong, dung, con = shutil.disk_usage(duong)
    pct = int(round(dung * 100.0 / (dung + con))) if (dung + con) else 0
    if gia:
        pct = int(gia)
        con = int(float(os.environ.get("DISK_GUARD_GIA_LAP_GB", "12")) * 1024**3)
    return pct, con / 1024**3, duong


def cho_don():
    """Ba kho tạm lớn nhất còn dọn được — nói LUÔN dọn gì, không chỉ đưa con số."""
    ung_vien = [
        ("kho tạm npm", "~/.npm"),
        ("kho gói pnpm", "~/Library/pnpm"),
        ("kho tạm trình duyệt Chrome", "~/Library/Caches/Google/Chrome"),
        ("máy ảo giả lập iPhone", "~/Library/Developer/CoreSimulator/Devices"),
        ("kho tạm pip", "~/Library/Caches/pip"),
        ("bản dựng cũ trong /tmp", "/tmp"),
    ]
    ket = []
    for ten, p in ung_vien:
        duong = os.path.expanduser(p)
        if not os.path.isdir(duong):
            continue
        try:
            out = subprocess.run(["du", "-sk", "-x", duong], capture_output=True,
                                 text=True, timeout=6).stdout.split("\t")[0]
            gb = int(out) / 1024 / 1024
        except Exception:
            continue
        if gb >= 1:
            ket.append((gb, ten, p))
    ket.sort(reverse=True)
    return ket[:3]


def bo_nho():
    """Đo nhanh bộ nhớ — chỉ gọi khi đã ở mức cảnh báo, khỏi làm nặng mỗi lượt."""
    if platform.system() != "Darwin":
        return ""
    try:
        vm = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=4).stdout
        so = {}
        for dong in vm.splitlines():
            if ":" in dong:
                k, v = dong.split(":", 1)
                so[k.strip()] = v.strip().rstrip(".")
        pageout = int(so.get("Pageouts", "0") or 0)
        if pageout > 1_000_000:
            return f" · máy đã đẩy {pageout:,} lượt dữ liệu ra đĩa (dấu hiệu thiếu bộ nhớ)".replace(",", ".")
    except Exception:
        pass
    return ""


def doc_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {}


def ghi_state(d):
    try:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        with open(STATE, "w") as f:
            json.dump(d, f)
    except Exception:
        pass


def main():
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    pct, con_gb, duong = do_dia()

    # ---- Mức 0: an toàn -> IM TUYỆT ĐỐI ----
    if pct < AN_TOAN:
        sys.exit(0)

    st = doc_state()
    bay_gio = time.time()

    if pct < NGUY_HIEM:
        # ---- Mức 1: chớm căng -> nhắc MỘT LẦN mỗi CACH_NHAC_GIO tiếng ----
        if bay_gio - float(st.get("nhac_chom_cang", 0)) < CACH_NHAC_GIO * 3600:
            sys.exit(0)
        st["nhac_chom_cang"] = bay_gio
        ghi_state(st)
        print(f"🟡 Đĩa máy đang dùng đã {pct}% — còn {con_gb:.0f} GB trống ({duong}). "
              f"Chưa nguy hiểm, nhưng nên dọn kho tạm trước khi dựng bản lớn. "
              f"(nhắc lại sau {CACH_NHAC_GIO:.0f} tiếng)")
        sys.exit(0)

    # ---- Mức 2: nguy hiểm -> nhắc mỗi lượt, kèm dọn được gì ----
    st["nhac_nguy_hiem"] = bay_gio
    ghi_state(st)
    goi_y = cho_don()
    dong_goi_y = " · ".join(f"{ten} ~{gb:.0f} GB ({p})" for gb, ten, p in goi_y) or "không thấy kho tạm lớn"
    print(f"🔴 ĐĨA MÁY SẮP HẾT: đã dùng {pct}%, chỉ còn {con_gb:.0f} GB trống ({duong})"
          f"{bo_nho()}.\n"
          f"   Hậu quả thật: dựng bản (build) và tải gói có thể chết giữa chừng, "
          f"trình duyệt thử nghiệm không mở được.\n"
          f"   Dọn được ngay: {dong_goi_y}.\n"
          f"   Lệnh an toàn: `npm cache clean --force` · `pnpm store prune` · "
          f"`pip3 cache purge` · `brew cleanup --prune=all` · `xcrun simctl erase all`.")
    sys.exit(0)


if __name__ == "__main__":
    main()
