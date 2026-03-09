#!/bin/bash
# ============================================================
# ElGringo VM Deploy Script (runs ON the VM via gcloud ssh)
# Sets up venv, systemd services, kills old AITeamPlatform
# ============================================================
set -e

DIR=/opt/elgringo
OLD_DIR=/opt/AITeamPlatform

echo "============================================================"
echo "  ElGringo VM Deploy"
echo "============================================================"

# ----------------------------------------------------------
# 1. Create service user
# ----------------------------------------------------------
echo "=== Creating service user if needed ==="
id elgringo &>/dev/null || useradd --system --shell /usr/sbin/nologin --home-dir $DIR elgringo

# ----------------------------------------------------------
# 2. Kill old AITeamPlatform processes
# ----------------------------------------------------------
echo "=== Stopping old AITeamPlatform processes ==="
# Kill processes running from /opt/AITeamPlatform
pkill -f "/opt/AITeamPlatform" 2>/dev/null || true
sleep 2
# Force kill if still alive
pkill -9 -f "/opt/AITeamPlatform" 2>/dev/null || true

# ----------------------------------------------------------
# 3. Extract new code
# ----------------------------------------------------------
echo "=== Extracting ElGringo ==="
mkdir -p $DIR/logs
tar -xzf /tmp/elgringo.tar.gz -C $DIR
rm -f /tmp/elgringo.tar.gz

# ----------------------------------------------------------
# 3b. Set up password protection (nginx basic auth)
# ----------------------------------------------------------
echo "=== Setting up password protection ==="
apt-get install -y apache2-utils 2>/dev/null || true
htpasswd -cb /etc/nginx/.htpasswd fred '@Gringo420'
chmod 640 /etc/nginx/.htpasswd
chown root:www-data /etc/nginx/.htpasswd
echo "  htpasswd file created at /etc/nginx/.htpasswd"

# ----------------------------------------------------------
# 4. Migrate .env from old install (if exists and new one doesn't)
# ----------------------------------------------------------
if [ ! -f "$DIR/.env" ] && [ -f "$OLD_DIR/.env" ]; then
    echo "=== Migrating .env from old AITeamPlatform ==="
    cp "$OLD_DIR/.env" "$DIR/.env"
fi

# Ensure PROJECTS_DIR is set in .env
if [ -f "$DIR/.env" ] && ! grep -q "^PROJECTS_DIR=" "$DIR/.env"; then
    echo "PROJECTS_DIR=/opt/elgringo/projects" >> "$DIR/.env"
fi

# ----------------------------------------------------------
# 5. Set up Python venv
# ----------------------------------------------------------
echo "=== Setting up Python venv ==="
if [ ! -d "$DIR/venv" ]; then
    python3.11 -m venv "$DIR/venv"
fi
$DIR/venv/bin/pip install -q --upgrade pip setuptools wheel
$DIR/venv/bin/pip install -q -r $DIR/requirements.txt
# Install extras needed for all services (pr-bot, gradio UIs, gunicorn)
$DIR/venv/bin/pip install -q \
    'pydantic-settings>=2.0.0' \
    'gradio>=4.0.0' \
    'PyJWT>=2.8.0' \
    'cryptography>=42.0.0' \
    'httpx>=0.27.0' \
    'gunicorn>=21.2.0' \
    'streamlit>=1.30.0'
# Install the package itself in editable mode
cd $DIR && $DIR/venv/bin/pip install -q -e .

# ----------------------------------------------------------
# 5b. Build Command Center React frontend
# ----------------------------------------------------------
FRONTEND_DIR="$DIR/products/command_center/frontend"
if [ -f "$FRONTEND_DIR/package.json" ]; then
    echo "=== Building Command Center frontend ==="
    if ! command -v node &>/dev/null; then
        echo "  Node.js not found, installing..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        apt-get install -y nodejs
    fi
    rm -rf "$FRONTEND_DIR/node_modules"
    cd "$FRONTEND_DIR" && npm ci && npx vite build --base=/command/
    chown -R elgringo:elgringo "$FRONTEND_DIR/dist"
    echo "  Frontend built to $FRONTEND_DIR/dist/"
fi

