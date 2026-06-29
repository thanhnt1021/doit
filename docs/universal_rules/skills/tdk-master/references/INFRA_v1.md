# INFRA — INFRASTRUCTURE & CI/CD

## 🧔 Sa Tăng + 🐴 Bạch Long Mã — Server Setup, Deploy, Monitoring, Pipeline

---

```yaml
---
framework: TDK-Pipeline
role: INFRA (Sa Tăng + Bạch Long Mã)
version: 1.0
execution_protocol: v1
min_claude_model: sonnet
mode: [setup, deploy, monitor, incident, cicd, audit]
related_files: [MASTER_v1.md, PGA_v1.md, RRI-T_v1.md]
---
```

---

# PART 1: CLI EXECUTION PROTOCOL

> **Claude: đọc Part 1 TRƯỚC. Dùng Part 2 làm knowledge base. Part 3 cho templates.**
> **Nếu đến từ MASTER pipeline → context đã có, skip EP.3.**

---

## EP.1 Khi nhận file này, Claude phải:

```
1. ĐỌC Part 1 — hiểu modes + protocol
2. KHÔNG dump toàn bộ checklist ra trừ khi user hỏi
3. Nếu từ MASTER → dùng context, execute mode phù hợp
4. Nếu standalone → hỏi: "Server gì? Dự án gì? Cần setup/deploy/fix?"
5. OUTPUT checklist + commands, user confirm trước khi chạy
6. SAU MỖI THAY ĐỔI: verify (curl, systemctl status, log check)
```

## EP.2 Execution Modes

```
MODE 1: SETUP ("setup server mới" / "cài đặt VPS")
  → Part 2 Section 1-6 → Full server setup checklist
  → Output: Server ready, all services running

MODE 2: DEPLOY ("deploy dự án X" / "đưa lên server")
  → Part 2 Section 7 → Deploy procedure
  → Output: App running, health check pass

MODE 3: MONITOR ("setup monitoring" / "cần alert")
  → Part 2 Section 8 → Monitoring + alerting setup
  → Output: Monitoring active, test alert sent

MODE 4: INCIDENT ("server chết" / "502" / "disk full" / "bị hack")
  → Part 2 Section 9 → Incident Response
  → KHÔNG cần user confirm giữa steps — chạy liên tục
  → Output: Service restored, root cause identified

MODE 5: CICD ("setup auto deploy" / "GitHub Actions")
  → Part 2 Section 10 → CI/CD Pipeline setup
  → Output: Pipeline configured, test deploy success

MODE 6: AUDIT ("check security server" / "server health")
  → Part 2 Section 11 → Security + Health audit
  → Output: Audit report, action items
```

## EP.3 Interactive Flow

```
Nếu standalone (không từ MASTER):

Q1: "Server gì?" → Ubuntu version, VPS provider, specs (RAM/CPU/disk)
Q2: "Dự án gì?" → Tech stack (Next.js, Python, Node, etc.)
Q3: "Cần gì?" → Setup / Deploy / Fix / Monitor / CI/CD
Q4: "Domain?" → Domain name, SSL needed?

Config tự động:
  Next.js → nginx reverse proxy + PM2 + Node
  Python bot → systemd service + venv
  Static site → nginx direct serve
  Multiple projects → nginx multi-site + PM2 ecosystem
```

---

# PART 2: KNOWLEDGE BASE

---

## 1. INITIAL SERVER SETUP

### 1.1 First Login & Security

```bash
# === SAU KHI NHẬN VPS MỚI ===

# 1. Login as root, update system
apt update && apt upgrade -y

# 2. Create non-root user
adduser deploy
usermod -aG sudo deploy

# 3. Setup SSH key auth
mkdir -p /home/deploy/.ssh
# Copy public key vào authorized_keys
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh

# 4. Harden SSH
# /etc/ssh/sshd_config:
#   PermitRootLogin no
#   PasswordAuthentication no
#   PubkeyAuthentication yes
#   MaxAuthTries 3
systemctl restart sshd

# 5. Firewall
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
ufw status
```

### 1.2 fail2ban

```bash
apt install fail2ban -y

# /etc/fail2ban/jail.local
cat << 'EOF' > /etc/fail2ban/jail.local
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 86400
EOF

systemctl enable fail2ban
systemctl start fail2ban
fail2ban-client status sshd
```

### 1.3 Automatic Security Updates

