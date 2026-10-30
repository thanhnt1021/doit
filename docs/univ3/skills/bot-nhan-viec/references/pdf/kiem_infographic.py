#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kiem_infographic.py — chép nguyên từ EtsyFulfillChichub docs/templates/kiem-infographic.py (28/10/2026).
CỔNG: tài liệu gửi NGƯỜI (đối tác, xưởng, team, anh Thành) phải là
infographic, không được là trang toàn chữ.

CA GỐC 08/10/2026: tệp hỏi Merchize (1C) xuất ra PDF 2 trang toàn bảng chữ song ngữ (trang 1:
485 chữ, 0 khối màu). Anh Thành: «nhìn trông kinh … đéo có hình minh hoạ infographic visual gì
cả đéo ai mà hiểu … fix root cause». Cùng ngày 2 ảnh hướng dẫn Flowdy (sơ đồ bước + icon + ít
chữ) được khen -> đó là chuẩn. Luật chữ = xác suất, nên đo bằng máy:

  PDF : MỖI trang phải có khối hình — trong phần CÓ MỰC của trang (điểm ảnh không trắng), tỉ lệ
        là màu đậm / nền màu nhạt ≥ NGUONG_HINH (đo trên bản dựng 30 dpi; tính trên phần có mực để
        trang ngắn không bị phạt oan) — VÀ ≤ TRAN_CHU chữ. Đo 08/10: PDF toàn chữ cũ 1C = 0,14–0,16
        / 474 chữ; tài liệu chữ + vài khung (Flowdy 07/10, KPI 02/10) = 0,17–0,26; bản infographic
        1C mới = 0,47–0,61; ảnh Flowdy = 0,75; mẫu = 0,84–0,96.
  MD  : phải nhúng ảnh (`![…](…)`) trong 15 dòng có chữ đầu tiên, và không có đoạn văn
        trơn nào dài quá TRAN_DONG ký tự (ý dài -> tách gạch đầu dòng / bảng).
  PNG/JPG: tỉ lệ khối hình ≥ NGUONG_HINH (ảnh chụp chữ trắng trơn không qua).

Dùng:  python3 scripts/sep-viec/pdf/kiem_infographic.py <tệp> [<tệp> …]   -> exit 0 đạt, 1 rớt, 2 lỗi dùng.
Gắn vào: scripts/sep-viec/pdf/lam_pdf.mjs — chạy trên chính PDF vừa dựng.
Cách làm đạt: viết .md rồi `node scripts/sep-viec/pdf/lam_pdf.mjs <tệp.md> --ra <tệp.pdf>`
(ra PNG từng trang + PDF khung 1080×1600 theo mẫu infographic của Fulfill).
"""
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

NGUONG_HINH = 0.35
TRAN_CHU = 420
TRAN_DONG = 300


def ti_le_hinh(png):
    from PIL import Image
    im = Image.open(png).convert('RGB')
    im.thumbnail((400, 600))
    px = list(im.getdata())
    mau = sum(1 for r, g, b in px if max(r, g, b) - min(r, g, b) > 40)
    nen = sum(1 for r, g, b in px if 12 < max(r, g, b) - min(r, g, b) <= 40 and min(r, g, b) > 150)
    muc = sum(1 for r, g, b in px if min(r, g, b) < 235)
    return (mau + nen) / max(muc, 1)


def kiem_pdf(f):
    loi = []
    if not shutil.which('pdftoppm') or not shutil.which('pdftotext'):
        return ['máy thiếu poppler (pdftoppm/pdftotext) — cài: brew install poppler']
    d = tempfile.mkdtemp()
    subprocess.run(['pdftoppm', '-r', '30', '-png', f, d + '/p'], check=True, capture_output=True)
    trang = sorted(glob.glob(d + '/p*.png'))
    for i, p in enumerate(trang, 1):
        h = ti_le_hinh(p)
        chu = len(subprocess.run(['pdftotext', '-f', str(i), '-l', str(i), f, '-'],
                                 capture_output=True, text=True).stdout.split())
        if h < NGUONG_HINH:
            loi.append(f'trang {i}: gần như toàn chữ (khối hình {h:.3f} < {NGUONG_HINH}) — thêm sơ đồ bước / khối màu / icon')
        if chu > TRAN_CHU:
            loi.append(f'trang {i}: {chu} chữ > {TRAN_CHU} — cắt chữ, chuyển ý thành bước/bảng nhỏ')
    shutil.rmtree(d, ignore_errors=True)
    return loi


def kiem_md(f):
    loi = []
    dong = open(f, encoding='utf-8').read().split('\n')
    co_chu = [l for l in dong if l.strip()]
    if not any(re.search(r'!\[[^\]]*\]\([^)]+\)', l) for l in co_chu[:15]):
        loi.append('không nhúng ảnh infographic ở đầu tệp (`![…](anh.png)` trong 15 dòng đầu)')
    trong_code = False
    for i, l in enumerate(dong, 1):
        if l.strip().startswith('```'):
            trong_code = not trong_code
            continue
        s = l.strip()
        if trong_code or not s or s[0] in '|#>-*!<' or re.match(r'^\d+\.', s):
            continue
        if len(s) > TRAN_DONG:
            loi.append(f'dòng {i}: đoạn văn trơn {len(s)} ký tự > {TRAN_DONG} — tách gạch đầu dòng có icon')
    return loi


def kiem_anh(f):
    h = ti_le_hinh(f)
    return [] if h >= NGUONG_HINH else [f'ảnh gần như toàn chữ (khối hình {h:.3f} < {NGUONG_HINH})']


def main(ds):
    if not ds:
        print(__doc__)
        return 2
    rot = 0
    for f in ds:
        if not os.path.isfile(f):
            print(f'✗ {f}: không có tệp')
            rot = 1
            continue
        duoi = os.path.splitext(f)[1].lower()
        loi = (kiem_pdf(f) if duoi == '.pdf' else kiem_md(f) if duoi == '.md'
               else kiem_anh(f) if duoi in ('.png', '.jpg', '.jpeg') else None)
        if loi is None:
            print(f'· {f}: loại tệp không soi (chỉ soi .pdf .md .png .jpg)')
            continue
        if loi:
            rot = 1
            print(f'✗ {f} — CHƯA PHẢI INFOGRAPHIC:')
            for x in loi:
                print('   - ' + x)
        else:
            print(f'✓ {f}')
    if rot:
        print('\nMỗi ý một dòng ngắn có icon 🔴🟡🟢✅, bớt đoạn văn trơn, dựng lại bằng'
              ' scripts/sep-viec/pdf/lam_pdf.mjs. Luật: Fulfill docs/univ3/rules/WORKFLOWS.md §Tài-liệu-gửi-người.')
    return rot


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
