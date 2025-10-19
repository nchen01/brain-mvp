"""Production-ready configuration management system."""

import os
import json
import yaml
from typing import Dict, Any, Optional, List, Union, Type, Set
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime
import threading
import time
from builtins import set as builtin_set

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    Observer = None
    FileSystemEventHandler = object
    WATCHDOG_AVAILABLE = False

try:
    from pydantic import BaseModel, ValidationError, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    BaseModel = object
    ValidationError = Exception
    Field = lambda **kwargs: None
    PYDANTIC_AVAILABLE = False


class Environment(str, Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigFormat(str, Enum):
    """Configuration file formats."""
    JSON = "json"
    YAML = "yaml"
    ENV = "env"


@dataclass
class ConfigSource:
    """Configuration source definition."""
    path: str
    format: ConfigFormat
    required: bool = True
    environment_specific: bool = False
    hot_reload: bool = False
    priority: int = 0  # Higher priority overrides lower


class ConfigValidationError(Exception):
    """Configuration validation error."""
    pass


class ConfigSecurityError(Exception):
    """Configuration security error."""
    pass


class ConfigFileWatcher(FileSystemEventHandler):
    """File system watcher for configuration hot-reloading."""
    
    def __init__(self, config_manager, watched_files: List[str]):
        """Initialize file watcher."""
        self.config_manager = config_manager
        self.watched_files = set(watched_files)
        self.logger = logging.getLogger(__name__)
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and event.src_path in self.watched_files:
            self.logger.info(f"Configuration file modified: {event.src_path}")
            try:
                self.config_manager.reload_config()
            except Exception as e:
                self.logger.error(f"Failed to reload configuration: {e}")


class ConfigManager:
    """Centralized configuration management system."""
    
    def __init__(
        self,
        environment: Optional[Environment] = None,
        config_dir: str = "config",
        enable_hot_reload: bool = False
    ):
        """Initialize configuration manager."""
        self.environment = environment or self._detect_environment()
        self.config_dir = Path(config_dir)
        self.enable_hot_reload = enable_hot_reload
        
        self.config_sources: List[ConfigSource] = []
        self.config_data: Dict[str, Any] = {}
        self.sensitive_keys: Set[str] = builtin_set()
        self.validation_schemas: Dict[str, Any] = {}
        
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        
        # File watcher for hot reload
        self.observer = None
        self.file_watcher = None
        
        # Load default configuration sources
        self._setup_default_sources()
        
        # Load initial configuration
        self.load_config()
        
        # Setup hot reload if enabled
        if self.enable_hot_reload:
            self._setup_hot_reload()
    
    def _detect_environment(self) -> Environment:
        """Detect current environment from environment variables."""
        env_name = os.getenv("DOCFORGE_ENV", os.getenv("ENV", "development")).lower()
        
        env_mapping = {
            "dev": Environment.DEVELOPMENT,
            "development": Environment.DEVELOPMENT,
            "test": Environment.TESTING,
            "testing": Environment.TESTING,
            "stage": Environment.STAGING,
            "staging": Environment.STAGING,
            "prod": Environment.PRODUCTION,
            "production": Environment.PRODUCTION
        }
        
        return env_mapping.get(env_name, Environment.DEVELOPMENT)
    
    def _setup_default_sources(self):
        """Setup default configuration sources."""
        # Base configuration
        self.add_config_source(ConfigSource(
            path=str(self.config_dir / "base.yaml"),
            format=ConfigFormat.YAML,
            required=True,
            priority=1
        ))
        
        # Environment-specific configuration
        env_config_path = str(self.config_dir / f"{self.environment.value}.yaml")
        self.add_config_source(ConfigSource(
            path=env_config_path,
            format=ConfigFormat.YAML,
            required=False,
            environment_specific=True,
            hot_reload=True,
            priority=2
        ))
        
        # Local overrides (not in version control)
        self.add_config_source(ConfigSource(
            path=str(self.config_dir / "local.yaml"),
            format=ConfigFormat.YAML,
            required=False,
            hot_reload=True,
            priority=3
        ))
        
        # Environment variables
        self.add_config_source(ConfigSource(
            path=".env",
            format=ConfigFormat.ENV,
            required=False,
            priority=4
        ))
    
    def add_config_source(self, source: ConfigSource):
        """Add a configuration source."""
        with self._lock:
            self.config_sources.append(source)
            # Sort by priority (higher priority first)
            self.config_sources.sort(key=lambda x: x.priority, reverse=True)
    
    def add_sensitive_key(self, key: str):
        """Mark a configuration key as sensitive."""
        self.sensitive_keys.add(key)
    
    def add_validation_schema(self, section: str, schema: Any):
        """Add validation schema for a configuration section."""
        self.validation_schemas[section] = schema
    
    def load_config(self, config_dir: Optional[str] = None):
        """Load configuration from all sources.
        
        Args:
            config_dir: Optional directory to load configuration from.
                       If provided, adds this directory as a config source.
        """
        with self._lock:
            # If config_dir is provided, add it as a config source
            if config_dir:
                self.add_config_source(config_dir, ConfigFormat.JSON, required=False)
            new_config = {}
            
            # Load from sources in priority order (lowest to highest)
            for source in reversed(self.config_sources):
                try:
                    source_config = self._load_config_source(source)
                    if source_config:
                        new_config = self._merge_config(new_config, source_config)
                        self.logger.debug(f"Loaded configuration from {source.path}")
                except Exception as e:
                    if source.required:
                        raise ConfigValidationError(f"Failed to load required config {source.path}: {e}")
                    else:
                        self.logger.warning(f"Failed to load optional config {source.path}: {e}")
            
            # Validate configuration
            self._validate_config(new_config)
            
            # Update configuration
            self.config_data = new_config
            
            self.logger.info(f"Configuration loaded successfully for environment: {self.environment.value}")
    
    def _load_config_source(self, source: ConfigSource) -> Optional[Dict[str, Any]]:
        """Load configuration from a single source."""
        path = Path(source.path)
        
        if not path.exists():
            return None
        
        try:
            if source.format == ConfigFormat.JSON:
                with open(path, 'r') as f:
                    return json.load(f)
            
            elif source.format == ConfigFormat.YAML:
                with open(path, 'r') as f:
                    return yaml.safe_load(f)
            
            elif source.format == ConfigFormat.ENV:
                return self._load_env_file(path)
            
            else:
                raise ConfigValidationError(f"Unsupported config format: {source.format}")
        
        except Exception as e:
            raise ConfigValidationError(f"Failed to parse {source.path}: {e}")
    
    def _load_env_file(self, path: Path) -> Dict[str, Any]:
        """Load environment variables from .env file."""
        config = {}
        
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        
                        # Convert to nested dict using dot notation
                        self._set_nested_value(config, key, value)
        
        return config
    
    def _set_nested_value(self, config: Dict[str, Any], key: str, value: str):
        """Set nested configuration value using dot notation."""
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Try to convert value to appropriate type
        final_key = keys[-1]
        try:
            # Try boolean
            if value.lower() in ('true', 'false'):
                current[final_key] = value.lower() == 'true'
            # Try integer
            elif value.isdigit():
                current[final_key] = int(value)
            # Try float
            elif '.' in value and value.replace('.', '').isdigit():
                current[final_key] = float(value)
            else:
                current[final_key] = value
        except ValueError:
            current[final_key] = value
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _validate_config(self, config: Dict[str, Any]):
        """Validate configuration against schemas."""
        if not PYDANTIC_AVAILABLE:
            self.logger.warning("Pydantic not available, skipping schema validation")
            return
        
        for section, schema in self.validation_schemas.items():
            if section in config:
                try:
                    if hasattr(schema, 'parse_obj'):
                        schema.parse_obj(config[section])
                    elif callable(schema):
                        schema(config[section])
                except ValidationError as e:
                    raise ConfigValidationError(f"Validation failed for section '{section}': {e}")
    
    def _setup_hot_reload(self):
        """Setup hot reload for configuration files."""
        if not self.enable_hot_reload or not WATCHDOG_AVAILABLE:
            if not WATCHDOG_AVAILABLE and self.enable_hot_reload:
                self.logger.warning("Hot reload requested but watchdog not available. Install with: pip install watchdog")
            return
        
        watched_files = []
        for source in self.config_sources:
            if source.hot_reload and Path(source.path).exists():
                watched_files.append(str(Path(source.path).absolute()))
        
        if watched_files:
            self.file_watcher = ConfigFileWatcher(self, watched_files)
            self.observer = Observer()
            
            # Watch config directory
            if self.config_dir.exists():
                self.observer.schedule(self.file_watcher, str(self.config_dir), recursive=False)
            
            # Watch individual files outside config directory
            for file_path in watched_files:
                file_dir = str(Path(file_path).parent)
                if file_dir != str(self.config_dir):
                    self.observer.schedule(self.file_watcher, file_dir, recursive=False)
            
            self.observer.start()
            self.logger.info("Hot reload enabled for configuration files")
    
    def reload_config(self):
        """Reload configuration from all sources."""
        self.logger.info("Reloading configuration...")
        self.load_config()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
        with self._lock:
            keys = key.split('.')
            current = self.config_data
            
            try:
                for k in keys:
                    current = current[k]
                return current
            except (KeyError, TypeError):
                return default
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration data."""
        with self._lock:
            return self.config_data.copy()
    
    def set(self, key: str, value: Any, persist: bool = False):
        """Set configuration value using dot notation."""
        with self._lock:
            keys = key.split('.')
            current = self.config_data
            
            # Navigate to parent
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            # Set value
            current[keys[-1]] = value
            
            if persist:
                self._persist_config_change(key, value)
    
    def _persist_config_change(self, key: str, value: Any):
        """Persist configuration change to local config file."""
        local_config_path = self.config_dir / "local.yaml"
        
        # Load existing local config
        local_config = {}
        if local_config_path.exists():
            try:
                with open(local_config_path, 'r') as f:
                    local_config = yaml.safe_load(f) or {}
            except Exception as e:
                self.logger.warning(f"Failed to load local config for persistence: {e}")
        
        # Set new value
        self._set_nested_dict_value(local_config, key, value)
        
        # Save local config
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(local_config_path, 'w') as f:
                yaml.dump(local_config, f, default_flow_style=False)
            self.logger.info(f"Persisted configuration change: {key}")
        except Exception as e:
            self.logger.error(f"Failed to persist configuration change: {e}")
    
    def _set_nested_dict_value(self, config: Dict[str, Any], key: str, value: Any):
        """Set nested dictionary value using dot notation."""
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section."""
        return self.get(section, {})
    
    def has(self, key: str) -> bool:
        """Check if configuration key exists."""
        return self.get(key) is not None
    
    def get_all(self, mask_sensitive: bool = True) -> Dict[str, Any]:
        """Get all configuration data."""
        with self._lock:
            if not mask_sensitive:
                return self.config_data.copy()
            
            # Mask sensitive values
            masked_config = self._mask_sensitive_values(self.config_data.copy())
            return masked_config
    
    def _mask_sensitive_values(self, config: Dict[str, Any], path: str = "") -> Dict[str, Any]:
        """Mask sensitive configuration values."""
        masked = {}
        
        for key, value in config.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, dict):
                masked[key] = self._mask_sensitive_values(value, current_path)
            elif current_path in self.sensitive_keys or any(
                sensitive_key in current_path.lower() 
                for sensitive_key in ['password', 'secret', 'key', 'token', 'credential']
            ):
                masked[key] = "***MASKED***"
            else:
                masked[key] = value
        
        return masked
    
    def get_environment(self) -> Environment:
        """Get current environment."""
        return self.environment
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get configuration system information."""
        with self._lock:
            sources_info = []
            for source in self.config_sources:
                sources_info.append({
                    'path': source.path,
                    'format': source.format.value,
                    'required': source.required,
                    'environment_specific': source.environment_specific,
                    'hot_reload': source.hot_reload,
                    'priority': source.priority,
                    'exists': Path(source.path).exists()
                })
            
            return {
                'environment': self.environment.value,
                'config_dir': str(self.config_dir),
                'hot_reload_enabled': self.enable_hot_reload,
                'sources': sources_info,
                'sensitive_keys_count': len(self.sensitive_keys),
                'validation_schemas_count': len(self.validation_schemas),
                'total_config_keys': len(self._flatten_dict(self.config_data))
            }
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def shutdown(self):
        """Shutdown configuration manager."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.logger.info("Configuration hot reload stopped")


