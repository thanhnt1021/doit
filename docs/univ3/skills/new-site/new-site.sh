#!/usr/bin/env bash
# new-site — create a new Cloudflare Pages site (direct-upload) + GitHub repo, headless via API token.
# Credentials come from ~/.claude/cloudflare-deploy.env (NEVER inside univ3).
#
# Usage:
#   new-site.sh <name> [--no-d1] [--domain <fqdn>] [--dir <path>]
# Examples:
#   new-site.sh vevoi2                 # -> vevoi2.jst4.fun, D1 vevoi2-db, repo <owner>/vevoi2
#   new-site.sh shop --domain shop.jst4.fun
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ENVFILE="${CLOUDFLARE_DEPLOY_ENV:-$HOME/.claude/cloudflare-deploy.env}"
[ -f "$ENVFILE" ] || { echo "Thiếu $ENVFILE — xem SKILL.md."; exit 1; }
# shellcheck disable=SC1090
source "$ENVFILE"
[ "${CF_API_TOKEN:-}" = "DAN_TOKEN_VAO_DAY" ] && { echo "Chưa dán CF_API_TOKEN vào $ENVFILE."; exit 1; }
: "${CF_API_TOKEN:?}" "${CF_ACCOUNT_ID:?}" "${CF_ZONE_NAME:?}" "${CF_ZONE_ID:?}" "${GH_OWNER:?}"

# wrangler uses the token instead of OAuth when these two vars are set
export CLOUDFLARE_API_TOKEN="$CF_API_TOKEN"
export CLOUDFLARE_ACCOUNT_ID="$CF_ACCOUNT_ID"

NAME=""; USE_D1=1; DOMAIN=""; DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --no-d1) USE_D1=0;;
    --domain) DOMAIN="$2"; shift;;
    --dir) DIR="$2"; shift;;
    -*) echo "Tham số lạ: $1"; exit 1;;
    *) NAME="$1";;
  esac; shift
done
[ -n "$NAME" ] || { echo "Thiếu <name>. Cú pháp: new-site.sh <name>"; exit 1; }
[ -n "$DOMAIN" ] || DOMAIN="$NAME.$CF_ZONE_NAME"
[ -n "$DIR" ] || DIR="$HOME/PycharmProjects/$NAME"
API="https://api.cloudflare.com/client/v4"
cf() { curl -s -H "Authorization: Bearer $CF_API_TOKEN" -H "Content-Type: application/json" "$@"; }
ok() { python3 -c 'import sys,json;d=json.load(sys.stdin);print("OK" if d.get("success") else "LỖI "+json.dumps(d.get("errors"),ensure_ascii=False))'; }

echo "==> Tạo trang: $NAME | domain: $DOMAIN | dir: $DIR | D1: $USE_D1"
[ -e "$DIR" ] && { echo "$DIR đã tồn tại."; exit 1; }
mkdir -p "$DIR/public" "$DIR/functions/api" "$DIR/db"
cd "$DIR"

# 1) Scaffold
cat > wrangler.toml <<TOML
name = "$NAME"
compatibility_date = "2025-06-01"
pages_build_output_dir = "public"
TOML
cat > public/index.html <<HTML
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>$NAME</title>
<meta name="description" content="$NAME">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:url" content="https://$DOMAIN/">
<meta property="og:title" content="$NAME">
<meta property="og:description" content="$NAME">
<meta property="og:image" content="https://$DOMAIN/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="$NAME">
<meta name="twitter:image" content="https://$DOMAIN/og.png">
</head>
<body><h1>$NAME</h1><p>Khung Cloudflare Pages. Thử <a href="/api/health">/api/health</a></p></body>
</html>
HTML
# favicon.svg + og.png (1200x630 có tên site) + apple-touch-icon.png
bash "$SCRIPT_DIR/gen-assets.sh" "$NAME" "$DOMAIN" "$DIR/public" || echo "  (bỏ qua asset: gen-assets lỗi)"
cat > functions/api/health.js <<'JS'
export async function onRequestGet({ env }) {
  let db = "off";
  try { if (env.DB) { const r = await env.DB.prepare("SELECT 1 AS ok").first(); db = r?.ok === 1 ? "ok" : "err"; } }
  catch (e) { db = "err:" + e.message; }
  return Response.json({ status: "ok", db });
}
JS
cat > db/schema.sql <<'SQL'
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
SQL
cat > package.json <<JSON
{ "name": "$NAME", "private": true, "scripts": {
  "dev": "wrangler pages dev public",
  "deploy": "wrangler pages deploy public --project-name=$NAME",
  "db:schema": "wrangler d1 execute $NAME-db --remote --file=db/schema.sql"
}, "devDependencies": { "wrangler": "^4" } }
JSON
printf 'node_modules/\n.dev.vars\n.wrangler/\n.DS_Store\n*.pdf\n' > .gitignore

