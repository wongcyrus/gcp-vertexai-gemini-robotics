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

# Verify frontend webapp deployment on Google Cloud Run

set -e

# Configuration
SERVICE_NAME="robot-adk-frontend"
REGION="${REGION:-us-central1}"
PROJECT_ID="${PROJECT_ID:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if PROJECT_ID is set
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$PROJECT_ID" ]; then
        log_error "PROJECT_ID environment variable is not set and no default project configured"
        exit 1
    fi
fi

log_info "Verifying deployment for project: $PROJECT_ID"

# Check if service exists
log_info "Checking if service exists..."
if ! gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --quiet >/dev/null 2>&1; then
    log_error "Service $SERVICE_NAME not found in region $REGION"
    exit 1
fi

# Get service details
log_info "Getting service details..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format="value(status.url)")

READY_CONDITION=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format="value(status.conditions[0].status)")

log_info "Service URL: $SERVICE_URL"
log_info "Service Ready Status: $READY_CONDITION"

# Test HTTP connectivity
log_info "Testing HTTP connectivity..."
if curl -s --max-time 10 --fail "$SERVICE_URL" >/dev/null; then
    log_info "✅ HTTP connectivity test passed"
else
    log_warn "❌ HTTP connectivity test failed"
fi

# Display summary
echo ""
log_info "=== Deployment Summary ==="
echo "Service Name: $SERVICE_NAME"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service URL: $SERVICE_URL"
echo "Status: $READY_CONDITION"
echo ""
log_info "🌐 Open in browser: $SERVICE_URL"
