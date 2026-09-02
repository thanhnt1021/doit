#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""shared_file_deploy_enforce.py — TỆP DÙNG CHUNG phải TẢI-VỀ → SỬA → ĐẨY,
và phiên nào có đẩy thì CUỐI PHIÊN phải verify lại prod.

BÀI HỌC THẬT (2026-08-25, ba lần trong một phiên): worker giẫm chân nhau lên cùng một tệp.
Lần thứ ba suýt mở lại lỗ hổng vừa bịt: lúc 11:53 một worker sửa link `/pages/lien-he` đã
**đẩy bản `.htaccess` trong kho mã đè lên bản đang chạy**, xoá sạch 4 luật chặn của worker
bảo mật. Đo trên prod ngay sau đó:
    /admin.php        403 -> 200   (trang quản trị cũ, KHÔNG có chống dò mật khẩu)
    /admin-config.php 403 -> 200   (chứa chuỗi mã hoá mật khẩu)
    /orders-status.json, /fetcher.php, /count.php   mất luật chặn
May là PHP vẫn thực thi nên thân phản hồi 0 byte — **ăn may, không phải thiết kế**.

Điểm mấu chốt: `ps aux | grep ftp_push` KHÔNG bắt được vì worker kia dùng script tên riêng.
Thứ duy nhất bắt được là **worker bảo mật tự verify lại prod SAU KHI đã báo cáo xong**.

