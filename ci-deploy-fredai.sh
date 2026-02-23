#!/bin/bash
# ============================================================
# FredAI VM Deploy Script (runs ON the VM via gcloud ssh)
# Sets up venv, systemd services, kills old AITeamPlatform
# ============================================================
set -e

DIR=/opt/fredai
OLD_DIR=/opt/AITeamPlatform

echo "============================================================"
echo "  FredAI VM Deploy"
echo "============================================================"

# ----------------------------------------------------------
# 1. Create service user
# ----------------------------------------------------------
echo "=== Creating service user if needed ==="
id fredai &>/dev/null || useradd --system --shell /usr/sbin/nologin --home-dir $DIR fredai

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
echo "=== Extracting FredAI ==="
mkdir -p $DIR/logs
tar -xzf /tmp/fredai.tar.gz -C $DIR
rm -f /tmp/fredai.tar.gz

# ----------------------------------------------------------
# 4. Migrate .env from old install (if exists and new one doesn't)
# ----------------------------------------------------------
if [ ! -f "$DIR/.env" ] && [ -f "$OLD_DIR/.env" ]; then
    echo "=== Migrating .env from old AITeamPlatform ==="
    cp "$OLD_DIR/.env" "$DIR/.env"
fi

# Ensure PROJECTS_DIR is set in .env
if [ -f "$DIR/.env" ] && ! grep -q "^PROJECTS_DIR=" "$DIR/.env"; then
    echo "PROJECTS_DIR=/opt/fredai/projects" >> "$DIR/.env"
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
    chown -R fredai:fredai "$FRONTEND_DIR/dist"
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
    chown -R fredai:fredai "$ASSISTANT_DIR/dist"
    echo "  Fred Assistant frontend built to $ASSISTANT_DIR/dist/"
fi

# ----------------------------------------------------------
# 6. Set ownership + project clone directory
# ----------------------------------------------------------
echo "=== Setting ownership ==="
chown -R fredai:fredai $DIR
mkdir -p /opt/fredai/projects
chown fredai:fredai /opt/fredai/projects

# ----------------------------------------------------------
# 7. Create systemd services
# ----------------------------------------------------------
echo "=== Creating systemd services ==="