# ----------------------------------------------------------
# 5c. Build Fred Assistant React frontend
# ----------------------------------------------------------
ASSISTANT_DIR="$DIR/products/fred_assistant/frontend"
if [ -f "$ASSISTANT_DIR/package.json" ]; then
    echo "=== Building Fred Assistant frontend ==="
    if ! command -v node &>/dev/null; then
        echo "  Node.js not found, installing..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        apt-get install -y nodejs
    fi
    rm -rf "$ASSISTANT_DIR/node_modules"
    cd "$ASSISTANT_DIR" && npm ci && VITE_API_URL=/assistant/api npx vite build --base=/assistant/
    chown -R elgringo:elgringo "$ASSISTANT_DIR/dist"
    echo "  Fred Assistant frontend built to $ASSISTANT_DIR/dist/"
fi

# ----------------------------------------------------------
# 6. Set ownership + project clone directory
# ----------------------------------------------------------
echo "=== Setting ownership ==="
chown -R elgringo:elgringo $DIR
mkdir -p /opt/elgringo/projects
chown elgringo:elgringo /opt/elgringo/projects

# ----------------------------------------------------------
# 7. Create systemd services
# ----------------------------------------------------------
echo "=== Creating systemd services ==="

# --- Remove old elgringo-api service (replaced by elgringo-fred-api on 8080) ---
systemctl stop elgringo-api 2>/dev/null || true
systemctl disable elgringo-api 2>/dev/null || true
rm -f /etc/systemd/system/elgringo-api.service

# --- elgringo-pr-bot: PR Review Bot (port 8001) ---
cat > /etc/systemd/system/elgringo-pr-bot.service << 'EOF'
[Unit]
Description=ElGringo PR Review Bot (FastAPI)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=elgringo
Group=elgringo
WorkingDirectory=/opt/elgringo
Environment=PATH=/opt/elgringo/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/elgringo
Environment=PORT=8001
EnvironmentFile=-/opt/elgringo/.env
ExecStart=/opt/elgringo/venv/bin/uvicorn products.pr_review_bot.server:app --host 0.0.0.0 --port 8001 --log-level info
Restart=always
RestartSec=5
StandardOutput=append:/opt/elgringo/logs/pr-bot.log
StandardError=append:/opt/elgringo/logs/pr-bot-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- elgringo-chat: Chat UI (port 7860) ---
cat > /etc/systemd/system/elgringo-chat.service << 'EOF'
[Unit]
Description=ElGringo Chat UI (Gradio)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=elgringo
Group=elgringo
WorkingDirectory=/opt/elgringo
Environment=PATH=/opt/elgringo/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/elgringo
Environment=PORT=7860
EnvironmentFile=-/opt/elgringo/.env
ExecStart=/opt/elgringo/venv/bin/python -m elgringo.ui.chat_ui
Restart=always
RestartSec=5
StandardOutput=append:/opt/elgringo/logs/chat.log
StandardError=append:/opt/elgringo/logs/chat-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- elgringo-studio: Studio IDE (port 7861) ---
cat > /etc/systemd/system/elgringo-studio.service << 'EOF'
[Unit]
Description=ElGringo Studio IDE (Gradio)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=elgringo
Group=elgringo
WorkingDirectory=/opt/elgringo
Environment=PATH=/opt/elgringo/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/elgringo
Environment=PORT=7861
EnvironmentFile=-/opt/elgringo/.env
ExecStart=/opt/elgringo/venv/bin/python -m elgringo.ui.studio_ui
Restart=always
RestartSec=5
StandardOutput=append:/opt/elgringo/logs/studio.log
StandardError=append:/opt/elgringo/logs/studio-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- elgringo-fred-api: Fred API (port 8080) ---
cat > /etc/systemd/system/elgringo-fred-api.service << 'EOF'
[Unit]
Description=ElGringo Fred API (FastAPI)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=elgringo
Group=elgringo
WorkingDirectory=/opt/elgringo
Environment=PATH=/opt/elgringo/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/elgringo
Environment=PORT=8080
EnvironmentFile=-/opt/elgringo/.env
ExecStart=/opt/elgringo/venv/bin/uvicorn products.fred_api.server:app --host 0.0.0.0 --port 8080 --log-level info
Restart=always
RestartSec=5
StandardOutput=append:/opt/elgringo/logs/fred-api.log
StandardError=append:/opt/elgringo/logs/fred-api-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- elgringo-code-audit: Code Audit (port 8081) ---
cat > /etc/systemd/system/elgringo-code-audit.service << 'EOF'
[Unit]
Description=ElGringo Code Audit Service (FastAPI)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=elgringo
Group=elgringo
WorkingDirectory=/opt/elgringo
Environment=PATH=/opt/elgringo/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/elgringo
Environment=PORT=8081
EnvironmentFile=-/opt/elgringo/.env
ExecStart=/opt/elgringo/venv/bin/uvicorn products.code_audit.server:app --host 0.0.0.0 --port 8081 --log-level info
Restart=always
RestartSec=5
StandardOutput=append:/opt/elgringo/logs/code-audit.log
StandardError=append:/opt/elgringo/logs/code-audit-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- elgringo-test-gen: Test Generator (port 8082) ---
cat > /etc/systemd/system/elgringo-test-gen.service << 'EOF'
[Unit]
Description=ElGringo Test Generator (FastAPI)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=elgringo
Group=elgringo
WorkingDirectory=/opt/elgringo
Environment=PATH=/opt/elgringo/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/elgringo
Environment=PORT=8082
EnvironmentFile=-/opt/elgringo/.env
ExecStart=/opt/elgringo/venv/bin/uvicorn products.test_generator.server:app --host 0.0.0.0 --port 8082 --log-level info
Restart=always
RestartSec=5
StandardOutput=append:/opt/elgringo/logs/test-gen.log
StandardError=append:/opt/elgringo/logs/test-gen-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- elgringo-doc-gen: Doc Generator (port 8083) ---
cat > /etc/systemd/system/elgringo-doc-gen.service << 'EOF'
[Unit]
Description=ElGringo Doc Generator (FastAPI)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=elgringo
Group=elgringo
WorkingDirectory=/opt/elgringo
Environment=PATH=/opt/elgringo/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/elgringo
Environment=PORT=8083
EnvironmentFile=-/opt/elgringo/.env
ExecStart=/opt/elgringo/venv/bin/uvicorn products.doc_generator.server:app --host 0.0.0.0 --port 8083 --log-level info
Restart=always
RestartSec=5
StandardOutput=append:/opt/elgringo/logs/doc-gen.log
StandardError=append:/opt/elgringo/logs/doc-gen-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- elgringo-assistant: Fred Assistant (port 7870) ---
cat > /etc/systemd/system/elgringo-assistant.service << 'EOF'
[Unit]
Description=ElGringo Fred Assistant (FastAPI)
After=network.target
Wants=network-online.target
StartLimitBurst=5
StartLimitIntervalSec=60

