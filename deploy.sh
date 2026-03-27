#!/bin/bash

##############################################################################
# Media Download Service - Quick Deployment Script
# 
# Usage:
#   ./deploy.sh local      # Deploy locally with Docker
#   ./deploy.sh staging    # Deploy to staging server
#   ./deploy.sh production # Deploy to production (requires AWS CLI)
##############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    print_success "Docker is installed"
}

check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    print_success "Docker Compose is installed"
}

deploy_local() {
    print_header "Deploying to Local Docker"
    
    # Check prerequisites
    check_docker
    check_docker_compose
    
    # Check .env file
    if [ ! -f .env ]; then
        print_warning ".env file not found"
        if [ -f .env.example ]; then
            cp .env.example .env
            print_info "Created .env from .env.example - PLEASE EDIT IT with your values"
            exit 1
        else
            print_error ".env.example not found either"
            exit 1
        fi
    fi
    
    print_info "Building Docker images..."
    docker-compose build
    print_success "Docker images built"
    
    print_info "Starting services..."
    docker-compose down 2>/dev/null || true
    docker-compose up -d
    print_success "Services started"
    
    # Wait for services to be ready
    print_info "Waiting for services to be healthy..."
    max_attempts=30
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose ps | grep -q "postgres.*healthy"; then
            print_success "PostgreSQL is healthy"
            break
        fi
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    print_info "Running database migrations..."
    docker-compose exec -T api alembic upgrade head
    print_success "Migrations completed"
    
    print_header "Deployment Complete!"
    echo ""
    echo "Services are now running:"
    echo -e "  ${BLUE}Web UI:${NC} http://localhost:8000"
    echo -e "  ${BLUE}API Docs:${NC} http://localhost:8000/docs"
    echo -e "  ${BLUE}MinIO Console:${NC} http://localhost:9001 (user: minioadmin, pass: minioadmin)"
    echo -e "  ${BLUE}Flower Dashboard:${NC} http://localhost:5555"
    echo ""
    echo "View logs:"
    echo "  docker-compose logs -f"
    echo ""
    echo "Test the API:"
    echo "  curl http://localhost:8000/health"
}

deploy_staging() {
    print_header "Deploying to Staging"
    
    # Validate environment
    if [ -z "$STAGING_SERVER" ]; then
        print_error "STAGING_SERVER environment variable not set"
        print_info "Usage: export STAGING_SERVER=user@staging.example.com && ./deploy.sh staging"
        exit 1
    fi
    
    print_info "Connecting to staging server: $STAGING_SERVER"
    
    # SSH into server and deploy
    ssh "$STAGING_SERVER" << 'EOF'
        set -e
        cd ~/media-download-service || (print_error "Repository not found"; exit 1)
        
        echo "Pulling latest code..."
        git pull origin main
        
        echo "Building Docker images..."
        docker-compose build
        
        echo "Restarting services..."
        docker-compose down
        docker-compose up -d
        
        echo "Running migrations..."
        docker-compose exec -T api alembic upgrade head
        
        echo "Checking service health..."
        docker-compose ps
EOF
    
    print_success "Staging deployment complete"
}

deploy_production() {
    print_header "Deploying to Production (AWS ECS)"
    
    # Validate prerequisites
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        exit 1
    fi
    
    # Get AWS account ID
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    print_info "AWS Account: $AWS_ACCOUNT_ID"
    
    # Get ECR repository URLs
    API_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/media-download-api"
    WORKER_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/media-download-worker"
    
    print_info "API Repository: $API_REPO"
    print_info "Worker Repository: $WORKER_REPO"
    
    # Login to ECR
    print_info "Logging in to ECR..."
    aws ecr get-login-password --region us-east-1 | \
        docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
    print_success "ECR login successful"
    
    # Build and push images
    print_info "Building and pushing API image..."
    docker build -f Dockerfile.api -t $API_REPO:latest -t $API_REPO:$(date +%Y%m%d-%H%M%S) .
    docker push $API_REPO:latest
    docker push $API_REPO:$(date +%Y%m%d-%H%M%S)
    print_success "API image pushed"
    
    print_info "Building and pushing Worker image..."
    docker build -f Dockerfile.worker -t $WORKER_REPO:latest -t $WORKER_REPO:$(date +%Y%m%d-%H%M%S) .
    docker push $WORKER_REPO:latest
    docker push $WORKER_REPO:$(date +%Y%m%d-%H%M%S)
    print_success "Worker image pushed"
    
    # Update ECS services
    print_info "Updating ECS services..."
    aws ecs update-service \
        --cluster media-download-prod \
        --service api \
        --force-new-deployment \
        --region us-east-1 > /dev/null
    
    aws ecs update-service \
        --cluster media-download-prod \
        --service worker \
        --force-new-deployment \
        --region us-east-1 > /dev/null
    
    print_success "ECS services updated"
    
    print_header "Production Deployment Started!"
    echo ""
    echo "Deployment is in progress. Monitor the rollout:"
    echo "  aws ecs describe-services --cluster media-download-prod --services api --region us-east-1"
    echo ""
}

show_usage() {
    echo "Usage: $0 {local|staging|production}"
    echo ""
    echo "Examples:"
    echo "  $0 local              # Deploy locally with Docker"
    echo "  $0 staging            # Deploy to staging (requires STAGING_SERVER env var)"
    echo "  $0 production         # Deploy to AWS ECS (requires AWS CLI configured)"
    echo ""
}

# Main
if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

case "$1" in
    local)
        deploy_local
        ;;
    staging)
        deploy_staging
        ;;
    production)
        deploy_production
        ;;
    *)
        print_error "Unknown deployment target: $1"
        show_usage
        exit 1
        ;;
esac

