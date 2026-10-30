#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cong_tep.py — cổng tệp của `sep_viec.py gui --tep` (oHa-28102026-02, chép Fulfill scripts/task-dev.mjs:1202-1220).

GỐC: `gui --tep` gửi thẳng mọi tệp, không đo → PDF in thẳng Markdown ra A4 lọt tới người (anh Thành chê «format xấu»).
  .pdf → chạy pdf/kiem_infographic.py; rớt = CHẶN gửi (mã thoát 1).
  .md  → tự dựng PDF bằng lam_pdf (khuôn infographic Fulfill, tự qua cổng) rồi gửi CẢ HAI: PDF trước, .md nối sau
         (Fulfill 11/10: tệp chữ để chủ nhà chép / chuyển người khác).
  tệp khác (.csv .xlsx .txt …) → đi thẳng.

Dùng trong sep_viec.py:  ds = cong_tep.loc(duong_tep)  → danh sách tệp gửi theo thứ tự.
Thử tay:                  python3 scripts/sep-viec/cong_tep.py <tệp>   → in danh sách, mã thoát như khi gửi.
"""
import os
import subprocess
import sys
import tempfile

DAY = os.path.dirname(os.path.abspath(__file__))


def loc(duong):
    duoi = os.path.splitext(duong)[1].lower()
    if duoi == ".md":
        pdf = os.path.join(tempfile.mkdtemp(prefix="sep-viec-pdf-"), os.path.splitext(os.path.basename(duong))[0] + ".pdf")
        r = subprocess.run([os.path.join(DAY, "lam_pdf"), duong, "--ra", pdf])
        if r.returncode != 0 or not os.path.isfile(pdf):
            print(f"Dựng PDF từ «{duong}» rớt (lam_pdf mã {r.returncode}) — không gửi. Sửa .md theo lời cổng ở trên.", file=sys.stderr)
            sys.exit(1)
        return [pdf, duong]
    if duoi == ".pdf":
        r = subprocess.run([sys.executable, os.path.join(DAY, "pdf", "kiem_infographic.py"), duong])
        if r.returncode != 0:
            print(f"Tệp «{duong}» chưa phải infographic — không gửi. Viết .md rồi gửi thẳng .md "
                  "(tự dựng PDF), hoặc: scripts/sep-viec/lam_pdf <tệp.md> --ra <tệp.pdf>", file=sys.stderr)
            sys.exit(1)
    return [duong]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Dùng: python3 scripts/sep-viec/cong_tep.py <tệp>")
    print("\n".join(loc(sys.argv[1])))