# Global configuration manager instance
config_manager: Optional[ConfigManager] = None


def initialize_config(
    environment: Optional[Environment] = None,
    config_dir: str = "config",
    enable_hot_reload: bool = False
) -> ConfigManager:
    """Initialize global configuration manager."""
    global config_manager
    
    if config_manager is not None:
        config_manager.shutdown()
    
    config_manager = ConfigManager(
        environment=environment,
        config_dir=config_dir,
        enable_hot_reload=enable_hot_reload
    )
    
    return config_manager


def get_config() -> ConfigManager:
    """Get global configuration manager."""
    global config_manager
    
    if config_manager is None:
        config_manager = initialize_config()
    
    return config_manager


# Convenience functions
def get(key: str, default: Any = None) -> Any:
    """Get configuration value."""
    return get_config().get(key, default)


def set(key: str, value: Any, persist: bool = False):
    """Set configuration value."""
    get_config().set(key, value, persist)


def get_section(section: str) -> Dict[str, Any]:
    """Get configuration section."""
    return get_config().get_section(section)


def has(key: str) -> bool:
    """Check if configuration key exists."""
    return get_config().has(key)


def is_production() -> bool:
    """Check if running in production."""
    return get_config().is_production()


def is_development() -> bool:
    """Check if running in development."""
    return get_config().is_development()