Nên hook này ép hai thứ, đều nhìn vào HÀNH VI chứ không nhìn tên script:
  A. PreToolUse `Bash` — lệnh sắp ĐẨY một tệp dùng chung lên máy chủ:
     * BỌC TỰ ĐỘNG (26/8, founder chốt) — thay vì từ chối thẳng, hook VIẾT LẠI lệnh
       (`hookSpecificOutput.updatedInput`, có từ claude-code 2.x) cho đi qua
       `deploy-shared.sh`: xin khoá theo tài nguyên -> tải bản đang chạy về -> gộp thay
       đổi của worker lên đó -> đẩy -> verify HTTP thật -> lệch thì tự khôi phục.
       Worker không phải bấm gì, không phải nhớ gì; task vẫn xong một mạch.
       Điều kiện bọc: tệp được nêu ĐÍCH DANH (biết chắc đẩy tệp nào) -> đảo được lệnh
       đẩy thành lệnh tải. Không nêu đích danh (đẩy cả thư mục) thì không đảo được ->
       giữ chặn + đưa sẵn lệnh đã bọc để agent chạy ngay bước sau.
     * chặn (deny) nếu bản sắp đẩy KHÔNG được dựng từ bản đang chạy, đo bằng: có bước
       TẢI VỀ tệp đó trong phiên (hook tự ghi nhật ký khi thấy lệnh tải) và mtime của tệp
       sắp đẩy phải MỚI HƠN lần tải đó (tải xong rồi mới sửa);
     * CHO QUA + chèn lời nhắc mạnh (allow + additionalContext) khi lệnh rõ ràng là đẩy
       nhưng KHÔNG nêu tên tệp (đẩy cả thư mục, script tự quét) — không đủ dữ kiện để chặn
       cứng. 26/8 founder chốt: hook KHÔNG được hỏi (founder đi vắng, hỏi = kẹt cả phiên),
       chỉ chặn cứng thứ làm MẤT việc của người khác. Đánh đổi: lượt đẩy cả thư mục có tệp
       dùng chung nay chỉ được NHẮC, agent phải tự đọc và tự làm TẢI-VỀ → SỬA → ĐẨY.

  A'. Nhận diện "đẩy" chỉ nhìn VỊ TRÍ LỆNH (`tu_lenh`) sau khi đã bỏ THÂN heredoc — 26/8
      một lệnh chỉ ghi tệp local rồi `tsc` bị xếp nhầm là lệnh đẩy vì trong mã Python có
      chuỗi 'src/lib/pipeline/push-drive.ts'.
  B. Stop / SubagentStop — phiên đã đẩy mà CHƯA verify lại prod sau lần đẩy cuối:
     chặn đóng phiên ĐÚNG MỘT LẦN, yêu cầu verify. Verify = lệnh gọi HTTP tới prod
     (`curl`/`wget` tới http(s)://) chạy SAU lần đẩy cuối.

CHO QUA (chặn nhầm là nghẽn việc): lệnh chỉ đọc/tải về · thao tác git (`git push` KHÔNG
phải deploy) · rsync/scp cục bộ (không có `user@host:` hay `://`) · đẩy tệp không nằm
trong danh sách dùng chung · phiên không hề đẩy gì (Stop im lặng) · cửa thoát `shared-ok`.

Fail-open tuyệt đối: lỗi bất kỳ -> exit 0.
"""
import json
import os
import re
import shlex
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



ESCAPE = "shared-ok"
# Script bọc 5 bước — hook viết lại lệnh cho đi qua đây (xem docstring §A).
WRAPPER = os.path.expanduser(
    os.environ.get("UNIV3_DEPLOY_WRAPPER",
                   "~/.claude/universal-hooks/deploy-shared.sh"))
STATE_ROOT = os.environ.get("UNIV3_DEPLOY_STATE", "/tmp/claude-deploy-state")

# Tệp DÙNG CHUNG: nhiều worker cùng đụng, đẩy đè là mất việc của người khác.
# Nối thêm bằng UNIV3_SHARED_FILES="a.js,b.css" (theo tên tệp, không phải đường dẫn).
SHARED = {".htaccess", ".user.ini", "index.html", "order.php", "assemble.py",
          "clone-cart.js", "longchau-redesign.css", "timber.js",
          "nginx.conf", "httpd.conf", "web.config", "php.ini", "robots.txt",
          "sitemap.xml", "wp-config.php"}
SHARED |= {x.strip() for x in os.environ.get("UNIV3_SHARED_FILES", "").split(",") if x.strip()}

# Tệp CẤU HÌNH MÁY CHỦ: nhóm nguy hiểm nhất — đẩy bản kho mã đè lên là gỡ luật chặn của
# người khác (đúng sự cố 11:53). Nhóm này bị CHẶN kể cả khi chỉ nằm trong thư mục sắp đẩy;
# các tệp dùng chung còn lại nếu chỉ "nằm trong thư mục" thì HỎI, vì đẩy cả thư mục build
# (luôn có index.html) là việc bình thường, chặn cứng sẽ nghẽn.
CONFIG = {".htaccess", ".user.ini", "nginx.conf", "httpd.conf", "web.config",
          "php.ini", "wp-config.php"}

# Công cụ chuyển tệp lên máy chủ — nhận diện theo HÀNH VI, không theo tên script.
XFER = {"lftp", "ftp", "sftp", "ncftpput", "s3cmd", "rclone", "wrangler", "surge"}
XFER_REMOTE = {"rsync", "scp"}          # chỉ tính khi có đích từ xa
NOT_DEPLOY = {"git", "gh", "npm", "pnpm", "yarn", "pip", "pip3", "brew", "docker"}
# Script tự đặt tên kiểu deploy (bài học: tên nào cũng có, nên chỉ dùng để HỎI, không chặn)
DEPLOY_NAME = re.compile(r"(deploy|push|upload|publish|release|day[-_]?len|ftp|sync)",
                         re.I)
SCRIPT_EXT = (".py", ".sh", ".js", ".mjs", ".ts", ".php", ".rb", ".pl")
# 26/8: thêm dạng KHÔNG có `user@` — `scp tep may-chu:/duong/dan` là cách gõ phổ biến
# nhất nhưng regex cũ đòi `@` nên bỏ lọt hoàn toàn. Chỉ nhận khi sau dấu `:` là `/`
# hoặc `~` (đường dẫn tuyệt đối trên máy đích) -> không bắt nhầm `sed s:a:b:`.
REMOTE = re.compile(r"[\w.-]+@[\w.-]+:|://|(?:^|[\s=])[A-Za-z][\w.-]*:[/~]")
DOWNLOAD = re.compile(r"(?i)\b(curl|wget|lftp|sftp|scp|rsync|aws|s3cmd|rclone)\b")
HTTP_URL = re.compile(r"https?://")


def sess_dir(cwd: str) -> str:
    key = re.sub(r"[^A-Za-z0-9]+", "_", os.path.abspath(cwd or os.getcwd()))[:120]
    d = os.path.join(STATE_ROOT, key)
    os.makedirs(os.path.join(d, "dl"), exist_ok=True)
    return d


def cham(path: str) -> None:
    try:
        with open(path, "w") as fh:
            fh.write(str(time.time()))
    except Exception:
        pass


def doc_luc(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def toks(cmd: str):
    try:
        return shlex.split(cmd, posix=True)
    except Exception:
        return cmd.split()


HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
# Tách đoạn lệnh theo toán tử shell -> biết đâu là VỊ TRÍ LỆNH của từng đoạn.
SEP = re.compile(r"\|\||&&|[;|&\n()]")
# Vỏ bọc: `sudo scp ...`, `timeout 30 rsync ...` -> lệnh thật nằm sau
WRAP = {"sudo", "env", "nohup", "time", "timeout", "nice", "command", "exec",
        "builtin", "stdbuf", "xargs"}
INTERP = {"bash", "sh", "zsh", "ksh", "dash", "python", "python2", "python3",
          "node", "perl", "ruby", "php", "tsx", "ts-node", "deno"}
GAN_BIEN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def bo_than_heredoc(cmd: str) -> str:
    """Bỏ THÂN heredoc — đó là DỮ LIỆU (mã Python, nội dung tệp), KHÔNG phải lệnh shell.

    BÀI HỌC 26/8: `python3 - <<'PY' ... p='src/lib/pipeline/push-drive.ts' ... PY`
    chỉ ghi tệp trong kho mã local rồi `tsc`, nhưng hook quét cả thân heredoc, thấy chuỗi
    kết thúc `.ts` và chứa chữ `push` nên xếp thành 'lệnh đẩy lên máy chủ' -> hỏi oan,
    founder đi vắng là kẹt phiên."""
    ra, cho = [], []
    for dong in cmd.split("\n"):
        if cho:
            if dong.strip() in (cho[0], cho[0] + ";"):
                cho.pop(0)
            continue
        ra.append(dong)
        for m in HEREDOC.finditer(dong):
            cho.append(m.group(2))
    return "\n".join(ra)


def tu_lenh(cmd: str):
    """[(tên_chương_trình, đoạn_lệnh, token_của_đoạn, token_gốc)] — thứ THẬT SỰ được chạy.

    Chỉ nhìn VỊ TRÍ LỆNH của từng đoạn (đầu đoạn, sau `;` `&&` `||` `|`), bỏ gán biến
    `VAR=...`, bỏ vỏ bọc `sudo/timeout/...`. Trước đây hook quét MỌI token của cả lệnh nên
    một chuỗi bất kỳ trùng tên script cũng bị coi là lệnh đẩy."""
    ra = []
    for doan in SEP.split(bo_than_heredoc(cmd)):
        t = toks(doan)
        i = 0
        while i < len(t):
            x = t[i]
            if GAN_BIEN.match(x):
                i += 1
                continue
            b = x.rsplit("/", 1)[-1]
            if b in WRAP:
                i += 1
                while i < len(t) and (t[i].startswith("-") or
                                      re.match(r"^\d+[smhd]?$", t[i])):
                    i += 1
                continue
            ra.append((b, doan, t[i:], x))
            if b in INTERP:            # `bash deploy.sh` -> deploy.sh cũng là 'từ lệnh'
                for y in t[i + 1:]:
                    if y.startswith("<") or y.startswith(">"):
                        break
                    if y.startswith("-"):
                        continue
                    ra.append((y.rsplit("/", 1)[-1], doan, t[i:], y))
                    break
            break
    return ra


def la_tep(x: str, cwd: str) -> bool:
    try:
        return os.path.isfile(x if os.path.isabs(x) else os.path.join(cwd or ".", x))
    except Exception:
        return False


def la_upload_curl(t) -> bool:
    return "curl" in [x.rsplit("/", 1)[-1] for x in t] and any(
        x in ("-T", "--upload-file") or x.startswith("--upload-file=") for x in t)


def phan_loai(cmd: str, t, cwd: str = ""):
    """('day'|'tai'|'') — lệnh này ĐẨY lên máy chủ, TẢI về, hay không liên quan.

    Chỉ xét những chương trình THẬT SỰ được chạy (`tu_lenh`), không quét bừa mọi token."""
    cmd_s = bo_than_heredoc(cmd)
    for b, doan, tt, goc in tu_lenh(cmd):
        if b in NOT_DEPLOY:
            continue
        if b in XFER:
            # lftp/sftp cũng dùng để tải về: có `get`/`mget`/`mirror` (không `-R`) -> tải
            # `get` hay nằm trong chuỗi nháy `lftp -c 'open h; get x'` -> soi CẢ lệnh,
            # vì tách đoạn theo `;` cắt luôn bên trong dấu nháy.
            if b in ("lftp", "sftp") and re.search(r"(?i)\b(get|mget)\b", cmd_s) and \
                    not re.search(r"(?i)\b(put|mput|mirror\s+-R)\b", cmd_s):
                return "tai"
            return "day"
        if b in XFER_REMOTE and REMOTE.search(doan):
            # scp remote:… local  = tải về; scp local remote:…  = đẩy
            args = [x for x in tt if not x.startswith("-")][1:]
            if args and REMOTE.search(args[-1]):
                return "day"
            return "tai"
        if b == "curl" and la_upload_curl(tt):
            return "day"
        if b == "ssh" and re.search(r">\s*\S", doan):
            return "day"                      # ssh host 'cat > tệp' = ghi lên máy chủ
        if b == "aws" and re.search(r"(?i)\bs3\s+(cp|sync)\b", doan):
            return "day" if "s3://" in doan.rsplit(" ", 1)[-1] else "tai"
        # script tự đặt tên kiểu deploy — CHỈ tính khi nó thật sự là tệp đang chạy
        if b.endswith(SCRIPT_EXT) and DEPLOY_NAME.search(b):
            # Trừ công cụ luật nằm trong universal-hooks (sync-uni.sh, wlock.sh…): chúng chỉ
            # nói chuyện với GitHub, không đụng máy chủ web, nhưng tên lại chứa "sync"/"push"
            # nên bị bắt nhầm — 25/8 đúng lỗi này đã chặn một lượt đẩy luật lên SSOT.
            if "universal-hooks/" in goc:
                continue
            if not la_tep(goc, cwd):
                continue          # chuỗi trùng tên script chứ không phải script đang chạy
            return "day"
    if DOWNLOAD.search(cmd_s) and HTTP_URL.search(cmd_s):
        return "tai"
    return ""


# Thư mục build/phụ thuộc: nội dung là artifact sinh ra, không phải tệp dùng chung.
BUILD_DIRS = {".next", "node_modules", "dist", "build", "out", ".git", ".turbo",
              ".cache", ".parcel-cache", "coverage", "vendor", "__pycache__",
              ".venv", "venv", ".output", ".svelte-kit", ".nuxt"}


def la_thu_muc_build(ten: str) -> bool:
    return ten in BUILD_DIRS or ten.startswith(".next-") or ten.startswith("node_modules")


def tep_dung_chung(t, cwd: str):
    """([(đường_dẫn, tên)] tệp dùng chung, có_nêu_rõ_danh_sách_tệp_hay_không).

    "Nêu rõ" = mọi đối số đường dẫn đều là TỆP cụ thể đang tồn tại -> biết chắc lượt đẩy
    gồm những gì. Có thư mục hoặc không có đối số nào -> không đủ dữ kiện, phải hỏi lại."""
    ra, seen = [], set()
    co_tep, co_thu_muc = False, False
    # ra: [(đường_dẫn, tên, nêu_đích_danh?)]
    for x in t:
        if x.startswith("-"):
            continue
        p = x if os.path.isabs(x) else os.path.join(cwd or ".", x)
        name = os.path.basename(x.rstrip("/"))
        if os.path.isfile(p):
            co_tep = True
        if name in SHARED and os.path.isfile(p) and p not in seen:
            seen.add(p)
            ra.append((p, name, True))
        elif os.path.isdir(p):
            co_thu_muc = True
            for goc, thu, tep in os.walk(p):
                # Cắt hẳn nhánh build tạm: 25/8 hook chặn nhầm một lệnh ĐẨY LUẬT LÊN GITHUB
                # chỉ vì cây thư mục có `.next-batch/server/app/index.html` — rác do build
                # sinh ra, không phải tệp dùng chung của máy chủ. Chỉ cắt THƯ MỤC CON: ai
                # trỏ thẳng vào `.next` để đẩy thì vẫn phải soi như thường.
                thu[:] = [x for x in thu if not la_thu_muc_build(x)]
                if goc.count(os.sep) - p.count(os.sep) > 3:
                    continue
                for f in tep:
                    if f in SHARED:
                        fp = os.path.join(goc, f)
                        if fp not in seen:
                            seen.add(fp)
                            ra.append((fp, f, False))
    return ra, (co_tep and not co_thu_muc)


def lenh_da_boc(cmd: str, files):
    """Lệnh gốc -> lệnh ĐÃ BỌC qua deploy-shared.sh (chuỗi shell, đã trích dẫn an toàn).

    Bọc bằng `bash -c '<lệnh gốc>'` để lệnh ghép (`cd x && scp ...`) vẫn chạy nguyên văn."""
    tep = " ".join("--tep " + shlex.quote(p) for p, _, _ in files)
    return "bash %s %s -- bash -c %s" % (shlex.quote(WRAPPER), tep, shlex.quote(cmd))


HOW_TO = """CÁCH ĐÚNG — TẢI VỀ → SỬA → ĐẨY (rules/AGENTS-ORCH.md §Tệp-dùng-chung):
  1. TẢI bản ĐANG CHẠY về trước (đây là bản duy nhất đúng — worker khác có thể vừa sửa):
        curl -fsS https://<miền>/<tệp> -o <tệp>        # hoặc lftp get / scp <host>:<tệp> .
  2. Sửa ĐÚNG phần của mình trên bản vừa tải, giữ nguyên mọi thứ khác.
  3. Đẩy lên, rồi VERIFY LẠI PROD bằng HTTP thật (không tin bản trong kho mã).
  4. Xin khoá trước khi đẩy: `bash ~/.claude/universal-hooks/wlock.sh run deploy --owner=<slug> -- <lệnh đẩy>`

VÌ SAO CẤM ĐẨY BẢN TRONG KHO MÃ ĐÈ LÊN: 25/8 lúc 11:53 một worker làm đúng thế với
`.htaccess` → xoá 4 luật chặn của worker bảo mật → `/admin.php` và `/admin-config.php`
từ 403 thành 200, mở ra Internet. Kho mã KHÔNG phải nguồn sự thật cho tệp dùng chung.

Tệp này thật sự chỉ mình bạn sở hữu và founder đã đồng ý → thêm `shared-ok` vào lệnh."""


def bash(data) -> int:
    cmd = str((data.get("tool_input") or {}).get("command") or "")
    if not cmd or ESCAPE in cmd:
        return 0
    cwd = str(data.get("cwd") or os.getcwd())
    t = toks(cmd)
    d = sess_dir(cwd)

    # Lệnh ĐÃ BỌC (do chính hook viết lại, hoặc agent tự gọi): wrapper đã tự verify bằng
    # HTTP thật ở bước 4 -> đóng dấu luôn để cổng Stop không đòi verify lần nữa.
    if os.path.basename(WRAPPER) in cmd:
        cham(os.path.join(d, "deploy.last"))
        cham(os.path.join(d, "verify.last"))
        return 0

    loai = phan_loai(cmd, t, cwd)

    if loai == "tai":
        for x in t:
            name = os.path.basename(x.split("?")[0].rstrip("/"))
            if name in SHARED:
                cham(os.path.join(d, "dl", name))
        if HTTP_URL.search(cmd):
            cham(os.path.join(d, "verify.last"))    # gọi HTTP tới prod = một lần verify
        return 0

    if loai != "day":
        return 0

    cham(os.path.join(d, "deploy.last"))
    files, ro_rang = tep_dung_chung(t, cwd)

    if not files and ro_rang:
        return 0        # đẩy đúng những tệp cụ thể, không con nào là tệp dùng chung

    if not files:
        reason = (
            "XÁC NHẬN TRƯỚC — lệnh này ĐẨY LÊN MÁY CHỦ nhưng không nêu đích danh tệp nào, "
            "nên hook không kiểm được là bạn đẩy bản vừa tải về hay bản trong kho mã.\n\n"
            "Nếu trong lượt đẩy này có TỆP DÙNG CHUNG (" + ", ".join(sorted(SHARED)[:6]) +
            "…) thì phải TẢI VỀ → SỬA → ĐẨY. Đúng lỗi này ngày 25/8 đã mở lại "
            "`/admin.php` ra Internet.\n\n" + HOW_TO)
        json.dump({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "allow",
            "permissionDecisionReason": reason,
            "additionalContext": reason}}, sys.stdout, ensure_ascii=False)
        return 0

    xau = []
    for p, name, dich_danh in files:
        luc_tai = doc_luc(os.path.join(d, "dl", name))
        if luc_tai <= 0:
            ly = "CHƯA hề tải bản đang chạy về trong phiên này"
        elif os.path.getmtime(p) < luc_tai:
            ly = ("bản này CŨ HƠN lần tải gần nhất (%.0f phút trước) — tức chưa dựng lại "
                  "từ bản đang chạy" % ((time.time() - luc_tai) / 60))
        else:
            continue
        xau.append((p, name, ly, dich_danh))
    if not xau:
        return 0

    # Chặn cứng khi: tệp được nêu ĐÍCH DANH, hoặc là tệp CẤU HÌNH MÁY CHỦ (dù chỉ nằm
    # trong thư mục sắp đẩy). Còn lại -> hỏi xác nhận, khỏi nghẽn việc đẩy cả thư mục build.
    cung = [x for x in xau if x[3] or x[1] in CONFIG]
    ds = "\n".join("    - %-22s %s\n      (%s)" % (n, p, ly) for p, n, ly, _ in xau)
    if cung:
        # BỌC TỰ ĐỘNG khi biết chắc đẩy đúng những tệp nào (nêu đích danh) và wrapper có
        # mặt: viết lại lệnh, KHÔNG từ chối -> worker chạy tiếp một mạch mà dữ liệu của
        # người khác vẫn còn. 26/8 founder chốt thay cho `deny` thẳng.
        boc_duoc = all(x[3] for x in cung) and os.path.isfile(WRAPPER)
        if boc_duoc:
            moi = lenh_da_boc(cmd, [(p, n, True) for p, n, _, _ in cung])
            reason = ("TỰ BỌC — lệnh này đẩy TỆP DÙNG CHUNG mà bản sắp đẩy không dựng từ bản "
                      "đang chạy:\n" + ds + "\n\nHook đã VIẾT LẠI lệnh cho đi qua "
                      "`deploy-shared.sh` (không cần bạn làm gì thêm):\n"
                      "  1. xin khoá theo tài nguyên (worker khác đụng cùng tệp sẽ xếp hàng)\n"
                      "  2. tải bản ĐANG CHẠY về, lưu backup 2 nơi\n"
                      "  3. gộp thay đổi của bạn lên bản đó (giữ nguyên phần của người khác)\n"
                      "  4. đẩy rồi verify bằng HTTP thật (403 còn 403, 200 còn 200)\n"
                      "  5. lệch -> tự khôi phục bản ở bước 2 rồi báo lỗi\n\n"
                      "Lệnh thực chạy:\n  " + moi + "\n\n"
                      "Gộp đụng độ (mã 3) hoặc verify lệch (mã 4) -> ĐỌC output rồi sửa, "
                      "đừng ép đẩy lại bằng `shared-ok`.")
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "permissionDecision": "allow",
                "permissionDecisionReason": reason,
                "additionalContext": reason,
                "updatedInput": dict((data.get("tool_input") or {}), command=moi),
            }}, sys.stdout, ensure_ascii=False)
            return 0
        # Không nêu đích danh (đẩy cả thư mục) -> không đảo được lệnh đẩy thành lệnh tải,
        # nên không bọc được. Vẫn chặn, nhưng ĐƯA SẴN lệnh đã bọc để chạy ngay bước sau.
        goi_y = ""
        if os.path.isfile(WRAPPER):
            goi_y = ("\n\nCHẠY NGAY LỆNH NÀY (đã bọc đủ 5 bước, chỉ cần thay <lệnh đẩy chỉ "
                     "riêng tệp đó>):\n  " + lenh_da_boc("<lệnh đẩy CHỈ tệp đó>",
                                                        [(p, n, True) for p, n, _, _ in cung]))
        reason = ("CHẶN — lệnh này đẩy TỆP DÙNG CHUNG mà bản sắp đẩy không được dựng từ bản "
                  "đang chạy, và vì lệnh KHÔNG nêu đích danh tệp nên hook không tự bọc được:\n"
                  + ds + goi_y + "\n\n" + HOW_TO)
        quyet = "deny"
    else:
        reason = ("XÁC NHẬN TRƯỚC — trong lượt đẩy này có TỆP DÙNG CHUNG chưa dựng từ bản "
                  "đang chạy:\n" + ds + "\n\nĐẩy cả thư mục build thì thường là đúng, nhưng "
                  "nếu tệp trên do worker khác cũng đang sửa thì bản của họ sẽ bị xoá.\n\n"
                  + HOW_TO)
        quyet = "allow"
    out = {"hookEventName": "PreToolUse", "permissionDecision": quyet,
           "permissionDecisionReason": reason}
    if quyet == "allow":
        out["additionalContext"] = reason   # cho qua nhưng agent BẮT BUỘC đọc lời nhắc
    json.dump({"hookSpecificOutput": out}, sys.stdout, ensure_ascii=False)
    return 0


def stop(data) -> int:
    """Đã đẩy mà chưa verify lại prod sau lần đẩy cuối -> chặn đóng phiên ĐÚNG 1 lần."""
    d = sess_dir(str(data.get("cwd") or os.getcwd()))
    day = doc_luc(os.path.join(d, "deploy.last"))
    if day <= 0:
        return 0                                   # phiên không đẩy gì -> im
    if doc_luc(os.path.join(d, "verify.last")) >= day:
        return 0                                   # đã verify sau lần đẩy cuối
    nag = os.path.join(d, "nag-%d.flag" % int(day))
    if os.path.exists(nag):
        return 0                                   # đã nhắc rồi -> không nhắc lại, khỏi kẹt
    cham(nag)
    json.dump({"decision": "block", "reason": _viet_lai((
        "CHƯA XONG — phiên này có ĐẨY LÊN MÁY CHỦ (%.0f phút trước) mà chưa verify lại prod "
        "sau đó.\n\nLuật (25/8): worker khác có thể đã đè lên bản của bạn NGAY SAU khi bạn "
        "verify giữa chừng — lần `.htaccess` bị đè xảy ra đúng như vậy và chỉ bị phát hiện "
        "nhờ verify LẠI ở cuối. Verify giữa chừng KHÔNG tính.\n\n"
        "Làm ngay rồi hãy kết thúc:\n"
        "  curl -sS -o /dev/null -w '%%{http_code}\\n' https://<miền>/<đường-dẫn-vừa-sửa>\n"
        "  # tệp cấu hình máy chủ: kiểm cả các đường dẫn ĐÁNG LẼ bị chặn vẫn còn 403\n"
        "Kết quả lệch mong đợi -> sửa lại rồi đẩy lại, đừng báo xong."
        % ((time.time() - day) / 60)),
        sid=str(data.get("session_id") or ""),
        transcript=str(data.get("transcript_path") or ""))},
        sys.stdout, ensure_ascii=False)
    return 0


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    try:
        ev = str(data.get("hook_event_name") or "")
        if ev == "PreToolUse" and str(data.get("tool_name") or "") == "Bash":
            return bash(data)
        if ev in ("Stop", "SubagentStop"):
            return stop(data)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
