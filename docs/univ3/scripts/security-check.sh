#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# Security Health Check — generic template
# ─────────────────────────────────────────────────────────────────
# Usage (one-off):
#   SSH_PORT=22 DOMAIN=example.com CONTAINERS="app db nginx" \
#     bash security-check.sh
#
# Usage (with env file):
#   cat > ~/.env.security-check <<EOF
#   SSH_PORT=22
#   DOMAIN=example.com
#   CONTAINERS="app db nginx"
#   EXPECTED_CF_RULES=15              # 0 = skip Cloudflare check
#   BACKUP_DIR=/home/deploy/backups   # optional, skip if unset
#   BACKUP_GLOB="myapp.daily.*.sql.gz"
#   APP_DIRS="/home/deploy/myapp"     # space-separated, for npm audit
#   EOF
#   set -a; . ~/.env.security-check; set +a
#   bash security-check.sh
#
# Exit codes: always 0 — this is a report, not a gate. Read output.
# ─────────────────────────────────────────────────────────────────

set +e

# ── Defaults (override via env) ──────────────────────────────────
SSH_PORT="${SSH_PORT:-22}"
DOMAIN="${DOMAIN:-}"
CONTAINERS="${CONTAINERS:-}"
EXPECTED_CF_RULES="${EXPECTED_CF_RULES:-0}"
BACKUP_DIR="${BACKUP_DIR:-}"
BACKUP_GLOB="${BACKUP_GLOB:-*.sql.gz}"
BACKUP_MAX_AGE_HOURS="${BACKUP_MAX_AGE_HOURS:-30}"
APP_DIRS="${APP_DIRS:-}"

BOLD='\033[1m'; RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
err()  { echo -e "  ${RED}✗${NC} $1"; }
skip() { echo -e "  ${YELLOW}–${NC} $1 (skipped — not configured)"; }
hdr()  { echo -e "\n${BOLD}$1${NC}"; }

echo "============================================================"
echo "  SECURITY HEALTH CHECK — $(date -u +'%Y-%m-%d %H:%M UTC')"
echo "  Host: $(hostname)"
echo "============================================================"

# ── 1. SSH ───────────────────────────────────────────────────────
hdr "[1/7] SSH Configuration"
CFG_PORT=$(grep -iE '^Port ' /etc/ssh/sshd_config 2>/dev/null | awk '{print $2}')
if [ -n "$CFG_PORT" ]; then
  [ "$CFG_PORT" = "$SSH_PORT" ] && ok "Port matches expected ($SSH_PORT)" || warn "Port = $CFG_PORT, expected $SSH_PORT"
else
  warn "Cannot read SSH port from config"
fi

grep -qiE '^PermitRootLogin no' /etc/ssh/sshd_config 2>/dev/null && ok "Root login disabled" || err "Root login NOT disabled"

if grep -qirE '^PasswordAuthentication no' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/ 2>/dev/null; then
  ok "Password auth disabled"
else
  err "Password auth NOT disabled"
fi

grep -qE '^AuthenticationMethods publickey,keyboard-interactive' /etc/ssh/sshd_config 2>/dev/null && ok "Key + 2FA required" || warn "2FA not enforced (optional)"
grep -qE 'pam_google_authenticator.so .*nullok' /etc/pam.d/sshd 2>/dev/null && warn "PAM 2FA fail-open (nullok)" || ok "PAM 2FA fail-secure (or not enabled)"

# ── 2. Firewall ──────────────────────────────────────────────────
hdr "[2/7] UFW Firewall"
if systemctl is-active ufw >/dev/null 2>&1; then
  ok "UFW active"
  if [ "$EXPECTED_CF_RULES" -gt 0 ]; then
    UFW_OUT=$(sudo -n ufw status 2>/dev/null)
    if [ -z "$UFW_OUT" ]; then
      warn "Cannot read UFW rules (needs sudo)"
    else
      CF_RULES=$(echo "$UFW_OUT" | grep -c 'CF')
      [ "$CF_RULES" -ge "$EXPECTED_CF_RULES" ] && ok "UFW allowing $CF_RULES Cloudflare ranges" || warn "Only $CF_RULES CF rules — expected $EXPECTED_CF_RULES+"
    fi
  else
    skip "Cloudflare IP allowlist check"
  fi
else
  err "UFW NOT active"
fi

# ── 3. fail2ban ──────────────────────────────────────────────────
hdr "[3/7] fail2ban"
if systemctl is-active fail2ban >/dev/null 2>&1; then
  ok "fail2ban active"
  BANNED=$(sudo -n fail2ban-client status sshd 2>/dev/null | grep -oE 'Currently banned:\s*[0-9]+' | awk '{print $NF}')
  [ -n "$BANNED" ] && ok "sshd jail — currently banned: $BANNED" || warn "Cannot read jail (needs sudo)"
else
  err "fail2ban NOT active"