# --- fredai-api: Flask API server (port 5050) ---
cat > /etc/systemd/system/fredai-api.service << 'EOF'
[Unit]
Description=FredAI API Server (Flask)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=fredai
Group=fredai
WorkingDirectory=/opt/fredai
Environment=PATH=/opt/fredai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/fredai
EnvironmentFile=/opt/fredai/.env
ExecStart=/opt/fredai/venv/bin/python servers/api_server.py
Restart=always
RestartSec=5
StandardOutput=append:/opt/fredai/logs/api.log
StandardError=append:/opt/fredai/logs/api-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- fredai-pr-bot: PR Review Bot (port 8001) ---
cat > /etc/systemd/system/fredai-pr-bot.service << 'EOF'
[Unit]
Description=FredAI PR Review Bot (FastAPI)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=fredai
Group=fredai
WorkingDirectory=/opt/fredai
Environment=PATH=/opt/fredai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/fredai
Environment=PORT=8001
EnvironmentFile=/opt/fredai/.env
ExecStart=/opt/fredai/venv/bin/uvicorn products.pr_review_bot.server:app --host 0.0.0.0 --port 8001 --log-level info
Restart=always
RestartSec=5
StandardOutput=append:/opt/fredai/logs/pr-bot.log
StandardError=append:/opt/fredai/logs/pr-bot-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- fredai-chat: Chat UI (port 7860) ---
cat > /etc/systemd/system/fredai-chat.service << 'EOF'
[Unit]
Description=FredAI Chat UI (Gradio)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=fredai
Group=fredai
WorkingDirectory=/opt/fredai
Environment=PATH=/opt/fredai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/fredai
Environment=PORT=7860
EnvironmentFile=/opt/fredai/.env
ExecStart=/opt/fredai/venv/bin/python -m ai_dev_team.chat_ui
Restart=always
RestartSec=5
StandardOutput=append:/opt/fredai/logs/chat.log
StandardError=append:/opt/fredai/logs/chat-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- fredai-studio: Studio IDE (port 7861) ---
cat > /etc/systemd/system/fredai-studio.service << 'EOF'
[Unit]
Description=FredAI Studio IDE (Gradio)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=fredai
Group=fredai
WorkingDirectory=/opt/fredai
Environment=PATH=/opt/fredai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/fredai
Environment=PORT=7861
EnvironmentFile=/opt/fredai/.env
ExecStart=/opt/fredai/venv/bin/python -m ai_dev_team.studio_ui
Restart=always
RestartSec=5
StandardOutput=append:/opt/fredai/logs/studio.log
StandardError=append:/opt/fredai/logs/studio-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- fredai-fred-api: Fred API (port 8080) ---
cat > /etc/systemd/system/fredai-fred-api.service << 'EOF'
[Unit]
Description=FredAI Fred API (FastAPI)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=fredai
Group=fredai
WorkingDirectory=/opt/fredai
Environment=PATH=/opt/fredai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/fredai
Environment=PORT=8080
EnvironmentFile=/opt/fredai/.env
ExecStart=/opt/fredai/venv/bin/uvicorn products.fred_api.server:app --host 0.0.0.0 --port 8080 --log-level info
Restart=always
RestartSec=5
StandardOutput=append:/opt/fredai/logs/fred-api.log
StandardError=append:/opt/fredai/logs/fred-api-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- fredai-code-audit: Code Audit (port 8081) ---
cat > /etc/systemd/system/fredai-code-audit.service << 'EOF'
[Unit]
Description=FredAI Code Audit Service (FastAPI)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=fredai
Group=fredai
WorkingDirectory=/opt/fredai
Environment=PATH=/opt/fredai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/fredai
Environment=PORT=8081
EnvironmentFile=/opt/fredai/.env
ExecStart=/opt/fredai/venv/bin/uvicorn products.code_audit.server:app --host 0.0.0.0 --port 8081 --log-level info
Restart=always
RestartSec=5
StandardOutput=append:/opt/fredai/logs/code-audit.log
StandardError=append:/opt/fredai/logs/code-audit-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- fredai-test-gen: Test Generator (port 8082) ---
cat > /etc/systemd/system/fredai-test-gen.service << 'EOF'
[Unit]
Description=FredAI Test Generator (FastAPI)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=fredai
Group=fredai
WorkingDirectory=/opt/fredai
Environment=PATH=/opt/fredai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/fredai
Environment=PORT=8082
EnvironmentFile=/opt/fredai/.env
ExecStart=/opt/fredai/venv/bin/uvicorn products.test_generator.server:app --host 0.0.0.0 --port 8082 --log-level info
Restart=always
RestartSec=5
StandardOutput=append:/opt/fredai/logs/test-gen.log
StandardError=append:/opt/fredai/logs/test-gen-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- fredai-doc-gen: Doc Generator (port 8083) ---
cat > /etc/systemd/system/fredai-doc-gen.service << 'EOF'
[Unit]
Description=FredAI Doc Generator (FastAPI)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=fredai
Group=fredai
WorkingDirectory=/opt/fredai
Environment=PATH=/opt/fredai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/fredai
Environment=PORT=8083
EnvironmentFile=/opt/fredai/.env
ExecStart=/opt/fredai/venv/bin/uvicorn products.doc_generator.server:app --host 0.0.0.0 --port 8083 --log-level info
Restart=always
RestartSec=5
StandardOutput=append:/opt/fredai/logs/doc-gen.log
StandardError=append:/opt/fredai/logs/doc-gen-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- fredai-assistant: Fred Assistant (port 7870) ---
cat > /etc/systemd/system/fredai-assistant.service << 'EOF'
[Unit]
Description=FredAI Fred Assistant (FastAPI)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=fredai
Group=fredai
WorkingDirectory=/opt/fredai
Environment=PATH=/opt/fredai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/fredai
Environment=PORT=7870
EnvironmentFile=/opt/fredai/.env
ExecStart=/opt/fredai/venv/bin/uvicorn products.fred_assistant.server:app --host 0.0.0.0 --port 7870 --log-level info
Restart=always
RestartSec=5
StandardOutput=append:/opt/fredai/logs/assistant.log
StandardError=append:/opt/fredai/logs/assistant-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- fredai-command-api: Command Center API (port 7862) ---
cat > /etc/systemd/system/fredai-command-api.service << 'EOF'
[Unit]
Description=FredAI Command Center API (FastAPI)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=fredai
Group=fredai
WorkingDirectory=/opt/fredai
Environment=PATH=/opt/fredai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/fredai
Environment=PORT=7862
EnvironmentFile=/opt/fredai/.env
ExecStart=/opt/fredai/venv/bin/uvicorn products.command_center.server:app --host 127.0.0.1 --port 7862 --log-level info
Restart=always
RestartSec=5
StandardOutput=append:/opt/fredai/logs/command-api.log
StandardError=append:/opt/fredai/logs/command-api-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# --- Command Center UI: Static React app served by nginx ---
# No systemd service needed — nginx serves dist/ directly.
# Stop old Streamlit service if it exists.
systemctl stop fredai-command-center 2>/dev/null || true
systemctl disable fredai-command-center 2>/dev/null || true
rm -f /etc/systemd/system/fredai-command-center.service