[Service]
Type=simple
User=elgringo
Group=elgringo
WorkingDirectory=/opt/elgringo
Environment=PATH=/opt/elgringo/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/elgringo
Environment=PORT=7870
EnvironmentFile=-/opt/elgringo/.env
ExecStart=/opt/elgringo/venv/bin/uvicorn products.fred_assistant.server:app --host 0.0.0.0 --port 7870 --log-level info
Restart=on-failure
RestartSec=5
MemoryMax=800M
StandardOutput=append:/opt/elgringo/logs/assistant.log
StandardError=append:/opt/elgringo/logs/assistant-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- elgringo-command-api: Command Center API (port 7862) ---
cat > /etc/systemd/system/elgringo-command-api.service << 'EOF'
[Unit]
Description=ElGringo Command Center API (FastAPI)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=elgringo
Group=elgringo
WorkingDirectory=/opt/elgringo
Environment=PATH=/opt/elgringo/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/elgringo
Environment=PORT=7862
EnvironmentFile=-/opt/elgringo/.env
ExecStart=/opt/elgringo/venv/bin/uvicorn products.command_center.server:app --host 127.0.0.1 --port 7862 --log-level info
Restart=always
RestartSec=5
StandardOutput=append:/opt/elgringo/logs/command-api.log
StandardError=append:/opt/elgringo/logs/command-api-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- Command Center UI: Static React app served by nginx ---
# No systemd service needed — nginx serves dist/ directly.
# Stop old Streamlit service if it exists.
systemctl stop elgringo-command-center 2>/dev/null || true
systemctl disable elgringo-command-center 2>/dev/null || true
rm -f /etc/systemd/system/elgringo-command-center.service

