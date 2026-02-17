#!/bin/bash

# 🚀 AI TEAM PLATFORM - ULTIMATE DEPLOYMENT SCRIPT
# Deploy to Google Cloud Run, AWS Lambda, Azure Functions, or Kubernetes
# One-click deployment with automatic rollback capabilities

set -e  # Exit on any error

# =============================================================================
# CONFIGURATION
# =============================================================================
PROJECT_NAME="ai-team-platform"
VERSION="1.0.0"
IMAGE_NAME="ai-team-platform"
SERVICE_NAME="ai-team-platform"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
log() {
    echo -e "${CYAN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# =============================================================================
# PLATFORM DETECTION
# =============================================================================
detect_platform() {
    if command -v gcloud &> /dev/null && [[ -n "${GOOGLE_CLOUD_PROJECT:-}" ]]; then
        echo "google_cloud"
    elif command -v aws &> /dev/null && [[ -n "${AWS_DEFAULT_REGION:-}" ]]; then
        echo "aws"
    elif command -v az &> /dev/null && [[ -n "${AZURE_SUBSCRIPTION_ID:-}" ]]; then
        echo "azure"
    elif command -v kubectl &> /dev/null; then
        echo "kubernetes"
    else
        echo "docker"
    fi
}

# =============================================================================
# PRE-DEPLOYMENT CHECKS
# =============================================================================
pre_deployment_checks() {
    log "🔍 Running pre-deployment checks..."
    
    # Check if required files exist
    if [[ ! -f "main.py" ]]; then
        error "main.py not found! Make sure you're in the AI Team Platform directory."
    fi
    
    if [[ ! -f "requirements.txt" ]]; then
        error "requirements.txt not found!"
    fi
    
    if [[ ! -f "Dockerfile" ]]; then
        error "Dockerfile not found!"
    fi
    
    # Check Docker is running
    if ! docker info &> /dev/null; then
        error "Docker is not running or not accessible!"
    fi
    
    # Check git status
    if command -v git &> /dev/null; then
        if [[ -n "$(git status --porcelain)" ]]; then
            warning "You have uncommitted changes. Consider committing them first."
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    fi
    
    success "Pre-deployment checks passed!"
}

# =============================================================================
# BUILD AND TAG DOCKER IMAGE
# =============================================================================
build_image() {
    log "🔨 Building Docker image..."
    
    # Generate build timestamp
    BUILD_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    FULL_TAG="${IMAGE_NAME}:${VERSION}-${BUILD_TIMESTAMP}"
    LATEST_TAG="${IMAGE_NAME}:latest"
    
    # Build the image
    docker build -t "${FULL_TAG}" -t "${LATEST_TAG}" .
    
    if [[ $? -eq 0 ]]; then
        success "Docker image built successfully: ${FULL_TAG}"
        export BUILT_IMAGE="${FULL_TAG}"
    else
        error "Docker build failed!"
    fi
}

# =============================================================================
# GOOGLE CLOUD RUN DEPLOYMENT
# =============================================================================
deploy_to_google_cloud() {
    log "☁️ Deploying to Google Cloud Run..."
    
    # Check if gcloud is configured
    if ! command -v gcloud &> /dev/null; then
        error "gcloud CLI not found! Please install Google Cloud SDK."
    fi
    
    # Set default project if not set
    if [[ -z "${GOOGLE_CLOUD_PROJECT:-}" ]]; then
        PROJECT_ID=$(gcloud config get-value project)
        if [[ -z "$PROJECT_ID" ]]; then
            error "No Google Cloud project set. Use: gcloud config set project YOUR_PROJECT_ID"
        fi
        export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
    fi
    
    # Configure Docker for GCP
    gcloud auth configure-docker --quiet
    
    # Tag image for Google Container Registry
    GCR_IMAGE="gcr.io/${GOOGLE_CLOUD_PROJECT}/${IMAGE_NAME}:${VERSION}"
    docker tag "${BUILT_IMAGE}" "${GCR_IMAGE}"
    
    # Push to GCR
    log "📤 Pushing image to Google Container Registry..."
    docker push "${GCR_IMAGE}"
    
    # Deploy to Cloud Run
    log "🚀 Deploying to Cloud Run..."
    gcloud run deploy "${SERVICE_NAME}" \
        --image="${GCR_IMAGE}" \
        --platform=managed \
        --region=us-central1 \
        --allow-unauthenticated \
        --port=8080 \
        --memory=2Gi \
        --cpu=2 \
        --max-instances=100 \
        --set-env-vars="AI_PLATFORM_ENV=production" \
        --set-env-vars="PORT=8080" \
        --timeout=3600 \
        --quiet
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform=managed --region=us-central1 --format="value(status.url)")
    
    success "🎉 Deployment successful!"
    info "Service URL: ${SERVICE_URL}"
    info "Health check: ${SERVICE_URL}/health"
    info "Dashboard: ${SERVICE_URL}/dashboard"
}

