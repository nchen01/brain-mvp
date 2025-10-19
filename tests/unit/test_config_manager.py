"""Tests for configuration management system."""

import pytest
import tempfile
import json
import yaml
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.config.config_manager import (
    ConfigManager, Environment, ConfigFormat, ConfigSource,
    ConfigValidationError, ConfigSecurityError,
    initialize_config, get_config, get, set, get_section
)
from src.config.schemas import DatabaseConfig, StorageConfig, AppConfig


class TestConfigManager:
    """Test ConfigManager functionality."""
    
    def test_config_manager_initialization(self):
        """Test ConfigManager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(
                environment=Environment.DEVELOPMENT,
                config_dir=temp_dir,
                enable_hot_reload=False
            )
            
            assert config_manager.environment == Environment.DEVELOPMENT
            assert config_manager.config_dir == Path(temp_dir)
            assert config_manager.enable_hot_reload is False
            assert len(config_manager.config_sources) > 0
            assert isinstance(config_manager.config_data, dict)
    
    def test_environment_detection(self):
        """Test environment detection from environment variables."""
        with patch.dict(os.environ, {"DOCFORGE_ENV": "production"}):
            config_manager = ConfigManager()
            assert config_manager.environment == Environment.PRODUCTION
        
        with patch.dict(os.environ, {"ENV": "testing"}):
            config_manager = ConfigManager()
            assert config_manager.environment == Environment.TESTING
        
        # Test default
        with patch.dict(os.environ, {}, clear=True):
            config_manager = ConfigManager()
            assert config_manager.environment == Environment.DEVELOPMENT
    
    def test_add_config_source(self):
        """Test adding configuration sources."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(config_dir=temp_dir, enable_hot_reload=False)
            
            initial_count = len(config_manager.config_sources)
            
            config_manager.add_config_source(ConfigSource(
                path="test.yaml",
                format=ConfigFormat.YAML,
                priority=10
            ))
            
            assert len(config_manager.config_sources) == initial_count + 1
            
            # Check priority sorting
            priorities = [source.priority for source in config_manager.config_sources]
            assert priorities == sorted(priorities, reverse=True)
    
    def test_load_yaml_config(self):
        """Test loading YAML configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test.yaml"
            config_data = {
                "app": {"name": "TestApp", "debug": True},
                "database": {"host": "localhost", "port": 5432}
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            config_manager = ConfigManager(config_dir=temp_dir, enable_hot_reload=False)
            config_manager.add_config_source(ConfigSource(
                path=str(config_file),
                format=ConfigFormat.YAML,
                priority=1
            ))
            
            config_manager.load_config()
            
            assert config_manager.get("app.name") == "TestApp"
            assert config_manager.get("app.debug") is True
            assert config_manager.get("database.host") == "localhost"
            assert config_manager.get("database.port") == 5432
    
    def test_load_json_config(self):
        """Test loading JSON configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test.json"
            config_data = {
                "app": {"name": "TestApp", "version": "1.0.0"},
                "storage": {"base_path": "/tmp/storage"}
            }
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f)
            
            config_manager = ConfigManager(config_dir=temp_dir, enable_hot_reload=False)
            config_manager.add_config_source(ConfigSource(
                path=str(config_file),
                format=ConfigFormat.JSON,
                priority=1
            ))
            
            config_manager.load_config()
            
            assert config_manager.get("app.name") == "TestApp"
            assert config_manager.get("app.version") == "1.0.0"
            assert config_manager.get("storage.base_path") == "/tmp/storage"
    
    def test_load_env_config(self):
        """Test loading environment file configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_content = """
