#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""db_that_gate.py — CỔNG: CẤM tra DB DEV rồi kết luận như dữ liệu THẬT.

BỆNH THẬT (28/08/2026, đo được bằng lệnh — không đoán):
main chạy hàng loạt lệnh kiểu

    DB_URL="$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2- | tr -d '"')" node .w25-kind.mjs

rồi báo cáo cho founder *"bảng `sku_csv_import` trống hoàn toàn — 0 dòng, không có dòng
nào từ trước tới giờ"*. Nhưng:

    grep -m1 '^DATABASE_URL=' .env  ->  host=localhost:5432 db=chichub_dev

`.env` của repo trỏ **DB DEV**, không phải DB sống. Founder mắng: *"thế tại sao lúc làm
việc không dùng .env của dự án thật mà lại đi trỏ về cái DB giả rồi kết luận thật nhỉ???
đéo có rule nào dạy mày à?????"*

LUẬT ĐÃ CÓ MÀ KHÔNG AI TUÂN — `CLAUDE.md` §"KHO CÔNG CỤ VERIFY": *"DB dev qua tunnel:
localhost:5432 -> chichub_dev. DB demo/prod qua CÙNG tunnel: đổi dbname connection."*
Và memory `prod-app-dung-chichub-demo-db`: **DB sống DUY NHẤT = `chichub_bigdb`**.
Markdown = xác suất; cổng = tất định -> dựng cổng.

VÌ SAO CHẶN Ở PreToolUse:Bash (không phải `Stop`):
chặn ở `Stop` là chặn SAU khi con số sai đã nằm trong đầu main — lúc đó main đã tin
"0 dòng" rồi, cãi lại chính mình rất khó. Chặn TRƯỚC khi lệnh chạy thì không có con số
sai nào ra đời. Đây là cổng DUY NHẤT, cố ý không đẻ thêm lớp `Stop`: lớp đó phải đoán
"câu này có phải kết luận về dữ liệu không" -> chặn oan hàng loạt, làm main câm.

LUỒNG QUYẾT ĐỊNH (dừng ở bước nào thì trả kết quả bước đó):
  1. lệnh KHÔNG nối DB (không có `pg.Client` / `postgres://` / `psql` / `connectionString`…)
     -> CHO QUA. (`grep DATABASE_URL .env` đơn thuần để CHẨN ĐOÁN vẫn chạy được.)
  2. lệnh nêu RÕ tên DB sống (`chichub_bigdb` / `chichub_demo` / `chichub`) -> CHO QUA.
     Kể cả kiểu `.replace('/chichub_dev','/chichub_bigdb')` — đích cuối là DB sống.
  3. lệnh nêu rõ tên DB dev (`..._dev` / `..._test` / `..._local`) -> CHẶN.
  4. lệnh lấy `DATABASE_URL` TRẦN (từ `.env`, `process.env`, `dotenv`) mà không nêu DB đích:
     đọc `.env` thật của thư mục làm việc -> dbname là dev-ish thì CHẶN, ngược lại CHO QUA.
     (Founder sửa `.env` trỏ DB sống thì cổng tự hết chặn — không hard-code.)
  5. họ lệnh schema của Prisma (`migrate` / `db push` / `db pull` / `generate` / `studio`
     KHÔNG nằm trong nhóm này) -> CHO QUA: chúng BUỘC chạy trên DB dev, chặn là chặn oan.

CỬA THOÁT (ghi nhật ký 2 nơi) — thật sự muốn tra DB dev, vd đang dựng ca thử:
    dung-db-dev-co-y: <lý do >= 15 ký tự>
viết thẳng trong chính lệnh (comment shell cũng được). Thiếu lý do = vẫn chặn.

FAIL-OPEN: mọi bất trắc -> exit 0.

TỰ KIỂM:
    python3 db_that_gate.py --ca-thu        # 6 ca THẬT trích từ transcript 28/08
    python3 db_that_gate.py --thu '<lệnh>' [thư-mục]
