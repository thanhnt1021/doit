#!/usr/bin/env bash
# univ3 bootstrap — clone bộ rule v3 vào <project>/docs/univ3 rồi cài đặt.
# SSOT: thanhnt1021/univ3 (PRIVATE — cần gh auth tài khoản thanhnt1021 hoặc SSH key).
#
# Dùng:
#   cd <project>
#   bash <(curl -fsSL https://raw.githubusercontent.com/thanhnt1021/univ3/main/bootstrap.sh)
# hoặc chạy từ bản đã có: bash docs/univ3/bootstrap.sh
set -e

REPO_SSH="git@github.com:thanhnt1021/univ3.git"
REPO_HTTPS="https://github.com/thanhnt1021/univ3.git"
DEST="docs/univ3"

echo "univ3 bootstrap → $DEST"

if [ -d "$DEST/.git" ] || [ -f "$DEST/VERSION" ]; then
  echo "  Đã có $DEST — bỏ qua clone (dùng 'sync uni' để cập nhật). Chỉ chạy install."
else
  mkdir -p docs
  TMP="$(mktemp -d)"
  # Ưu tiên gh (xử lý auth private repo gọn nhất), fallback SSH, rồi HTTPS.
  if command -v gh >/dev/null 2>&1 && gh repo clone thanhnt1021/univ3 "$TMP" -- -q 2>/dev/null; then
    echo "  cloned qua gh"
  elif git clone -q "$REPO_SSH" "$TMP" 2>/dev/null; then
    echo "  cloned qua SSH"
  elif git clone -q "$REPO_HTTPS" "$TMP" 2>/dev/null; then
    echo "  cloned qua HTTPS"
  else
    echo "  !! Clone thất bại. Cần quyền truy cập repo PRIVATE thanhnt1021/univ3:"
    echo "     gh auth login   (tài khoản thanhnt1021)   HOẶC cài SSH key."
    rm -rf "$TMP"; exit 1
  fi
  rm -rf "$TMP/.git"          # nhúng làm cache trong project, KHÔNG nested repo
  mv "$TMP" "$DEST"
  echo "  → $DEST"
fi

# Cài hook Claude + skill + git pre-commit + sinh AGENTS.md/MANIFEST
python3 "$DEST/install.py" --harness all

echo "Xong. Tạo CLAUDE.md (dòng đầu '@AGENTS.md') + copy $DEST/AGENTS.md ra root nếu chưa có."