fi

# ── 4. Auto-upgrades ─────────────────────────────────────────────
hdr "[4/7] Security Updates"
systemctl is-active unattended-upgrades >/dev/null 2>&1 && ok "unattended-upgrades active" || err "unattended-upgrades NOT active"
LAST_UP=$(ls -t /var/log/unattended-upgrades/ 2>/dev/null | head -1)
[ -n "$LAST_UP" ] && ok "Last upgrade log: $LAST_UP" || warn "No upgrade log yet (new server?)"
AVAILABLE=$(apt list --upgradable 2>/dev/null | grep -c security)
[ "$AVAILABLE" -gt 0 ] && warn "$AVAILABLE security updates pending" || ok "No pending security updates"

# ── 5. Docker stack ──────────────────────────────────────────────
hdr "[5/7] Docker Stack"
if [ -n "$CONTAINERS" ]; then
  for c in $CONTAINERS; do
    STATE=$(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null)
    [ "$STATE" = "running" ] && ok "$c: running" || err "$c: ${STATE:-NOT FOUND}"
  done
  EXPOSED=$(docker ps --format '{{.Ports}}' | grep -oE '0\.0\.0\.0:[0-9]+' | sort -u | tr '\n' ' ' | xargs)
  echo "  Host-exposed ports: ${EXPOSED:-none}"
else
  skip "Docker container check"
fi

# ── 6. Rootkit scanner ───────────────────────────────────────────
hdr "[6/7] Rootkit Scanner"
command -v rkhunter >/dev/null && ok "rkhunter installed" || warn "rkhunter NOT installed"
[ -f /etc/cron.d/rkhunter-weekly ] && ok "Weekly cron configured" || warn "No weekly rkhunter cron"
LAST_SCAN=$(stat -c %y /var/log/rkhunter.log 2>/dev/null | cut -d' ' -f1)
[ -n "$LAST_SCAN" ] && ok "Last scan: $LAST_SCAN" || warn "No rkhunter log"

# ── 7. Backup ────────────────────────────────────────────────────
hdr "[7/7] Backup"
crontab -l 2>/dev/null | grep -qE 'backup' && ok "Backup cron in user crontab" || warn "No backup cron in user crontab"
if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR" ]; then
  LATEST_BAK=$(ls -t "$BACKUP_DIR"/$BACKUP_GLOB 2>/dev/null | head -1)
  if [ -n "$LATEST_BAK" ]; then
    AGE=$(( ( $(date +%s) - $(stat -c %Y "$LATEST_BAK") ) / 3600 ))
    SIZE=$(du -h "$LATEST_BAK" | cut -f1)
    [ "$AGE" -lt "$BACKUP_MAX_AGE_HOURS" ] && ok "Latest backup: ${AGE}h ago ($SIZE)" || warn "Latest backup ${AGE}h ago — TOO OLD (max ${BACKUP_MAX_AGE_HOURS}h)"
  else
    err "No backup files matching '$BACKUP_GLOB' in $BACKUP_DIR"
  fi
else
  skip "Backup file freshness check (set BACKUP_DIR)"
fi

if command -v rclone >/dev/null 2>&1 && [ -f "$HOME/.config/rclone/rclone.conf" ]; then
  ok "rclone off-site configured"
else
  warn "No off-site backup (local only = SPOF)"
fi

# ── Extras ───────────────────────────────────────────────────────
if [ -n "$APP_DIRS" ]; then
  hdr "[+] App Dependencies (npm audit)"
  for app in $APP_DIRS; do
    [ -f "$app/package.json" ] || continue
    name=$(basename "$app")
    VULN=$(docker run --rm -v "$app":/app:ro -w /app node:20-slim sh -c 'npm audit --audit-level=high --json 2>/dev/null | grep -oE "\"total\":[0-9]+" | head -1' 2>/dev/null | awk -F: '{print $2}')
    [ -z "$VULN" ] && VULN=0
    [ "$VULN" -eq 0 ] && ok "$name: 0 high+ vulnerabilities" || warn "$name: $VULN high+ vulnerabilities — run npm audit"
  done
fi

if [ -n "$DOMAIN" ]; then
  hdr "[+] SSL Certificate — $DOMAIN"
  EXPIRY=$(echo | openssl s_client -servername "$DOMAIN" -connect "$DOMAIN":443 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
  [ -n "$EXPIRY" ] && ok "Cert expires: $EXPIRY" || warn "Cannot check cert for $DOMAIN"
fi

hdr "[+] Recent Auth Failures"
FAIL_COUNT=$(sudo -n grep "Failed password" /var/log/auth.log 2>/dev/null | wc -l)
echo "  Failed SSH attempts in auth.log: $FAIL_COUNT (requires sudo for accurate count)"

echo ""
echo "============================================================"
echo "  DONE. Review any ⚠ or ✗ above."
echo "============================================================"
