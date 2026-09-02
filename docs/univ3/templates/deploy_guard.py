#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deploy_guard.py — CHỐT CHẶN DEPLOY dùng chung: không bao giờ để `.env`, tài liệu,
bản sao lưu `*.bak-*` hay nhật ký chạy ra được web thật.

VÌ SAO CÓ TỆP NÀY (bài học thật, 2026-08-25, dự án nhathuocbenhvien): script đẩy tệp lên
máy chủ quét NGUYÊN thư mục gốc và KHÔNG có bộ lọc nào. Trong vùng quét lúc đó có 9 tệp
`index.html.bak-*`, một tệp `*.bak-env` chứa mật khẩu FTP nguyên chữ, và cả thư mục
`docs/` chứa mật khẩu quản trị. Chỉ là MAY chưa bị đẩy lên. Chốt chặn này biến cái may
đó thành cái chắc.

CÁCH GẮN VÀO SCRIPT DEPLOY (2 dòng, đặt NGAY TRƯỚC vòng lặp upload):
    from deploy_guard import guard_or_die          # cùng thư mục với script deploy
    files = guard_or_die(files)                    # có tệp cấm -> DỪNG HẲN, không đẩy gì

Nguyên tắc: FAIL CLOSED — phát hiện một tệp vi phạm là dừng TOÀN BỘ lượt đẩy, không
"đẩy phần còn lại". Đẩy nhầm một tệp là lộ vĩnh viễn, dừng lại chỉ tốn 1 phút.

Dự án nào cần đẩy thêm/bớt loại tệp thì sửa `DEPLOY_DENY` NGAY TRONG BẢN SAO của dự án
đó và ghi lý do — đừng nới lỏng bản dùng chung này.
"""
import re as _re

DEPLOY_DENY = [
    (_re.compile(r"(^|/)\.env($|\.)"),                  "tệp .env (chứa secret thật)"),
    (_re.compile(r"(^|/)docs(/|$)"),                    "thư mục tài liệu nội bộ"),
    (_re.compile(r"\.bak(-|\.|$)"),                     "bản sao lưu *.bak-*"),
    (_re.compile(r"(^|/)backup[^/]*(/|$)"),             "thư mục sao lưu"),
    (_re.compile(r"(^|/)scratchpad(/|$)"),              "thư mục nháp"),
    (_re.compile(r"(^|/)\.git(/|$)"),                   "kho git"),
    (_re.compile(r"(^|/)\.claude(/|$)"),                "cấu hình Claude Code"),
    (_re.compile(r"(^|/)\.DS_Store$"),                  "rác macOS"),
    (_re.compile(r"(^|/)node_modules(/|$)"),            "thư viện nguồn"),
    (_re.compile(r"\.(log|ini|sql|pem|key|p12|env|sqlite3?|db)$", _re.I),
                                                        "nhật ký / khoá / dữ liệu thô"),
    (_re.compile(r"\.md$", _re.I),                      "tài liệu markdown"),
    (_re.compile(r"(^|/)(id_rsa|id_ed25519|\.htpasswd|credentials[^/]*\.json)$", _re.I),
                                                        "khoá riêng / thông tin đăng nhập"),
]


# ── TỆP DÙNG CHUNG: không cấm đẩy, nhưng phải CẢNH BÁO ──────────────
# Bài học 2026-08-25: một worker đẩy bản `.htaccess` trong kho mã đè lên bản đang chạy,
# xoá 4 luật chặn của worker bảo mật -> `/admin.php` và `/admin-config.php` từ 403 thành
# 200, mở ra Internet. Kho mã KHÔNG phải nguồn sự thật cho những tệp này.
SHARED_FILES = {".htaccess", ".user.ini", "index.html", "order.php", "assemble.py",
                "clone-cart.js", "longchau-redesign.css", "timber.js",
                "nginx.conf", "httpd.conf", "web.config", "php.ini", "wp-config.php"}


def shared_in(paths):
    """Danh sách tệp dùng chung có trong lượt đẩy này."""
    return sorted({p for p in paths if str(p).replace("\\", "/").rsplit("/", 1)[-1]
                   in SHARED_FILES})


def deploy_blocked(path):
    """Trả về LÝ DO bị chặn, hoặc None nếu tệp được phép đẩy."""
    name = str(path).replace("\\", "/")
    if ".." in name.split("/"):
        return "đường dẫn chứa '..' (thoát khỏi thư mục gốc)"
    for rx, why in DEPLOY_DENY:
        if rx.search(name):
            return "%s — khớp mẫu cấm `%s`" % (why, rx.pattern)
    return None


def guard_or_die(paths, exit_fn=None):
    """Lọc danh sách tệp sắp đẩy. Có tệp bị cấm -> DỪNG HẲN, không đẩy gì cả."""
    bad = [(p, deploy_blocked(p)) for p in paths]
    bad = [(p, why) for p, why in bad if why]
    if bad:
        import sys as _sys
        print("DỪNG: %d tệp vi phạm chốt chặn deploy, KHÔNG đẩy gì cả:" % len(bad))
        for p, why in bad[:20]:
            print("  CHẶN %s  <- %s" % (p, why))
        if len(bad) > 20:
            print("  ... và %d tệp khác" % (len(bad) - 20))
        print("Cách xử lý: bỏ tệp đó khỏi vùng quét, hoặc dọn nó đi "
              "(secret phải nằm trong .env, chmod 600).")
        (exit_fn or _sys.exit)(2)
    chung = shared_in(paths)
    if chung:
        print("CẢNH BÁO: lượt đẩy này có %d TỆP DÙNG CHUNG — nhiều worker cùng đụng:"
              % len(chung))
        for p in chung[:10]:
            print("  ! %s" % p)
        print("  Quy tắc TẢI-VỀ → SỬA → ĐẨY: bản sắp đẩy PHẢI được dựng từ bản ĐANG CHẠY")
        print("  (curl/lftp get về trước rồi mới sửa), KHÔNG đẩy bản trong kho mã đè lên.")
        print("  Đẩy xong PHẢI verify lại prod bằng HTTP thật — worker khác có thể vừa đè.")
    return list(paths)


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        why = deploy_blocked(arg)
        print(("CHẶN  " + arg + "  <- " + why) if why else ("CHO ĐẨY  " + arg))
