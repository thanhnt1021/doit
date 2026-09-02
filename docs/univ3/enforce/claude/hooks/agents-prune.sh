#!/bin/bash
# ==========================================================================
# agents-prune.sh — dọn session ĐÃ CHẾT khỏi Agent View (`/agents`).
#
# VÌ SAO CÓ FILE NÀY: `claude agents --help` (bản 2.1.241) KHÔNG có cờ
# prune/cleanup nào — chỉ có `--json`, `--all`, `--cwd`. Agent View không tự
# xoá entry đã xong, nên session chết nằm lại hàng ngày trời và người dùng
# tưởng nó còn treo. Dọn tay = tự so hai danh sách JSON rồi gõ `claude rm`
# từng id — dễ gõ nhầm vào id ĐANG CHẠY. Script này làm phần so sánh đó.
#
# AN TOÀN — phải thoả ĐỒNG THỜI 2 điều kiện độc lập mới xoá 1 session:
#   (1) id KHÔNG có trong `claude agents --json` (danh sách đang sống), VÀ
#   (2) state nằm trong danh sách trạng thái chết đã biết (DEAD_STATES).
# State lạ/thiếu → BỎ QUA (không xoá). Thà sót còn hơn giết nhầm việc đang
# thi công dở. Sót thì `claude rm <id>` tay.
#
# FAIL-SAFE: không lấy được danh sách sống (claude lỗi / JSON hỏng / thiếu
# python3) → THOÁT, KHÔNG xoá gì. Không bao giờ "cứ xoá cho chắc".
#
# CHỈ CHẠY TAY — CỐ Ý không cắm vào hook tự động mỗi lượt.
#
# Dùng:
#   agents-prune.sh --thu    # thử khan: chỉ in ra sẽ xoá gì, KHÔNG xoá
#   agents-prune.sh          # xoá thật, từng id một, dừng ngay khi có lỗi
# ==========================================================================
set -uo pipefail

DRY=0
case "${1:-}" in
  --thu|--dry-run) DRY=1 ;;
  -h|--help|help)  sed -n '2,27p' "$0"; exit 0 ;;
  "")              ;;
  *) echo "❌ Tham số lạ: $1 (chỉ nhận --thu)"; exit 2 ;;
esac

command -v claude  >/dev/null 2>&1 || { echo "❌ Không thấy lệnh 'claude' — KHÔNG xoá gì."; exit 3; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Không thấy python3 (cần để đọc JSON) — KHÔNG xoá gì."; exit 3; }

# python3 tự gọi `claude`, tự lọc, in ra mỗi dòng 1 id chết. Lỗi bất kỳ -> exit != 0.
DEAD_LIST="$(python3 <<'PY'
import json, os, subprocess, sys

# Trạng thái coi là CHẾT. Cố ý hẹp: state lạ thì bỏ qua, không đoán.
DEAD_STATES = {"done", "failed", "stopped", "cancelled", "canceled", "error", "killed"}

def lay(*args):
    """Chạy `claude agents ...` và ép ra list JSON. Sai bất cứ đâu -> thoát, không xoá."""
    try:
        p = subprocess.run(["claude", "agents", "--json", *args],
                           capture_output=True, text=True, timeout=60)
    except Exception as e:
        print(f"❌ Gọi `claude agents {' '.join(args)}` hỏng: {e}", file=sys.stderr)
        sys.exit(3)
    if p.returncode != 0:
        print(f"❌ `claude agents {' '.join(args)}` exit {p.returncode}: {p.stderr.strip()[:300]}", file=sys.stderr)
        sys.exit(3)
    try:
        d = json.loads(p.stdout)
    except Exception as e:
        print(f"❌ JSON hỏng từ `claude agents {' '.join(args)}`: {e}", file=sys.stderr)
        sys.exit(3)
    if not isinstance(d, list):
        print("❌ JSON không phải mảng — KHÔNG xoá gì.", file=sys.stderr)
        sys.exit(3)
    return d

song = lay()               # đang sống
tat_ca = lay("--all")      # đủ cả đã xong

# Hai rào chắn id: id ngắn + sessionId đầy đủ.
id_song  = {s.get("id") for s in song if s.get("id")}
sid_song = {s.get("sessionId") for s in song if s.get("sessionId")}
# Phiên hiện tại (nếu script chạy từ trong 1 phiên Claude) — tuyệt đối không đụng.
sid_toi = os.environ.get("CLAUDE_SESSION_ID")
if sid_toi:
    sid_song.add(sid_toi)

chet, bo_qua = [], []
for s in tat_ca:
    sid_ngan = s.get("id")
    if not sid_ngan:
        continue                      # phiên interactive: `claude rm` không nhận, bỏ
    if sid_ngan in id_song or s.get("sessionId") in sid_song:
        continue                      # ĐANG SỐNG -> cấm đụng
    st = (s.get("state") or "").lower()
    if st in DEAD_STATES:
        chet.append((sid_ngan, s.get("name", ""), st))
    else:
        bo_qua.append((sid_ngan, s.get("name", ""), st or "(trống)"))

print(f"# sống: {len(song)} · tổng: {len(tat_ca)} · sẽ xoá: {len(chet)} · bỏ qua (state lạ): {len(bo_qua)}",
      file=sys.stderr)
for i, n, st in bo_qua:
    print(f"#   bỏ qua {i} | {n} | state={st} — không nằm trong danh sách chết đã biết", file=sys.stderr)
for i, n, st in chet:
    print(f"{i}\t{n}\t{st}")
PY
)" || { echo "⛔ Không lấy được danh sách tin cậy — KHÔNG xoá gì (fail-safe)."; exit 3; }

if [ -z "${DEAD_LIST//[$'\t\r\n ']/}" ]; then
  echo "✅ Không có session chết nào để dọn."
  exit 0
fi

echo "── Session sẽ xoá ──"
printf '%s\n' "$DEAD_LIST" | while IFS=$'\t' read -r id ten st; do
  [ -n "$id" ] && echo "  $id | $ten | state=$st"
done

if [ "$DRY" = "1" ]; then
  echo "── THỬ KHAN (--thu): không xoá gì. Bỏ --thu để xoá thật. ──"
  exit 0
fi

echo "── Xoá thật ──"
loi=0
while IFS=$'\t' read -r id ten st; do
  [ -n "$id" ] || continue
  echo "\$ claude rm $id"
  if claude rm "$id"; then :; else
    echo "❌ Xoá $id lỗi — DỪNG, không chạy tiếp."; loi=1; break
  fi
done <<< "$DEAD_LIST"

[ "$loi" = "0" ] && echo "✅ Xong. Transcript vẫn giữ (\`claude --resume\` được)."
exit "$loi"
