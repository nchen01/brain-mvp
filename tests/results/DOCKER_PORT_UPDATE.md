# Docker Port Configuration Update

## Summary

This update changes the Docker host port mappings to avoid conflicts with local services and improve clarity.

## Changes Made

### Port Mappings

**Previous Configuration:**
```yaml
ports:
  - "8000:8000"  # Web App
  - "5432:5432"  # PostgreSQL
  - "6379:6379"  # Redis
```

**New Configuration:**
```yaml
ports:
  - "8080:8000"  # Web App (host:container)
  - "5433:5432"  # PostgreSQL (host:container)
  - "6380:6379"  # Redis (host:container)
```

### Access Points

After this update, access the services at:
- **Web Interface**: http://localhost:8080
- **API Documentation**: http://localhost:8080/docs
- **PostgreSQL**: localhost:5433
- **Redis**: localhost:6380

### Files Updated

1. **docker-compose.yml** - Updated port mappings
2. **Test Scripts** - Updated all test files to use new ports:
   - `final_e2e_test.py`
   - `test_document_upload.py`
   - `simple_docker_test.py`
   - `test_docker_e2e.py`
3. **Documentation** - Updated all references:
   - `README.md`
   - `USAGE_GUIDE.md`
   - `INSTALLATION.md`

### Bug Fixes

Fixed a bug in `final_e2e_test.py` where the Docker container status test was failing due to incorrect newline character handling in the JSON parsing logic.

## Migration Guide

If you have existing containers running:

```bash
# Stop and remove old containers
docker-compose down

# Start with new port configuration
docker-compose up -d

# Verify services are running
docker-compose ps
```

Update any external tools or scripts that connect to:
- Change `localhost:8000` → `localhost:8080`
- Change `localhost:5432` → `localhost:5433`
- Change `localhost:6379` → `localhost:6380`

## Benefits

1. **Avoids Port Conflicts**: Prevents conflicts with local development services
2. **Clearer Configuration**: Host and container ports are now different, making the mapping more explicit
3. **Better Documentation**: All documentation now consistently references the correct ports
