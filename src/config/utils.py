"""Configuration utilities and helper functions."""

import os
import json
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
from datetime import datetime

from .config_manager import ConfigManager, Environment
from .schemas import SCHEMA_REGISTRY, get_default_config


logger = logging.getLogger(__name__)


def setup_config_from_env() -> ConfigManager:
    """Setup configuration manager from environment variables."""
    # Detect environment
    env_name = os.getenv("DOCFORGE_ENV", "development")
    try:
        environment = Environment(env_name.lower())
    except ValueError:
        logger.warning(f"Unknown environment '{env_name}', defaulting to development")
        environment = Environment.DEVELOPMENT
    
    # Determine config directory
    config_dir = os.getenv("CONFIG_DIR", "config")
    
    # Enable hot reload in development
    enable_hot_reload = environment == Environment.DEVELOPMENT
    
    # Initialize config manager
    config_manager = ConfigManager(
        environment=environment,
        config_dir=config_dir,
        enable_hot_reload=enable_hot_reload
    )
    
    # Add validation schemas
    for section, schema in SCHEMA_REGISTRY.items():
        config_manager.add_validation_schema(section, schema)
    
    # Mark sensitive keys
    sensitive_keys = [
        "database.password",
        "security.secret_key",
        "external_services.openai_api_key",
        "external_services.anthropic_api_key",
        "external_services.huggingface_token",
        "cache.redis_url"
    ]
    
    for key in sensitive_keys:
        config_manager.add_sensitive_key(key)
    
    return config_manager


def create_default_config_files(config_dir: str = "config", force: bool = False):
    """Create default configuration files if they don't exist."""
    config_path = Path(config_dir)
    config_path.mkdir(parents=True, exist_ok=True)
    
    # Create simple default configurations without strict validation
    files_to_create = [
        ("base.yaml", {
            "app": {
                "name": "DocForge",
                "version": "1.0.0",
                "debug": False,
                "host": "0.0.0.0",
                "port": 8000,
                "workers": 1
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "docforge",
                "user": "docforge_user",
                "password": "change-me",
                "pool_size": 10
            },
            "storage": {
                "base_path": "storage",
                "max_file_size": 104857600,
                "allowed_extensions": [".pdf", ".txt", ".docx", ".md"]
            },
            "processing": {
                "max_workers": 4,
                "timeout": 300,
                "chunk_size": 1000,
                "chunk_overlap": 200
            },
            "rag": {
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "embedding_dimension": 384,
                "vector_store_type": "faiss",
                "similarity_threshold": 0.7,
                "max_results": 10
            },
            "security": {
                "secret_key": "change-me-in-production-must-be-at-least-32-chars",
                "jwt_algorithm": "HS256",
                "jwt_expiration": 3600
            },
            "logging": {
                "level": "INFO",
                "format": "detailed",
                "file_enabled": True,
                "console_enabled": True
            }
        }),
        ("development.yaml", {
            "app": {"debug": True},
            "database": {"echo": True, "name": "docforge_dev"},
            "logging": {"level": "DEBUG"}
        }),
        ("production.yaml", {
            "app": {"debug": False, "workers": 4},
            "logging": {"level": "INFO", "format": "json"},
            "security": {"enable_2fa": True}
        }),
        ("testing.yaml", {
            "app": {"debug": True},
            "database": {"name": "docforge_test"},
            "logging": {"level": "WARNING", "file_enabled": False}
        })
    ]
    
    for filename, config_data in files_to_create:
        file_path = config_path / filename
        
        if not file_path.exists() or force:
            try:
                with open(file_path, 'w') as f:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                logger.info(f"Created configuration file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to create configuration file {file_path}: {e}")


