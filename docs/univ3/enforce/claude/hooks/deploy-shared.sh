#!/usr/bin/env bash
# ==========================================================================
# deploy-shared.sh — BỌC một lệnh đẩy TỆP DÙNG CHUNG lên máy chủ, tự làm đủ
#                    5 bước để "dữ liệu không bao giờ mất, task vẫn xong một mạch".
# --------------------------------------------------------------------------
# WHY: 25/8 lúc 11:53 một worker đẩy bản `.htaccess` TRONG KHO MÃ đè lên bản đang
# chạy -> xoá sạch 4 luật chặn của worker bảo mật: `/admin.php` và
# `/admin-config.php` từ 403 thành 200 (mở ra Internet). Trước đây hook chặn thẳng
# (deny) nên worker kẹt giữa chừng. Nay hook VIẾT LẠI lệnh cho đi qua script này:
# worker không phải nhớ gì, không phải bấm gì, mà bản của người khác vẫn còn.
#
# 5 bước (đúng thứ tự, hỏng bước nào là khôi phục ngay):
#   1. XIN KHOÁ theo TÀI NGUYÊN (wlock.sh) -> worker khác đến thì XẾP HÀNG, không đè.
#   2. TẢI bản ĐANG CHẠY về (đảo chiều chính lệnh đẩy -> cùng giao thức, cùng thông
#      tin đăng nhập), lưu bản gốc ra 2 nơi để còn khôi phục.
#   3. GỘP thay đổi của worker lên bản vừa tải (git merge-file 3 chiều; không có bản
#      gốc để so thì gộp kiểu hợp nhất, KHÔNG xoá dòng của người khác).
#   4. ĐẨY lên rồi VERIFY THẬT: tải lại so byte + gọi HTTP kiểm 403/200.
#   5. LỆCH -> tự đẩy bản ở bước 2 trở lại, verify lại, rồi báo lỗi rõ ràng.
#
# Dùng:
#   deploy-shared.sh --tep <đường-dẫn-tệp> [--tep ...] [--chu=<slug>] -- <lệnh đẩy gốc...>
#
# Cấu hình mong đợi HTTP (không bắt buộc) — ~/.claude/deploy-verify.json:
#   { "targets": [ { "match": "example.com",
#                    "base_url": "https://example.com",
#                    "expect_403": ["/admin.php", "/admin-config.php"],
#                    "expect_200": ["/"] } ] }
#   `match` = chuỗi con so với LỆNH ĐẨY. Không khớp -> chỉ verify tải-lại-so-byte.
#   Ghi đè nhanh bằng biến môi trường: DEPLOY_BASE_URL / DEPLOY_EXPECT_403 /
#   DEPLOY_EXPECT_200 (danh sách ngăn cách bằng dấu phẩy).
#
# Mã thoát: 0 = đẩy + verify OK · 3 = gộp đụng độ (KHÔNG đẩy) · 4 = verify lệch, đã
#           khôi phục · 5 = verify lệch VÀ khôi phục thất bại (BÁO NGƯỜI) · 75 = hết
#           giờ chờ khoá · còn lại = mã lỗi của chính lệnh đẩy.
# ==========================================================================
set -uo pipefail

W="${WLOCK:-$HOME/.claude/universal-hooks/wlock.sh}"
STATE_ROOT="${UNIV3_DEPLOY_STATE:-/tmp/claude-deploy-state}"
BAK_BEN="${UNIV3_DEPLOY_BACKUP:-$HOME/.claude/deploy-backups}"   # nơi lưu bền thứ 2
CFG="${DEPLOY_VERIFY_CFG:-$HOME/.claude/deploy-verify.json}"
TIMEOUT="${DEPLOY_LOCK_TIMEOUT:-900}"

FILES=(); CHU=""; CMD=(); seen_dd=0
while [ $# -gt 0 ]; do
  if [ "$1" = "--" ]; then seen_dd=1; shift; CMD=("$@"); break; fi
  case "$1" in
    --tep=*)  FILES+=("${1#*=}") ;;
    --tep)    shift; FILES+=("${1:-}") ;;
    --chu=*)  CHU="${1#*=}" ;;
    --chu)    shift; CHU="${1:-}" ;;
    -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
    *) echo "deploy-shared: cờ lạ '$1'" >&2; exit 2 ;;
  esac
  shift