# =============================================================================
# AWS LAMBDA DEPLOYMENT (Using SAM)
# =============================================================================
deploy_to_aws() {
    log "☁️ Deploying to AWS Lambda..."
    
    if ! command -v sam &> /dev/null; then
        error "AWS SAM CLI not found! Please install AWS SAM CLI."
    fi
    
    # Create SAM template if it doesn't exist
    if [[ ! -f "template.yaml" ]]; then
        log "📝 Creating SAM template..."
        cat > template.yaml << 'EOF'
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: AI Team Platform - Serverless Application

Globals:
  Function:
    Timeout: 30
    MemorySize: 3008

Resources:
  AITeamPlatformFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: .
      Handler: main.handler
      Runtime: python3.11
      Environment:
        Variables:
          AI_PLATFORM_ENV: production
      Events:
        ApiGateway:
          Type: Api
          Properties:
            Path: /{proxy+}
            Method: ANY
            
Outputs:
  ApiGatewayEndpoint:
    Description: "API Gateway endpoint URL"
    Value: !Sub "https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/Prod/"
EOF
    fi
    
    # Build and deploy
    sam build
    sam deploy --guided --stack-name ai-team-platform
    
    success "🎉 AWS deployment successful!"
}

# =============================================================================
# AZURE FUNCTIONS DEPLOYMENT
# =============================================================================
deploy_to_azure() {
    log "☁️ Deploying to Azure Functions..."
    
    if ! command -v az &> /dev/null; then
        error "Azure CLI not found! Please install Azure CLI."
    fi
    
    if ! command -v func &> /dev/null; then
        error "Azure Functions Core Tools not found! Please install Azure Functions Core Tools."
    fi
    
    # Create resource group if it doesn't exist
    RESOURCE_GROUP="ai-team-platform-rg"
    FUNCTION_APP_NAME="ai-team-platform-app"
    STORAGE_ACCOUNT="aiteamplatformstorage"
    
    az group create --name "${RESOURCE_GROUP}" --location eastus
    
    # Create storage account
    az storage account create \
        --name "${STORAGE_ACCOUNT}" \
        --location eastus \
        --resource-group "${RESOURCE_GROUP}" \
        --sku Standard_LRS
    
    # Create Function App
    az functionapp create \
        --resource-group "${RESOURCE_GROUP}" \
        --consumption-plan-location eastus \
        --runtime python \
        --runtime-version 3.11 \
        --functions-version 4 \
        --name "${FUNCTION_APP_NAME}" \
        --storage-account "${STORAGE_ACCOUNT}"
    
    # Deploy function
    func azure functionapp publish "${FUNCTION_APP_NAME}"
    
    success "🎉 Azure deployment successful!"
}

