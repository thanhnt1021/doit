#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cua_thoat.py — CỬA THOÁT KHAI BẰNG TỆP CỜ, KHÔNG KHAI BẰNG CÂU TRẢ LỜI.

BỆNH THẬT (04/09/2026, founder): ba lượt liên tiếp main dán chuỗi `nghi-roi-noi: …` /
`khong-can-ve: …` / `khac-vung-that: …` lên đầu câu trả lời. Founder KHÔNG đọc code, nên hai
dòng ký hiệu đó vừa là rác vừa trông như đang công khai lách luật. Nguyên nhân gốc đo được:
mọi cổng `Stop` chỉ dò chuỗi cửa thoát TRONG CHÍNH VĂN BẢN main sắp gửi founder — đó là chỗ
duy nhất nó nhìn, nên main không có đường nào khác ngoài viết vào đấy.

CÁCH MỚI — khai ở chỗ MÁY đọc được mà FOUNDER không phải đọc:

    python3 ~/.claude/universal-hooks/cua_thoat.py mo <tên-cổng> "<lý do >= 15 ký tự>"

Lệnh ghi một tệp cờ DÙNG MỘT LẦN `~/.claude/cua-thoat/<tên-cổng>.json`. Cổng nào sắp chặn thì
gọi `lay(<tên-cổng>)`: đọc được -> XOÁ tệp, ghi nhật ký, cho qua. Câu trả lời gửi founder sạch
trơn, không còn ký hiệu nào.

KHÔNG NỚI LUẬT — cách mới CHẶT HƠN cách cũ, đo được từng điểm:
  · Lý do vẫn phải >= 15 ký tự, kiểm CẢ lúc ghi lẫn lúc đọc (cũ chỉ kiểm lúc đọc).
  · DÙNG MỘT LẦN: đọc xong tệp bị xoá -> lượt sau muốn thoát phải mở cờ lại. (Cũ: chuỗi nằm
    trong văn bản, main copy nguyên đoạn cũ sang lượt sau là qua tiếp, không ai biết.)
  · HẾT HẠN 15 phút -> không tích trữ cờ mở sẵn từ đầu phiên.
  · Tên cổng phải nằm trong danh sách trắng; gõ sai tên = không mở được cửa nào.
  · Mở cờ phải TỐN MỘT LƯỢT GỌI Bash có thật, hiện trên màn hình như một lệnh — cũ chỉ cần gõ
    thêm mấy chữ vào câu văn, không để lại vết gì ngoài chính câu văn đó.
  · Nhật ký 2 nơi mỗi lần MỞ và mỗi lần DÙNG (ai, cổng nào, lý do gì, lúc nào).

