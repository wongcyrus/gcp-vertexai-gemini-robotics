#!/bin/bash

# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Deploy frontend webapp to Google Cloud Run

set -e

# Configuration
SERVICE_NAME="robot-adk-frontend"
REGION="${REGION:-us-central1}"
PROJECT_ID="${PROJECT_ID:-}"
IMAGE_NAME="frontend-webapp"
ARTIFACT_REGISTRY_REPO="${ARTIFACT_REGISTRY_REPO:-robot-adk-agent}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
MAX_INSTANCES="${MAX_INSTANCES:-1}"
CPU="${CPU:-1}"
MEMORY="${MEMORY:-512Mi}"
CONCURRENCY="${CONCURRENCY:-80}"
PORT="${PORT:-80}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

check_requirements() {
    log_info "Checking requirements..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed"
        exit 1
    fi
    
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check if PROJECT_ID is set
    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
        if [ -z "$PROJECT_ID" ]; then
            log_error "PROJECT_ID environment variable is not set and no default project configured"
            log_info "Set PROJECT_ID: export PROJECT_ID=your-project-id"
            exit 1
        fi
    fi
    
    log_info "Using PROJECT_ID: $PROJECT_ID"
    log_info "Using REGION: $REGION"
}

build_and_push_image() {
    log_info "Building and pushing Docker image..."
    
    # Configure Docker for Artifact Registry
    log_info "Configuring Docker for Artifact Registry..."
    if ! gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet >/dev/null 2>&1; then
        log_error "Failed to configure Docker for Artifact Registry" >&2
        return 1
    fi
    
    # Full image URL
    IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REGISTRY_REPO}/${IMAGE_NAME}:latest"
    
    # Build the image (redirect all output to stderr)
    log_info "Building Docker image: $IMAGE_URL"
    if ! docker build -t "$IMAGE_URL" . >/dev/null 2>&1; then
        log_error "Docker build failed" >&2
        return 1
    fi
    
    # Push the image (redirect all output to stderr)
    log_info "Pushing Docker image to Artifact Registry..."
    if ! docker push "$IMAGE_URL" >/dev/null 2>&1; then
        log_error "Docker push failed" >&2
        return 1
    fi
    
    # Only output the image URL to stdout (no extra characters)
    printf "%s" "$IMAGE_URL"
}

deploy_to_cloud_run() {
    local image_url=$1
    
    log_info "Deploying to Cloud Run..."
    
    # Deploy to Cloud Run
    gcloud run deploy $SERVICE_NAME \
        --image=$image_url \
        --region=$REGION \
        --project=$PROJECT_ID \
        --platform=managed \
        --allow-unauthenticated \
        --port=$PORT \
        --min-instances=$MIN_INSTANCES \
        --max-instances=$MAX_INSTANCES \
        --cpu=$CPU \
        --memory=$MEMORY \
        --concurrency=$CONCURRENCY \
        --labels="created-by=adk,component=frontend" \
        --quiet
    
    # Get the service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
        --region=$REGION \
        --project=$PROJECT_ID \
        --format="value(status.url)")
    
    log_info "Deployment completed successfully!"
    log_info "Service URL: $SERVICE_URL"
}

cleanup() {
    log_info "Cleaning up local Docker images..."
    docker image prune -f || true
}

print_usage() {
    echo "Usage: $0 [OPTIONS]" >&2
    echo "" >&2
    echo "Deploy frontend webapp to Google Cloud Run" >&2
    echo "" >&2
    echo "Environment Variables:" >&2
    echo "  PROJECT_ID                 GCP Project ID (required)" >&2
    echo "  REGION                     GCP Region (default: us-central1)" >&2
    echo "  ARTIFACT_REGISTRY_REPO     Artifact Registry repository (default: robot-adk-agent)" >&2
    echo "  MIN_INSTANCES              Minimum instances (default: 0)" >&2
    echo "  MAX_INSTANCES              Maximum instances (default: 10)" >&2
    echo "  CPU                        CPU allocation (default: 1)" >&2
    echo "  MEMORY                     Memory allocation (default: 512Mi)" >&2
    echo "  CONCURRENCY                Max concurrent requests (default: 80)" >&2
    echo "" >&2
    echo "Options:" >&2
    echo "  -h, --help                 Show this help message" >&2
    echo "  --cleanup-only             Only cleanup local Docker images" >&2
    echo "" >&2
    echo "Example:" >&2
    echo "  export PROJECT_ID=my-project" >&2
    echo "  $0" >&2
}

# Main execution
main() {
    case "${1:-}" in
        -h|--help)
            print_usage
            exit 0
            ;;
        --cleanup-only)
            cleanup
            exit 0
            ;;
    esac
    
    log_info "Starting Cloud Run deployment for frontend webapp..."
    
    check_requirements
    
    # Build and push image
    log_info "Starting build and push process..."
    IMAGE_URL=$(build_and_push_image)
    
    # Debug: verify image URL was captured correctly
    if [ -z "$IMAGE_URL" ]; then
        log_error "Failed to capture image URL from build process"
        exit 1
    fi
    
    # Additional validation of image URL format
    if [[ ! "$IMAGE_URL" =~ ^[a-z0-9-]+-docker\.pkg\.dev/.+$ ]]; then
        log_error "Invalid image URL format captured: '$IMAGE_URL'"
        log_error "Expected format: region-docker.pkg.dev/project/repo/image:tag"
        exit 1
    fi
    
    log_info "Successfully captured image URL: $IMAGE_URL"
    
    # Deploy to Cloud Run
    deploy_to_cloud_run "$IMAGE_URL"
    
    # Cleanup
    cleanup
    
    log_info "Deployment process completed!"
}

# Run main function with all arguments
main "$@"
