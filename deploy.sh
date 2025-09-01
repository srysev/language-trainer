#!/bin/bash

# Define variables for better maintainability
IMAGE_NAME="gcr.io/openai-experiments-373016/language-trainer"
REGION="europe-west1"
SERVICE_NAME="language-trainer"
PROJECT_SA="application-service-account@openai-experiments-373016.iam.gserviceaccount.com"

# Check if auth password parameter is provided
AUTH_PASSWORD=""
if [ -n "$1" ]; then
    AUTH_PASSWORD="$1"
    echo "🔐 Deploying with authentication enabled"
else
    echo "🔓 Deploying without authentication (no password provided)"
fi

echo "🚀 Starting deployment process..."

# Determine Git commit and dirty state
GIT_COMMIT=$(git rev-parse --short HEAD)
if git diff-index --quiet HEAD --; then
  APP_VERSION=$GIT_COMMIT
else
  APP_VERSION="${GIT_COMMIT}-dirty"
fi
echo "Building Docker image with APP_VERSION=${APP_VERSION}..."

# Build Docker image with version arg
docker build --build-arg APP_VERSION=$APP_VERSION -t $IMAGE_NAME .

# Push image to Google Container Registry
echo "Pushing image to Google Container Registry..."
docker push $IMAGE_NAME

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."

# Build environment variables string conditionally
ENV_VARS="ENVIRONMENT=production"
if [ -n "$AUTH_PASSWORD" ]; then
    ENV_VARS="$ENV_VARS,AUTH_PASSWORD=$AUTH_PASSWORD"
fi

gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --vpc-connector=run-conn-ew1 \
  --vpc-egress=all-traffic \
  --set-secrets OPENAI_API_KEY=kyrill_chat_app_openai-api-key:latest,MONGO_URL=kyrill_chat_app_mongo_url:latest \
  --set-env-vars "$ENV_VARS" \
  --allow-unauthenticated \
  --service-account=$PROJECT_SA

echo "✅ Deployment completed!"

if [ -n "$AUTH_PASSWORD" ]; then
    echo ""
    echo "🔐 Authentication is enabled with the provided password"
    echo "   Users will need to login before accessing the application"
else
    echo ""
    echo "🔓 Authentication is disabled - application is publicly accessible"
    echo "   To enable auth next time, use: ./deploy.sh \"your-password\""
fi