# Update nginx for Command Center (static files + API proxy with SSE)
NGINX_CMD_CONF=/etc/nginx/sites-available/fredai-command-center
cat > "$NGINX_CMD_CONF" << 'NGINX_EOF'
# Command Center React app (static files)
location /command/ {
    alias /opt/fredai/products/command_center/frontend/dist/;
    try_files $uri $uri/ /command/index.html;
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
NGINX_ASST_CONF=/etc/nginx/sites-available/fredai-assistant
cat > "$NGINX_ASST_CONF" << 'NGINX_EOF'
# Fred Assistant React app (static files)
location /assistant/ {
    alias /opt/fredai/products/fred_assistant/frontend/dist/;
    try_files $uri $uri/ /assistant/index.html;
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

# Auto-include nginx snippets in main server block if not already there
NGINX_MAIN="/etc/nginx/sites-available/ai.chatterfix.com"
if [ -f "$NGINX_MAIN" ]; then
    for SNIPPET in "$NGINX_CMD_CONF" "$NGINX_ASST_CONF"; do
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
# 8. Reload and start services
# ----------------------------------------------------------
echo "=== Starting services ==="
systemctl daemon-reload
systemctl enable fredai-api fredai-pr-bot fredai-chat fredai-studio fredai-fred-api fredai-code-audit fredai-test-gen fredai-doc-gen fredai-command-api fredai-assistant
systemctl restart fredai-api
systemctl restart fredai-pr-bot
systemctl restart fredai-chat
systemctl restart fredai-studio
systemctl restart fredai-fred-api
systemctl restart fredai-code-audit
systemctl restart fredai-test-gen
systemctl restart fredai-doc-gen
systemctl restart fredai-command-api
systemctl restart fredai-assistant
# Reload nginx for Command Center static files
nginx -t && systemctl reload nginx

# ----------------------------------------------------------
# 9. Verify
# ----------------------------------------------------------
echo ""
echo "=== Service Status ==="
systemctl is-active fredai-api && echo "  fredai-api:        RUNNING (port 5050)" || echo "  fredai-api:        FAILED"
systemctl is-active fredai-pr-bot && echo "  fredai-pr-bot:     RUNNING (port 8001)" || echo "  fredai-pr-bot:     FAILED"
systemctl is-active fredai-chat && echo "  fredai-chat:       RUNNING (port 7860)" || echo "  fredai-chat:       FAILED"
systemctl is-active fredai-studio && echo "  fredai-studio:     RUNNING (port 7861)" || echo "  fredai-studio:     FAILED"
systemctl is-active fredai-fred-api && echo "  fredai-fred-api:   RUNNING (port 8080)" || echo "  fredai-fred-api:   FAILED"
systemctl is-active fredai-code-audit && echo "  fredai-code-audit: RUNNING (port 8081)" || echo "  fredai-code-audit: FAILED"
systemctl is-active fredai-test-gen && echo "  fredai-test-gen:   RUNNING (port 8082)" || echo "  fredai-test-gen:   FAILED"
systemctl is-active fredai-doc-gen && echo "  fredai-doc-gen:    RUNNING (port 8083)" || echo "  fredai-doc-gen:    FAILED"
systemctl is-active fredai-command-api && echo "  fredai-cmd-api:    RUNNING (port 7862)" || echo "  fredai-cmd-api:    FAILED"
systemctl is-active fredai-assistant && echo "  fredai-assistant:  RUNNING (port 7870)" || echo "  fredai-assistant:  FAILED"
[ -f /opt/fredai/products/command_center/frontend/dist/index.html ] && echo "  command-center:    STATIC (nginx at /command/)" || echo "  command-center:    NOT BUILT"
[ -f /opt/fredai/products/fred_assistant/frontend/dist/index.html ] && echo "  fred-assistant:    STATIC (nginx at /assistant/)" || echo "  fred-assistant:    NOT BUILT"

echo ""
echo "=== Deploy complete ==="
echo "API:        http://localhost:5050/api/health"
echo "PR Bot:     http://localhost:8001/health"
echo "Chat:       http://localhost:7860"
echo "Studio:     http://localhost:7861"
echo "Fred API:   http://localhost:8080/v1/health"
echo "Code Audit: http://localhost:8081/audit/health"
echo "Test Gen:   http://localhost:8082/tests/health"
echo "Doc Gen:    http://localhost:8083/docs/health"
echo "Command:    https://ai.chatterfix.com/command/"
echo "Assistant:  http://localhost:7870/health"
echo "Asst. UI:   https://ai.chatterfix.com/assistant/"
