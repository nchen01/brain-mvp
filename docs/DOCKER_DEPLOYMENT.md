# Docker Deployment Guide for Brain MVP

This guide covers containerized deployment of the Brain MVP system using Docker and Docker Compose.

## 🏗️ **Architecture Overview**

The Brain MVP Docker setup provides a complete containerized environment with:

- **Main Application**: FastAPI server with document processing capabilities
- **PostgreSQL**: Production-ready database with proper initialization
- **Redis**: Caching and session management
- **Nginx**: Reverse proxy with load balancing and SSL termination
- **Monitoring**: Optional Prometheus, Grafana, and Loki stack

## 🚀 **Quick Start**

### **Development Environment**

1. **Clone and Setup**
   ```bash
   git clone https://github.com/nchen01/brain-mvp.git
   cd brain-mvp
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start Development Environment**
   ```bash
   ./scripts/docker-dev.sh start
   ```

3. **Access Services**
   - Application: http://localhost:8088
   - API Docs: http://localhost:8088/docs
   - PostgreSQL: localhost:5433
   - Redis: localhost:6380

### **Production Environment**

1. **Prepare Production Environment**
   ```bash
   cp .env.example .env
   # Configure production values in .env
   ```

2. **Deploy Production**
   ```bash
   ./scripts/docker-prod.sh deploy
   ```

3. **Access Production Services**
   - Application: http://localhost (via Nginx)
   - Monitoring: http://localhost:3000 (Grafana)

## 📋 **Prerequisites**

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB+ RAM available
- 10GB+ disk space

## 🔧 **Configuration**

### **Environment Variables**

Copy `.env.example` to `.env` and configure:

```bash
# Application Settings
ENVIRONMENT=production
SECRET_KEY=your-super-secret-key-change-this
DEBUG=false
LOG_LEVEL=WARNING

# Database Configuration
POSTGRES_PASSWORD=secure_password_here
DATABASE_URL=postgresql://brain_user:secure_password_here@postgres:5432/brain_mvp

# Redis Configuration
REDIS_PASSWORD=redis_secure_password
REDIS_URL=redis://:redis_secure_password@redis:6379/0

# Security
JWT_SECRET_KEY=jwt-secret-key-change-this
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Monitoring
GRAFANA_PASSWORD=admin_password_change_this
```

### **Service Configuration**

#### **Main Application**
- **Port**: 8088 (external), 8000 (internal container), 80/443 (via Nginx)
- **Resources**: 2-4 CPU, 4-8GB RAM (production)
- **Health Check**: `/health` endpoint
- **Restart Policy**: `unless-stopped` (development), `always` (production)

#### **PostgreSQL**
- **Version**: PostgreSQL 15 Alpine
- **Port**: 5432
- **Resources**: 1 CPU, 2GB RAM
- **Persistence**: Named volume `postgres_data`
- **Initialization**: Automated via `scripts/init-db.sql`

#### **Redis**
- **Version**: Redis 7 Alpine
- **Port**: 6379
- **Resources**: 0.5 CPU, 1GB RAM
- **Persistence**: Named volume `redis_data`
- **Configuration**: AOF persistence enabled

#### **Nginx**
- **Version**: Nginx Alpine
- **Ports**: 80, 443
- **Features**: Rate limiting, compression, SSL termination
- **Configuration**: `nginx/nginx.conf`

## 🛠️ **Management Commands**

### **Development Commands**

```bash
# Start all services
./scripts/docker-dev.sh start

# Stop all services
./scripts/docker-dev.sh stop

# View logs
./scripts/docker-dev.sh logs

# Open application shell
./scripts/docker-dev.sh shell

# Run tests
./scripts/docker-dev.sh test

# Open database shell
./scripts/docker-dev.sh db-shell

# Open Redis CLI
./scripts/docker-dev.sh redis-cli

# Clean up everything
./scripts/docker-dev.sh clean
```

### **Production Commands**

```bash
# Deploy production environment
./scripts/docker-prod.sh deploy

# Start/stop services
./scripts/docker-prod.sh start
./scripts/docker-prod.sh stop

# View production logs
./scripts/docker-prod.sh logs

# Create database backup
./scripts/docker-prod.sh backup

# Restore from backup
./scripts/docker-prod.sh restore backups/backup_file.sql.gz

# Update to latest version
./scripts/docker-prod.sh update

# Start monitoring stack
./scripts/docker-prod.sh monitoring

# Check system status
./scripts/docker-prod.sh status
```

## 🔍 **Monitoring and Logging**

### **Application Monitoring**

The production setup includes comprehensive monitoring:

- **Prometheus**: Metrics collection (port 9090)
- **Grafana**: Visualization dashboard (port 3000)
- **Loki**: Log aggregation (port 3100)

### **Health Checks**

All services include health checks:

```bash
# Check service health
docker-compose ps

# View health check logs
docker-compose logs brain-mvp | grep health
```

### **Log Management**

Logs are structured and centralized:

```bash
# View application logs
./scripts/docker-prod.sh logs brain-mvp

# View all service logs
./scripts/docker-prod.sh logs