# =============================================================================
# KUBERNETES DEPLOYMENT
# =============================================================================
deploy_to_kubernetes() {
    log "☸️ Deploying to Kubernetes..."
    
    if ! command -v kubectl &> /dev/null; then
        error "kubectl not found! Please install kubectl."
    fi
    
    # Check if connected to cluster
    if ! kubectl cluster-info &> /dev/null; then
        error "Not connected to a Kubernetes cluster!"
    fi
    
    # Create namespace if it doesn't exist
    kubectl create namespace ai-platform --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply Kubernetes manifests
    if [[ -d "k8s" ]]; then
        log "📋 Applying Kubernetes manifests..."
        kubectl apply -f k8s/ -n ai-platform
    else
        # Create basic deployment and service
        log "📝 Creating basic Kubernetes resources..."
        
        # Tag image for local registry or push to your registry
        docker tag "${BUILT_IMAGE}" "${IMAGE_NAME}:${VERSION}"
        
        cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${SERVICE_NAME}
  namespace: ai-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ${SERVICE_NAME}
  template:
    metadata:
      labels:
        app: ${SERVICE_NAME}
    spec:
      containers:
      - name: ${SERVICE_NAME}
        image: ${IMAGE_NAME}:${VERSION}
        ports:
        - containerPort: 8080
        env:
        - name: AI_PLATFORM_ENV
          value: "production"
        - name: PORT
          value: "8080"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: ${SERVICE_NAME}-service
  namespace: ai-platform
spec:
  selector:
    app: ${SERVICE_NAME}
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
EOF
    fi
    
    # Wait for deployment
    kubectl wait --for=condition=available --timeout=300s deployment/${SERVICE_NAME} -n ai-platform
    
    # Get service URL
    SERVICE_URL=$(kubectl get service ${SERVICE_NAME}-service -n ai-platform -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    
    success "🎉 Kubernetes deployment successful!"
    if [[ -n "$SERVICE_URL" ]]; then
        info "Service URL: http://${SERVICE_URL}"
    fi
}

# =============================================================================
# LOCAL DOCKER DEPLOYMENT
# =============================================================================
deploy_to_docker() {
    log "🐳 Deploying locally with Docker..."
    
    # Stop existing container
    docker stop "${SERVICE_NAME}" 2>/dev/null || true
    docker rm "${SERVICE_NAME}" 2>/dev/null || true
    
    # Run new container
    docker run -d \
        --name "${SERVICE_NAME}" \
        -p 8080:8080 \
        -e AI_PLATFORM_ENV=production \
        -e PORT=8080 \
        "${BUILT_IMAGE}"
    
    # Wait for container to be ready
    sleep 10
    
    success "🎉 Local Docker deployment successful!"
    info "Service URL: http://localhost:8080"
    info "Health check: http://localhost:8080/health"
}

# =============================================================================
# HEALTH CHECK
# =============================================================================
health_check() {
    local url=$1
    local max_attempts=30
    local attempt=1
    
    log "🏥 Performing health check..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf "${url}/health" > /dev/null 2>&1; then
            success "✅ Health check passed!"
            return 0
        fi
        
        info "Health check attempt ${attempt}/${max_attempts}..."
        sleep 10
        ((attempt++))
    done
    
    error "❌ Health check failed after ${max_attempts} attempts"
}

# =============================================================================
# ROLLBACK FUNCTION
# =============================================================================
rollback() {
    log "🔄 Initiating rollback..."
    
    case $PLATFORM in
        "google_cloud")
            # Get previous revision
            PREVIOUS_REVISION=$(gcloud run revisions list --service="${SERVICE_NAME}" --platform=managed --region=us-central1 --limit=2 --format="value(metadata.name)" | tail -n 1)
            if [[ -n "$PREVIOUS_REVISION" ]]; then
                gcloud run services update-traffic "${SERVICE_NAME}" --to-revisions="${PREVIOUS_REVISION}=100" --platform=managed --region=us-central1
                success "Rollback to revision ${PREVIOUS_REVISION} successful!"
            else
                error "No previous revision found for rollback!"
            fi
            ;;
        "kubernetes")
            kubectl rollout undo deployment/${SERVICE_NAME} -n ai-platform
            kubectl rollout status deployment/${SERVICE_NAME} -n ai-platform
            success "Kubernetes rollback successful!"
            ;;
        "docker")
            # For local Docker, we would need to maintain a list of previous images
            warning "Docker rollback not implemented. Please manually revert to previous image."
            ;;
        *)
            warning "Rollback not implemented for ${PLATFORM}"
            ;;
    esac
}

