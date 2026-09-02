#!/bin/bash
# Ký lại (build + cài lại) app iOS native.
# Từ 02/09/2026 dùng team TRẢ PHÍ GYNRKXCZPQ (Huu Anh Nguyen), ký THỦ CÔNG bằng hồ sơ
# "Thanh Dev fun" / "Thanh Dev com" — chứng chỉ + hồ sơ hết hạn 2027-09-01, tức 1 NĂM
# ký lại 1 lần (không còn 7 ngày như team miễn phí cũ Q27B6K3LNC).
# Đọc registry ~/.claude/ios-apps-registry.json (do skill ios-native-app ghi khi build app mới).
#   bash resign.sh          # ký lại TẤT CẢ app
#   bash resign.sh <name>   # ký lại 1 app theo "name"
# ĐK: Mac bật · iPhone cùng WiFi (KHÔNG cần cáp, KHÔNG cần mở khoá) · chứng chỉ .p12 đã nạp keychain và 4 hồ sơ
#     đã nằm ở ~/Library/MobileDevice/Provisioning Profiles/ (bộ gốc: DOC-tool/appdev/BO-KY-CHO-THANH).
set -uo pipefail
REG="$HOME/.claude/ios-apps-registry.json"
[ -f "$REG" ] || { echo "❌ Không thấy registry $REG — build 1 app trước đã."; exit 1; }
FILTER="${1:-}"
TSV=$(mktemp)

python3 - "$REG" "$FILTER" > "$TSV" <<'PY'
import json, sys
reg = json.load(open(sys.argv[1])); flt = sys.argv[2]
for a in reg.get("apps", []):
    if flt and a.get("name") != flt: continue
    print("\t".join(a.get(k, "") for k in
        ("name","project_dir","app_dir","scheme","bundle_id","team","udid","app_product","project_name")))
PY

[ -s "$TSV" ] || { echo "❌ Registry rỗng hoặc không có app tên '$FILTER'."; rm -f "$TSV"; exit 1; }

OK=0; FAIL=0
while IFS=$'\t' read -r name pdir adir scheme bundle team udid product projname; do
  # Tên .xcodeproj KHÁC tên scheme ở stremiox (project StremioX, scheme StremioXiOSNative),
  # nên đọc project_name từ registry; app cũ không có trường này thì lùi về dùng scheme.
  projname="${projname:-$scheme}"
  echo "=== $name ($bundle) ==="
  DIR="$pdir/$adir"; DD="/tmp/ios_$name"
  if [ ! -f "$DIR/project.yml" ]; then echo "  ❌ thiếu $DIR/project.yml"; FAIL=$((FAIL+1)); continue; fi
  xcodegen generate -s "$DIR/project.yml" -p "$DIR" >/dev/null 2>&1
  if xcodebuild -project "$DIR/$projname.xcodeproj" -scheme "$scheme" \
       -destination "id=$udid" -derivedDataPath "$DD" build 2>&1 \
       | grep -q 'BUILD SUCCEEDED'; then
    # Cài qua WiFi hay dính CoreDeviceError 4000 ("device disconnected immediately
    # after connecting") ở lần bắt tay đầu — chập chờn, thử lại là ăn. Nên lặp tối đa 6 lần.
    INSTALLED=0
    for try in 1 2 3 4 5 6; do
      IOUT=$(xcrun devicectl device install app --device "$udid" \
               "$DD/Build/Products/Debug-iphoneos/$product" 2>&1)
      if echo "$IOUT" | grep -q 'App installed'; then INSTALLED=1; break; fi
      echo "  … lần $try cài trượt, thử lại: $(echo "$IOUT" | grep -m1 -E 'ERROR|error' | head -c 120)"
      sleep 3
    done
    if [ "$INSTALLED" = 1 ]; then
      echo "  ✅ build + cài xong (hạn tới 2027-09-01)"; OK=$((OK+1))
    else
      echo "  ⚠️ build OK nhưng CÀI lỗi sau 6 lần — kiểm iPhone cùng WiFi với Mac + xcrun devicectl list devices"; FAIL=$((FAIL+1))
    fi
  else
    echo "  ❌ BUILD FAILED — thường do thiếu chứng chỉ/hồ sơ: chạy security find-identity -v -p codesigning (phải thấy GYNRKXCZPQ) và kiểm ~/Library/MobileDevice/Provisioning Profiles/"; FAIL=$((FAIL+1))
  fi
done < "$TSV"
rm -f "$TSV"
echo "── Xong: $OK ok, $FAIL lỗi ──"