```bash
# Ubuntu Pro (nếu eligible)
pro attach [token]

# Unattended upgrades
apt install unattended-upgrades -y
dpkg-reconfigure -plow unattended-upgrades
```

---

## 2. WEB SERVER — NGINX

### 2.1 Install & Base Config

```bash
apt install nginx -y
systemctl enable nginx
```

### 2.2 Reverse Proxy Template (Next.js / Node)

```nginx
# /etc/nginx/sites-available/myapp.com
server {
    listen 80;
    server_name myapp.com www.myapp.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files cache
    location /_next/static/ {
        proxy_pass http://127.0.0.1:3000;
        expires 365d;
        add_header Cache-Control "public, immutable";
    }

    # Limit upload size
    client_max_body_size 10M;
}
```

### 2.3 Static Site Template

```nginx
server {
    listen 80;
    server_name static.myapp.com;
    root /var/www/static.myapp.com;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2)$ {
        expires 30d;
        add_header Cache-Control "public";
    }
}
```

### 2.4 Enable Site + SSL

```bash
ln -s /etc/nginx/sites-available/myapp.com /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# SSL with Certbot
apt install certbot python3-certbot-nginx -y
certbot --nginx -d myapp.com -d www.myapp.com
# Auto-renewal: certbot renew runs via systemd timer
```

---

## 3. PROCESS MANAGEMENT — PM2

### 3.1 Install & Setup

```bash
npm install -g pm2

# Start app
cd /home/deploy/myapp
pm2 start npm --name "myapp" -- start
# hoặc
pm2 start ecosystem.config.js

# Save + auto-start on boot
pm2 save
pm2 startup systemd -u deploy --hp /home/deploy
```

### 3.2 Ecosystem File

```javascript
// ecosystem.config.js
module.exports = {
  apps: [
    {
      name: 'myapp',
      cwd: '/home/deploy/myapp',
      script: 'npm',
      args: 'start',
      env: {
        NODE_ENV: 'production',
        PORT: 3000,
      },
      instances: 1,          // hoặc 'max' cho cluster
      exec_mode: 'fork',     // hoặc 'cluster'
      max_memory_restart: '500M',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      error_file: '/home/deploy/logs/myapp-error.log',
      out_file: '/home/deploy/logs/myapp-out.log',
      merge_logs: true,
    }
  ]
};
```

### 3.3 Common Commands

```bash
pm2 status                    # List all processes
pm2 logs myapp --lines 50    # View logs
pm2 restart myapp            # Restart
pm2 reload myapp             # Zero-downtime reload (cluster mode)
pm2 monit                    # Real-time monitor
pm2 flush                    # Clear logs
```

---

## 4. SYSTEMD SERVICES (Python bots, background jobs)

### 4.1 Service Template

```ini
# /etc/systemd/system/mybot.service
[Unit]
Description=My Telegram Bot
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/home/deploy/mybot
ExecStart=/home/deploy/mybot/venv/bin/python bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mybot

# Environment
EnvironmentFile=/home/deploy/mybot/.env

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### 4.2 Common Commands

```bash
systemctl daemon-reload
systemctl enable mybot
systemctl start mybot
systemctl status mybot
journalctl -u mybot -f --no-pager    # Live logs
journalctl -u mybot --since "1 hour ago"
```

---

## 5. DATABASE — POSTGRESQL

### 5.1 Install & Setup

```bash
apt install postgresql postgresql-contrib -y
systemctl enable postgresql

# Create user + database
sudo -u postgres psql
CREATE USER myapp WITH PASSWORD 'secure_password';
CREATE DATABASE myapp_db OWNER myapp;
GRANT ALL PRIVILEGES ON DATABASE myapp_db TO myapp;
\q
```

### 5.2 Backup Strategy

```bash
# Daily backup script
cat << 'EOF' > /home/deploy/scripts/backup-db.sh
#!/bin/bash
BACKUP_DIR="/home/deploy/backups/db"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="myapp_db"

mkdir -p $BACKUP_DIR
pg_dump -U myapp $DB_NAME | gzip > "$BACKUP_DIR/${DB_NAME}_${DATE}.gz"

# Keep last 14 days
find $BACKUP_DIR -name "*.gz" -mtime +14 -delete

echo "$(date): Backup completed — ${DB_NAME}_${DATE}.gz"
EOF