"""
import json
import os
import re
import sys
import time

LOG_TMP = "/tmp/claude_hooks/db-that-gate.log"
LOG_BEN = os.path.expanduser("~/.claude/logs/db-that-gate.log")

CUA_THOAT = "dung-db-dev-co-y"
RE_VUOT_CONG = re.compile(re.escape(CUA_THOAT) + r"\s*:\s*(.{15,})", re.I | re.S)

# 1. DẤU HIỆU NỐI DB — cố ý KHÔNG bắt `.query(` trần (quá rộng, dính mọi ORM/HTTP).
RE_NOI_DB = re.compile(
    r"pg\.Client|pg\.Pool|new\s+Client\s*\(|new\s+Pool\s*\("
    r"|postgres(?:ql)?://|\bpsql\b|connectionString|PGDATABASE"
    r"|\$queryRaw|\$executeRaw|pg_dump|pg_restore"
    # biến DB gán ngay trước khi chạy script -> chắc chắn là đi nối DB, dù câu lệnh
    # không chứa chữ `pg.Client` nào (file .mjs đã được viết ở lệnh trước).
    r"|(?:DB_URL|DATABASE_URL|PGPASSWORD|PGUSER|PGHOST)\s*=[^\n]{0,200}?"
    r"\b(?:node|tsx|ts-node|bun|deno|python3?)\b",
    re.I)

# 2. TÊN DB SỐNG nêu rõ trong lệnh -> yên tâm cho qua.
#    `\bchichub\b` KHÔNG dính `chichub_user` (dấu `_` là ký tự từ nên mất ranh giới).
RE_DB_SONG = re.compile(r"\bchichub_bigdb\b|\bchichub_demo\b|\bchichub\b(?!_)", re.I)

# 3. TÊN DB DEV nêu rõ. Chỉ soi ở CHỖ THẬT SỰ LÀ TÊN DB (sau `database:`, `dbname=`,
#    `-d `, hoặc sau dấu `/` của URL) -> không dính `npm run test_local`.
RE_DB_DEV = re.compile(
    r"(?:database\s*[:=]\s*['\"]?|dbname\s*=\s*|-d\s+|/)"
    r"([A-Za-z0-9]+_(?:dev|test|local))\b")

# 4. LẤY DATABASE_URL TRẦN — không nêu DB đích, đi đâu là do `.env` quyết.
RE_ENV_TRAN = re.compile(
    r"DATABASE_URL"                       # grep '^DATABASE_URL=' .env · process.env.DATABASE_URL
    r"|readFileSync\(\s*['\"][^'\"]*\.env"
    r"|\bdotenv\b|\bsource\s+\.env\b",
    re.I)

# 5. Họ lệnh Prisma buộc chạy trên DB dev -> miễn.
RE_PRISMA_DEV = re.compile(
    r"prisma\s+(?:migrate|db\s+push|db\s+pull|generate|format|validate)", re.I)

DEV_ISH = re.compile(r"_(?:dev|test|local)$", re.I)


def ghi_log(ban: dict) -> None:
    dong = json.dumps(ban, ensure_ascii=False)
    for p in (LOG_TMP, LOG_BEN):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(dong + "\n")
        except Exception:
            pass


def db_cua_env(cwd: str) -> str:
    """Đọc `.env` thật -> tên DB nó đang trỏ. Rỗng = không đọc được."""
    for ten in (".env", ".env.local"):
        p = os.path.join(cwd or ".", ten)
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                for dong in f:
                    if dong.startswith("DATABASE_URL"):
                        m = re.search(r"@[^/\s]+/([A-Za-z0-9_]+)", dong)
                        if m:
                            return m.group(1)
        except Exception:
            continue
    return ""


def soi(cmd: str, cwd: str) -> tuple:
    """Trả (chan?, ma_ly_do, db_dang_tro). Không chặn -> (False, mã, '')."""
    if not cmd or not RE_NOI_DB.search(cmd):
        return False, "khong-noi-db", ""
    if RE_PRISMA_DEV.search(cmd):
        return False, "prisma-schema-buoc-chay-dev", ""
    if RE_DB_SONG.search(cmd):
        return False, "neu-ro-db-song", ""
    m = RE_DB_DEV.search(cmd)
    if m:
        return True, "neu-thang-db-dev", m.group(1)
    if RE_ENV_TRAN.search(cmd):
        db = db_cua_env(cwd)
        if db and DEV_ISH.search(db):
            return True, "database-url-tran-tu-env", db
        return False, "env-tro-db-that" if db else "khong-doc-duoc-env", db
    return False, "khong-suy-duoc-db-dich", ""


def _ly_do(ma: str, db: str) -> str:
    dau = ("⛔ LỆNH NÀY TRA **DB DEV** — số ra KHÔNG phải dữ liệu hệ thống thật.\n\n")
    if ma == "neu-thang-db-dev":
        dau += "Lệnh nêu thẳng DB `%s`.\n" % db
    else:
        dau += ("Lệnh lấy `DATABASE_URL` TRẦN từ `.env`, mà `.env` của thư mục này đang trỏ "
                "DB `%s`.\n" % db)
    return dau + (
        "\nCA CẢNH CÁO THẬT (28/08/2026): main query đúng kiểu này rồi báo founder *\"bảng "
        "sku_csv_import trống hoàn toàn — 0 dòng\"*. Bảng thật KHÔNG trống; đó chỉ là DB dev. "
        "Founder mắng *\"đi trỏ về cái DB giả rồi kết luận thật\"*.\n"
        "\n**DB sống DUY NHẤT = `chichub_bigdb`** (memory `prod-app-dung-chichub-demo-db`); "
        "`chichub_demo` / `chichub` là bản cũ đã DROP.\n"
        "\nCHỌN 1:\n"
        "  1. Ép tên DB sống vào connection — cách đang dùng ở các lệnh ĐÚNG hôm nay:\n"
        "       const url = fs.readFileSync('.env','utf8')\n"
        "           .match(/DATABASE_URL=\"?([^\"\\n]+)\"?/)[1]\n"
        "           .replace('/chichub_dev','/chichub_bigdb');\n"
        "  2. Hoặc khai thẳng trong client:\n"
        "       new pg.Client({host:'localhost',port:5432,user:'chichub_user',\n"
        "                      password:process.env.PGPASSWORD,database:'chichub_bigdb'})\n"
        "  3. Thật sự CẦN DB dev (đang dựng ca thử) → viết trong chính lệnh:\n"
        "       # %s: <lý do ≥15 ký tự>\n"
        "\nTunnel là CHUNG cho cả 3 DB — chỉ đổi dbname, không phải dựng lại gì "
        "(CLAUDE.md §KHO CÔNG CỤ VERIFY)." % CUA_THOAT)


# ── TỰ KIỂM: 6 ca THẬT trích từ transcript 28/08 ────────────────────────────
_CA_THU = [
    ("PHẢI CHẶN — lệnh 08:22 main dùng DATABASE_URL trần rồi kết luận sku_csv_import trống",
     "DB_URL=\"$(grep -m1 '^DATABASE_URL=' .env | cut -d= -f2- | tr -d '\\\"')\" node .w25-kind.mjs",
     True),
    ("PHẢI CHẶN — biến thể sed lấy .env, vẫn là chichub_dev",
     "cat > .q.mjs <<'EOF'\nimport pg from 'pg';\nconst c=new pg.Client({connectionString:process.env.DB_URL});\nEOF\n"
     "DB_URL=\"$(grep -m1 '^DATABASE_URL' .env | sed -E 's/^[^=]+=//')\" node .q.mjs",
     True),
    ("PHẢI CHO QUA — lệnh 05:22 nêu thẳng database:'chichub_bigdb'",
     "node -e \"const c=new pg.Client({host:'localhost',port:5432,database:'chichub_bigdb',"
     "user:'chichub_user',password:process.env.PGPASSWORD})\"",
     False),
    ("PHẢI CHO QUA — lệnh 06:45 đọc .env rồi replace sang chichub_bigdb (lối ĐÚNG)",
     "node -e \"const url=fs.readFileSync('.env','utf8').match(/DATABASE_URL=\\\"?([^\\\"\\n]+)\\\"?/)[1]"
     ".replace('/chichub_dev','/chichub_bigdb'); const c=new pg.Client({connectionString:url})\"",
     False),
    ("PHẢI CHO QUA — lệnh 10:30 chỉ grep .env để CHẨN ĐOÁN, không nối DB",
     "grep -m1 '^DATABASE_URL=' .env | sed -E 's|.*@([^/]+)/([a-zA-Z0-9_]+).*|host=\\1 db=\\2|'",
     False),
    ("PHẢI CHO QUA — cửa thoát có lý do đủ dài",
     "# dung-db-dev-co-y: dựng ca thử migration trên bản sao dev, không kết luận số\n"
     "psql -d chichub_dev -c 'select 1'",
     False),
]


def _ca_thu(cwd: str) -> int:
    loi = 0
    for i, (nhan, cmd, phai_chan) in enumerate(_CA_THU, 1):
        if RE_VUOT_CONG.search(cmd):
            chan, ma, db = False, "vuot-cong", ""
        else:
            chan, ma, db = soi(cmd, cwd)
        ok = chan == phai_chan
        loi += 0 if ok else 1
        print("\n" + "=" * 78)
        print("CA %d — %s" % (i, nhan))
        print("LỆNH: %s" % cmd.replace("\n", " ⏎ ")[:160])
        print("KẾT QUẢ: %s (%s%s)  %s" % ("CHẶN" if chan else "CHO QUA", ma,
                                          " db=" + db if db else "",
                                          "✅ đúng" if ok else "❌ SAI"))
    print("\n" + "=" * 78)
    print("TỔNG: %d/%d ca đúng" % (len(_CA_THU) - loi, len(_CA_THU)))
    return 1 if loi else 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--ca-thu":
        return _ca_thu(sys.argv[2] if len(sys.argv) > 2 else os.getcwd())
    if len(sys.argv) > 2 and sys.argv[1] == "--thu":
        cwd = sys.argv[3] if len(sys.argv) > 3 else os.getcwd()
        chan, ma, db = soi(sys.argv[2], cwd)
        print(_ly_do(ma, db) if chan else "✓ cho qua (%s%s)" % (ma, " db=" + db if db else ""))
        return 0

    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    cmd = str((data.get("tool_input") or {}).get("command", "") or "")
    if not cmd:
        return 0
    cwd = str(data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())

    m = RE_VUOT_CONG.search(cmd)
    if m:
        ghi_log({"luc": time.strftime("%F %T"), "vuot_cong": True,
                 "ly_do": m.group(1)[:200].strip(), "cwd": cwd})
        return 0

    chan, ma, db = soi(cmd, cwd)
    if not chan:
        return 0
    ghi_log({"luc": time.strftime("%F %T"), "chan": ma, "db": db,
             "cwd": cwd, "lenh": cmd[:300]})
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": _ly_do(ma, db),
    }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)                       # fail-open tuyệt đối