# 2) D1
if [ "$USE_D1" = 1 ]; then
  echo "==> Tạo D1..."; DBID=$(pnpm dlx wrangler d1 create "$NAME-db" 2>/dev/null | grep -oE '[0-9a-f-]{36}' | head -1)
  [ -n "$DBID" ] || { echo "Tạo D1 thất bại"; exit 1; }
  cat >> wrangler.toml <<TOML

[[d1_databases]]
binding = "DB"
database_name = "$NAME-db"
database_id = "$DBID"
TOML
  pnpm dlx wrangler d1 execute "$NAME-db" --remote --file=db/schema.sql -y >/dev/null 2>&1 && echo "    schema OK"
fi

# 3) Git + GitHub repo
git init -q; git add -A; git -c user.email=bot@local -c user.name=new-site commit -q -m "khoi tao $NAME"
echo "==> GitHub repo $GH_OWNER/$NAME..."
gh repo create "$GH_OWNER/$NAME" --private --source=. --remote=origin --push >/dev/null 2>&1 && echo "    pushed"

# 4) Pages project + deploy (headless, token)
echo "==> Pages project + deploy..."
pnpm dlx wrangler pages project create "$NAME" --production-branch=main >/dev/null 2>&1 || true
# WHY: tên <name>.pages.dev có thể đã thuộc người khác → Cloudflare cấp tên khác (ca oha → oha-65v.pages.dev);
# tự ghép "$NAME.pages.dev" sẽ trỏ CNAME sang site của người khác. Phải đọc subdomain thật từ API.
PAGES_HOST=$(cf "$API/accounts/$CF_ACCOUNT_ID/pages/projects/$NAME" \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print((d.get("result") or {}).get("subdomain") or "")' 2>/dev/null || true)
[ -n "$PAGES_HOST" ] || { echo "Không đọc được subdomain Pages của project $NAME — DỪNG, không đoán (kiểm lại token/tên project)."; exit 1; }
echo "    Pages host: $PAGES_HOST"
pnpm dlx wrangler pages deploy public --project-name="$NAME" --branch=main --commit-dirty=true 2>&1 | grep -iE 'Success|Deployment complete|http' | tail -2

# 5) Custom domain + DNS CNAME (API)
echo -n "==> Custom domain $DOMAIN: "
cf -X POST "$API/accounts/$CF_ACCOUNT_ID/pages/projects/$NAME/domains" --data "{\"name\":\"$DOMAIN\"}" | ok
SUB="${DOMAIN%.$CF_ZONE_NAME}"
echo -n "==> DNS CNAME $SUB -> $PAGES_HOST: "
cf -X POST "$API/zones/$CF_ZONE_ID/dns_records" \
  --data "{\"type\":\"CNAME\",\"name\":\"$SUB\",\"content\":\"$PAGES_HOST\",\"proxied\":true}" | ok

# 6) Info file
cat > CLOUDFLARE_PAGES_SETUP.md <<MD
# Cloudflare — $DOMAIN

| Field | Giá trị |
|---|---|
| Account ID | \`$CF_ACCOUNT_ID\` |
| Pages project | \`$NAME\` (direct-upload) |
| URL | \`$PAGES_HOST\` / \`$DOMAIN\` |
| GitHub repo | \`$GH_OWNER/$NAME\` |
| D1 | $( [ "$USE_D1" = 1 ] && echo "\`$NAME-db\` id \`$DBID\`, binding \`DB\`" || echo "không" ) |

Deploy lại: \`pnpm run deploy\`. Sinh bởi skill new-site.
MD
git add -A; git -c user.email=bot@local -c user.name=new-site commit -q -m "docs: cloudflare setup" && git push -q 2>/dev/null || true

echo ""
echo "XONG: https://$DOMAIN  (DNS/SSL custom domain có thể mất 1-2 phút để Active)"
echo "      https://$PAGES_HOST  (chạy ngay)"