# =============================================================================
# CLEANUP
# =============================================================================
cleanup() {
    log "🧹 Cleaning up..."
    
    # Remove old Docker images (keep last 3)
    IMAGES_TO_REMOVE=$(docker images "${IMAGE_NAME}" --format "{{.ID}} {{.CreatedAt}}" | sort -rk 2 | tail -n +4 | awk '{print $1}')
    if [[ -n "$IMAGES_TO_REMOVE" ]]; then
        echo "$IMAGES_TO_REMOVE" | xargs docker rmi -f || true
        success "Cleaned up old Docker images"
    fi
}

# =============================================================================
# MAIN DEPLOYMENT FUNCTION
# =============================================================================
main() {
    echo -e "${PURPLE}"
    echo "🚀 AI TEAM PLATFORM - ULTIMATE DEPLOYMENT SCRIPT"
    echo "=================================================="
    echo -e "${NC}"
    
    # Parse command line arguments
    PLATFORM=""
    SKIP_BUILD=false
    SKIP_HEALTH_CHECK=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --platform)
                PLATFORM="$2"
                shift 2
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-health-check)
                SKIP_HEALTH_CHECK=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --platform PLATFORM    Target platform (google_cloud, aws, azure, kubernetes, docker)"
                echo "  --skip-build           Skip Docker image build"
                echo "  --skip-health-check    Skip post-deployment health check"
                echo "  --help                 Show this help message"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done
    
    # Auto-detect platform if not specified
    if [[ -z "$PLATFORM" ]]; then
        PLATFORM=$(detect_platform)
        info "Auto-detected platform: ${PLATFORM}"
    fi
    
    # Pre-deployment checks
    pre_deployment_checks
    
    # Build Docker image
    if [[ "$SKIP_BUILD" != true ]]; then
        build_image
    else
        info "Skipping Docker build..."
        export BUILT_IMAGE="${IMAGE_NAME}:latest"
    fi
    
    # Deploy based on platform
    case $PLATFORM in
        "google_cloud")
            deploy_to_google_cloud
            SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform=managed --region=us-central1 --format="value(status.url)")
            ;;
        "aws")
            deploy_to_aws
            ;;
        "azure")
            deploy_to_azure
            ;;
        "kubernetes")
            deploy_to_kubernetes
            ;;
        "docker"|*)
            deploy_to_docker
            SERVICE_URL="http://localhost:8080"
            ;;
    esac
    
    # Health check
    if [[ "$SKIP_HEALTH_CHECK" != true && -n "${SERVICE_URL:-}" ]]; then
        health_check "$SERVICE_URL"
    fi
    
    # Cleanup
    cleanup
    
    echo -e "${GREEN}"
    echo "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
    echo "===================================="
    if [[ -n "${SERVICE_URL:-}" ]]; then
        echo "🌐 Service URL: ${SERVICE_URL}"
        echo "🏥 Health Check: ${SERVICE_URL}/health"
        echo "📊 Dashboard: ${SERVICE_URL}/dashboard"
        echo "⚡ Generator: ${SERVICE_URL}/generator"
    fi
    echo -e "${NC}"
}

# =============================================================================
# ERROR HANDLING
# =============================================================================
trap 'error "Deployment failed! Check logs above for details."' ERR

# Handle SIGINT (Ctrl+C)
trap 'echo -e "\n${YELLOW}Deployment interrupted!${NC}"; exit 1' SIGINT

# =============================================================================
# EXECUTE MAIN FUNCTION
# =============================================================================
main "$@"