chmod +x /home/deploy/scripts/backup-db.sh
```

### 5.3 Backup Cron

```bash
# crontab -e (as deploy user)
# Backup daily at 3:00 UTC
0 3 * * * /home/deploy/scripts/backup-db.sh >> /home/deploy/logs/backup.log 2>&1
```

### 5.4 Restore

```bash
# Restore from backup
gunzip -k backup_file.gz
psql -U myapp myapp_db < backup_file
```

---

## 6. DISK & RESOURCE MANAGEMENT

### 6.1 Disk Monitoring

```bash
# Check disk usage
df -h
du -sh /home/deploy/*/
du -sh /var/log/

# Common disk hogs
journalctl --disk-usage          # systemd journal
du -sh /home/deploy/logs/        # PM2 logs
du -sh /home/deploy/backups/     # Old backups
```

### 6.2 Cleanup Script

```bash
cat << 'EOF' > /home/deploy/scripts/cleanup.sh
#!/bin/bash
echo "=== Disk before cleanup ==="
df -h /

# Truncate PM2 logs > 100MB
find /home/deploy/logs/ -name "*.log" -size +100M -exec truncate -s 10M {} \;

# Clean old journals
journalctl --vacuum-size=200M

# Clean apt cache
apt autoremove -y
apt autoclean

# Clean old backups (keep 14 days)
find /home/deploy/backups/ -name "*.gz" -mtime +14 -delete

echo "=== Disk after cleanup ==="
df -h /
EOF

chmod +x /home/deploy/scripts/cleanup.sh
```

### 6.3 Disk Alert Cron

```bash
# Alert when disk > 85%
cat << 'EOF' > /home/deploy/scripts/disk-alert.sh
#!/bin/bash
THRESHOLD=85
USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$USAGE" -gt "$THRESHOLD" ]; then
    echo "⚠️ DISK ALERT: ${USAGE}% used on $(hostname) at $(date)" | \
    # Send via Telegram bot, email, or webhook
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
         -d "chat_id=${ADMIN_CHAT_ID}" \
         -d "text=⚠️ DISK ALERT: ${USAGE}% used on $(hostname)"
fi
EOF

# Check every 6 hours
0 */6 * * * /home/deploy/scripts/disk-alert.sh
```

---

## 7. DEPLOYMENT PROCEDURES

### 7.1 Manual Deploy (Simple)

```bash
# === DEPLOY SCRIPT ===
cat << 'EOF' > /home/deploy/scripts/deploy-myapp.sh
#!/bin/bash
set -e

APP_DIR="/home/deploy/myapp"
APP_NAME="myapp"

echo "$(date): Starting deploy..."

cd $APP_DIR

# Pull latest
git pull origin main

# Install dependencies
npm ci --production=false

# Build
npm run build

# Run migrations (if applicable)
npx prisma migrate deploy

# Restart
pm2 restart $APP_NAME

# Health check
sleep 5
if curl -sf http://localhost:3000/api/health > /dev/null; then
    echo "$(date): Deploy SUCCESS ✅"
else
    echo "$(date): Deploy FAILED ❌ — health check failed"
    # Rollback
    git checkout HEAD~1
    npm ci --production=false
    npm run build
    pm2 restart $APP_NAME
    echo "$(date): Rolled back to previous version"
    exit 1
fi
EOF

chmod +x /home/deploy/scripts/deploy-myapp.sh
```

### 7.2 Zero-Downtime Deploy (PM2 Cluster)

```bash
# ecosystem.config.js phải dùng cluster mode
# instances: 2 (hoặc 'max')
# exec_mode: 'cluster'

pm2 reload myapp    # Rolling restart, 0 downtime
```

### 7.3 Rollback Procedure

```bash
# Quick rollback
cd /home/deploy/myapp
git log --oneline -5              # Find previous commit
git checkout <commit-hash>        # Checkout
npm ci --production=false && npm run build
pm2 restart myapp

# Verify
curl -sf http://localhost:3000/api/health
```

---

## 8. MONITORING & ALERTING

### 8.1 Basic Monitoring Stack

```bash
# UptimeRobot (free tier)
# → Monitor: https://myapp.com (HTTP check every 5 min)
# → Alert: Telegram webhook hoặc email

# PM2 built-in
pm2 monit                    # Real-time CPU/memory
pm2 status                   # Process status

# Manual health check cron
cat << 'EOF' > /home/deploy/scripts/health-check.sh
#!/bin/bash
URLS=(
    "https://myapp.com"
    "https://myapp.com/api/health"
)