# Update nginx for Command Center (static files + API proxy with SSE)
NGINX_CMD_CONF=/etc/nginx/sites-available/elgringo-command-center
cat > "$NGINX_CMD_CONF" << 'NGINX_EOF'
# Command Center React app (static files)
location /command/ {
    alias /opt/elgringo/products/command_center/frontend/dist/;
    try_files $uri $uri/ /command/index.html;

    location = /command/index.html {
        alias /opt/elgringo/products/command_center/frontend/dist/index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
    location /command/assets/ {
        alias /opt/elgringo/products/command_center/frontend/dist/assets/;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }
}

# Command Center API proxy (with SSE support)
location /command/api/ {
    proxy_pass http://127.0.0.1:7862/;
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 300s;
}
NGINX_EOF
echo "  Nginx config written to $NGINX_CMD_CONF"
echo "  NOTE: Include this file in your main nginx server block if not already included."

# Update nginx for Fred Assistant (static files + API proxy)
NGINX_ASST_CONF=/etc/nginx/sites-available/elgringo-assistant
cat > "$NGINX_ASST_CONF" << 'NGINX_EOF'
# Fred Assistant React app (static files)
location /assistant/ {
    alias /opt/elgringo/products/fred_assistant/frontend/dist/;
    try_files $uri $uri/ /assistant/index.html;

    # Cache-bust index.html so new deploys are picked up immediately
    location = /assistant/index.html {
        alias /opt/elgringo/products/fred_assistant/frontend/dist/index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
    # Hashed assets can be cached forever
    location /assistant/assets/ {
        alias /opt/elgringo/products/fred_assistant/frontend/dist/assets/;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }
}

# Fred Assistant API proxy
location /assistant/api/ {
    proxy_pass http://127.0.0.1:7870/;
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 300s;
}
NGINX_EOF
echo "  Nginx Fred Assistant config written to $NGINX_ASST_CONF"

# Update nginx for Landing Page (auth + health + webhook handled in main config)
NGINX_LANDING_CONF=/etc/nginx/sites-available/elgringo-landing
cat > "$NGINX_LANDING_CONF" << 'NGINX_EOF'
# --- Landing page ---
location = / {
    root /opt/elgringo/products/landing;
    try_files /index.html =404;
}
location /landing/ {
    alias /opt/elgringo/products/landing/;
}
NGINX_EOF
echo "  Nginx landing config written to $NGINX_LANDING_CONF"

# Auto-include nginx snippets in main server block if not already there
NGINX_MAIN="/etc/nginx/sites-available/ai.chatterfix.com"
if [ -f "$NGINX_MAIN" ]; then
    # Remove old bare-JSON root location (replaced by landing page)
    # Matches: location = / { return 200 ...; } or similar single-line/multi-line blocks
    if grep -q 'location = / {' "$NGINX_MAIN"; then
        echo "  Removing old root location block from nginx main config..."
        sed -i '/location = \/ {/,/}/d' "$NGINX_MAIN"
    fi

    # Add auth_basic off to existing webhook location (if not already there)
    if grep -q 'location.*\/webhook' "$NGINX_MAIN" && ! grep -A1 'location.*\/webhook' "$NGINX_MAIN" | grep -q 'auth_basic off'; then
        sed -i '/location.*\/webhook.*{/a\    auth_basic off;' "$NGINX_MAIN"
        echo "  Added auth_basic off to existing webhook location"
    fi

    for SNIPPET in "$NGINX_LANDING_CONF" "$NGINX_CMD_CONF" "$NGINX_ASST_CONF"; do
        if ! grep -qF "include $SNIPPET" "$NGINX_MAIN"; then
            # Insert include before the last closing brace of the server block
            sed -i "/^}/i\\    include $SNIPPET;" "$NGINX_MAIN"
            echo "  Added include for $SNIPPET in nginx main config"
        fi
    done
    # Sync to sites-enabled (some setups use a copy, not a symlink)
    cp "$NGINX_MAIN" /etc/nginx/sites-enabled/ai.chatterfix.com
fi

# ----------------------------------------------------------
# 8. Ensure swap space (prevents OOM on 4GB VMs)
# ----------------------------------------------------------
if [ ! -f /swapfile ]; then
    echo "=== Creating 2GB swap file ==="
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "  Swap file created and enabled"
else
    echo "  Swap file already exists"
    swapon /swapfile 2>/dev/null || true
fi

# ----------------------------------------------------------
# 9. Reload and start services
# ----------------------------------------------------------
echo "=== Starting services ==="
systemctl daemon-reload
systemctl enable elgringo-pr-bot elgringo-chat elgringo-studio elgringo-fred-api elgringo-code-audit elgringo-test-gen elgringo-doc-gen elgringo-command-api elgringo-assistant
systemctl restart elgringo-pr-bot || true
systemctl restart elgringo-chat || true
systemctl restart elgringo-studio || true
systemctl restart elgringo-fred-api || true
systemctl restart elgringo-code-audit || true
systemctl restart elgringo-test-gen || true
systemctl restart elgringo-doc-gen || true
systemctl restart elgringo-command-api || true
systemctl restart elgringo-assistant || true
# Reload nginx for Command Center static files
nginx -t && systemctl reload nginx

# ----------------------------------------------------------
# 9. Verify
# ----------------------------------------------------------
echo ""
echo "=== Service Status ==="
systemctl is-active elgringo-pr-bot && echo "  elgringo-pr-bot:     RUNNING (port 8001)" || echo "  elgringo-pr-bot:     FAILED"
systemctl is-active elgringo-chat && echo "  elgringo-chat:       RUNNING (port 7860)" || echo "  elgringo-chat:       FAILED"
systemctl is-active elgringo-studio && echo "  elgringo-studio:     RUNNING (port 7861)" || echo "  elgringo-studio:     FAILED"
systemctl is-active elgringo-fred-api && echo "  elgringo-fred-api:   RUNNING (port 8080)" || echo "  elgringo-fred-api:   FAILED"
systemctl is-active elgringo-code-audit && echo "  elgringo-code-audit: RUNNING (port 8081)" || echo "  elgringo-code-audit: FAILED"
systemctl is-active elgringo-test-gen && echo "  elgringo-test-gen:   RUNNING (port 8082)" || echo "  elgringo-test-gen:   FAILED"
systemctl is-active elgringo-doc-gen && echo "  elgringo-doc-gen:    RUNNING (port 8083)" || echo "  elgringo-doc-gen:    FAILED"
systemctl is-active elgringo-command-api && echo "  elgringo-cmd-api:    RUNNING (port 7862)" || echo "  elgringo-cmd-api:    FAILED"
systemctl is-active elgringo-assistant && echo "  elgringo-assistant:  RUNNING (port 7870)" || echo "  elgringo-assistant:  FAILED"
[ -f /opt/elgringo/products/command_center/frontend/dist/index.html ] && echo "  command-center:    STATIC (nginx at /command/)" || echo "  command-center:    NOT BUILT"
[ -f /opt/elgringo/products/fred_assistant/frontend/dist/index.html ] && echo "  fred-assistant:    STATIC (nginx at /assistant/)" || echo "  fred-assistant:    NOT BUILT"
[ -f /opt/elgringo/products/landing/index.html ] && echo "  landing-page:      STATIC (nginx at /)" || echo "  landing-page:      MISSING"
[ -f /etc/nginx/.htpasswd ] && echo "  auth:              ENABLED (basic auth)" || echo "  auth:              NOT SET UP"

echo ""
echo "=== Deploy complete ==="
echo "Landing:    https://ai.chatterfix.com/ (user: fred)"
echo "Fred API:   http://localhost:8080/v1/health"
echo "PR Bot:     http://localhost:8001/health"
echo "Chat:       http://localhost:7860"
echo "Studio:     http://localhost:7861"
echo "Code Audit: http://localhost:8081/audit/health"
echo "Test Gen:   http://localhost:8082/tests/health"
echo "Doc Gen:    http://localhost:8083/docs/health"
echo "Command:    https://ai.chatterfix.com/command/"
echo "Assistant:  http://localhost:7870/health"
echo "Asst. UI:   https://ai.chatterfix.com/assistant/"
