#!/usr/bin/env bash
# ============================================================
# FredAI → VM Deploy (run from your Mac)
# Packages code, SCPs to VM, runs ci-deploy-fredai.sh
# ============================================================
set -euo pipefail

VM_NAME="${VM_NAME:-managers-dashboard}"
VM_ZONE="${VM_ZONE:-us-central1-a}"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================================"
echo "  FredAI → VM Deploy"
echo "  VM: ${VM_NAME} (${VM_ZONE})"
echo "============================================================"

# ----------------------------------------------------------
# 1. Package code (exclude dev/test/infra files)
# ----------------------------------------------------------
echo ""
echo "[1/3] Packaging FredAI..."
tar -czf /tmp/fredai.tar.gz \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='tests' \
    --exclude='terraform' \
    --exclude='k8s' \
    --exclude='mlx-training' \
    --exclude='.pytest_cache' \
    --exclude='.ruff_cache' \
    --exclude='*.egg-info' \
    --exclude='dist' \
    --exclude='build' \
    --exclude='htmlcov' \
    --exclude='.coverage' \
    -C "$PROJECT_DIR" .

SIZE=$(du -h /tmp/fredai.tar.gz | cut -f1)
echo "  Package size: ${SIZE}"

# ----------------------------------------------------------
# 2. Upload to VM
# ----------------------------------------------------------
echo ""
echo "[2/3] Uploading to VM..."
gcloud compute scp /tmp/fredai.tar.gz ci-deploy-fredai.sh \
    "${VM_NAME}:/tmp/" \
    --zone="${VM_ZONE}" --quiet

rm -f /tmp/fredai.tar.gz

# ----------------------------------------------------------
# 3. Run deploy script on VM
# ----------------------------------------------------------
echo ""
echo "[3/3] Deploying on VM..."
gcloud compute ssh "${VM_NAME}" \
    --zone="${VM_ZONE}" --quiet \
    --command="sudo bash /tmp/ci-deploy-fredai.sh"

# ----------------------------------------------------------
# 4. Health check
# ----------------------------------------------------------
echo ""
echo "Waiting 10s for services to start..."
sleep 10

echo "=== Health Checks ==="
API_STATUS=$(gcloud compute ssh "${VM_NAME}" \
    --zone="${VM_ZONE}" --quiet \
    --command="curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5050/api/health" 2>/dev/null || echo "000")
echo "  API Server (5050): HTTP ${API_STATUS}"

BOT_STATUS=$(gcloud compute ssh "${VM_NAME}" \
    --zone="${VM_ZONE}" --quiet \
    --command="curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/health" 2>/dev/null || echo "000")
echo "  PR Bot     (8001): HTTP ${BOT_STATUS}"

echo ""
echo "============================================================"
echo "  Deploy complete!"
echo "============================================================"