for URL in "${URLS[@]}"; do
    STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$URL" --max-time 10)
    if [ "$STATUS" != "200" ]; then
        echo "❌ $URL returned $STATUS at $(date)"
        # Alert via Telegram
        curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
             -d "chat_id=${ADMIN_CHAT_ID}" \
             -d "text=❌ Health check failed: $URL returned $STATUS"
    fi
done
EOF

# Every 5 minutes
*/5 * * * * /home/deploy/scripts/health-check.sh >> /home/deploy/logs/health.log 2>&1
```

### 8.2 Log Management

```bash
# Centralized log location
mkdir -p /home/deploy/logs

# Logrotate for PM2 logs
cat << 'EOF' > /etc/logrotate.d/pm2-deploy
/home/deploy/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF
```

---

## 9. INCIDENT RESPONSE

### 9.1 Triage Flowchart

```
INCIDENT DETECTED
  ↓
Step 1: IDENTIFY (2 min)
  ├── Server unreachable? → Check VPS provider status
  ├── 502/503? → Check nginx + app process
  ├── Slow? → Check CPU/memory/disk
  ├── Specific error? → Check app logs
  └── Security? → Check auth.log, fail2ban
  ↓
Step 2: STABILIZE (5 min)
  ├── Restart app: pm2 restart myapp
  ├── Restart nginx: systemctl restart nginx
  ├── Clear disk: /home/deploy/scripts/cleanup.sh
  ├── Kill runaway process: kill -9 [PID]
  └── Block attacker: fail2ban-client set sshd banip [IP]
  ↓
Step 3: VERIFY (2 min)
  ├── curl health check
  ├── pm2 status
  ├── Check logs for new errors
  └── User-facing check (open in browser)
  ↓
Step 4: ROOT CAUSE (after stable, 15-30 min)
  ├── What changed? (deploy, config, traffic spike)
  ├── When did it start? (correlate with logs)
  ├── Prevent recurrence → update scripts/monitoring
  └── Document in incident log
```

### 9.2 Common Incidents

```
502 BAD GATEWAY:
  1. pm2 status → app crashed?
  2. pm2 restart myapp
  3. Check logs: pm2 logs myapp --lines 100
  4. If OOM: increase max_memory_restart in ecosystem.config.js
  5. If port conflict: lsof -i :3000

