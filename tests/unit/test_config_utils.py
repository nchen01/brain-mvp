"""Tests for configuration utilities."""

import pytest
import tempfile
import json
import yaml
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.config.utils import (
    setup_config_from_env, create_default_config_files,
    validate_config_files, export_config_documentation,
    backup_config, restore_config_from_backup,
    get_config_health_check
)
from src.config.config_manager import ConfigManager, Environment


class TestConfigUtils:
    """Test configuration utility functions."""
    
    def test_setup_config_from_env(self):
        """Test setting up configuration from environment."""
        with patch.dict(os.environ, {"DOCFORGE_ENV": "production"}):
            config_manager = setup_config_from_env()
            
            assert isinstance(config_manager, ConfigManager)
            assert config_manager.environment == Environment.PRODUCTION
            assert len(config_manager.validation_schemas) > 0
            assert len(config_manager.sensitive_keys) > 0
    
    def test_create_default_config_files(self):
        """Test creating default configuration files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            create_default_config_files(config_dir=temp_dir)
            
            config_path = Path(temp_dir)
            
            # Check that files were created
            assert (config_path / "base.yaml").exists()
            assert (config_path / "development.yaml").exists()
            assert (config_path / "production.yaml").exists()
            assert (config_path / "testing.yaml").exists()
            
            # Check that files contain valid YAML
            with open(config_path / "base.yaml", 'r') as f:
                base_config = yaml.safe_load(f)
                assert isinstance(base_config, dict)
                assert "app" in base_config
    
    def test_create_default_config_files_force(self):
        """Test creating default config files with force option."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir)
            
            # Create existing file
            existing_file = config_path / "base.yaml"
            existing_file.parent.mkdir(parents=True, exist_ok=True)
            existing_file.write_text("existing: content")
            
            # Create without force - should not overwrite
            create_default_config_files(config_dir=temp_dir, force=False)
            content = existing_file.read_text()
            assert "existing: content" in content
            
            # Create with force - should overwrite
            create_default_config_files(config_dir=temp_dir, force=True)
            content = existing_file.read_text()
            assert "existing: content" not in content
    
    def test_validate_config_files_valid(self):
        """Test validating valid configuration files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir)
            
            # Create valid config file
            config_file = config_path / "test.yaml"
            config_data = {
                "app": {"name": "TestApp", "debug": True},
                "database": {"host": "localhost", "port": 5432}
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            result = validate_config_files(config_dir=temp_dir)
            
            assert result["valid"] is True
            assert len(result["errors"]) == 0
            assert str(config_file) in result["files"]
            assert result["files"][str(config_file)]["valid_yaml"] is True
    
    def test_validate_config_files_invalid_yaml(self):
        """Test validating invalid YAML configuration files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir)
            
            # Create invalid YAML file
            config_file = config_path / "invalid.yaml"
            config_file.write_text("invalid: yaml: content: [")
            
            result = validate_config_files(config_dir=temp_dir)
            
            assert result["valid"] is False
            assert len(result["errors"]) > 0
            assert str(config_file) in result["files"]
            assert result["files"][str(config_file)]["valid_yaml"] is False
    
    def test_validate_config_files_missing_directory(self):
        """Test validating configuration files in missing directory."""
        result = validate_config_files(config_dir="/nonexistent/directory")
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "Configuration directory not found" in result["errors"][0]
    
    def test_export_config_documentation(self):
        """Test exporting configuration documentation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(config_dir=temp_dir, enable_hot_reload=False)
            config_manager.set("app.name", "TestApp")
            config_manager.set("database.host", "localhost")
            
            doc_file = Path(temp_dir) / "config_docs.md"
            
            export_config_documentation(config_manager, str(doc_file))
            
            assert doc_file.exists()
            
            content = doc_file.read_text()
            assert "# DocForge Configuration Documentation" in content
            assert "Configuration Overview" in content
            assert "Configuration Sources" in content
            assert "TestApp" in content
    
    def test_backup_config(self):
        """Test creating configuration backup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(config_dir=temp_dir, enable_hot_reload=False)
            config_manager.set("app.name", "TestApp")
            config_manager.set("database.host", "localhost")
            
            backup_dir = Path(temp_dir) / "backups"
            backup_file = backup_config(config_manager, str(backup_dir))
            
            assert backup_file is not None
            assert Path(backup_file).exists()
            
            # Check backup content
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            assert "timestamp" in backup_data
            assert "environment" in backup_data
            assert "configuration" in backup_data
            assert backup_data["configuration"]["app"]["name"] == "TestApp"
    
    def test_restore_config_from_backup(self):
        """Test restoring configuration from backup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create original config
            config_manager = ConfigManager(config_dir=temp_dir, enable_hot_reload=False)
            config_manager.set("app.name", "OriginalApp")
            config_manager.set("database.host", "original-host")
            
            # Create backup
            backup_file = backup_config(config_manager, temp_dir)
            
            # Modify config
            config_manager.set("app.name", "ModifiedApp")
            config_manager.set("database.host", "modified-host")
            
            # Restore from backup
            restore_config_from_backup(backup_file, config_manager)
            
            # Check restored values
            assert config_manager.get("app.name") == "OriginalApp"
            assert config_manager.get("database.host") == "original-host"
    
    def test_restore_config_invalid_backup(self):
        """Test restoring from invalid backup file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(config_dir=temp_dir, enable_hot_reload=False)
            
            # Create invalid backup file
            invalid_backup = Path(temp_dir) / "invalid_backup.json"
            invalid_backup.write_text('{"invalid": "backup"}')
            
            with pytest.raises(ValueError):
                restore_config_from_backup(str(invalid_backup), config_manager)
    
    def test_get_config_health_check_healthy(self):
        """Test configuration health check when healthy."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.config.utils.get_config') as mock_get_config:
                mock_config_manager = MagicMock()
                mock_config_manager.get_environment.return_value = Environment.DEVELOPMENT
                mock_config_manager.enable_hot_reload = True
                mock_config_manager.observer = MagicMock()
                mock_config_manager.config_sources = [MagicMock(), MagicMock()]
                mock_config_manager.validation_schemas = {"test": MagicMock()}
                mock_config_manager.sensitive_keys = {"secret1", "secret2"}
                mock_config_manager.config_dir = Path(temp_dir)
                
                mock_get_config.return_value = mock_config_manager
                
                health_info = get_config_health_check()
                
                assert health_info["status"] == "healthy"
                assert health_info["config_loaded"] is True
                assert health_info["environment"] == "development"
                assert health_info["hot_reload_active"] is True
                assert health_info["sources_loaded"] == 2
                assert health_info["validation_schemas"] == 1
                assert health_info["sensitive_keys_protected"] == 2
    
    def test_get_config_health_check_unhealthy(self):
        """Test configuration health check when unhealthy."""
        with patch('src.config.utils.get_config') as mock_get_config:
            mock_get_config.side_effect = Exception("Config error")
            
            health_info = get_config_health_check()
            
            assert health_info["status"] == "unhealthy"
            assert health_info["config_loaded"] is False
            assert "error" in health_info


class TestConfigFileOperations:
    """Test configuration file operations."""
    
    def test_yaml_file_operations(self):
        """Test YAML file creation and validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create config files
            create_default_config_files(config_dir=temp_dir)
            
            # Validate files
            result = validate_config_files(config_dir=temp_dir)
            
            assert result["valid"] is True
            
            # Check specific files
            config_path = Path(temp_dir)
            for filename in ["base.yaml", "development.yaml", "production.yaml", "testing.yaml"]:
                file_path = config_path / filename
                assert file_path.exists()
                
                # Validate YAML syntax
                with open(file_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                    assert isinstance(config_data, dict)
    
    def test_environment_specific_configs(self):
        """Test environment-specific configuration files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            create_default_config_files(config_dir=temp_dir)
            
            config_path = Path(temp_dir)
            
            # Check development config
            with open(config_path / "development.yaml", 'r') as f:
                dev_config = yaml.safe_load(f)
                assert dev_config["app"]["debug"] is True
            
            # Check production config
            with open(config_path / "production.yaml", 'r') as f:
                prod_config = yaml.safe_load(f)
                assert prod_config["app"]["debug"] is False
                assert prod_config["app"]["workers"] == 4
            
            # Check testing config
            with open(config_path / "testing.yaml", 'r') as f:
                test_config = yaml.safe_load(f)
                assert test_config["app"]["debug"] is True
                assert test_config["logging"]["level"] == "WARNING"


if __name__ == "__main__":
    pytest.main([__file__])