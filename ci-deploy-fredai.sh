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
# 6. Set ownership
# ----------------------------------------------------------
echo "=== Setting ownership ==="
chown -R fredai:fredai $DIR

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

# --- fredai-command-center: Command Center UI (port 7863) ---
cat > /etc/systemd/system/fredai-command-center.service << 'EOF'
[Unit]
Description=FredAI Command Center UI (Streamlit)
After=network.target fredai-command-api.service
Wants=network-online.target fredai-command-api.service

[Service]
Type=simple
User=fredai
Group=fredai
WorkingDirectory=/opt/fredai
Environment=PATH=/opt/fredai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/fredai
Environment=PORT=7863
Environment=COMMAND_CENTER_API=http://127.0.0.1:7862
EnvironmentFile=/opt/fredai/.env
ExecStart=/opt/fredai/venv/bin/python -m streamlit run ai_dev_team/command_center.py --server.port 7863 --server.headless true
Restart=always
RestartSec=5
StandardOutput=append:/opt/fredai/logs/command-center.log
StandardError=append:/opt/fredai/logs/command-center-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# ----------------------------------------------------------
# 8. Reload and start services
# ----------------------------------------------------------
echo "=== Starting services ==="
systemctl daemon-reload
systemctl enable fredai-api fredai-pr-bot fredai-chat fredai-studio fredai-fred-api fredai-code-audit fredai-test-gen fredai-doc-gen fredai-command-api fredai-command-center
systemctl restart fredai-api
systemctl restart fredai-pr-bot
systemctl restart fredai-chat
systemctl restart fredai-studio
systemctl restart fredai-fred-api
systemctl restart fredai-code-audit
systemctl restart fredai-test-gen
systemctl restart fredai-doc-gen
systemctl restart fredai-command-api
systemctl restart fredai-command-center

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
systemctl is-active fredai-command-center && echo "  fredai-command:    RUNNING (port 7863)" || echo "  fredai-command:    FAILED"

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
echo "Command:    http://localhost:7863"
