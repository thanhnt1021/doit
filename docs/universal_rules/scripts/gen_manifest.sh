#!/usr/bin/env bash
# Sinh MANIFEST.txt = sha256 của mọi file rule trong repo (SSOT integrity).
# Chạy từ ROOT repo universal-workflow TRƯỚC MỖI COMMIT có đổi rule:
#   bash scripts/gen_manifest.sh
# So 2 bản copy bất kỳ (project vs repo):
#   cd <project>/docs/universal_rules && shasum -a 256 -c MANIFEST.txt --quiet
set -e
cd "$(dirname "$0")/.."

OUT="MANIFEST.txt"
# Chỉ hash phần ĐƯỢC SYNC sang project (loại meta của repo: README/CLAUDE/.gitignore
# — bootstrap xoá/không copy chúng) + loại rác; sort để diff ổn định.
find . -type f \
  ! -path "./.git/*" \
  ! -name "$OUT" \
  ! -name ".DS_Store" \
  ! -path "*/__pycache__/*" \
  ! -name "telegram_config.env" \
  ! -path "./README.md" \
  ! -path "./CLAUDE.md" \
  ! -path "./.gitignore" \
  | sed 's|^\./||' | LC_ALL=C sort \
  | xargs shasum -a 256 > "$OUT"

echo "✅ $OUT: $(wc -l < "$OUT" | tr -d ' ') file — version $(cat VERSION 2>/dev/null || echo '?')"
