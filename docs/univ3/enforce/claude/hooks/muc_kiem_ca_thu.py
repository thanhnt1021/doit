#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""muc_kiem_ca_thu.py — kéo hai bộ ca thử về ĐÚNG LƯỢT CHẠY CHUNG.

`chay-het-ca-thu.sh` chỉ gom tệp tên `*_ca_thu.py`; ca thử của hai cổng tin nhóm lại nằm
TRONG chính tệp cổng (`--tu-kiem`) nên trước nay không bộ nào chạy tới — đúng cái bệnh
"sửa 1 hook là gãy âm thầm hook khác" mà script gom kia sinh ra để trị.

Gom:
  · `tin_nhom_trung_thuc_gate.py` — MỨC KIỂM + trạng thái CHỜ NGƯỜI DÙNG XÁC NHẬN (W05).
  · `tin_van_hanh_gate.py`        — tin gửi nhóm vận hành còn dính chữ kỹ thuật.

Chạy: python3 muc_kiem_ca_thu.py   (mã thoát 0 = cả hai bộ ĐẠT)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def chay() -> int:
    loi = 0
    for ten in ("tin_nhom_trung_thuc_gate", "tin_van_hanh_gate"):
        print("── %s ──" % ten)
        mo_dun = __import__(ten)
        loi += int(mo_dun.tu_kiem() or 0)
        print("")
    print("KẾT: %s" % ("ĐẠT HẾT" if not loi else "CÓ BỘ TRƯỢT"))
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(chay())