DISK FULL:
  1. df -h → which partition?
  2. du -sh /home/deploy/*/ → what's eating space?
  3. Run cleanup.sh
  4. If DB: check pg_dump size, vacuum
  5. If logs: pm2 flush + truncate

SSH BRUTE FORCE:
  1. fail2ban-client status sshd → check bans
  2. grep "Failed password" /var/log/auth.log | tail -20
  3. If persistent: change SSH port, add IP whitelist

MEMORY LEAK:
  1. pm2 monit → watch memory over time
  2. If climbing: pm2 restart myapp (temporary fix)
  3. Set max_memory_restart in PM2 config
  4. Investigate code (→ route to RRI-T Code-Path analysis)

SSL EXPIRED:
  1. certbot renew
  2. nginx -t && systemctl reload nginx
  3. Check auto-renewal: systemctl status certbot.timer
```

### 9.3 Incident Log Template

```
═══════════════════════════════════════
INCIDENT LOG — [Date] [Time]
═══════════════════════════════════════
Severity: [P0 Critical | P1 Major | P2 Minor]
Duration: [start] → [resolved] = [N min]
Impact: [what users experienced]

Timeline:
  [HH:MM] Detected: [how]
  [HH:MM] Action: [what was done]
  [HH:MM] Resolved: [confirmation]

Root Cause: [description]

Prevention:
  □ [action to prevent recurrence]
  □ [monitoring improvement]
═══════════════════════════════════════
```

---

## 10. CI/CD PIPELINE

> **Workflow templates đầy đủ** (Node.js, Python, Docker — lint + test + security audit + deploy):
> Xem `docs/universal_rules/rules/CI_CD_TEMPLATE.md`
>
> Section này chỉ cover SSH deploy pattern cơ bản. Dùng `CI_CD_TEMPLATE.md` khi cần full CI/CD pipeline.

### 10.1 GitHub Actions — SSH Deploy

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /home/deploy/myapp
            git pull origin main
            npm ci --production=false
            npm run build
            npx prisma migrate deploy
            pm2 restart myapp
            sleep 5
            curl -sf http://localhost:3000/api/health || exit 1
```

### 10.2 GitHub Actions — With Build Check

```yaml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - run: npm run lint

  deploy:
    needs: check
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: /home/deploy/scripts/deploy-myapp.sh
```

### 10.3 GitHub Secrets Setup

```
Repository → Settings → Secrets and variables → Actions

Required secrets:
  SERVER_HOST     = IP hoặc domain của VPS
  SERVER_USER     = deploy (non-root user)
  SSH_PRIVATE_KEY = Private key (ed25519 recommended)
```

### 10.4 Deploy Key Setup on Server

```bash
# On local machine
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/deploy_key

# On server: add public key
cat deploy_key.pub >> /home/deploy/.ssh/authorized_keys

# In GitHub: add private key as secret SSH_PRIVATE_KEY
```

---

## 11. SECURITY & HEALTH AUDIT

> **App-level security** (OWASP Top 10, auth, file upload, dependency audit):
> Xem `docs/universal_rules/rules/SECURITY_CHECKLIST.md`
>
> **Secrets management** (.env, rotation, classification):
> Xem `docs/universal_rules/rules/ENV_RULES.md`
>
> Section này focus server-level security. Kết hợp với 2 file trên cho coverage đầy đủ.

### 11.1 Security Checklist

```
ACCESS:
  □ Root SSH disabled?
  □ Password auth disabled (key-only)?
  □ fail2ban active?
  □ Firewall (ufw) enabled? Only necessary ports open?
  □ Non-root user for app?

NETWORK:
  □ SSL/TLS on all domains? (certbot)
  □ Auto-renewal working? (certbot renew --dry-run)
  □ Security headers in nginx? (X-Frame-Options, CSP, HSTS)
  □ Rate limiting on sensitive endpoints?

APP:
  □ .env file not in git? (.gitignore)
  □ Secrets not hardcoded?
  □ Dependencies updated? (npm audit, pip audit)
  □ Database credentials not default?
  □ File upload restrictions?

DATA:
  □ Database backup working? (check last backup)
  □ Backup tested? (restore to test env)
  □ Sensitive data encrypted at rest?
  □ Logs not containing passwords/tokens?

MONITORING:
  □ Health check running?
  □ Disk alert active?
  □ Log rotation configured?
  □ Uptime monitoring external? (UptimeRobot etc.)
```

### 11.2 Hardening Patterns — Docker + Cloudflare Stack

> **Nguồn:** session hardening server production 2026-04-17 → 18 (post-compromise rebuild).
> Các pattern bên dưới đã verify chạy production, áp dụng được cho mọi stack
> Docker + Next.js/Python + nginx behind Cloudflare.

#### 11.2.1 SSH — Key + Google Authenticator 2FA

```bash
apt install libpam-google-authenticator -y
# User chạy (KHÔNG sudo): google-authenticator
# Chọn: time-based, DISALLOW reuse, rate-limit 3/30s, scratch codes

# /etc/pam.d/sshd — thêm cuối file:
auth required pam_google_authenticator.so
# ⚠️ KHÔNG dùng `nullok` trong production — user chưa setup 2FA vẫn login được (fail-open)

# /etc/ssh/sshd_config
Port 52847                              # custom, tránh bot scan 22
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication yes
UsePAM yes
AuthenticationMethods publickey,keyboard-interactive   # BẮT BUỘC cả key + OTP
AllowUsers deploy
MaxAuthTries 3
LoginGraceTime 20

# Test trong session SSH THỨ HAI trước khi đóng session hiện tại.
systemctl reload ssh
```

#### 11.2.2 UFW — Restrict 80/443 to Cloudflare IPs (anti IP leak)

Sau khi bật Cloudflare Proxied, origin IP vẫn có thể leak qua Shodan/DNS history.
Attacker hit thẳng IP → bypass WAF/rate-limit Cloudflare.

```bash
# Fetch official CF ranges
for ip in $(curl -s https://www.cloudflare.com/ips-v4); do
  ufw allow proto tcp from $ip to any port 80,443 comment 'CF'
done
for ip in $(curl -s https://www.cloudflare.com/ips-v6); do
  ufw allow proto tcp from $ip to any port 80,443 comment 'CF6'
done
ufw delete allow 80/tcp
ufw delete allow 443/tcp
ufw reload

# Weekly sync (CF đôi khi thêm range):
# 0 5 * * 0 root /home/deploy/scripts/sync-cf-ufw.sh
```

#### 11.2.3 Nginx — DNS Resolver cho Docker Upstream (CRITICAL)

**Gotcha:** `upstream { server name; }` resolve DNS **1 lần lúc startup** rồi cache mãi mãi.
Khi container restart → đổi IP trên docker bridge → nginx vẫn gọi IP cũ → **502 Bad Gateway**.

❌ **Sai (cache stale):**
```nginx
upstream myapp {
    server myapp-container:3000;
}
server {
    location / { proxy_pass http://myapp; }
}
```

✅ **Đúng (re-resolve mỗi request qua resolver):**
```nginx
resolver 127.0.0.11 valid=10s ipv6=off;    # Docker's embedded DNS

server {
    set $upstream_myapp "myapp-container:3000";

    location / {
        proxy_pass http://$upstream_myapp$request_uri;
    }
}
```

Key points:
- `resolver` với `valid=10s` → DNS refresh mỗi 10s
- `set $variable` trong `proxy_pass` → ép nginx dùng resolver (upstream block KHÔNG dùng resolver)
- `$request_uri` phải append vì với variable, nginx không tự pass URI
- Nginx open-source native hỗ trợ pattern này — không cần nginx-plus

#### 11.2.4 Cron — Weekly rkhunter + chkrootkit

```bash
apt install rkhunter chkrootkit -y

# Fix WEB_CMD config (Ubuntu 24.04 ships broken default)
sed -i 's|^WEB_CMD=.*|WEB_CMD=""|' /etc/rkhunter.conf

# Baseline trên server fresh
rkhunter --propupd

# Weekly scan
cat > /etc/cron.d/rkhunter-weekly <<'EOF'
0 4 * * 0 root /usr/bin/rkhunter --check --skip-keypress --report-warnings-only --quiet >> /var/log/rkhunter-cron.log 2>&1
EOF
```

#### 11.2.5 DMARC — Progressive Enforcement

Không nhảy thẳng `p=reject` — sẽ reject cả email hợp lệ nếu SPF/DKIM config sai.

```
Tuần 1-2: v=DMARC1; p=quarantine; pct=25; rua=mailto:dmarc@yourdomain.com
  → Monitor rua reports. Fix SPF/DKIM cho mọi source hợp lệ.
Tuần 3-4: v=DMARC1; p=quarantine; pct=100; rua=...
Tuần 5+:  v=DMARC1; p=reject; pct=100; rua=...
```

#### 11.2.6 Docker Socket Mount — Defense in Depth

Nếu app container cần `/var/run/docker.sock` (restart, health check từ bot) — đó là **đường nâng quyền = root on host**. Mitigate bằng multi-layer auth TRƯỚC endpoint điều khiển:

```
Client → [Layer 1: URL path secret random]
       → [Layer 2: HMAC/secret_token header verification]
       → [Layer 3: Allowlist user_id / API key]
       → [Layer 4: Nginx IP allowlist (chỉ IP source hợp lệ: Telegram/CF/office)]
       → [Layer 5: Rate limit]
       → App code với docker.sock access
```

Attacker phải vượt đồng thời cả 5 lớp → practically impossible nếu không leak full secret set.

---

### 11.3 Ongoing Maintenance Schedule

> Nguồn: pattern post-compromise rebuild — giữ server secure qua thời gian, không phải one-time setup.

**Tư duy:** Security không phải trạng thái, là process. Setup đúng ngày 0 → 6 tháng sau drift nếu không audit định kỳ. Lịch bên dưới thiết kế để tối thiểu hóa công thủ công (auto hết) + 5 phút/tháng check kết quả.

**Script kèm theo:** `scripts/security-check.sh` trong repo universal-workflow — generic, set biến env rồi chạy trên server bất kỳ.

**Nice-to-have mỗi server — Claude Code hooks + TMUX:** `scripts/claude-hooks/` — Telegram notification khi Claude xong task / hỏi câu hỏi + TMUX auto-menu khi SSH. Reusable, setup 1 lần 5 phút. Xem `scripts/claude-hooks/README.md`.

#### Daily — AUTOMATED (setup 1 lần, xong quên)

| Job | Tool | Command/path |
|---|---|---|
| Security patches | unattended-upgrades | `/etc/apt/apt.conf.d/20auto-upgrades` |
| SSH brute-force block | fail2ban | jail sshd, `bantime=24h` |
| DB backup | cron + pg_dump | `0 3 * * * backup-db.sh` |

#### Weekly — AUTOMATED

| Job | Cron |
|---|---|
| Rootkit scan | `0 4 * * 0 rkhunter --check --skip-keypress --report-warnings-only --quiet` |
| (Optional) UFW sync Cloudflare IPs | `0 5 * * 0 sync-cf-ufw.sh` (CF đôi khi thêm range mới) |

#### Monthly — MANUAL, ~5 phút

```bash
# 1. Chạy health check — xem tất cả 7 lớp + extras
sudo bash scripts/security-check.sh

# 2. Action theo warning/error trong output

# 3. Check DMARC reports inbox (nếu đang enforce quarantine/reject)
# 4. Test restore DB backup — verify file không corrupt:
gunzip -c /path/to/backups/latest.sql.gz | head -20

# 5. Review fail2ban banned IPs — có pattern attack đặc biệt không?
sudo fail2ban-client status sshd
```

#### Quarterly — MANUAL, ~30 phút

```bash
# 1. npm/pip audit — CVE mới tuần nào cũng có
npm audit --audit-level=high                # hoặc pip-audit

# 2. Docker base images — patch security
docker compose pull
docker compose up -d

# 3. Review authorized SSH keys — thiết bị mất/bán?
cat ~/.ssh/authorized_keys                  # xem comment field

# 4. SSL cert (nếu dùng Let's Encrypt — 90 ngày). Cloudflare Origin 15 năm skip.
echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | \
  openssl x509 -noout -enddate

# 5. DMARC enforcement bump (nếu đang p=quarantine pct=25 + reports clean 2-3 tuần):
# → quarantine pct=100 → reject pct=100
```

#### Per-feature deploy — code-level

Trước mỗi `quick deploy`: `SECURITY_CHECKLIST.md §0` — grep RCE risk + input validation + `npm audit` sau `npm install`.

#### Per-OS-upgrade — CRITICAL

Ubuntu major version upgrade thường reset `/etc/ssh/sshd_config` về default.

```bash
# 1. Backup config trước
sudo tar czf /tmp/pre-upgrade-$(date +%F).tar.gz \
  /etc/ssh /etc/pam.d/sshd /etc/fail2ban /etc/ufw /etc/cron.d

# 2. do-release-upgrade
sudo do-release-upgrade

# 3. NGAY SAU khi reboot — chạy health check để detect drift
sudo bash scripts/security-check.sh

# 4. Verify SSH hardening còn đúng:
grep -E '^(Port|PermitRootLogin|PasswordAuthentication|AuthenticationMethods)' /etc/ssh/sshd_config
```

#### Drift signals — khi nào cần audit đột xuất

- CPU/memory/disk tăng đột biến (→ có thể miner)
- Outbound connections lạ (`ss -tn state established` → IP unknown)
- `last -n 20` thấy user hoặc IP lạ login
- fail2ban banned count tăng đột ngột (có thể là reconnaissance phase)
- Website chậm/lỗi không do deploy mới (có thể đang bị probe)

```bash
top                                    # CPU/memory
ss -tn state established               # outbound connections
last -n 20                             # recent logins
sudo fail2ban-client status sshd
```

---

### 11.4 Quick Health Check

```bash
# Run this periodically or after incidents
echo "=== SERVER HEALTH CHECK ==="
echo "Uptime: $(uptime)"
echo ""
echo "=== DISK ==="
df -h /
echo ""
echo "=== MEMORY ==="
free -h
echo ""
echo "=== CPU LOAD ==="
cat /proc/loadavg
echo ""
echo "=== PM2 PROCESSES ==="
pm2 status
echo ""
echo "=== NGINX ==="
systemctl is-active nginx
echo ""
echo "=== POSTGRESQL ==="
systemctl is-active postgresql
echo ""
echo "=== FAIL2BAN ==="
fail2ban-client status sshd 2>/dev/null || echo "Not installed"
echo ""
echo "=== SSL EXPIRY ==="
for domain in myapp.com; do
    echo -n "$domain: "
    echo | openssl s_client -servername $domain -connect $domain:443 2>/dev/null | \
    openssl x509 -noout -enddate 2>/dev/null || echo "N/A"
done
echo ""
echo "=== DISK HOGS (top 10) ==="
du -sh /home/deploy/*/ 2>/dev/null | sort -rh | head -10
echo ""
echo "=== RECENT ERRORS (last 1h) ==="
journalctl --since "1 hour ago" -p err --no-pager | tail -20
```

---

## 12. CRON MANAGEMENT

### 12.1 Rules

```
RULE 1: TẤT CẢ cron jobs dùng UTC
  Server timezone = UTC. KHÔNG dùng local timezone.
  VN (GMT+7): muốn chạy 10:00 VN = 03:00 UTC

