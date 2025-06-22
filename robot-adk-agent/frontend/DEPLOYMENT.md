# Frontend Deployment Guide

This directory contains the deployment configuration and scripts for deploying the React frontend webapp to Google Cloud Run.

## Files Overview

- `Dockerfile` - Multi-stage Docker build for the React app
- `deploy-to-cloudrun.sh` - Manual deployment script
- `cloudbuild.yaml` - Production Cloud Build configuration
- `cloudbuild-staging.yaml` - Staging Cloud Build configuration
- `deploy-config.yaml` - Environment-specific configuration
- `docker-run.sh` - Local Docker development script
- `.dockerignore` - Docker build optimization

## Prerequisites

1. **Google Cloud CLI**: Install and authenticate

   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Docker**: Install Docker for local builds

3. **Artifact Registry**: Ensure repository exists

   ```bash
   gcloud artifacts repositories create robot-adk-agent \
     --repository-format=docker \
     --location=us-central1
   ```

4. **Cloud Run API**: Enable the API
   ```bash
   gcloud services enable run.googleapis.com
   ```

## Manual Deployment

### Quick Deploy

```bash
# Set your project ID
export PROJECT_ID=	robot-adk-agent

# Deploy to Cloud Run
./deploy-to-cloudrun.sh
```

### Custom Configuration

```bash
# Set environment variables
export PROJECT_ID=your-project-id
export REGION=us-central1
export MIN_INSTANCES=1
export MAX_INSTANCES=10
export CPU=1
export MEMORY=512Mi

# Deploy
./deploy-to-cloudrun.sh
```

## CI/CD Deployment

### Production Deployment

Use Cloud Build with the production configuration:

```bash
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_PROD_PROJECT_ID=your-prod-project \
  ../..
```

### Staging Deployment

Use Cloud Build with the staging configuration:

```bash
gcloud builds submit \
  --config=cloudbuild-staging.yaml \
  --substitutions=_STAGING_PROJECT_ID=your-staging-project \
  ../..
```

## Environment Configuration

Update `deploy-config.yaml` with your project-specific settings:

```yaml
production:
  project_id: "your-prod-project-id"
  service_name: "robot-adk-frontend"
  # ... other settings

staging:
  project_id: "your-staging-project-id"
  service_name: "robot-adk-frontend-staging"
  # ... other settings
```

## Local Development

### Run with Docker

```bash
# Build and run locally
./docker-run.sh

# Access at http://localhost:3000
```

### Run with npm

```bash
# Install dependencies
npm install

# Start development server
npm start

# Access at http://localhost:3000
```

## Cloud Run Service Configuration

The deployment creates a Cloud Run service with:

- **Port**: 80 (nginx serves the built React app)
- **CPU**: 1 vCPU (configurable)
- **Memory**: 512Mi (configurable)
- **Concurrency**: 80 requests per instance
- **Scaling**: 0-10 instances (configurable)
- **Authentication**: Public (unauthenticated access)

## Monitoring and Logs

### View Logs

```bash
# Cloud Run logs
gcloud logs read --service=robot-adk-frontend \
  --project=your-project-id

# Build logs
gcloud logs read --filter="resource.type=build" \
  --project=your-project-id
```

### Service Status

```bash
# Get service details
gcloud run services describe robot-adk-frontend \
  --region=us-central1 \
  --project=your-project-id
```

## Troubleshooting

### Common Issues

1. **Build Failures**

   - Check Node.js version compatibility
   - Verify package.json dependencies
   - Review Docker build logs

2. **Deployment Failures**

   - Verify project permissions
   - Check Artifact Registry access
   - Ensure Cloud Run API is enabled

3. **Runtime Issues**
   - Check container logs
   - Verify nginx configuration
   - Test Docker image locally

### Debug Commands

```bash
# Test Docker build locally
docker build -t test-frontend .
docker run -p 8080:80 test-frontend

# Check Cloud Run service
gcloud run services list --project=your-project-id

# View recent deployments
gcloud run revisions list --service=robot-adk-frontend \
  --region=us-central1 --project=your-project-id
```

## Security Considerations

- The service allows unauthenticated access (suitable for public frontend)
- Static files are served with appropriate caching headers
- Security headers are included in nginx configuration
- Consider adding Cloud CDN for production workloads

## Cost Optimization

- Uses `min-instances: 0` for staging to avoid idle costs
- Production uses `min-instances: 1` for better performance
- Nginx serves static files efficiently
- Multi-stage Docker build minimizes image size

## Next Steps

1. Update project IDs in configuration files
2. Set up Cloud Build triggers for automated deployment
3. Configure custom domain and SSL certificate
4. Set up monitoring and alerting
5. Consider implementing Blue/Green deployments