# Follow logs in real-time
docker-compose -f docker-compose.prod.yml logs -f
```

## 🔒 **Security Considerations**

### **Production Security**

1. **Environment Variables**
   - Use strong, unique passwords
   - Never commit `.env` files
   - Rotate secrets regularly

2. **Network Security**
   - Services communicate via internal network
   - Only necessary ports exposed
   - Rate limiting configured

3. **Container Security**
   - Non-root user in containers
   - Minimal base images
   - Regular security updates

### **SSL/TLS Configuration**

For production with SSL:

1. **Obtain SSL Certificates**
   ```bash
   # Using Let's Encrypt
   certbot certonly --webroot -w /var/www/html -d yourdomain.com
   ```

2. **Configure Nginx SSL**
   ```bash
   # Copy certificates to nginx/ssl/
   cp /etc/letsencrypt/live/yourdomain.com/* nginx/ssl/
   ```

3. **Update Nginx Configuration**
   - Modify `nginx/nginx.prod.conf`
   - Add SSL server block
   - Configure HTTPS redirects

## 📊 **Performance Tuning**

### **Resource Allocation**

Adjust resources in `docker-compose.prod.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '1.0'
      memory: 2G
```

### **Database Optimization**

PostgreSQL tuning in `scripts/init-db.sql`:

```sql
-- Adjust based on available memory
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
```

### **Application Scaling**

Scale services horizontally:

```bash
# Scale application instances
docker-compose -f docker-compose.prod.yml up -d --scale brain-mvp=3
```

## 🔄 **Backup and Recovery**

### **Automated Backups**

Set up automated backups with cron:

```bash
# Add to crontab
0 2 * * * /path/to/brain-mvp/scripts/docker-prod.sh backup
```

### **Backup Strategy**

- **Daily**: Database backups
- **Weekly**: Full system backup
- **Monthly**: Archive old backups
- **Retention**: 30 days local, 90 days remote

### **Disaster Recovery**

1. **Database Recovery**
   ```bash
   ./scripts/docker-prod.sh restore backups/latest_backup.sql.gz
   ```

2. **Full System Recovery**
   ```bash
   # Restore from backup
   docker-compose -f docker-compose.prod.yml down -v
   # Restore volumes from backup
   # Restart services
   ./scripts/docker-prod.sh deploy
   ```

## 🐛 **Troubleshooting**

### **Common Issues**

1. **Services Won't Start**
   ```bash
   # Check logs
   docker-compose logs
   
   # Check system resources
   docker system df
   docker stats
   ```

2. **Database Connection Issues**
   ```bash
   # Check PostgreSQL logs
   docker-compose logs postgres
   
   # Test connection
   docker-compose exec postgres pg_isready -U brain_user
   ```

3. **Memory Issues**
   ```bash
   # Check memory usage
   docker stats --no-stream
   
   # Adjust resource limits
   # Edit docker-compose.prod.yml
   ```

### **Performance Issues**

1. **Slow Response Times**
   - Check resource allocation
   - Review application logs
   - Monitor database performance

2. **High Memory Usage**
   - Adjust worker processes
   - Optimize database queries
   - Implement caching

### **Debug Mode**

Enable debug mode for troubleshooting:

```bash
# Set in .env
DEBUG=true
LOG_LEVEL=DEBUG

# Restart services
./scripts/docker-dev.sh restart
```

## 🎮 **GPU Deployment (NVIDIA)**

### Prerequisites

- NVIDIA GPU with compute capability 8.0+ (Ampere/Ada/Hopper architecture)
- NVIDIA Container Toolkit installed
- Linux or WSL2 on Windows

### Tested Configurations

| GPU | VRAM | Memory Utilization Setting |
|-----|------|---------------------------|
| RTX 3060 Ti | 8GB | `VLLM_GPU_MEMORY_UTILIZATION=0.85` |
| RTX 3060 | 12GB | `VLLM_GPU_MEMORY_UTILIZATION=0.90` |
| RTX 3090/4090 | 24GB | Default settings |

### Starting GPU Profile

```bash
# Start all GPU services
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile gpu up -d

# Check GPU is being used
nvidia-smi

# View MinerU logs
docker compose logs -f mineru-api
```

### GPU Services

| Service | Port | Description |
|---------|------|-------------|
| brain-mvp-app | 8088 | Main application |
| mineru-api | 8001 | MinerU GPU processing service |
| mineru-gradio | 7860 | MinerU web interface |

### Configuration (`docker-compose.gpu.yml`)

The GPU override file configures:
- `MINERU_BACKEND=pipeline` - Uses reliable pipeline backend with GPU-accelerated OCR
- `VLLM_GPU_MEMORY_UTILIZATION=0.85` - Optimized for 8GB VRAM cards
- GPU device reservation and capabilities
- Extended health check timeouts for model loading

### Known Issues

See [`KNOWN_ISSUES.md`](../KNOWN_ISSUES.md) for:
- MinerU API duplicate backend parameter error
- PyTorch version conflicts with VLM backends
- Recommended backend configurations

---

## 📚 **Additional Resources**

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [PostgreSQL Docker Guide](https://hub.docker.com/_/postgres)
- [Nginx Docker Guide](https://hub.docker.com/_/nginx)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

## 🆘 **Support**

For issues and questions:

1. Check the troubleshooting section above
2. Review application logs
3. Check GitHub issues
4. Create a new issue with:
   - Docker version
   - System specifications
   - Error logs
   - Steps to reproduce

---

**Last Updated**: January 2026
**Docker Version**: 20.10+
**Compose Version**: 2.0+