RULE 2: Log EVERY cron job
  Append >> /home/deploy/logs/cronname.log 2>&1

RULE 3: List tất cả crons ở 1 chỗ
  Giữ file /home/deploy/CRON_REGISTRY.md
  Mỗi khi thêm/sửa/xóa cron → update file này

RULE 4: Test trước khi schedule
  Chạy command manually trước. Chạy được → thêm vào crontab.
```

### 12.2 Cron Registry Template

```markdown
# CRON REGISTRY — [Server Name]
# Updated: [date]

| Schedule (UTC) | VN Time | Command | Purpose | Log |
|---|---|---|---|---|
| 0 3 * * * | 10:00 | backup-db.sh | Daily DB backup | backup.log |
| */5 * * * * | every 5m | health-check.sh | HTTP health check | health.log |
| 0 */6 * * * | every 6h | disk-alert.sh | Disk usage alert | disk.log |
| 0 4 * * 0 | Sun 11:00 | cleanup.sh | Weekly cleanup | cleanup.log |
```

---

## 13. INTEGRATION VỚI BỘ TDK

```
MASTER → INFRA:
  TYPE A (dự án mới) → INFRA setup full (server + nginx + PM2/systemd + DB + SSL + CI/CD)
  TYPE C1 (sự cố server) → INFRA incident response
  TYPE E (infra request) → INFRA specific mode

