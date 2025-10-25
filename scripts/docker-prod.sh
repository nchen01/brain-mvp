#!/bin/bash
# Production Docker deployment script for Brain MVP

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Do not run this script as root for security reasons"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found. Please create it from .env.example and configure for production."
    exit 1
fi

# Function to show usage
show_usage() {
    echo "Usage: $0 {deploy|start|stop|restart|logs|backup|restore|update|status|monitoring}"
    echo ""
    echo "Commands:"
    echo "  deploy      - Deploy Brain MVP in production mode"
    echo "  start       - Start production services"
    echo "  stop        - Stop production services"
    echo "  restart     - Restart production services"
    echo "  logs        - Show production logs"
    echo "  backup      - Create database backup"
    echo "  restore     - Restore database from backup"
    echo "  update      - Update to latest version"
    echo "  status      - Show production status"
    echo "  monitoring  - Start monitoring stack"
}

# Function to deploy production
deploy_production() {
    print_status "Deploying Brain MVP in production mode..."
    
    # Validate environment
    print_status "Validating production environment..."
    
    # Check required environment variables
    required_vars=("SECRET_KEY" "POSTGRES_PASSWORD" "REDIS_PASSWORD")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            print_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Build and start services
    print_status "Building production images..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    print_status "Starting production services..."
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for services
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Run database migrations
    print_status "Running database migrations..."
    docker-compose -f docker-compose.prod.yml exec brain-mvp alembic upgrade head
    
    # Check service health
    if docker-compose -f docker-compose.prod.yml ps | grep -q "Up (healthy)"; then
        print_success "Production deployment completed successfully!"
        print_status "Application available at: http://localhost"
        print_status "API Documentation: http://localhost/docs"
    else
        print_error "Some services failed to start properly"
        docker-compose -f docker-compose.prod.yml ps
        exit 1
    fi
}

# Function to start production services
start_production() {
    print_status "Starting production services..."
    docker-compose -f docker-compose.prod.yml up -d
    print_success "Production services started!"
}

# Function to stop production services
stop_production() {
    print_status "Stopping production services..."
    docker-compose -f docker-compose.prod.yml down
    print_success "Production services stopped!"
}

# Function to restart production services
restart_production() {
    print_status "Restarting production services..."
    docker-compose -f docker-compose.prod.yml restart
    print_success "Production services restarted!"
}

# Function to show production logs
show_production_logs() {
    if [ -n "$2" ]; then
        docker-compose -f docker-compose.prod.yml logs -f "$2"
    else
        docker-compose -f docker-compose.prod.yml logs -f
    fi
}

# Function to backup database
backup_database() {
    print_status "Creating database backup..."
    
    # Create backup directory
    mkdir -p backups
    
    # Generate backup filename with timestamp
    backup_file="backups/brain_mvp_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    # Create backup
    docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U brain_user brain_mvp > "$backup_file"
    
    # Compress backup
    gzip "$backup_file"
    
    print_success "Database backup created: ${backup_file}.gz"
    
    # Clean old backups (keep last 30 days)
    find backups/ -name "*.sql.gz" -mtime +30 -delete
    print_status "Old backups cleaned up (kept last 30 days)"
}

# Function to restore database
restore_database() {
    if [ -z "$2" ]; then
        print_error "Please specify backup file to restore"
        echo "Usage: $0 restore <backup_file>"
        exit 1
    fi
    
    backup_file="$2"
    
    if [ ! -f "$backup_file" ]; then
        print_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    print_warning "This will overwrite the current database. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Restoring database from: $backup_file"
        
        # Stop application to prevent connections
        docker-compose -f docker-compose.prod.yml stop brain-mvp
        
        # Restore database
        if [[ "$backup_file" == *.gz ]]; then
            gunzip -c "$backup_file" | docker-compose -f docker-compose.prod.yml exec -T postgres psql -U brain_user brain_mvp
        else
            docker-compose -f docker-compose.prod.yml exec -T postgres psql -U brain_user brain_mvp < "$backup_file"
        fi
        
        # Restart application
        docker-compose -f docker-compose.prod.yml start brain-mvp
        
        print_success "Database restored successfully!"
    else
        print_status "Restore cancelled."
    fi
}

# Function to update production
update_production() {
    print_status "Updating Brain MVP to latest version..."
    
    # Create backup before update
    backup_database
    
    # Pull latest code
    git pull origin main
    
    # Rebuild and restart services
    docker-compose -f docker-compose.prod.yml build --no-cache
    docker-compose -f docker-compose.prod.yml up -d
    
    # Run migrations
    docker-compose -f docker-compose.prod.yml exec brain-mvp alembic upgrade head
    
    print_success "Update completed successfully!"
}

# Function to show production status
show_production_status() {
    print_status "Brain MVP Production Status:"
    docker-compose -f docker-compose.prod.yml ps
    echo ""
    print_status "System Resources:"
    docker stats --no-stream
    echo ""
    print_status "Disk Usage:"
    docker system df
}

# Function to start monitoring
start_monitoring() {
    print_status "Starting monitoring stack..."
    docker-compose -f docker-compose.prod.yml --profile monitoring up -d
    
    print_success "Monitoring started!"
    print_status "Prometheus: http://localhost:9090"
    print_status "Grafana: http://localhost:3000 (admin/admin)"
}

# Main script logic
case "$1" in
    deploy)
        deploy_production
        ;;
    start)
        start_production
        ;;
    stop)
        stop_production
        ;;
    restart)
        restart_production
        ;;
    logs)
        show_production_logs "$@"
        ;;
    backup)
        backup_database
        ;;
    restore)
        restore_database "$@"
        ;;
    update)
        update_production
        ;;
    status)
        show_production_status
        ;;
    monitoring)
        start_monitoring
        ;;
    *)
        show_usage
        exit 1
        ;;
esac