# Test environment file
APP_NAME=TestApp
APP_DEBUG=true
DATABASE_HOST=localhost
DATABASE_PORT=5432
NESTED_CONFIG_VALUE=test
"""
            
            with open(env_file, 'w') as f:
                f.write(env_content)
            
            config_manager = ConfigManager(config_dir=temp_dir, enable_hot_reload=False)
            config_manager.add_config_source(ConfigSource(
                path=str(env_file),
                format=ConfigFormat.ENV,
                priority=1
            ))
            
            config_manager.load_config()
            
            assert config_manager.get("APP_NAME") == "TestApp"
            assert config_manager.get("APP_DEBUG") is True
            assert config_manager.get("DATABASE_HOST") == "localhost"
            assert config_manager.get("DATABASE_PORT") == 5432
    
    def test_config_merging(self):
        """Test configuration merging from multiple sources."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Base config
            base_config = Path(temp_dir) / "base.yaml"
            base_data = {
                "app": {"name": "BaseApp", "debug": False, "version": "1.0.0"},
                "database": {"host": "localhost", "port": 5432}
            }
            with open(base_config, 'w') as f:
                yaml.dump(base_data, f)
            
            # Override config
            override_config = Path(temp_dir) / "override.yaml"
            override_data = {
                "app": {"debug": True, "new_setting": "test"},
                "database": {"host": "override-host"}
            }
            with open(override_config, 'w') as f:
                yaml.dump(override_data, f)
            
            config_manager = ConfigManager(config_dir=temp_dir, enable_hot_reload=False)
            config_manager.add_config_source(ConfigSource(
                path=str(base_config),
                format=ConfigFormat.YAML,
                priority=1
            ))
            config_manager.add_config_source(ConfigSource(
                path=str(override_config),
                format=ConfigFormat.YAML,
                priority=2
            ))
            
            config_manager.load_config()
            
            # Check merged values
            assert config_manager.get("app.name") == "BaseApp"  # From base
            assert config_manager.get("app.debug") is True  # Overridden
            assert config_manager.get("app.version") == "1.0.0"  # From base
            assert config_manager.get("app.new_setting") == "test"  # From override
            assert config_manager.get("database.host") == "override-host"  # Overridden
            assert config_manager.get("database.port") == 5432  # From base
    
    def test_get_and_set_config_values(self):
        """Test getting and setting configuration values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(config_dir=temp_dir, enable_hot_reload=False)
            
            # Test setting values
            config_manager.set("app.name", "TestApp")
            config_manager.set("database.host", "localhost")
            config_manager.set("nested.deep.value", "test")
            
            # Test getting values
            assert config_manager.get("app.name") == "TestApp"
            assert config_manager.get("database.host") == "localhost"
            assert config_manager.get("nested.deep.value") == "test"
            
            # Test default values
            assert config_manager.get("nonexistent.key", "default") == "default"
            assert config_manager.get("nonexistent.key") is None
    
    def test_get_section(self):
        """Test getting configuration sections."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(config_dir=temp_dir, enable_hot_reload=False)
            
            config_manager.set("app.name", "TestApp")
            config_manager.set("app.debug", True)
            config_manager.set("app.version", "1.0.0")
            
            app_section = config_manager.get_section("app")
            
            assert isinstance(app_section, dict)
            assert app_section["name"] == "TestApp"
            assert app_section["debug"] is True
            assert app_section["version"] == "1.0.0"
    
    def test_has_config_key(self):
        """Test checking if configuration key exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(config_dir=temp_dir, enable_hot_reload=False)
            
            config_manager.set("existing.key", "value")
            
            assert config_manager.has("existing.key") is True
            assert config_manager.has("nonexistent.key") is False
    
    def test_sensitive_key_masking(self):
        """Test sensitive key masking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(config_dir=temp_dir, enable_hot_reload=False)
            
            # Set sensitive values
            config_manager.set("database.password", "secret123")
            config_manager.set("api.key", "api_key_123")
            config_manager.set("normal.value", "not_secret")
            
            # Mark keys as sensitive
            config_manager.add_sensitive_key("database.password")
            config_manager.add_sensitive_key("api.key")
            
            # Get all config with masking
            all_config = config_manager.get_all(mask_sensitive=True)
            
            assert all_config["database"]["password"] == "***MASKED***"
            assert all_config["api"]["key"] == "***MASKED***"
            assert all_config["normal"]["value"] == "not_secret"
            
            # Get all config without masking
            all_config_unmasked = config_manager.get_all(mask_sensitive=False)
            
            assert all_config_unmasked["database"]["password"] == "secret123"
            assert all_config_unmasked["api"]["key"] == "api_key_123"
    
    def test_config_validation(self):
        """Test configuration validation with schemas."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(config_dir=temp_dir, enable_hot_reload=False)
            
            # Add validation schema
            config_manager.add_validation_schema("database", DatabaseConfig)
            
            # Valid configuration
            config_manager.set("database.host", "localhost")
            config_manager.set("database.port", 5432)
            config_manager.set("database.name", "testdb")
            config_manager.set("database.user", "testuser")
            config_manager.set("database.password", "testpass")
            
            # Should not raise exception
            config_manager._validate_config(config_manager.config_data)
            
            # Invalid configuration
            config_manager.set("database.port", "invalid_port")
            
            with pytest.raises(ConfigValidationError):
                config_manager._validate_config(config_manager.config_data)
    
    def test_config_info(self):
        """Test getting configuration information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(config_dir=temp_dir, enable_hot_reload=False)
            
            config_manager.set("test.key", "value")
            config_manager.add_sensitive_key("sensitive.key")
            config_manager.add_validation_schema("test", dict)
            
            info = config_manager.get_config_info()
            
            assert "environment" in info
            assert "config_dir" in info
            assert "hot_reload_enabled" in info
            assert "sources" in info
            assert "sensitive_keys_count" in info
            assert "validation_schemas_count" in info
            assert "total_config_keys" in info
            
            assert info["environment"] == config_manager.environment.value
            assert info["sensitive_keys_count"] == 1
            assert info["validation_schemas_count"] == 1


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_initialize_config(self):
        """Test initialize_config function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = initialize_config(
                environment=Environment.TESTING,
                config_dir=temp_dir,
                enable_hot_reload=False
            )
            
            assert isinstance(config_manager, ConfigManager)
            assert config_manager.environment == Environment.TESTING
    
    def test_get_config(self):
        """Test get_config function."""
        # Initialize config first
        with tempfile.TemporaryDirectory() as temp_dir:
            initialize_config(config_dir=temp_dir, enable_hot_reload=False)
            
            config_manager = get_config()
            assert isinstance(config_manager, ConfigManager)
    
    def test_convenience_get_set(self):
        """Test convenience get and set functions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            initialize_config(config_dir=temp_dir, enable_hot_reload=False)
            
            # Test set
            set("test.key", "test_value")
            
            # Test get
            value = get("test.key")
            assert value == "test_value"
            
            # Test get with default
            default_value = get("nonexistent.key", "default")
            assert default_value == "default"
    
    def test_convenience_get_section(self):
        """Test convenience get_section function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            initialize_config(config_dir=temp_dir, enable_hot_reload=False)
            
            set("section.key1", "value1")
            set("section.key2", "value2")
            
            section = get_section("section")
            
            assert isinstance(section, dict)
            assert section["key1"] == "value1"
            assert section["key2"] == "value2"


class TestConfigFileWatcher:
    """Test configuration file watching for hot reload."""
    
    @pytest.mark.skipif(os.name == 'nt', reason="File watching tests may be flaky on Windows")
    def test_hot_reload_disabled(self):
        """Test that hot reload can be disabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(
                config_dir=temp_dir,
                enable_hot_reload=False
            )
            
            assert config_manager.observer is None
            assert config_manager.file_watcher is None


if __name__ == "__main__":
    pytest.main([__file__])