INFRA → RRI-T:
  INFRA setup xong → RRI-T check D6 Infrastructure dimension
  INFRA incident resolved → RRI-T regression check

INFRA → PGA:
  INFRA constraint (server specs, cost) → PGA adjusts recommendations
  INFRA monitoring data → PGA G6 Retention input (uptime affects retention)

RRI-T → INFRA:
  RRI-T D6 FAIL → INFRA fix infrastructure issue
  RRI-T DevOps persona findings → INFRA address
```

---

# PART 3: TEMPLATES

## T.1 New Server Setup Checklist

```
PROJECT: _______________
SERVER: _______________ (provider, specs)
DOMAIN: _______________
DATE: _______________

PHASE 1 — BASE:
  □ OS updated
  □ Non-root user created
  □ SSH key auth only
  □ fail2ban installed
  □ UFW enabled (SSH + Nginx)
  □ Timezone = UTC

PHASE 2 — WEB:
  □ nginx installed
  □ Site config created
  □ SSL via certbot
  □ Auto-renewal verified

PHASE 3 — APP:
  □ Node/Python installed
  □ PM2 / systemd configured
  □ App running
  □ Health check passing

PHASE 4 — DATA:
  □ PostgreSQL installed (if needed)
  □ Database + user created
  □ Backup script configured
  □ Backup cron scheduled