def validate_config_files(config_dir: str = "config") -> Dict[str, Any]:
    """Validate all configuration files in the directory."""
    config_path = Path(config_dir)
    validation_results = {
        "valid": True,
        "files": {},
        "errors": [],
        "warnings": []
    }
    
    if not config_path.exists():
        validation_results["valid"] = False
        validation_results["errors"].append(f"Configuration directory not found: {config_dir}")
        return validation_results
    
    # Find all YAML configuration files
    config_files = list(config_path.glob("*.yaml")) + list(config_path.glob("*.yml"))
    
    for config_file in config_files:
        file_result = {
            "exists": True,
            "valid_yaml": False,
            "schema_valid": False,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Test YAML parsing
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            file_result["valid_yaml"] = True
            
            # Validate against schemas if available
            if config_data:
                schema_errors = []
                for section, section_data in config_data.items():
                    if section in SCHEMA_REGISTRY and isinstance(section_data, dict):
                        try:
                            schema = SCHEMA_REGISTRY[section]
                            if hasattr(schema, 'model_validate'):
                                schema.model_validate(section_data)
                            elif hasattr(schema, 'parse_obj'):
                                schema.parse_obj(section_data)
                        except Exception as e:
                            schema_errors.append(f"Schema validation failed for section '{section}': {e}")
                
                if not schema_errors:
                    file_result["schema_valid"] = True
                else:
                    file_result["errors"].extend(schema_errors)
                    validation_results["valid"] = False
            
        except yaml.YAMLError as e:
            file_result["errors"].append(f"YAML parsing error: {e}")
            validation_results["valid"] = False
        except Exception as e:
            file_result["errors"].append(f"File reading error: {e}")
            validation_results["valid"] = False
        
        validation_results["files"][str(config_file)] = file_result
        
        # Collect errors and warnings
        validation_results["errors"].extend([
            f"{config_file.name}: {error}" for error in file_result["errors"]
        ])
        validation_results["warnings"].extend([
            f"{config_file.name}: {warning}" for warning in file_result["warnings"]
        ])
    
    return validation_results


def export_config_documentation(config_manager: ConfigManager, output_file: str = "config_documentation.md"):
    """Export configuration documentation to markdown file."""
    doc_content = []
    
    # Header
    doc_content.append("# DocForge Configuration Documentation")
    doc_content.append(f"Generated on: {datetime.now().isoformat()}")
    doc_content.append(f"Environment: {config_manager.get_environment().value}")
    doc_content.append("")
    
    # Configuration overview
    config_info = config_manager.get_config_info()
    doc_content.append("## Configuration Overview")
    doc_content.append(f"- **Environment**: {config_info['environment']}")
    doc_content.append(f"- **Config Directory**: {config_info['config_dir']}")
    doc_content.append(f"- **Hot Reload**: {config_info['hot_reload_enabled']}")
    doc_content.append(f"- **Total Configuration Keys**: {config_info['total_config_keys']}")
    doc_content.append("")
    
    # Configuration sources
    doc_content.append("## Configuration Sources")
    doc_content.append("| Path | Format | Required | Environment Specific | Hot Reload | Priority | Exists |")
    doc_content.append("|------|--------|----------|---------------------|------------|----------|--------|")
    
    for source in config_info['sources']:
        doc_content.append(
            f"| {source['path']} | {source['format']} | {source['required']} | "
            f"{source['environment_specific']} | {source['hot_reload']} | "
            f"{source['priority']} | {source['exists']} |"
        )
    doc_content.append("")
    
    # Configuration sections
    doc_content.append("## Configuration Sections")
    
    all_config = config_manager.get_all(mask_sensitive=True)
    
    for section_name, section_data in all_config.items():
        doc_content.append(f"### {section_name.title()}")
        
        # Add schema information if available
        if section_name in SCHEMA_REGISTRY:
            schema = SCHEMA_REGISTRY[section_name]
            if hasattr(schema, '__doc__') and schema.__doc__:
                doc_content.append(f"{schema.__doc__.strip()}")
            doc_content.append("")
        
        # Add configuration values
        if isinstance(section_data, dict):
            doc_content.append("| Key | Value | Type |")
            doc_content.append("|-----|-------|------|")
            
            for key, value in section_data.items():
                value_str = str(value) if not isinstance(value, dict) else "{ ... }"
                value_type = type(value).__name__
                doc_content.append(f"| {key} | {value_str} | {value_type} |")
        else:
            doc_content.append(f"Value: `{section_data}` (Type: {type(section_data).__name__})")
        
        doc_content.append("")
    
    # Environment variables
    doc_content.append("## Environment Variables")
    doc_content.append("The following environment variables can be used to override configuration:")
    doc_content.append("")
    
    env_vars = [
        ("DOCFORGE_ENV", "Environment name (development, testing, production)"),
        ("CONFIG_DIR", "Configuration directory path"),
        ("DATABASE_HOST", "Database host"),
        ("DATABASE_PORT", "Database port"),
        ("DATABASE_NAME", "Database name"),
        ("DATABASE_USER", "Database user"),
        ("DATABASE_PASSWORD", "Database password"),
        ("SECRET_KEY", "Application secret key"),
        ("OPENAI_API_KEY", "OpenAI API key"),
        ("REDIS_URL", "Redis connection URL"),
        ("LOG_LEVEL", "Logging level"),
        ("DEBUG", "Debug mode (true/false)")
    ]
    
    doc_content.append("| Variable | Description |")
    doc_content.append("|----------|-------------|")
    
    for var_name, description in env_vars:
        doc_content.append(f"| {var_name} | {description} |")
    
    doc_content.append("")
    
    # Security considerations
    doc_content.append("## Security Considerations")
    doc_content.append("- Never commit sensitive configuration values to version control")
    doc_content.append("- Use environment variables or local configuration files for secrets")
    doc_content.append("- Ensure proper file permissions on configuration files")
    doc_content.append("- Regularly rotate API keys and secrets")
    doc_content.append("- Use strong, unique secret keys in production")
    doc_content.append("")
    
    # Write documentation file
    try:
        with open(output_file, 'w') as f:
            f.write('\n'.join(doc_content))
        logger.info(f"Configuration documentation exported to: {output_file}")
    except Exception as e:
        logger.error(f"Failed to export configuration documentation: {e}")


def backup_config(config_manager: ConfigManager, backup_dir: str = "config_backups"):
    """Create a backup of current configuration."""
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_path / f"config_backup_{timestamp}.json"
    
    try:
        # Get all configuration (masked for security)
        config_data = config_manager.get_all(mask_sensitive=True)
        
        # Add metadata
        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "environment": config_manager.get_environment().value,
            "config_info": config_manager.get_config_info(),
            "configuration": config_data
        }
        
        # Write backup file
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        logger.info(f"Configuration backup created: {backup_file}")
        return str(backup_file)
        
    except Exception as e:
        logger.error(f"Failed to create configuration backup: {e}")
        return None


