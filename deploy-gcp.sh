#!/usr/bin/env bash
# ============================================================
# FredAI → GCP Cloud Run Deploy Script
# Builds one Docker image, deploys 4 Cloud Run services
# ============================================================
set -euo pipefail

PROJECT="${GCP_PROJECT:-fredfix}"
REGION="${GCP_REGION:-us-central1}"
REPO="fredai"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/fredai"
TAG="${IMAGE_TAG:-latest}"

echo "============================================================"
echo "  FredAI → GCP Cloud Run Deploy"
echo "  Project: ${PROJECT}  Region: ${REGION}"
echo "============================================================"

# ----------------------------------------------------------
# 1. Ensure Artifact Registry repo exists
# ----------------------------------------------------------
echo ""
echo "[1/4] Ensuring Artifact Registry repo '${REPO}' exists..."
gcloud artifacts repositories describe "${REPO}" \
    --project="${PROJECT}" \
    --location="${REGION}" >/dev/null 2>&1 || \
gcloud artifacts repositories create "${REPO}" \
    --project="${PROJECT}" \
    --location="${REGION}" \
    --repository-format=docker \
    --description="FredAI Docker images"

# Configure Docker auth for Artifact Registry
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# ----------------------------------------------------------
# 2. Build & push Docker image
# ----------------------------------------------------------
echo ""
echo "[2/4] Building Docker image..."
docker build -f Dockerfile.cloud -t "${IMAGE}:${TAG}" .
echo "Pushing ${IMAGE}:${TAG}..."
docker push "${IMAGE}:${TAG}"

# ----------------------------------------------------------
# 3. Shared secrets flag (all services get these)
# ----------------------------------------------------------
SHARED_SECRETS="ANTHROPIC_API_KEY=fredai-anthropic-key:latest"
SHARED_SECRETS="${SHARED_SECRETS},OPENAI_API_KEY=fredai-openai-key:latest"
SHARED_SECRETS="${SHARED_SECRETS},GEMINI_API_KEY=fredai-gemini-key:latest"
SHARED_SECRETS="${SHARED_SECRETS},XAI_API_KEY=fredai-xai-key:latest"

PR_BOT_SECRETS="${SHARED_SECRETS}"
PR_BOT_SECRETS="${PR_BOT_SECRETS},GITHUB_APP_ID=fredai-github-app-id:latest"
PR_BOT_SECRETS="${PR_BOT_SECRETS},GITHUB_PRIVATE_KEY=fredai-github-private-key:latest"
PR_BOT_SECRETS="${PR_BOT_SECRETS},GITHUB_WEBHOOK_SECRET=fredai-github-webhook-secret:latest"

# ----------------------------------------------------------
# 4. Deploy each service
# ----------------------------------------------------------
echo ""
echo "[3/4] Deploying Cloud Run services..."

deploy_service() {
    local name="$1"
    local command="$2"
    local mem="$3"
    local cpu="$4"
    local max="$5"
    local secrets="$6"

    echo ""
    echo "  Deploying ${name}..."
    gcloud run deploy "${name}" \
        --project="${PROJECT}" \
        --region="${REGION}" \
        --image="${IMAGE}:${TAG}" \
        --command="/bin/sh" \
        --args="-c,${command}" \
        --memory="${mem}" \
        --cpu="${cpu}" \
        --min-instances=0 \
        --max-instances="${max}" \
        --timeout=600 \
        --set-env-vars="AI_PLATFORM_ENV=production" \
        --set-secrets="${secrets}" \
        --allow-unauthenticated \
        --quiet
}

# fredai-pr-bot: FastAPI PR review webhook receiver
deploy_service "fredai-pr-bot" \
    "uvicorn products.pr_review_bot.server:app --host 0.0.0.0 --port \$PORT" \
    "1Gi" "1" "10" "${PR_BOT_SECRETS}"

# fredai-api: Flask API server for IDE integration
deploy_service "fredai-api" \
    "gunicorn servers.api_server:app --bind 0.0.0.0:\$PORT --workers 2 --timeout 600" \
    "2Gi" "2" "20" "${SHARED_SECRETS}"

# fredai-chat: Gradio Chat UI
deploy_service "fredai-chat" \
    "python -m ai_dev_team.chat_ui" \
    "1Gi" "1" "5" "${SHARED_SECRETS}"

# fredai-studio: Gradio Studio IDE
deploy_service "fredai-studio" \
    "python -m ai_dev_team.studio_ui" \
    "1Gi" "1" "5" "${SHARED_SECRETS}"

# ----------------------------------------------------------
# 5. Print service URLs
# ----------------------------------------------------------
echo ""
echo "[4/4] Deployed services:"
echo "============================================================"
gcloud run services list \
    --project="${PROJECT}" \
    --region="${REGION}" \
    --filter="metadata.name~fredai" \
    --format="table(metadata.name, status.url)"
echo "============================================================"
echo "Done!"
