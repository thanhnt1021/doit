#!/usr/bin/env bash
# CHẠY HẾT BỘ CA THỬ CỦA universal-hooks — một câu duy nhất.
#
# WHY (W05 24/09/2026): 16 tệp `*_ca_thu.py` nằm cạnh hook nhưng KHÔNG nằm trong lượt chạy nào —
# máy này không có crontab (`crontab -l` → *no crontab for buddhy*), `~/Library/LaunchAgents` không
# có plist nào của univ3, và chỉ 3 bộ được hook gọi lồng (nghiem_thu_ca_thu ← nghiem_thu_gate.py,
# so_lenh_ca_thu ← so_lenh.py, bao_khach_ca_thu ← bao_khach_gui.py). 13 bộ còn lại chỉ được nhắc
# trong dòng chú thích "Chạy: python3 …" → sửa 1 hook là gãy âm thầm hook khác, không ai biết.
#
# Dùng:
#   bash ~/.claude/universal-hooks/chay-het-ca-thu.sh          # chạy hết, in bảng tổng kết
#   bash ~/.claude/universal-hooks/chay-het-ca-thu.sh -v       # kèm toàn bộ đầu ra từng bộ
#   bash ~/.claude/universal-hooks/chay-het-ca-thu.sh w08 w11  # chỉ chạy bộ có tên khớp
#
# Mã thoát: 0 = mọi bộ ĐẠT · 1 = có bộ TRƯỢT. Đầu ra chi tiết của bộ trượt LUÔN được in ra
# (kể cả không có -v) để đọc thẳng nguyên nhân, không phải chạy lại.
#
# LƯU Ý: mọi bộ ca thử đều tự dựng hộp cát rồi tự xoá (`shutil.rmtree` trong `finally`) — không
# bộ nào đụng sổ thật. `w98_p104_corpus_ca_thu.py` chỉ ghi `p104_trang_thai.json` khi có cờ
# `--bat-neu-dat`; script này KHÔNG truyền cờ đó.

set -uo pipefail

GOC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAI_DONG=0
LOC=()

for arg in "$@"; do
  case "$arg" in
    -v | --chi-tiet) DAI_DONG=1 ;;
    *) LOC+=("$arg") ;;
  esac
done

PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
  echo "KHÔNG CHẠY ĐƯỢC: máy không có python3" >&2
  exit 2
fi

DS=()
while IFS= read -r f; do
  ten="$(basename "$f")"
  if [ ${#LOC[@]} -gt 0 ]; then
    khop=0
    for k in "${LOC[@]}"; do case "$ten" in *"$k"*) khop=1 ;; esac; done
    [ "$khop" -eq 1 ] || continue
  fi
  DS+=("$f")
done < <(find "$GOC" -maxdepth 1 -name '*_ca_thu.py' -not -path '*__pycache__*' | sort)

if [ ${#DS[@]} -eq 0 ]; then
  echo "KHÔNG CÓ BỘ NÀO KHỚP (thư mục: $GOC)" >&2
  exit 2
fi

BAT_DAU=$(date +%s)
DAT=0
TRUOT=0
declare -a DONG_KQ=()
declare -a TEN_TRUOT=()

echo "══ CHẠY ${#DS[@]} BỘ CA THỬ — $(date '+%Y-%m-%d %H:%M:%S') ══"
echo

for f in "${DS[@]}"; do
  ten="$(basename "$f" .py)"
  t0=$(date +%s)
  out="$("$PY" "$f" 2>&1)"
  rc=$?
  t1=$(date +%s)
  giay=$((t1 - t0))
  # Dòng tổng kết của chính bộ đó (dòng cuối có chữ "ĐẠT"/"đạt"/"KẾT") để đọc số ca.
  tom="$(printf '%s\n' "$out" | grep -E 'ĐẠT|đạt|KẾT|ca ĐÚNG|ca đúng' | tail -1 | sed 's/^[[:space:]]*//' | cut -c1-58)"
  if [ "$rc" -eq 0 ]; then
    DAT=$((DAT + 1))
    printf '  ✅ %-34s %3ds  %s\n' "$ten" "$giay" "$tom"
    DONG_KQ+=("ĐẠT   $ten")
  else
    TRUOT=$((TRUOT + 1))
    TEN_TRUOT+=("$ten")
    printf '  ❌ %-34s %3ds  mã thoát=%d  %s\n' "$ten" "$giay" "$rc" "$tom"
    DONG_KQ+=("TRƯỢT $ten (mã thoát $rc)")
    echo "     ┌─ đầu ra $ten ──────────────────────────────"
    printf '%s\n' "$out" | sed 's/^/     │ /'
    echo "     └────────────────────────────────────────────"
  fi
  if [ "$DAI_DONG" -eq 1 ] && [ "$rc" -eq 0 ]; then
    printf '%s\n' "$out" | sed 's/^/       /'
  fi
done

HET=$(date +%s)
echo
echo "══ TỔNG: $DAT ĐẠT / ${#DS[@]} bộ · $TRUOT trượt · $((HET - BAT_DAU))s ══"
if [ "$TRUOT" -gt 0 ]; then
  echo "   Bộ trượt: ${TEN_TRUOT[*]}"
  exit 1
fi
exit 0
