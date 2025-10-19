# Configuration Management System

This document describes the comprehensive configuration management system implemented for DocForge.

## Overview

The configuration management system provides:

- **Centralized Configuration**: Single source of truth for all application settings
- **Environment-Specific Configs**: Different settings for development, testing, staging, and production
- **Configuration Validation**: Schema-based validation with Pydantic models
- **Secure Configuration Handling**: Sensitive data masking and secure storage
- **Hot-Reloading**: Non-critical settings can be reloaded without restart
- **CLI Management**: Command-line tools for configuration management

## Architecture

### Core Components

1. **ConfigManager**: Central configuration management class
2. **Configuration Sources**: Multiple sources with priority-based merging
3. **Schema Validation**: Pydantic models for configuration validation
4. **CLI Tools**: Command-line interface for configuration operations
5. **Hot Reload**: File watching for automatic configuration updates

### Configuration Sources (Priority Order)

1. **Environment Variables** (Highest Priority)
2. **Local Configuration** (`config/local.yaml`)
3. **Environment-Specific** (`config/{environment}.yaml`)
4. **Base Configuration** (`config/base.yaml`) (Lowest Priority)

## Usage

### Basic Usage

```python
from src.config.config_manager import get_config

# Get configuration manager
config = get_config()

# Get configuration values
database_host = config.get("database.host", "localhost")
debug_mode = config.get("app.debug", False)

# Get entire sections
database_config = config.get_section("database")

# Set configuration values
config.set("app.debug", True)
config.set("database.pool_size", 20, persist=True)  # Persist to local config
```

### Environment Setup

```python
from src.config.config_manager import initialize_config, Environment

# Initialize for specific environment
config_manager = initialize_config(
    environment=Environment.PRODUCTION,
    config_dir="config",
    enable_hot_reload=False
)
```

### Using with Settings Integration

```python
from src.config.settings import get_settings, reload_settings

# Get current settings
settings = get_settings()

# Access configuration
db_url = settings.database.url
storage_path = settings.storage.base_path

# Reload settings from configuration
reload_settings()
```

## Configuration Files

### Base Configuration (`config/base.yaml`)

Contains default settings that apply to all environments:

```yaml
app:
  name: "DocForge"
  version: "1.0.0"
  debug: false
  host: "0.0.0.0"
  port: 8000

database:
  host: "localhost"
  port: 5432
  name: "docforge"
  user: "docforge_user"
  pool_size: 10

storage:
  base_path: "storage"
  max_file_size: 104857600  # 100MB
  allowed_extensions:
    - ".pdf"
    - ".txt"
    - ".docx"
    - ".md"

# ... other sections
```

### Environment-Specific Configurations

#### Development (`config/development.yaml`)
```yaml
app:
  debug: true

database:
  name: "docforge_dev"
  echo: true  # Enable SQL logging

logging:
  level: "DEBUG"
```

#### Production (`config/production.yaml`)
```yaml
app:
  debug: false
  workers: 4

security:
  enable_2fa: true
  enable_audit_logging: true

logging:
  level: "INFO"
  format: "json"
```

#### Testing (`config/testing.yaml`)
```yaml
app:
  debug: true

database:
  name: "docforge_test"

logging:
  level: "WARNING"
  file_enabled: false
```

### Local Configuration (`config/local.yaml`)

For local overrides and sensitive data (not in version control):

```yaml
database:
  password: "my_secure_password"

external_services:
  openai_api_key: "sk-your-api-key"
  anthropic_api_key: "your-anthropic-key"

security:
  secret_key: "your-very-secure-secret-key"
```

## Environment Variables

Configuration can be overridden using environment variables:

```bash
# Environment
export DOCFORGE_ENV=production

# Database
export DATABASE_HOST=db.example.com
export DATABASE_PORT=5432
export DATABASE_NAME=docforge_prod
export DATABASE_USER=prod_user
export DATABASE_PASSWORD=secure_password

# Security
export SECRET_KEY=your-production-secret-key

# External Services
export OPENAI_API_KEY=sk-your-openai-key
export REDIS_URL=redis://redis.example.com:6379/0
```

## CLI Management

### Initialize Configuration

```bash
# Initialize default configuration files
python scripts/config_manager.py init

# Initialize with validation
python scripts/config_manager.py init --validate

# Force overwrite existing files
python scripts/config_manager.py init --force
```

### Validate Configuration

```bash
# Validate all configuration files
python scripts/config_manager.py validate

# Validate specific environment
python scripts/config_manager.py --environment production validate
```

### View Configuration

```bash
# Show all configuration
python scripts/config_manager.py show

# Show specific section
python scripts/config_manager.py show --section database

# Show with sensitive values
python scripts/config_manager.py show --show-sensitive
```

### Get/Set Values

