#!/usr/bin/env bash
# ============================================================
# ElGringo → VM Deploy (run from your Mac)
# Packages code, SCPs to VM, runs ci-deploy-elgringo.sh
# ============================================================
set -euo pipefail

VM_NAME="${VM_NAME:-elgringo-vm}"
VM_ZONE="${VM_ZONE:-us-central1-a}"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================================"
echo "  ElGringo → VM Deploy"
echo "  VM: ${VM_NAME} (${VM_ZONE})"
echo "============================================================"

# ----------------------------------------------------------
# 1. Package code (exclude dev/test/infra files)
# ----------------------------------------------------------
echo ""
echo "[1/3] Packaging ElGringo..."
tar -czf /tmp/elgringo.tar.gz \
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
    --exclude='node_modules' \
    --exclude='build' \
    --exclude='htmlcov' \
    --exclude='.coverage' \
    -C "$PROJECT_DIR" .

SIZE=$(du -h /tmp/elgringo.tar.gz | cut -f1)
echo "  Package size: ${SIZE}"

# ----------------------------------------------------------
# 2. Upload to VM
# ----------------------------------------------------------
echo ""
echo "[2/3] Uploading to VM..."
gcloud compute scp /tmp/elgringo.tar.gz ci-deploy-elgringo.sh \
    "${VM_NAME}:~/" \
    --zone="${VM_ZONE}" --quiet

rm -f /tmp/elgringo.tar.gz

# ----------------------------------------------------------
# 3. Run deploy script on VM
# ----------------------------------------------------------
echo ""
echo "[3/3] Deploying on VM..."
gcloud compute ssh "${VM_NAME}" \
    --zone="${VM_ZONE}" --quiet \
    --command="sudo mv ~/elgringo.tar.gz ~/ci-deploy-elgringo.sh /tmp/ && sudo bash /tmp/ci-deploy-elgringo.sh"

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

ASST_STATUS=$(gcloud compute ssh "${VM_NAME}" \
    --zone="${VM_ZONE}" --quiet \
    --command="curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:7870/health" 2>/dev/null || echo "000")
echo "  Assistant  (7870): HTTP ${ASST_STATUS}"

echo ""
echo "============================================================"
echo "  Deploy complete!"
echo "============================================================"