TỰ KIỂM: python3 cua_thoat.py --ca-thu
"""
import json
import os
import re
import sys
import time

THU_MUC = os.path.expanduser(os.environ.get("UNIV3_CUA_THOAT_DIR", "~/.claude/cua-thoat"))
NHAT_KY_BEN = os.path.expanduser("~/.claude/logs/cua-thoat.log")
NHAT_KY_TAM = "/tmp/claude_hooks/cua-thoat.log"
# W39 01/10/2026 — HỘP CÁT KHÔNG ĐƯỢC GHI VÀO NHẬT KÝ THẬT. Nhật ký này là nguồn của thước
# đo "lượt mở cửa thoát mỗi ngày" (phiếu P114). Đo thật: 49 dòng `MỞ` mang lý do
# "manager đã chốt ghép việc W07 với W09" là của `git_add_vung_ca_thu.py` (đã trỏ thư mục cờ
# sang hộp cát nhưng nhật ký vẫn ghi thẳng về đây) — phiếu đếm nhầm thành lượt lách thật.
# Thư mục cờ bị trỏ đi nơi khác = đang ở hộp cát -> nhật ký đi theo, nằm cạnh thư mục cờ.
if os.environ.get("UNIV3_CUA_THOAT_DIR"):
    NHAT_KY_BEN = os.path.join(THU_MUC, "cua-thoat.log")
    NHAT_KY_TAM = os.path.join(THU_MUC, "cua-thoat-tam.log")
LY_DO_TOI_THIEU = 15
HAN_PHUT = float(os.environ.get("UNIV3_CUA_THOAT_HAN_PHUT", "15"))

# Danh sách trắng: tên cổng -> cổng nào dùng (in ra khi gõ sai tên).
CONG = {
    "ve-de-sau":     "ve_de_sau_gate.py — «để sau» mà không có vé / khoe vé ma",
    "trung-vung":    "worker_de_trung_vung_gate.py + worker_cap_enforce.py — đẻ worker vào vùng worker khác giữ",
    "nghi-truoc":    "nghi_truoc_gate.py — nghĩ trước khi nói",
    "phan-bua":      "phan_bua_gate.py — khẳng định chưa kiểm (đã kiểm từ lượt trước)",
    "duong-thu-hai": "phan_bua_gate.py — kết luận phủ định đã đo bằng đường thứ hai",
    "nhai-lai":      "nhai_lai_gate.py — chưa tra gì mà đã nhại lại",
    "dia-chi-worker": "worker_dia_chi_gate.py — gửi SendMessage vào tên loại thợ thay vì mã định danh",
    "bao-xong-ten-viec": "worker_khai_xong_gate.py — câu báo xong khớp TÊN việc đang treo (W82) nhưng máy đo trúng oan",
    "git-ngoai-vung": "git_add_scope_enforce.py — `git add`/`commit` đụng tệp NGOÀI vùng `GHI:` của worker",
    "tin-van-hanh":  "tin_van_hanh_gate.py — tin gửi nhóm người vận hành còn dính chữ kỹ thuật",
    "muc-kiem":      "tin_nhom_trung_thuc_gate.py — chưa khai MỨC KIỂM / tin thiếu phần nhờ người dùng xác nhận",
    "ghi-khop-phieu": "ghi_khop_phieu.py (qua worker_cap_enforce.py) — dòng `GHI:` của brief thiếu vùng mà phiếu bắt ghi",
    "phuong-an-tho": "phuong_an_tho_gate.py — thợ chạy `task-dev.mjs phuong-an|ap-phuong-an|duyet-luot-huy` thật (thiếu --thu)",
}

# P138 11/10/2026 — CỜ CÓ CHỦ. Ca thật `cua-thoat.log:2615-2616`: main mở `git-ngoai-vung` cho
# việc commit của CHÍNH main lúc 09:36, bốn phút sau thợ P137 (`a35d50a54e1033838`) dùng mất cờ
# đó để commit tệp ngoài vùng -> tín hiệu sai vùng lộ muộn 27 phút. `lay()` cũ đọc rồi xoá,
# không so người mở với người lấy.
# Vì sao không so trường `ai`: lúc MỞ, `ai` lấy từ biến `CLAUDE_AGENT_ID` mà Bash của thợ KHÔNG
# có (đo 11/10: 399/399 lượt `MỞ git-ngoai-vung` đều ghi `main`, kể cả lượt thợ tự mở). Nên
# chủ cờ phải KHAI bằng `--cho <agent_id|W##>`.
# Cổng chỉ chạy cho thợ (người lấy không bao giờ là main) -> cờ không `--cho` là cờ vô chủ,
# ai lấy trước được trước. Chỉ áp cho các cổng trong tập này; cổng gửi tin
# (`tin_van_hanh_gate.py:417`, `tin_nhom_trung_thuc_gate.py:625`) thợ vẫn tự mở cho mình.
CONG_PHAI_CO_CHU = {"git-ngoai-vung", "phuong-an-tho"}  # W08 15/10: main mở cho đúng thợ

LENH_MAU = 'python3 ~/.claude/universal-hooks/cua_thoat.py mo %s "<lý do >= %d ký tự>"'


def lenh_mau(ten: str) -> str:
    return LENH_MAU % (ten, LY_DO_TOI_THIEU)


def _ghi_log(dong: str):
    for p in (NHAT_KY_BEN, NHAT_KY_TAM):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a", encoding="utf-8") as fh:
                fh.write(dong + "\n")
        except OSError:
            pass


def _duong(ten: str) -> str:
    return os.path.join(THU_MUC, "%s.json" % ten)


def mo(ten: str, ly_do: str, ai: str = "main", cwd: str = "", cho: str = "") -> str:
    """Mở cờ. Trả '' nếu OK, ngược lại trả chuỗi lỗi."""
    if ten not in CONG:
        return ("Không có cổng tên «%s». Tên hợp lệ:\n  %s"
                % (ten, "\n  ".join("%-14s %s" % (k, v) for k, v in sorted(CONG.items()))))
    ly_do = (ly_do or "").strip()
    if len(ly_do) < LY_DO_TOI_THIEU:
        return ("Lý do phải >= %d ký tự (đang %d). Cửa thoát không có lý do là cửa mở toang."
                % (LY_DO_TOI_THIEU, len(ly_do)))
    ban = {"cong": ten, "ly_do": ly_do, "luc": time.time(),
           "luc_doc": time.strftime("%Y-%m-%d %H:%M:%S"), "ai": ai,
           "cwd": cwd or os.getcwd(), "pid": os.getpid()}
    if cho:
        ban["cho"] = cho.strip()
    os.makedirs(THU_MUC, exist_ok=True)
    with open(_duong(ten), "w", encoding="utf-8") as fh:
        json.dump(ban, fh, ensure_ascii=False)
    _ghi_log("%s\tMỞ\t%s\t%s\t%s%s" % (ban["luc_doc"], ten, ai,
                                        ("cho=%s · " % ban["cho"]) if cho else "",
                                        ly_do[:200].replace("\n", " ")))
    return ""


def _la_chu(cho: str, ai: str) -> bool:
    """`cho` khớp người lấy: so nguyên chuỗi, hoặc so số `W##` (W7 == W07)."""
    a, b = (cho or "").strip(), (ai or "").strip()
    if not a or not b:
        return False
    if a == b:
        return True
    ma, mb = re.match(r"^[Ww]0*(\d+)$", a), re.match(r"^[Ww]0*(\d+)$", b)
    return bool(ma and mb and ma.group(1) == mb.group(1))


# W39 01/10/2026 (P114 mục 4.5 + A25) — CỜ KHÔNG ĐƯỢC CHÁY OAN KHI LỆNH HỎNG.
# Cổng tiêu cờ ở `PreToolUse`, TRƯỚC khi lệnh chạy; lệnh `git commit` sau đó chết (móc
# kiểm trước commit trượt, tệp lời nhắn trong /tmp bị dọn…) thì cờ đã mất, chạy lại y
# nguyên lệnh đó lại bị chặn, phải mở cờ lần nữa. Đo được: 5/21 lượt mở `git-ngoai-vung`
# ngày 30/09 và 2/3 lượt ngày 01/10 là mở LẠI cho cùng một việc.
# Chữa hẹp, không nới luật: cổng nào truyền `khoa` (dấu vân tay của ĐÚNG tập đối tượng
# vừa được cho qua — với `git-ngoai-vung` là tập tệp ngoài vùng + mã thợ) thì trong
# `HAN_DUNG_LAI_PHUT` phút, CHÍNH tập đó được qua lại mà không cần cờ mới. Đổi một tệp,
# đổi thợ, hay quá hạn -> vẫn chặn như cũ. Cổng không truyền `khoa` -> y như cũ.
HAN_DUNG_LAI_PHUT = float(os.environ.get("UNIV3_CUA_THOAT_DUNG_LAI_PHUT", "10"))


def _duong_dung_lai(ten: str) -> str:
    return os.path.join(THU_MUC, "%s.dung-lai.json" % ten)


def _dung_lai(ten: str, khoa: str, ai: str):
    """Lý do của lần cho qua TRƯỚC nếu `khoa` trùng và còn hạn; None nếu không."""
    if not khoa:
        return None
    try:
        with open(_duong_dung_lai(ten), encoding="utf-8") as fh:
            b = json.load(fh)
    except Exception:
        return None
    tuoi = (time.time() - float(b.get("luc") or 0)) / 60.0
    if b.get("khoa") != khoa or tuoi > HAN_DUNG_LAI_PHUT:
        return None
    _ghi_log("%s	DÙNG LẠI (lệnh trước hỏng, cùng đối tượng)	%s	%s	sau %.1f phút	%s"
             % (time.strftime("%Y-%m-%d %H:%M:%S"), ten, ai, tuoi,
                str(b.get("ly_do") or "")[:200].replace("\n", " ")))
    return str(b.get("ly_do") or "")


def lay(ten: str, ai: str = "main", cwd: str = "", khoa: str = ""):
    """Đọc + XOÁ cờ. Trả lý do (str) nếu cửa mở hợp lệ, None nếu không.

    Chỉ gọi ĐÚNG LÚC cổng sắp chặn — gọi sớm là đốt cờ oan.
    `khoa` (W39): dấu của đúng đối tượng được cho qua — xem `HAN_DUNG_LAI_PHUT`.
    """
    p = _duong(ten)
    try:
        with open(p, encoding="utf-8") as fh:
            ban = json.load(fh)
    except Exception:
        return _dung_lai(ten, khoa, ai)
    # P138: cờ không phải của người lấy -> KHÔNG xoá (chủ thật còn dùng được), không cho qua.
    cho = str(ban.get("cho") or "").strip()
    if (cho and not _la_chu(cho, ai)) or (not cho and ten in CONG_PHAI_CO_CHU and ai != "main"):
        _ghi_log("%s\tBỎ QUA (không phải chủ)\t%s\t%s\tcờ cho=%s"
                 % (time.strftime("%Y-%m-%d %H:%M:%S"), ten, ai, cho or "(không khai — cờ vô chủ)"))
        return _dung_lai(ten, khoa, ai)
    try:
        os.remove(p)                       # DÙNG MỘT LẦN — xoá ngay, kể cả khi hết hạn
    except OSError:
        pass
    ly_do = str(ban.get("ly_do") or "").strip()
    tuoi = (time.time() - float(ban.get("luc") or 0)) / 60.0
    luc = time.strftime("%Y-%m-%d %H:%M:%S")
    if len(ly_do) < LY_DO_TOI_THIEU:
        _ghi_log("%s\tTỪ CHỐI (lý do ngắn)\t%s\t%s\t%s" % (luc, ten, ai, ly_do))
        return None
    if tuoi > HAN_PHUT:
        _ghi_log("%s\tTỪ CHỐI (quá hạn %.1f phút)\t%s\t%s\t%s" % (luc, tuoi, ten, ai, ly_do[:200]))
        return None
    _ghi_log("%s\tDÙNG\t%s\t%s\tmở trước %.1f phút\t%s"
             % (luc, ten, ai, tuoi, ly_do[:200].replace("\n", " ")))
    if khoa:
        try:
            with open(_duong_dung_lai(ten), "w", encoding="utf-8") as fh:
                json.dump({"khoa": khoa, "ly_do": ly_do, "luc": time.time(), "ai": ai}, fh,
                          ensure_ascii=False)
        except OSError:
            pass
    return ly_do


def loi_khuyen(ten: str) -> str:
    """Dòng chỉ đường in trong lời chặn — KHÔNG bao giờ bảo main viết ký hiệu vào câu trả lời."""
    return ("Máy đo sai / thật sự không thuộc diện này -> CHẠY LỆNH (không viết gì vào câu trả "
            "lời gửi founder):\n    %s\nrồi trả lời lại bằng câu người thường đọc được. "
            "Cờ dùng một lần, hết hạn %.0f phút, ghi nhật ký %s."
            % (lenh_mau(ten), HAN_PHUT, NHAT_KY_BEN))


def _xem():
    if not os.path.isdir(THU_MUC):
        print("(không có cờ nào đang mở)")
        return 0
    co = sorted(os.listdir(THU_MUC))
    if not co:
        print("(không có cờ nào đang mở)")
        return 0
    for f in co:
        try:
            b = json.load(open(os.path.join(THU_MUC, f), encoding="utf-8"))
        except Exception:
            continue
        print("%-14s mở %.1f phút trước · %s" % (b.get("cong"),
              (time.time() - float(b.get("luc") or 0)) / 60.0, str(b.get("ly_do"))[:90]))
    return 0


def _ca_thu():
    goc = globals()["THU_MUC"]
    globals()["THU_MUC"] = "/tmp/claude_hooks/cua-thoat-ca-thu"
    # W39: ca thử KHÔNG được ghi vào nhật ký thật — nhật ký đó là nguồn đo "lượt mở cửa
    # thoát mỗi ngày" (P114 đích đo); bản cũ ghi thẳng, nên phiếu phải tự lọc chữ "ca thử".
    nk_goc = globals()["NHAT_KY_BEN"]
    globals()["NHAT_KY_BEN"] = "/tmp/claude_hooks/cua-thoat-ca-thu.log"
    os.makedirs(THU_MUC, exist_ok=True)
    for f in os.listdir(THU_MUC):
        os.remove(os.path.join(THU_MUC, f))
    loi = 0

    def kiem(ten, dat, mong):
        nonlocal loi
        ok = (dat == mong)
        loi += 0 if ok else 1
        print("  %s %-52s -> %s" % ("✓" if ok else "✗ SAI", ten, dat))

    kiem("tên cổng bịa -> từ chối", mo("cong-bia", "lý do rất dài đủ 15 ký tự") != "", True)
    kiem("lý do 5 ký tự -> từ chối", mo("ve-de-sau", "ngắn") != "", True)
    kiem("mở đúng -> OK", mo("ve-de-sau", "việc này founder chưa giao, tự rà thêm") == "", True)
    kiem("lấy lần 1 -> có lý do", lay("ve-de-sau") is not None, True)
    kiem("lấy lần 2 -> KHÔNG (dùng một lần)", lay("ve-de-sau") is None, True)
    mo("nghi-truoc", "cờ này cố ý để quá hạn cho ca thử")
    b = json.load(open(_duong("nghi-truoc"), encoding="utf-8"))
    b["luc"] = time.time() - (HAN_PHUT + 1) * 60
    json.dump(b, open(_duong("nghi-truoc"), "w", encoding="utf-8"), ensure_ascii=False)
    kiem("cờ quá hạn -> KHÔNG cho qua", lay("nghi-truoc") is None, True)
    kiem("cờ quá hạn cũng bị xoá", os.path.exists(_duong("nghi-truoc")), False)
    kiem("chưa mở cờ -> KHÔNG", lay("phan-bua") is None, True)
    # W39 — cờ không cháy oan khi lệnh hỏng: cùng khoá được qua lại, khoá khác thì không.
    mo("git-ngoai-vung", "ca thử: commit lần một hỏng vì móc kiểm, chạy lại y nguyên")
    kiem("dùng cờ có khoá -> qua", lay("git-ngoai-vung", khoa="W01|a.ts") is not None, True)
    kiem("chạy lại CÙNG khoá, không cờ mới -> qua", lay("git-ngoai-vung", khoa="W01|a.ts") is not None, True)
    kiem("KHOÁ KHÁC, không cờ mới -> KHÔNG", lay("git-ngoai-vung", khoa="W01|b.ts") is None, True)
    kiem("không truyền khoá -> KHÔNG (y như cũ)", lay("git-ngoai-vung") is None, True)
    b2 = json.load(open(_duong_dung_lai("git-ngoai-vung"), encoding="utf-8"))
    b2["luc"] = time.time() - (HAN_DUNG_LAI_PHUT + 1) * 60
    json.dump(b2, open(_duong_dung_lai("git-ngoai-vung"), "w", encoding="utf-8"))
    kiem("cùng khoá nhưng QUÁ HẠN -> KHÔNG", lay("git-ngoai-vung", khoa="W01|a.ts") is None, True)
    globals()["THU_MUC"] = goc
    globals()["NHAT_KY_BEN"] = nk_goc
    print("  ==> %d/13 ca đúng" % (13 - loi))
    return 1 if loi else 0


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if a[0] == "--ca-thu":
        return _ca_thu()
    if a[0] in ("xem", "liet-ke"):
        return _xem()
    if a[0] == "mo":
        if len(a) < 3:
            print("Thiếu tham số. Mẫu:\n    %s" % lenh_mau("<tên-cổng>"))
            return 2
        con, cho = [], ""
        i = 2
        while i < len(a):
            if a[i] == "--cho" and i + 1 < len(a):
                cho = a[i + 1]
                i += 2
                continue
            con.append(a[i])
            i += 1
        loi = mo(a[1], " ".join(con), ai=os.environ.get("CLAUDE_AGENT_ID") or "main", cho=cho)
        if loi:
            print("❌ " + loi)
            return 2
        print("🔓 Đã mở cửa thoát cổng «%s»%s — DÙNG MỘT LẦN, hết hạn sau %.0f phút.\n"
              "   Giờ trả lời founder bằng câu bình thường, KHÔNG viết ký hiệu nào vào đó."
              % (a[1], (" cho %s" % cho) if cho else "", HAN_PHUT))
        if not cho and a[1] in CONG_PHAI_CO_CHU:
            print("   ⚠️  Cổng này chỉ chạy cho THỢ — cờ không `--cho <W##|agent_id>` thì "
                  "không thợ nào lấy được (chống thợ khác dùng mất).")
        return 0
    print("Lệnh không hiểu. Dùng: mo | xem | --ca-thu")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("cua_thoat.py lỗi: %s" % e)
        sys.exit(2)
