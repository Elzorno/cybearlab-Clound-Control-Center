# ISCS 1800 Student Web Hosting Server — Rebuild Requirements

**Document version:** 1.0  
**Date:** 2026-04-29  
**Purpose:** Complete specification to rebuild this server from a fresh Ubuntu 24.04 image.  
**Primary use case:** Per-term academic HTTPS web hosting for an introductory web development course. Each student gets a sandboxed SFTP account, a live `<username>.cybearlab.cloud` website with PHP, and is auto-graded via the admin portal.

---

## Table of Contents

1. [Server Specifications](#1-server-specifications)
2. [DNS Requirements](#2-dns-requirements)
3. [OS and Base Configuration](#3-os-and-base-configuration)
4. [Firewall](#4-firewall)
5. [LEMP Stack](#5-lemp-stack)
6. [TLS / Let's Encrypt](#6-tls--lets-encrypt)
7. [Student Account Architecture](#7-student-account-architecture)
8. [SSH and SFTP Configuration](#8-ssh-and-sftp-configuration)
9. [Nginx Virtual Hosts](#9-nginx-virtual-hosts)
10. [PHP-FPM Pools](#10-php-fpm-pools)
11. [Admin Portal — Frontend](#11-admin-portal--frontend)
12. [Admin Portal — FastAPI Backend](#12-admin-portal--fastapi-backend)
13. [Automation Scripts](#13-automation-scripts)
14. [Systemd Services](#14-systemd-services)
15. [Fail2ban](#15-fail2ban)
16. [File Layout Reference](#16-file-layout-reference)
17. [Credentials and Secrets](#17-credentials-and-secrets)
18. [Post-Rebuild Verification Checklist](#18-post-rebuild-verification-checklist)
19. [Optimizations and Recommended Changes](#19-optimizations-and-recommended-changes)

---

## 1. Server Specifications

| Property | Current Value |
|----------|--------------|
| Provider | Hostinger VPS |
| Hostname | `srv1277965.hstgr.cloud` |
| Public IP | `72.61.7.180` |
| OS | Ubuntu 24.04.4 LTS (Noble Numbat) |
| Kernel | 6.8.0-100-generic |
| vCPUs | 2 (AMD EPYC 9354P) |
| RAM | 8 GB |
| Disk | 96 GB SSD (root), 1 GB /boot |
| Swap | **None** — add 2 GB swap file on rebuild (see §19) |
| Default gateway | 72.61.7.254 |

> **Note on routing:** GitHub's main DNS resolves to the `140.82.113.x` subnet which is unreachable from this provider. A `/etc/hosts` override is required: `140.82.112.3 github.com`. This entry must be added during rebuild.

---

## 2. DNS Requirements

All DNS is managed via **Hostinger DNS**. The following records must exist before provisioning TLS:

| Type | Name | Value |
|------|------|-------|
| A | `admin.cybearlab.cloud` | `72.61.7.180` |
| A | `*.cybearlab.cloud` | `72.61.7.180` |
| A | `cybearlab.cloud` | `72.61.7.180` |

The wildcard A record powers all student subdomains (`<username>.cybearlab.cloud`) without needing a per-student DNS entry.

---

## 3. OS and Base Configuration

### 3.1 Initial setup

```bash
apt update && apt upgrade -y
apt install -y curl wget git unzip build-essential ca-certificates gnupg lsb-release
timedatectl set-timezone UTC
hostnamectl set-hostname srv1277965.hstgr.cloud
```

### 3.2 Hosts file addition (GitHub routing workaround)

```bash
echo "140.82.112.3 github.com" >> /etc/hosts
```

### 3.3 No swap — add swap file

```bash
# Current server has NO swap. Recommended on rebuild:
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
sysctl vm.swappiness=10
echo 'vm.swappiness=10' >> /etc/sysctl.d/99-swappiness.conf
```

### 3.4 System file descriptor limits

```bash
# Add to /etc/security/limits.conf
*    soft nofile  65536
*    hard nofile  65536
root soft nofile  65536
root hard nofile  65536
```

---

## 4. Firewall (UFW)

```bash
apt install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
```

No other inbound ports are needed. The FastAPI backend listens on `127.0.0.1:8000` only (not externally exposed).

---

## 5. LEMP Stack

### 5.1 Nginx

```bash
apt install -y nginx
systemctl enable nginx
```

**Version used:** nginx/1.24.0 (Ubuntu)

**`/etc/nginx/nginx.conf` — required changes from default:**

```nginx
user www-data;
worker_processes auto;
pid /run/nginx.pid;
error_log /var/log/nginx/error.log;
include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections 768;
    multi_accept on;        # ← Enable (currently commented out — see §19)
}

http {
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;         # ← Add (see §19)
    types_hash_max_size 2048;
    server_tokens off;      # ← Uncomment (security)

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    ssl_protocols TLSv1.2 TLSv1.3;   # ← Drop TLSv1/1.1 (see §19)
    ssl_prefer_server_ciphers off;

    access_log /var/log/nginx/access.log;
    error_log  /var/log/nginx/error.log;

    gzip on;
    gzip_vary on;           # ← Enable (see §19)
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript
               text/xml application/xml text/javascript;

    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
```

### 5.2 PHP 8.3 FPM

```bash
apt install -y php8.3-fpm php8.3-cli php8.3-common php8.3-opcache php8.3-readline
systemctl enable php8.3-fpm
```

**`/etc/php/8.3/fpm/php.ini` key settings:**

```ini
expose_php = Off
max_execution_time = 30
memory_limit = 128M
post_max_size = 8M
upload_max_filesize = 2M

[opcache]
opcache.enable = 1
opcache.memory_consumption = 128
opcache.max_accelerated_files = 10000
opcache.revalidate_freq = 2          ; ← Add (see §19)
opcache.fast_shutdown = 1            ; ← Add (see §19)
```

### 5.3 No MySQL/MariaDB

This server does **not** use MySQL or MariaDB. The admin backend uses SQLite (`/var/www/iscs1800-admin/backend/iscs1800.db`). Do not install a database server.

### 5.4 Python 3.12

Comes with Ubuntu 24.04. Also install `python3-venv`, `python3-openpyxl`:

```bash
apt install -y python3.12 python3.12-venv python3-openpyxl
```

`python3-openpyxl` must be available system-wide because `iscs1800-bulk-add.real` calls it from a root bash heredoc, outside the app venv.

---

## 6. TLS / Let's Encrypt

### 6.1 Certbot in dedicated venv with Hostinger DNS plugin

```bash
apt install -y python3.12-venv
python3 -m venv /opt/certbot
/opt/certbot/bin/pip install --upgrade pip
/opt/certbot/bin/pip install certbot certbot-nginx certbot-dns-hostinger
ln -sf /opt/certbot/bin/certbot /usr/local/bin/certbot
```

**Version used:** certbot 5.2.2 with `certbot-dns-hostinger`

### 6.2 Hostinger API credentials

Create `/etc/letsencrypt/hostinger.ini` (mode `0600`, owner `root:root`):

```ini
dns_hostinger_api_token = <HOSTINGER_API_TOKEN>
```

> ⚠️ The current token is stored in the file — retrieve it from the existing server or Hostinger dashboard before decommissioning. Treat as a secret.

### 6.3 Obtain wildcard certificate

```bash
iscs1800-enable-https-wildcard --email <admin@example.com> --propagation-seconds 180
```

This produces `/etc/letsencrypt/live/wildcard.cybearlab.cloud/{fullchain,privkey}.pem` used by all student and admin vhosts.

### 6.4 Auto-renewal

Certbot installs a systemd timer (`certbot.timer`) automatically. Verify:

```bash
systemctl status certbot.timer
```

The wildcard cert expires 2026-06-28 (60 days from audit date). The timer fires twice daily and will renew it.

---

## 7. Student Account Architecture

### 7.1 Groups

| Group | GID | Purpose |
|-------|-----|---------|
| `iscs1800-students` | 1003 | Primary group for all student OS accounts |
| `sftpstudents` | 987 | SSH Match block target — enables SFTP chroot |
| `iscs1800-students-<TERM>` | dynamic | Per-term membership tracking (e.g. `iscs1800-students-2026sp`) |
| `iscs1800_admins` | 988 | Instructor/admin shell access |

```bash
groupadd --gid 987 sftpstudents
groupadd --gid 988 iscs1800_admins
groupadd --gid 1003 iscs1800-students
```

### 7.2 Per-student account layout

```
/home/<username>/              root:root  0755  (SFTP chroot — must be owned root)
/home/<username>/public_html/  <user>:iscs1800-students  0755  (student-writable webroot)
```

Students log in via SFTP only (`/usr/sbin/nologin` shell). Their SFTP session is jailed to `/home/<username>` and drops them directly into `/public_html`.

### 7.3 Username convention

- Derived from student email local-part (e.g., `jsmith@school.edu` → `jsmith`)
- Regex: `^[a-z][a-z0-9_-]{2,15}$`
- Duplicates get a numeric suffix: `smithj`, `smithj2`, etc.

### 7.4 Password convention

- Default: last 6 digits of student ID number (zero-padded)
- Instructors can override with `--password-mode random` for bulk add

### 7.5 Leftover legacy paths

Two legacy accounts (`testuser1`, `parkerz`) have home dirs under `/srv/students/2026SP/` from an earlier design. On rebuild, all students should use `/home/<username>/`. Do not recreate the `/srv/students/` layout.

---

## 8. SSH and SFTP Configuration

### 8.1 Base `/etc/ssh/sshd_config`

The Ubuntu defaults are largely kept. Only the `PasswordAuthentication` default matters — it is overridden by the drop-in.

### 8.2 Drop-in: `/etc/ssh/sshd_config.d/99-iscs1800.conf`

```sshd_config
# ISCS1800 SSH policy
# Students in group "sftpstudents" are jailed via ChrootDirectory.

PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
PermitRootLogin prohibit-password
X11Forwarding no
AllowTcpForwarding yes

# NAT-classroom friendliness: reduce intermittent drops during mass logins
MaxStartups 100:30:200

# Staff/admins (not jailed)
Match Group iscs1800_admins
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    PubkeyAuthentication yes
    X11Forwarding no
    AllowTcpForwarding no

# Students: SFTP only + chroot jail
Match Group sftpstudents
    PasswordAuthentication yes
    KbdInteractiveAuthentication yes
    PubkeyAuthentication no
    X11Forwarding no
    AllowTcpForwarding no
    ForceCommand internal-sftp -d /public_html
    ChrootDirectory /home/%u
```

### 8.3 Key behaviours

- Root login: key-only (`prohibit-password`)
- Students: password auth ONLY (no keys), SFTP-only, chroot to `/home/<username>`
- `ForceCommand internal-sftp -d /public_html` drops them straight into their webroot on connect
- `MaxStartups 100:30:200` handles the classroom scenario where 30+ students connect within seconds of each other
- The `Subsystem sftp /usr/lib/openssh/sftp-server` line in the main config is superseded by `internal-sftp` in the Match block

### 8.4 SFTP client guidance for students

Any SFTP client (FileZilla, WinSCP, Cyberduck) works. Settings:
- Host: `<username>.cybearlab.cloud` or server IP
- Port: 22
- Protocol: SFTP
- Username: their assigned username
- Password: their assigned password (last 6 digits of student ID by default)

---

## 9. Nginx Virtual Hosts

### 9.1 Admin portal — `/etc/nginx/sites-available/iscs1800-admin.conf`

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name admin.cybearlab.cloud;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name admin.cybearlab.cloud;

    ssl_certificate     /etc/letsencrypt/live/wildcard.cybearlab.cloud/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wildcard.cybearlab.cloud/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;  # Enable on rebuild

    access_log /var/log/nginx/iscs1800-admin.access.log;
    error_log  /var/log/nginx/iscs1800-admin.error.log;

    root /var/www/iscs1800-admin/public;
    index index.php index.html;

    auth_basic "ISCS1800 Admin Portal";
    auth_basic_user_file /etc/nginx/.htpasswd_iscs1800_admin;

    location ~ /\.(?!well-known) { deny all; }

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location = /api { return 307 /api/; }

    location /api/ {
        auth_basic off;
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Authorization $http_authorization;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php8.3-fpm.sock;
    }
}
```

Set up htpasswd:
```bash
apt install -y apache2-utils
htpasswd -c /etc/nginx/.htpasswd_iscs1800_admin iscs1800admin
chmod 640 /etc/nginx/.htpasswd_iscs1800_admin
chown root:www-data /etc/nginx/.htpasswd_iscs1800_admin
```

### 9.2 Student wildcard catch-all — `/etc/nginx/sites-available/iscs1800-students.conf`

HTTP baseline for any student subdomain not yet upgraded to HTTPS:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name "~^(?<u>[a-z0-9][a-z0-9-]{0,31})\.cybearlab\.cloud$";
    root /srv/students/2026SP/$u/public_html;  # legacy — see §7.5
    index index.html index.htm;
    autoindex off;
    server_tokens off;
    location / { try_files $uri $uri/ =404; }
}
```

> **Rebuild note:** This catch-all can be removed once all students have individual HTTPS vhosts. The per-student HTTPS vhosts (§9.3) are preferred.

### 9.3 Per-student HTTPS vhost template

Generated by `iscs1800-add-student` / `iscs1800-enable-https-students`. Stored at `/etc/nginx/sites-available/<username>.cybearlab.cloud`.

```nginx
# Managed by ISCS1800 scripts. Do not edit manually.
server {
    listen 80;
    listen [::]:80;
    server_name <username>.cybearlab.cloud;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name <username>.cybearlab.cloud;

    ssl_certificate     /etc/letsencrypt/live/wildcard.cybearlab.cloud/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wildcard.cybearlab.cloud/privkey.pem;

    root /home/<username>/public_html;
    index index.html index.htm index.php;

    location / { try_files $uri $uri/ =404; }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_pass unix:/run/php/iscs1800-<username>.sock;
    }

    location ~ /\. { deny all; }
}
```

---

## 10. PHP-FPM Pools

### 10.1 Default www pool

Keep `/etc/php/8.3/fpm/pool.d/www.conf` at defaults (used only by the admin PHP proxy). Ensure:
- `pm = dynamic`
- `pm.max_children = 5`
- `listen = /run/php/php8.3-fpm.sock`

### 10.2 Per-student pool template

Generated by `iscs1800-php-pool-create <username>`. Stored at `/etc/php/8.3/fpm/pool.d/iscs1800-<username>.conf`.

```ini
; Managed by ISCS1800 scripts. Do not edit manually.
[iscs1800-<username>]

user = <username>
group = iscs1800-students

listen = /run/php/iscs1800-<username>.sock
listen.owner = www-data
listen.group = www-data
listen.mode = 0660

pm = ondemand
pm.max_children = 6
pm.process_idle_timeout = 20s
pm.max_requests = 200

catch_workers_output = yes
clear_env = yes

php_admin_value[open_basedir] = /home/<username>/public_html:/tmp
php_admin_value[upload_tmp_dir] = /tmp
php_admin_value[session.save_path] = /tmp
php_admin_value[disable_functions] = exec,passthru,shell_exec,system,proc_open,popen,pcntl_exec
php_admin_value[memory_limit] = 128M
php_admin_value[post_max_size] = 16M
php_admin_value[upload_max_filesize] = 16M
php_admin_value[max_execution_time] = 20
php_admin_value[max_input_time] = 30
```

**Key security design:** Each student's PHP process runs as **their own OS user**, not `www-data`. `open_basedir` restricts file access to their webroot and `/tmp`. Shell exec functions are disabled.

### 10.3 FPM process count guidance

With 12+ students each having an `ondemand` pool (`pm.max_children = 6`), the theoretical peak is 72+ PHP workers. With 8 GB RAM and 128 MB per worker, this is ~9 GB peak — tight. On rebuild, lower `pm.max_children` to `3` per student pool, or add swap (see §3.3).

---

## 11. Admin Portal — Frontend

### 11.1 Location

`/var/www/iscs1800-admin/public/` — served by Nginx as the document root for `admin.cybearlab.cloud`.

### 11.2 PHP proxy file

`/var/www/iscs1800-admin/public/api-proxy.php` — lightweight reverse proxy for legacy compatibility.

### 11.3 SPA

Single-page application in `/var/www/iscs1800-admin/public/` (`index.php`, `app.js`, `styles.css`).

### 11.4 Clone from git

```bash
cd /var/www
git clone https://github.com/Elzorno/cybearlab-Clound-Control-Center.git iscs1800-admin
chown -R root:www-data /var/www/iscs1800-admin
chmod -R 750 /var/www/iscs1800-admin
chmod -R 755 /var/www/iscs1800-admin/public
```

---

## 12. Admin Portal — FastAPI Backend

### 12.1 Python venv setup

```bash
cd /var/www/iscs1800-admin/backend
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

### 12.2 Key Python dependencies (requirements.txt)

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.117.1 | API framework |
| uvicorn[standard] | 0.37.0 | ASGI server |
| pydantic | 2.11.9 | Validation/schemas |
| SQLAlchemy | 2.0.43 | ORM (SQLite in production) |
| httpx | 0.28.1 | HTTP client for web grader |
| beautifulsoup4 | 4.14.2 | HTML parsing for grader |
| alembic | 1.16.5 | DB migrations |
| celery | 5.5.3 | Task queue (installed, not currently active — see §19) |
| redis | 6.4.0 | Celery broker (installed, not currently active — see §19) |
| psycopg[binary] | 3.2.4 | PostgreSQL driver (unused — SQLite only for now) |
| python-multipart | 0.0.20 | File upload support |

### 12.3 Environment file `/var/www/iscs1800-admin/backend/.env`

```env
EXECUTION_MODE=live
# DATABASE_URL defaults to sqlite:///./iscs1800.db
# Set other vars here if needed (see app/config.py)
```

Full config options from `app/config.py`:

| Variable | Default | Notes |
|----------|---------|-------|
| `DATABASE_URL` | `sqlite:///./iscs1800.db` | Switch to PostgreSQL for production |
| `TOKEN_TTL_SECONDS` | `28800` | 8 hours |
| `EXECUTION_MODE` | `mock` | Set `live` to run real scripts |
| `BOOTSTRAP_ADMIN_USERNAME` | `admin` | First-run admin account |
| `BOOTSTRAP_ADMIN_PASSWORD` | `change-me-now` | **Change immediately** |
| `GRADER_MAX_PAGES` | `30` | Max pages crawled per grading run |
| `GRADER_VALIDATOR_ENDPOINT` | W3C validator URL | For HTML validation checks |

### 12.4 Database initialisation

The app auto-initialises the SQLite database and seeds default assignments on first start. To manually seed:

```bash
cd /var/www/iscs1800-admin/backend
.venv/bin/python -c "from app.db import init_db; init_db()"
```

### 12.5 Active assignment

After seeding, activate the ISCS 1800 Final Project rubric:

```bash
.venv/bin/python - <<'PY'
from app.db import SessionLocal
from app.models import Assignment
from app.services.rubric_templates import bootstrap_default_assignments
s = SessionLocal()
bootstrap_default_assignments(s)
s.query(Assignment).update({Assignment.is_active: False}, synchronize_session=False)
s.query(Assignment).filter(Assignment.name == 'ISCS 1800 Final Project').update({Assignment.is_active: True}, synchronize_session=False)
s.commit(); s.close()
PY
```

---

## 13. Automation Scripts

All scripts live in `/usr/local/sbin/` and are owned `root:root`. Install by copying from the repo or recreating:

```bash
cp /var/www/iscs1800-admin/scripts/* /usr/local/sbin/   # if bundled in repo
chmod +x /usr/local/sbin/iscs1800-*
```

### Script inventory

| Script | Purpose | Called by |
|--------|---------|-----------|
| `iscs1800-add-student` | Creates OS user, SFTP jail, PHP pool, Nginx vhost | API backend, bulk-add |
| `iscs1800-bulk-add.real` | Processes Excel roster (.xlsx), calls add-student | API backend |
| `iscs1800-bulk-add` | Thin wrapper/stub around bulk-add.real | API backend |
| `iscs1800-disable-student` | Locks password, removes nginx sites-enabled symlink | API backend |
| `iscs1800-reset-password` | Resets student password, updates term group | API backend |
| `iscs1800-fix-perms` | Resets chroot layout permissions | API backend, manual |
| `iscs1800-enable-https-students` | Writes/updates HTTPS vhosts for one or all students | API backend |
| `iscs1800-enable-https-wildcard` | Obtains/renews wildcard cert via Hostinger DNS | Manual / certbot hook |
| `iscs1800-enable-https-admin` | Sets up admin vhost (if needed separately) | Manual |
| `iscs1800-php-pool-create` | Creates/updates per-student PHP-FPM pool | add-student, enable-https |
| `iscs1800-fix-perms` | Fixes chroot ownership/permissions | API backend, manual |
| `iscs1800-verify-report` | Validates a bulk-add CSV report against live system | Manual |
| `iscs1800-state-snapshot` | Dumps current student provisioning state | Manual/debugging |
| `iscs1800-admin-portal-setpass` | Sets admin portal htpasswd | Setup |

### Script dependencies

- `bash` 5.x, `awk`, `sed`, `grep`, `find`, `install`, `stat`
- `useradd`, `groupadd`, `usermod`, `chpasswd`, `passwd`
- `nginx`, `php8.3-fpm`, `systemctl`
- `python3`, `openpyxl` (system-level, not venv)
- `certbot` at `/opt/certbot/bin/certbot`
- `sshpass` (optional — only for `iscs1800-verify-report --auth`)

---

## 14. Systemd Services

### 14.1 Backend service: `/etc/systemd/system/iscs1800-admin-backend.service`

```ini
[Unit]
Description=ISCS1800 Admin Backend (FastAPI)
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/var/www/iscs1800-admin/backend
Environment=DATABASE_URL=sqlite:///./iscs1800.db
ExecStart=/var/www/iscs1800-admin/backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

> **Rebuild improvement (see §19):** Change `User=root` to a dedicated `iscs1800` service user. Scripts that need root should be called via `sudo` with specific allow rules.

```bash
systemctl daemon-reload
systemctl enable --now iscs1800-admin-backend
```

### 14.2 All services that must be enabled and running

```bash
systemctl enable --now nginx
systemctl enable --now php8.3-fpm
systemctl enable --now ssh
systemctl enable --now fail2ban
systemctl enable --now iscs1800-admin-backend
systemctl enable --now certbot.timer
```

### 14.3 Services NOT needed (do not install)

- MySQL / MariaDB
- Redis (present in requirements.txt but Celery/Redis unused — see §19)
- Celery worker
- Node.js / npm

---

## 15. Fail2ban

### 15.1 `/etc/fail2ban/jail.local`

```ini
[DEFAULT]
banaction = nftables
banaction_allports = nftables[type=allports]
backend = systemd

[sshd]
enabled = true
```

This configuration bans IPs with repeated SSH failures using nftables (appropriate for Ubuntu 24.04 which uses nftables as the default firewall backend).

---

## 16. File Layout Reference

```
/
├── etc/
│   ├── nginx/
│   │   ├── nginx.conf                           # Main Nginx config
│   │   ├── sites-available/
│   │   │   ├── iscs1800-admin.conf              # Admin portal vhost
│   │   │   ├── iscs1800-students.conf           # Wildcard HTTP catch-all
│   │   │   └── <username>.cybearlab.cloud       # Per-student HTTPS vhosts
│   │   ├── sites-enabled/ -> (symlinks)
│   │   └── .htpasswd_iscs1800_admin             # Admin portal basic auth
│   ├── php/8.3/fpm/pool.d/
│   │   ├── www.conf                             # Default FPM pool
│   │   └── iscs1800-<username>.conf             # Per-student PHP pools
│   ├── ssh/
│   │   ├── sshd_config                          # Base SSH config
│   │   └── sshd_config.d/
│   │       └── 99-iscs1800.conf                 # ISCS1800 SSH policy drop-in
│   ├── letsencrypt/
│   │   ├── hostinger.ini                        # Hostinger API credentials (0600)
│   │   └── live/wildcard.cybearlab.cloud/       # Wildcard cert
│   └── systemd/system/
│       └── iscs1800-admin-backend.service
│
├── home/
│   └── <username>/                              # root:root 0755 (SFTP chroot)
│       └── public_html/                         # <user>:iscs1800-students 0755
│
├── usr/local/sbin/
│   └── iscs1800-*                               # All automation scripts
│
├── opt/certbot/                                 # Certbot venv
│
└── var/www/iscs1800-admin/                      # Application root
    ├── public/                                  # Nginx document root
    │   ├── index.php
    │   ├── app.js
    │   ├── styles.css
    │   └── api-proxy.php
    └── backend/
        ├── .env                                 # EXECUTION_MODE=live
        ├── .venv/                               # Python virtualenv
        ├── requirements.txt
        ├── iscs1800.db                          # SQLite database
        └── app/
            ├── main.py
            ├── models.py
            ├── schemas.py
            ├── config.py
            ├── db.py
            ├── routers/
            └── services/
```

---

## 17. Credentials and Secrets

**Retrieve all of the following from the existing server before decommissioning:**

| Secret | Location | Notes |
|--------|----------|-------|
| Hostinger DNS API token | `/etc/letsencrypt/hostinger.ini` | Required for wildcard cert renewal |
| Admin portal htpasswd | `/etc/nginx/.htpasswd_iscs1800_admin` | bcrypt hash; copy file or reset on rebuild |
| Backend admin password | SQLite DB or `BOOTSTRAP_ADMIN_PASSWORD` env var | Reset via API after first start |
| Root SSH authorized keys | `/root/.ssh/authorized_keys` | Copy to new server |
| Admin user `czornes` SSH keys | `/home/czornes/.ssh/authorized_keys` | Copy if needed |

---

## 18. Post-Rebuild Verification Checklist

```
[ ] Server is reachable via SSH (key auth only)
[ ] UFW rules active: 22, 80, 443 only
[ ] nginx -t passes with no errors
[ ] https://admin.cybearlab.cloud loads and requires auth
[ ] FastAPI health endpoint: curl http://127.0.0.1:8000/health → 200
[ ] certbot.timer is active: systemctl status certbot.timer
[ ] Wildcard cert valid: certbot certificates
[ ] Add one test student: iscs1800-add-student teststu TempPass123
[ ] Test student SFTP login works (FileZilla / sftp cli)
[ ] Test student site loads: https://teststu.cybearlab.cloud
[ ] Test student PHP works: upload a <?php phpinfo(); ?> page
[ ] PHP pool isolation: student cannot read /etc/passwd (open_basedir block)
[ ] Run iscs1800-verify-report on a test CSV
[ ] Web grader grades a live student site via admin portal
[ ] fail2ban is active: fail2ban-client status sshd
[ ] Swap is present: swapon --show
[ ] /etc/hosts has: 140.82.112.3 github.com
[ ] git push to GitHub succeeds
```

---

## 19. Optimizations and Recommended Changes

The following issues were identified during the audit. These are **not currently broken** but should be fixed on rebuild.

### 19.1 🔴 Security — Service running as root

**Current:** `iscs1800-admin-backend.service` runs uvicorn as `User=root`.  
**Risk:** If FastAPI has a vulnerability, an attacker has full root access immediately.  
**Fix:** Create a dedicated `iscs1800` user (no shell, no home). Scripts that need root (the sbin scripts) should be invoked via a tight `sudoers` entry.

```bash
useradd -r -s /usr/sbin/nologin iscs1800
# In /etc/sudoers.d/iscs1800:
iscs1800 ALL=(root) NOPASSWD: /usr/local/sbin/iscs1800-*
# In service file: User=iscs1800
```

### 19.2 🔴 Security — TLS 1.0/1.1 enabled in Nginx main config

**Current:** `ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;` in `nginx.conf`.  
**Fix:** Remove TLSv1 and TLSv1.1. Keep only `TLSv1.2 TLSv1.3`. (Student vhosts already inherit this.)

### 19.3 🔴 Security — HSTS not enabled

**Current:** HSTS header is commented out in the admin vhost.  
**Fix:** Uncomment `add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;` once the wildcard cert is confirmed stable. Add to student vhosts too.

### 19.4 🟡 Security — Hostinger API token exposed

**Current:** The Hostinger DNS API token is readable in plaintext at `/etc/letsencrypt/hostinger.ini` (0600, but root sees it trivially). The current token is committed in this document's audit output.  
**Fix:** Rotate the Hostinger API token immediately after rebuild.

### 19.5 🟡 Reliability — No swap

**Current:** Server has 0 swap. With 12+ `ondemand` PHP pools potentially spinning up simultaneously (e.g., during a class session), an OOM kill could take down PHP-FPM or Nginx.  
**Fix:** Add 2 GB swapfile (see §3.3). Also reduce student pool `pm.max_children` from 6 to 3.

### 19.6 🟡 Reliability — SQLite for backend database

**Current:** SQLite at `./iscs1800.db` with WAL mode (SQLAlchemy default).  
**Risk:** Concurrent API writes during bulk operations can hit SQLite locking limits.  
**Fix:** Switch to PostgreSQL if concurrent write load increases. The backend already has `psycopg[binary]` installed.

### 19.7 🟡 Unused Celery/Redis dependencies

**Current:** `celery` and `redis` are in `requirements.txt` and installed in the venv, but neither Redis nor a Celery worker is running. This adds ~30 MB to the venv and implies async task support that isn't wired up.  
**Fix:** Either remove them from requirements.txt (if background tasks aren't needed), or complete the implementation by installing Redis and creating a celery worker service.

### 19.8 🟡 Nginx performance — `multi_accept` and gzip types

**Current:** `multi_accept` is commented out; gzip types, `gzip_vary`, and `tcp_nodelay` are not configured.  
**Fix:** Enable `multi_accept on;`, `tcp_nodelay on;`, `gzip_vary on;`, and set full gzip type list (see §5.1).

### 19.9 🟡 OPcache tuning

**Current:** OPcache is enabled with defaults (128 MB memory, 10,000 files), but `opcache.revalidate_freq` and `opcache.fast_shutdown` are not set.  
**Fix:** Add `opcache.revalidate_freq = 2` and `opcache.fast_shutdown = 1` to reduce stat() calls and speed up PHP-FPM restarts.

### 19.10 🟢 Admin portal — Remove `.bak` files from sites-available

**Current:** Two backup sshd config files (`99-iscs1800.conf.bak.*`) and a backup nginx conf exist. These create confusion but are harmless.  
**Fix:** Do not recreate these on rebuild; they were intermediate versions from the initial setup.

### 19.11 🟢 Legacy `/srv/students/` path

**Current:** The wildcard catch-all vhost still points to `/srv/students/2026SP/$u/public_html`, a legacy path that doesn't exist. Two old accounts (`testuser1`, `parkerz`) still reference it.  
**Fix:** On rebuild, remove the wildcard catch-all vhost entirely. All students should have individual HTTPS vhosts using `/home/<username>/public_html`.

### 19.12 🟢 `server_tokens off` not set

**Current:** Nginx still exposes its version in error pages and headers.  
**Fix:** Uncomment `server_tokens off;` in `nginx.conf`.

### 19.13 🟢 Log rotation for student-related Nginx logs

**Current:** No custom logrotate rules for the per-student or admin vhost logs.  
**Fix:** Add `/etc/logrotate.d/iscs1800` with daily rotation, 14-day retention, compress, and nginx reload.
