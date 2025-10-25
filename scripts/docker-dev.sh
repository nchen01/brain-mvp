#!/bin/bash
# Development Docker management script for Brain MVP

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

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from .env.example..."
    cp .env.example .env
    print_warning "Please update .env file with your configuration before continuing."
    exit 1
fi

# Function to show usage
show_usage() {
    echo "Usage: $0 {start|stop|restart|logs|shell|test|clean|status}"
    echo ""
    echo "Commands:"
    echo "  start     - Start all services in development mode"
    echo "  stop      - Stop all services"
    echo "  restart   - Restart all services"
    echo "  logs      - Show logs from all services"
    echo "  shell     - Open shell in main application container"
    echo "  test      - Run tests in container"
    echo "  clean     - Clean up containers, volumes, and images"
    echo "  status    - Show status of all services"
    echo "  db-shell  - Open PostgreSQL shell"
    echo "  redis-cli - Open Redis CLI"
}

# Function to start services
start_services() {
    print_status "Starting Brain MVP development environment..."
    docker-compose up -d
    
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    if docker-compose ps | grep -q "Up (healthy)"; then
        print_success "Services started successfully!"
        print_status "Application available at: http://localhost:8000"
        print_status "API Documentation: http://localhost:8000/docs"
        print_status "PostgreSQL: localhost:5432"
        print_status "Redis: localhost:6379"
    else
        print_error "Some services failed to start properly"
        docker-compose ps
    fi
}

# Function to stop services
stop_services() {
    print_status "Stopping Brain MVP services..."
    docker-compose down
    print_success "Services stopped successfully!"
}

# Function to restart services
restart_services() {
    print_status "Restarting Brain MVP services..."
    docker-compose restart
    print_success "Services restarted successfully!"
}

# Function to show logs
show_logs() {
    if [ -n "$2" ]; then
        docker-compose logs -f "$2"
    else
        docker-compose logs -f
    fi
}

# Function to open shell
open_shell() {
    print_status "Opening shell in Brain MVP container..."
    docker-compose exec brain-mvp /bin/bash
}

# Function to run tests
run_tests() {
    print_status "Running tests in container..."
    docker-compose exec brain-mvp python -m pytest tests/ -v
}

# Function to clean up
clean_up() {
    print_warning "This will remove all containers, volumes, and images. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Cleaning up Docker resources..."
        docker-compose down -v --rmi all --remove-orphans
        docker system prune -f
        print_success "Cleanup completed!"
    else
        print_status "Cleanup cancelled."
    fi
}

# Function to show status
show_status() {
    print_status "Brain MVP Services Status:"
    docker-compose ps
    echo ""
    print_status "Docker System Info:"
    docker system df
}

# Function to open database shell
open_db_shell() {
    print_status "Opening PostgreSQL shell..."
    docker-compose exec postgres psql -U brain_user -d brain_mvp
}

# Function to open Redis CLI
open_redis_cli() {
    print_status "Opening Redis CLI..."
    docker-compose exec redis redis-cli -a redis_password
}

# Main script logic
case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    logs)
        show_logs "$@"
        ;;
    shell)
        open_shell
        ;;
    test)
        run_tests
        ;;
    clean)
        clean_up
        ;;
    status)
        show_status
        ;;
    db-shell)
        open_db_shell
        ;;
    redis-cli)
        open_redis_cli
        ;;
    *)
        show_usage
        exit 1
        ;;
esac