PHASE 5 — MONITORING:
  □ Health check cron active
  □ Disk alert cron active
  □ Log rotation configured
  □ UptimeRobot (or similar) configured

PHASE 6 — CI/CD:
  □ Deploy script created
  □ GitHub Actions configured
  □ Deploy key on server
  □ Test deploy successful

PHASE 7 — DOCUMENTATION:
  □ Cron Registry updated
  □ .env.example in repo
  □ Deploy procedure documented

STATUS: [🟢 READY | 🟡 PARTIAL | 🔴 INCOMPLETE]
```

## T.2 Deploy Checklist

```
BEFORE DEPLOY:
  □ All tests pass locally
  □ Build succeeds locally
  □ Migration tested (if any)
  □ .env production values confirmed

DEPLOY:
  □ git pull
  □ npm ci / pip install
  □ Build
  □ Migrate
  □ Restart process

AFTER DEPLOY:
  □ Health check pass
  □ Smoke test key flows
  □ Check logs for errors (5 min)
  □ Monitor metrics (15 min)

IF FAILED:
  □ Rollback to previous commit
  □ Rebuild + restart
  □ Verify rollback successful
  □ Investigate root cause
```

---

*INFRA_v1.md — Bộ Tây Du Ký Pipeline v1.0*
*🧔 Sa Tăng (Infrastructure) + 🐴 Bạch Long Mã (CI/CD Pipeline)*