done
[ "$seen_dd" = 1 ] && [ ${#CMD[@]} -gt 0 ] || {
  echo "deploy-shared: dùng 'deploy-shared.sh --tep <tệp> -- <lệnh đẩy>'" >&2; exit 2; }
[ ${#FILES[@]} -gt 0 ] || { echo "deploy-shared: thiếu --tep" >&2; exit 2; }

# `${CMD[*]}` nối bằng dấu cách -> MẤT dấu nháy: `bash -c 'scp a h:/b'` thành
# `bash -c scp a h:/b`, bộ đảo chiều đọc ra lệnh cụt. `%q` giữ nguyên ranh giới đối số.
LENH_GOC="$(printf '%q ' "${CMD[@]}")"
[ -n "$CHU" ] || CHU="${WLOCK_OWNER:-deploy-$$}"
TS="$(date +%Y%m%d-%H%M%S)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/deploy-shared.XXXXXX")"
cleanup() { rm -rf "$TMP" 2>/dev/null; }
trap cleanup EXIT

say() { printf '   %s\n' "$*"; }
buoc() { printf '\n▶ %s\n' "$*"; }

# ---------- đảo chiều lệnh đẩy -> lệnh TẢI VỀ (cùng giao thức, cùng creds) ----------
# In ra 1 dòng shell; chỗ ghi ra dùng biến $OUT. Rỗng = không đảo được.
lenh_tai() {
  python3 - "$1" "$2" <<'PY'
import re, shlex, sys
tep, cmd = sys.argv[1], sys.argv[2]
base = tep.rsplit("/", 1)[-1]
INTERP = {"bash", "sh", "zsh", "ksh", "dash"}


def tach(c):
    try:
        return shlex.split(c, posix=True)
    except Exception:
        return c.split()


# Hook bọc lệnh gốc bằng `bash -c '<lệnh>'` -> phải bóc ra mới soi được giao thức.
for _ in range(3):
    t = tach(cmd)
    if t and t[0].rsplit("/", 1)[-1] in INTERP and "-c" in t[:3]:
        i = t.index("-c")
        if i + 1 < len(t):
            cmd = t[i + 1]
            continue
    break
t = tach(cmd)
prog = [x.rsplit("/", 1)[-1] for x in t]
q = shlex.quote
REMOTE = re.compile(r"[\w.-]+@[\w.-]+:|://|(?:^|[\s=])[A-Za-z][\w.-]*:[/~]")


def xa(toks):
    """Đối số cuối trông như đích từ xa."""
    args = [x for x in toks if not x.startswith("-")][1:]
    return args[-1] if args and REMOTE.search(args[-1]) else ""


out = ""
if "scp" in prog or "rsync" in prog:
    i = prog.index("scp") if "scp" in prog else prog.index("rsync")
    tt = t[i:]
    dich = xa(tt)
    if dich:
        # scp a.txt host:/duong/dan  -> đích có thể là thư mục -> nối tên tệp
        if dich.endswith("/") or dich.endswith(":"):
            dich += base
        co = [x for x in tt[1:] if x.startswith("-") and x not in ("-r", "-a", "-v")]
        out = "%s %s %s $OUT" % (tt[0], " ".join(co), q(dich))
elif "curl" in prog:
    i = prog.index("curl")
    tt = t[i:]
    url = ""
    for j, x in enumerate(tt):
        if x in ("-T", "--upload-file"):
            pass
        elif REMOTE.search(x) and "://" in x:
            url = x
    if url:
        if url.endswith("/"):
            url += base
        # giữ lại cờ xác thực / chứng chỉ, bỏ cờ upload
        giu, k = [], 0
        while k < len(tt):
            x = tt[k]
            if x in ("-u", "--user", "--key", "--cert", "--cacert", "--pubkey",
                     "--interface", "--connect-timeout"):
                giu += [x, tt[k + 1] if k + 1 < len(tt) else ""]
                k += 2
                continue
            if x.startswith(("-u", "--user=", "--key=", "--cert=", "--insecure", "-k",
                             "--ftp-ssl", "--ssl")):
                giu.append(x)
            k += 1
        out = "curl -fsS %s %s -o $OUT" % (" ".join(q(x) for x in giu if x), q(url))
elif "aws" in prog and " s3 " in " " + cmd + " ":
    m = re.search(r"s3://\S+", cmd)
    if m:
        u = m.group(0)
        if u.endswith("/"):
            u += base
        out = "aws s3 cp %s $OUT" % q(u)
elif "ssh" in prog:
    # ssh host 'cat > /duong/dan'  ->  ssh host 'cat /duong/dan'
    m = re.search(r">\s*([^\s'\";|]+)", cmd)
    if m:
        i = prog.index("ssh")
        host = ""
        for x in t[i + 1:]:
            if not x.startswith("-"):
                host = x
                break
        if host:
            out = "ssh %s %s > $OUT" % (q(host), q("cat " + m.group(1)))
elif "lftp" in prog or "sftp" in prog:
    m = re.search(r"(?i)\b(?:put|mput)\s+(\S+)(?:\s+-o\s+(\S+))?", cmd)
    xa_path = ""
    if m:
        xa_path = (m.group(2) or m.group(1)).strip("'\"")
    if not xa_path:
        xa_path = base
    thay = re.sub(r"(?i)\bmput\b", "mget", re.sub(r"(?i)\bput\b", "get", cmd))
    thay = re.sub(r"(?i)\bmirror\s+-R\b", "mirror", thay)
    # ép ghi ra $OUT
    thay = re.sub(r"(?i)\b(get|mget)\s+\S+(\s+-o\s+\S+)?",
                  "get %s -o $OUT" % xa_path, thay, count=1)
    out = thay
print(out)
PY
}

# ---------- đọc cấu hình mong đợi HTTP ----------
doc_cfg() {   # in ra: BASE_URL\n403,403,...\n200,200,...
  python3 - "$CFG" "$LENH_GOC" <<'PY'
import json, os, sys
cfg, cmd = sys.argv[1], sys.argv[2]
base = os.environ.get("DEPLOY_BASE_URL", "")
e403 = [x for x in os.environ.get("DEPLOY_EXPECT_403", "").split(",") if x.strip()]
e200 = [x for x in os.environ.get("DEPLOY_EXPECT_200", "").split(",") if x.strip()]
if not base and os.path.isfile(cfg):
    try:
        d = json.load(open(cfg, encoding="utf-8"))
        for t in d.get("targets", []):
            m = str(t.get("match") or "")
            if m and m in cmd:
                base = base or str(t.get("base_url") or "")
                e403 = e403 or list(t.get("expect_403") or [])
                e200 = e200 or list(t.get("expect_200") or [])
                break
    except Exception:
        pass
print(base)
print(",".join(x.strip() for x in e403))
print(",".join(x.strip() for x in e200))
PY
}

http_code() { curl -sS -o /dev/null -m 20 -w '%{http_code}' "$1" 2>/dev/null; }

# Verify HTTP theo mong đợi. 0 = đạt, 1 = lệch (in ra chỗ lệch).
verify_http() {
  local base="$1" e403="$2" e200="$3" p code lech=0
  [ -n "$base" ] || { say "(không có base_url -> bỏ qua bước kiểm 403/200)"; return 0; }
  base="${base%/}"
  local old_ifs="$IFS"
  IFS=','
  set -f
  for p in $e403; do
    IFS="$old_ifs"; set +f
    [ -n "$p" ] || { IFS=','; set -f; continue; }
    code=$(http_code "$base/${p#/}")
    if [ "$code" = "403" ] || [ "$code" = "401" ] || [ "$code" = "404" ]; then
      say "✓ $p = $code (vẫn bị chặn)"
    else
      say "✗ $p = $code  — ĐÁNG LẼ 403"; lech=1
    fi
    IFS=','; set -f
  done
  for p in $e200; do
    IFS="$old_ifs"; set +f
    [ -n "$p" ] || { IFS=','; set -f; continue; }
    code=$(http_code "$base/${p#/}")
    if [ "$code" = "200" ] || [ "$code" = "301" ] || [ "$code" = "302" ]; then
      say "✓ $p = $code (còn sống)"
    else
      say "✗ $p = $code  — ĐÁNG LẼ 200"; lech=1
    fi
    IFS=','; set -f
  done
  IFS="$old_ifs"; set +f
  return $lech
}

# ---------------------- CÔNG VIỆC THẬT (chạy khi đã có khoá) ----------------------
lam_that() {
  local rc=0 f name dl base_src merged
  # bash 3.2 (macOS) không có `mapfile` -> đọc 3 dòng bằng read
  local BASE_URL E403 E200
  { read -r BASE_URL; read -r E403; read -r E200; } < <(doc_cfg)

  buoc "Bước 2 — TẢI bản ĐANG CHẠY về (nguồn sự thật là máy chủ, KHÔNG phải kho mã)"
  for f in "${FILES[@]}"; do
    name="$(basename "$f")"
    dl="$TMP/$name.dang-chay"
    local tai; tai="$(lenh_tai "$f" "$LENH_GOC")"
    if [ -z "$tai" ]; then
      say "✗ không đảo được lệnh đẩy thành lệnh tải cho $name"
      echo "   -> DỪNG, KHÔNG đẩy. Hãy tự tải bản đang chạy về rồi sửa trên đó." >&2
      return 3
    fi
    say "tải: ${tai//\$OUT/$dl}"
    if ! OUT="$dl" bash -c "$tai" >/dev/null 2>"$TMP/tai.err"; then
      say "✗ tải thất bại: $(head -3 "$TMP/tai.err" | tr '\n' ' ')"
      return 3
    fi
    [ -s "$dl" ] || { say "✗ bản tải về RỖNG -> không dám gộp"; return 3; }
    # lưu bản gốc ra 2 nơi (luật backup 2 nơi)
    mkdir -p "$BAK_BEN" "$STATE_ROOT/goc"
    cp -p "$dl" "$BAK_BEN/$name.$TS.dang-chay"
    cp -p "$dl" "$STATE_ROOT/goc/$name.$TS.dang-chay"
    say "✓ đã tải $(wc -l < "$dl" | tr -d ' ') dòng · backup: $BAK_BEN/$name.$TS.dang-chay"
  done

  buoc "Bước 3 — GỘP thay đổi của worker lên bản đang chạy (giữ nguyên phần của người khác)"
  for f in "${FILES[@]}"; do
    name="$(basename "$f")"; dl="$TMP/$name.dang-chay"; merged="$TMP/$name.gop"
    # bản GỐC để so 3 chiều: ưu tiên bản chính script này đẩy lần trước, rồi bản đã tải
    # trong phiên (hook ghi), rồi bản trong git HEAD (tức bản TRƯỚC khi worker sửa).
    # LƯU Ý: bản gốc phải là bản CHÍNH WORKER NÀY dựng ra, không phải "bản ai đó đẩy
    # gần nhất" — lấy bản của worker khác làm gốc thì thay đổi của họ trông như bị worker
    # này XOÁ, và merge sẽ xoá thật (đúng tai nạn `.htaccess` 25/8; đã tái hiện được ở ca
    # thử 2 tiến trình). Nên khoá theo cả TÀI NGUYÊN lẫn CHỦ.
    base_src=""
    [ -f "$STATE_ROOT/last/$RES/$CHU/$name" ] && base_src="$STATE_ROOT/last/$RES/$CHU/$name"
    if [ -z "$base_src" ]; then
      local key; key=$(python3 -c "import re,os,sys;print(re.sub(r'[^A-Za-z0-9]+','_',os.path.abspath(os.getcwd()))[:120])")
      [ -f "$STATE_ROOT/$key/dl/$name" ] && [ -s "$STATE_ROOT/$key/dl/$name" ] && base_src="$STATE_ROOT/$key/dl/$name"
    fi
    if [ -z "$base_src" ] && git rev-parse --git-dir >/dev/null 2>&1; then
      if git show "HEAD:$(git ls-files --full-name -- "$f" 2>/dev/null)" > "$TMP/$name.head" 2>/dev/null \
         && [ -s "$TMP/$name.head" ]; then
        base_src="$TMP/$name.head"
      fi
    fi

    if [ -n "$base_src" ]; then
      cp "$dl" "$merged"
      if git merge-file -q -p "$dl" "$base_src" "$f" > "$merged" 2>"$TMP/merge.err"; then
        say "✓ $name — gộp 3 chiều OK (gốc so sánh: $base_src)"
      elif git merge-file -q -p --union "$dl" "$base_src" "$f" > "$merged" 2>"$TMP/merge.err"; then
        # Đụng độ = hai bên sửa CÙNG chỗ. Không được chọn bên nào (chọn = xoá việc của bên
        # kia — đúng lỗi 25/8), nên GIỮ CẢ HAI. Cấu hình hỏng vì thế thì bước 4 verify HTTP
        # bắt được và bước 5 tự khôi phục -> vẫn không mất dữ liệu, task vẫn chạy tiếp.
        say "⚠ $name — đụng độ, đã gộp kiểu HỢP NHẤT (giữ CẢ HAI bên, không xoá của ai)"
        say "   kiểm lại bằng mắt sau khi xong: $BAK_BEN/$name.$TS.dang-chay là bản trước đó"
      else
        say "✗ $name — gộp thất bại hoàn toàn (git merge-file lỗi)."
        say "   bản đang chạy đã lưu ở: $BAK_BEN/$name.$TS.dang-chay"
        say "   -> DỪNG, KHÔNG đẩy."
        return 3
      fi
    else
      # Không có bản gốc -> HỢP NHẤT: giữ NGUYÊN bản đang chạy, chỉ THÊM dòng mới của
      # worker. Không xoá dòng nào của người khác (đúng bài học `.htaccess`).
      python3 - "$dl" "$f" "$merged" <<'PY'
import sys
dl, loc, out = sys.argv[1:4]
run = open(dl, encoding="utf-8", errors="replace").read().splitlines()
new = open(loc, encoding="utf-8", errors="replace").read().splitlines()
co = set(x.strip() for x in run)
them = [x for x in new if x.strip() and x.strip() not in co]
res = run + ([""] + them if them else [])
open(out, "w", encoding="utf-8").write("\n".join(res) + "\n")
print("them=%d" % len(them))
PY
      say "✓ $name — không có bản gốc để so 3 chiều -> HỢP NHẤT (chỉ thêm, không xoá)"
    fi
    # đưa bản đã gộp vào đúng chỗ lệnh đẩy sẽ đọc
    cp -p "$f" "$TMP/$name.cua-worker"
    cp "$merged" "$f"
    if ! diff -q "$TMP/$name.dang-chay" "$f" >/dev/null 2>&1; then
      say "   khác bản đang chạy: $(diff "$TMP/$name.dang-chay" "$f" | grep -c '^[<>]') dòng"
    else
      say "   nội dung y hệt bản đang chạy -> lượt đẩy này không đổi gì"
    fi
  done

  buoc "Bước 4 — ĐẨY rồi VERIFY THẬT"
  say "chạy: $LENH_GOC"
  "${CMD[@]}"; rc=$?
  if [ "$rc" != 0 ]; then
    say "✗ lệnh đẩy trả mã $rc — không verify, không đổi gì thêm"
    return "$rc"
  fi

  local lech=0
  for f in "${FILES[@]}"; do
    name="$(basename "$f")"
    local tai; tai="$(lenh_tai "$f" "$LENH_GOC")"
    OUT="$TMP/$name.sau" bash -c "$tai" >/dev/null 2>&1
    if [ -s "$TMP/$name.sau" ] && diff -q "$TMP/$name.sau" "$f" >/dev/null 2>&1; then
      say "✓ $name — tải lại khớp từng byte với bản vừa đẩy"
    else
      say "✗ $name — tải lại KHÁC bản vừa đẩy"; lech=1
    fi
  done
  verify_http "$BASE_URL" "$E403" "$E200" || lech=1

  if [ "$lech" = 0 ]; then
    mkdir -p "$STATE_ROOT/last/$RES/$CHU"
    for f in "${FILES[@]}"; do cp "$f" "$STATE_ROOT/last/$RES/$CHU/$(basename "$f")"; done
    buoc "XONG — đẩy + verify đều đạt"
    return 0
  fi

  buoc "Bước 5 — VERIFY LỆCH -> KHÔI PHỤC bản ở bước 2"
  local rcb=0
  for f in "${FILES[@]}"; do
    name="$(basename "$f")"
    cp "$TMP/$name.dang-chay" "$f"
  done
  "${CMD[@]}" >/dev/null 2>&1 || rcb=1
  local con_lech=0
  for f in "${FILES[@]}"; do
    name="$(basename "$f")"
    local tai; tai="$(lenh_tai "$f" "$LENH_GOC")"
    OUT="$TMP/$name.hoi" bash -c "$tai" >/dev/null 2>&1
    if [ -s "$TMP/$name.hoi" ] && diff -q "$TMP/$name.hoi" "$TMP/$name.dang-chay" >/dev/null 2>&1; then
      say "✓ $name — đã khôi phục về đúng bản đang chạy lúc đầu"
    else
      say "✗ $name — KHÔI PHỤC THẤT BẠI"; con_lech=1
    fi
  done
  verify_http "$BASE_URL" "$E403" "$E200" || con_lech=1
  if [ "$con_lech" = 0 ] && [ "$rcb" = 0 ]; then
    echo "❌ LỖI — bản vừa đẩy không đạt kỳ vọng, ĐÃ KHÔI PHỤC nguyên trạng máy chủ." >&2
    for f in "${FILES[@]}"; do
      name="$(basename "$f")"
      cp -p "$TMP/$name.cua-worker" "$BAK_BEN/$name.$TS.cua-worker" 2>/dev/null
      cp -p "$TMP/$name.gop"       "$BAK_BEN/$name.$TS.da-gop"     2>/dev/null
      echo "   bản đang chạy lúc đầu : $BAK_BEN/$name.$TS.dang-chay" >&2
      echo "   bản bạn định đẩy      : $BAK_BEN/$name.$TS.cua-worker" >&2
      echo "   bản đã gộp (gây lệch) : $BAK_BEN/$name.$TS.da-gop" >&2
    done
    echo "   -> Sửa cho đúng kỳ vọng rồi chạy lại; ĐỪNG ép đẩy bằng \`shared-ok\`." >&2
    return 4
  fi
  echo "🚨 NGUY — verify lệch VÀ khôi phục cũng thất bại. Máy chủ đang ở trạng thái SAI." >&2
  echo "   Bản đang chạy lúc đầu: $BAK_BEN/*.$TS.dang-chay — khôi phục TAY NGAY." >&2
  return 5
}

# ---------------------- Bước 1: KHOÁ THEO TÀI NGUYÊN ----------------------
# Tài nguyên = ĐÍCH + TÊN TỆP, nên 2 worker đẩy cùng `.htaccess` lên cùng site thì
# xếp hàng, còn đẩy 2 tệp/2 site khác nhau thì chạy song song bình thường.
RES="$(python3 - "$LENH_GOC" "${FILES[0]}" <<'PY'
import re, sys
cmd, tep = sys.argv[1], sys.argv[2]
m = re.search(r"(?:([\w.-]+)@)?([\w.-]+\.[\w.-]+)(?::|/)", cmd)
host = m.group(2) if m else "may-chu"
name = tep.rsplit("/", 1)[-1]
print("deploy-" + re.sub(r"[^A-Za-z0-9]+", "-", host + "-" + name).strip("-").lower()[:60])
PY
)"

buoc "Bước 1 — XIN KHOÁ tài nguyên «${RES}» (worker khác đụng cùng tệp sẽ XẾP HÀNG)"
export WLOCK_OWNER="$CHU"
bash "$W" acquire "$RES" --owner="$CHU" --pid=$$ --timeout="$TIMEOUT" \
     --note="đẩy $(basename "${FILES[0]}")" || { rc=$?; echo "deploy-shared: không lấy được khoá (mã $rc)" >&2; exit 75; }
trap 'bash "$W" release "$RES" --owner="$CHU" >/dev/null 2>&1; cleanup' EXIT

lam_that
RC=$?
bash "$W" release "$RES" --owner="$CHU" >/dev/null 2>&1
trap cleanup EXIT
exit $RC