def restore_config_from_backup(backup_file: str, config_manager: ConfigManager):
    """Restore configuration from backup file."""
    try:
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        if "configuration" not in backup_data:
            raise ValueError("Invalid backup file format")
        
        # Restore configuration
        config_data = backup_data["configuration"]
        
        for section, section_data in config_data.items():
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    config_key = f"{section}.{key}"
                    config_manager.set(config_key, value, persist=True)
        
        logger.info(f"Configuration restored from backup: {backup_file}")
        
    except Exception as e:
        logger.error(f"Failed to restore configuration from backup: {e}")
        raise


def get_config_health_check() -> Dict[str, Any]:
    """Get configuration system health check information."""
    try:
        from .config_manager import get_config
        config_manager = get_config()
        
        health_info = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "environment": config_manager.get_environment().value,
            "config_loaded": True,
            "hot_reload_active": config_manager.enable_hot_reload and config_manager.observer is not None,
            "sources_loaded": len(config_manager.config_sources),
            "validation_schemas": len(config_manager.validation_schemas),
            "sensitive_keys_protected": len(config_manager.sensitive_keys)
        }
        
        # Check configuration directory
        config_dir = Path(config_manager.config_dir)
        health_info["config_dir_exists"] = config_dir.exists()
        health_info["config_dir_writable"] = os.access(config_dir, os.W_OK) if config_dir.exists() else False
        
        return health_info
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "config_loaded": False
        }