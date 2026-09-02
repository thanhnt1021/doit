#!/usr/bin/env bash
# gen-assets — sinh favicon.svg + og.png (1200x630) + apple-touch-icon.png cho 1 site.
# Offline bang qlmanage + sips (built-in macOS), khong can npm/imagemagick.
# Dung: gen-assets.sh <name> <domain> <public_dir>
set -euo pipefail
NAME="${1:?name}"; DOMAIN="${2:?domain}"; PUB="${3:?public_dir}"
mkdir -p "$PUB"

# brand color deterministic tu ten
PALETTE=(4f7cff 22c55e f59e0b ef4444 a855f7 06b6d4 ec4899 14b8a6)
sum=0; for ((i=0;i<${#NAME};i++)); do sum=$((sum + $(printf '%d' "'${NAME:$i:1}"))); done
COLOR="#${PALETTE[$((sum % ${#PALETTE[@]}))]}"
LETTER=$(printf '%s' "${NAME:0:1}" | tr '[:lower:]' '[:upper:]')
esc(){ printf '%s' "$1" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'; }
NM=$(esc "$NAME"); DM=$(esc "$DOMAIN")

cat > "$PUB/favicon.svg" <<SVG
<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="$COLOR"/>
<text x="32" y="45" font-family="Helvetica,Arial" font-size="38" font-weight="bold" fill="#fff" text-anchor="middle">$LETTER</text>
</svg>
SVG

TMP=$(mktemp -d); mkdir -p "$TMP/out"
cat > "$TMP/og.svg" <<SVG
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630">
<rect width="1200" height="630" fill="#0b1020"/>
<rect width="1200" height="14" fill="$COLOR"/>
<rect x="80" y="250" width="96" height="96" rx="22" fill="$COLOR"/>
<text x="128" y="318" font-family="Helvetica,Arial" font-size="56" font-weight="bold" fill="#fff" text-anchor="middle">$LETTER</text>
<text x="208" y="305" font-family="Helvetica,Arial" font-size="92" font-weight="bold" fill="#fff">$NM</text>
<text x="82" y="415" font-family="Helvetica,Arial" font-size="38" fill="#9aa7c7">$DM</text>
</svg>
SVG
qlmanage -t -s 1200 -o "$TMP/out" "$TMP/og.svg" >/dev/null 2>&1
raw=$(ls "$TMP/out"/*.png 2>/dev/null | head -1)
[ -n "$raw" ] || { echo "qlmanage khong render duoc og.svg"; rm -rf "$TMP"; exit 1; }
# qlmanage tra PNG vuong 1200x1200 (letterbox) -> crop giua lay dung 1200x630
sips -c 630 1200 "$raw" --out "$PUB/og.png" >/dev/null 2>&1

qlmanage -t -s 180 -o "$TMP" "$PUB/favicon.svg" >/dev/null 2>&1
at=$(ls "$TMP"/*.png 2>/dev/null | head -1)
[ -n "$at" ] && sips -z 180 180 "$at" --out "$PUB/apple-touch-icon.png" >/dev/null 2>&1
rm -rf "$TMP"

dim=$(sips -g pixelWidth -g pixelHeight "$PUB/og.png" 2>/dev/null | awk '/pixelWidth|pixelHeight/{print $2}' | paste -sd x -)
echo "assets OK: favicon.svg + og.png ($dim) + apple-touch-icon.png -> $PUB"