```bash
# Get specific value
python scripts/config_manager.py get database.host

# Get with default
python scripts/config_manager.py get database.timeout --default 30

# Set value
python scripts/config_manager.py set database.pool_size 20

# Set and persist to local config
python scripts/config_manager.py set database.host db.local --persist

# Set different types
python scripts/config_manager.py set app.debug true --type bool
python scripts/config_manager.py set app.port 8080 --type int
```

### System Information

```bash
# Show configuration system info
python scripts/config_manager.py info

# Check system health
python scripts/config_manager.py health
```

### Backup and Restore

```bash
# Create backup
python scripts/config_manager.py backup

# Create backup in specific directory
python scripts/config_manager.py backup --backup-dir /path/to/backups

# Restore from backup
python scripts/config_manager.py restore backup_file.json
```

### Documentation Generation

```bash
# Generate configuration documentation
python scripts/config_manager.py docs --output config_docs.md

# Generate configuration template
python scripts/config_manager.py template --output template.yaml --format yaml
```

## Configuration Schemas

Configuration sections are validated using Pydantic models:

### Database Configuration
```python
class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = Field(default=5432, ge=1, le=65535)
    name: str = Field(..., min_length=1)
    user: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    pool_size: int = Field(default=10, ge=1, le=100)
    # ... other fields
```

### Storage Configuration
```python
class StorageConfig(BaseModel):
    base_path: str = "storage"
    max_file_size: int = Field(default=100*1024*1024, ge=1024)
    allowed_extensions: List[str] = Field(default=[".pdf", ".txt", ".docx", ".md"])
    # ... other fields
```

## Security Considerations

### Sensitive Data Handling

1. **Never commit sensitive data** to version control
2. **Use environment variables** for production secrets
3. **Use local configuration files** for development secrets
4. **Mask sensitive values** in logs and exports
5. **Validate file permissions** on configuration files

### Sensitive Keys

The following configuration keys are automatically masked:
- `database.password`
- `security.secret_key`
- `external_services.openai_api_key`
- `external_services.anthropic_api_key`
- Any key containing: `password`, `secret`, `key`, `token`, `credential`

### Production Security

```yaml
# Production security settings
security:
  secret_key: "MUST-BE-SET-VIA-ENVIRONMENT-VARIABLE"
  enable_2fa: true
  enable_audit_logging: true
  max_login_attempts: 3

logging:
  level: "INFO"  # Don't use DEBUG in production
  format: "json"  # Structured logging
  console_enabled: false  # Log to files only
```

## Hot Reload

Non-critical settings can be reloaded without restarting the application:

### Supported Hot-Reload Settings
- Log levels
- Batch sizes
- Chunk sizes
- Cache settings (non-critical)

### Usage
```python
from src.config.settings import get_settings

settings = get_settings()

# Check if hot reload succeeded
if settings.reload_hot_reloadable_settings():
    print("Configuration reloaded successfully")
```

## Integration Examples

### Database Connection
```python
from src.config.settings import get_database_config

db_config = get_database_config()
connection_url = db_config.url
```

### Storage Setup
```python
from src.config.settings import get_storage_config

storage_config = get_storage_config()
upload_path = Path(storage_config.base_path) / "uploads"
upload_path.mkdir(parents=True, exist_ok=True)
```

### Processing Configuration
```python
from src.config.settings import get_processing_config

proc_config = get_processing_config()
max_workers = proc_config.max_workers
timeout = proc_config.timeout
```

## Troubleshooting

### Common Issues

1. **Configuration not loading**
   - Check file permissions
   - Verify YAML syntax
   - Check environment variable `DOCFORGE_ENV`

2. **Validation errors**
   - Use `python scripts/config_manager.py validate` to check
   - Review schema requirements
   - Check for missing required fields

3. **Hot reload not working**
   - Ensure `watchdog` package is installed
   - Check if hot reload is enabled
   - Verify file permissions

### Debug Commands

```bash
# Check system health
python scripts/config_manager.py health

# Validate configuration
python scripts/config_manager.py validate

# Show current configuration
python scripts/config_manager.py show

# Check system information
python scripts/config_manager.py info
```

## Best Practices

1. **Use environment-specific configurations** for different deployment environments
2. **Keep sensitive data in environment variables** or secure local files
3. **Validate configuration** before deployment
4. **Use schema validation** to catch configuration errors early
5. **Document configuration changes** and their impact
6. **Regular backup** of configuration files
7. **Monitor configuration health** in production
8. **Use hot reload** only for non-critical settings

## Migration Guide

### From Old Settings System

1. **Install dependencies**:
   ```bash
   pip install watchdog pyyaml
   ```

2. **Initialize configuration**:
   ```bash
   python scripts/config_manager.py init
   ```

3. **Update imports**:
   ```python
   # Old
   from src.config.settings import settings
   
   # New
   from src.config.settings import get_settings
   settings = get_settings()
   ```

4. **Migrate configuration values** to new YAML files

5. **Update environment variables** to use new naming conventions

6. **Test configuration** with validation tools