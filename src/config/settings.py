"""Production-ready configuration management system."""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseConfig(BaseModel):
    """Database configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    url: str = Field(default="sqlite:///data/brain_mvp.db", description="Database connection URL")
    max_connections: int = Field(default=10, ge=1, le=100, description="Maximum database connections")
    connection_timeout: int = Field(default=30, ge=5, le=300, description="Connection timeout in seconds")
    query_timeout: int = Field(default=60, ge=10, le=600, description="Query timeout in seconds")
    enable_connection_pooling: bool = Field(default=True, description="Enable connection pooling")
    pool_size: int = Field(default=5, ge=1, le=50, description="Connection pool size")
    pool_overflow: int = Field(default=10, ge=0, le=50, description="Connection pool overflow")
    enable_query_logging: bool = Field(default=False, description="Enable SQL query logging")
    
    @field_validator('url')
    @classmethod
    def validate_database_url(cls, v):
        """Validate database URL format."""
        if not v or not isinstance(v, str):
            raise ValueError("Database URL must be a non-empty string")
        
        # Basic validation for common database URLs
        valid_prefixes = ['sqlite:///', 'postgresql://', 'mysql://', 'mongodb://']
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            logger.warning(f"Database URL may not be valid: {v}")
        
        return v


class StorageConfig(BaseModel):
    """Storage configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    base_dir: str = Field(default="data", description="Base directory for all storage")
    uploads_dir: str = Field(default="data/uploads", description="Directory for uploaded files")
    processed_dir: str = Field(default="data/processed", description="Directory for processed files")
    cache_dir: str = Field(default="data/cache", description="Directory for cache files")
    logs_dir: str = Field(default="logs", description="Directory for log files")
    temp_dir: str = Field(default="data/temp", description="Directory for temporary files")
    
    # Storage limits
    max_file_size_mb: int = Field(default=100, ge=1, le=1000, description="Maximum file size in MB")
    max_storage_gb: int = Field(default=10, ge=1, le=1000, description="Maximum total storage in GB")
    cleanup_temp_files_hours: int = Field(default=24, ge=1, le=168, description="Hours before temp file cleanup")
    
    # Storage features
    enable_compression: bool = Field(default=True, description="Enable file compression")
    enable_encryption: bool = Field(default=False, description="Enable file encryption")
    backup_enabled: bool = Field(default=True, description="Enable automatic backups")
    backup_retention_days: int = Field(default=30, ge=1, le=365, description="Backup retention in days")


class LightRAGConfig(BaseModel):
    """LightRAG configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    working_dir: str = Field(default="data/lightrag", description="LightRAG working directory")
    vector_db_path: str = Field(default="data/lightrag/vector_db", description="Vector database path")
    
    # Model configurations
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="Embedding model name")
    embedding_dim: int = Field(default=384, ge=128, le=2048, description="Embedding dimension")
    
    # Processing configurations
    chunk_token_size: int = Field(default=1200, ge=100, le=4000, description="Chunk size in tokens")
    chunk_overlap_token_size: int = Field(default=100, ge=0, le=500, description="Chunk overlap in tokens")
    
    # Performance configurations
    batch_size: int = Field(default=32, ge=1, le=128, description="Batch size for processing")
    max_async_workers: int = Field(default=4, ge=1, le=16, description="Maximum async workers")
    
    # Cache configurations
    enable_cache: bool = Field(default=True, description="Enable caching")
    cache_size_mb: int = Field(default=512, ge=64, le=4096, description="Cache size in MB")


class MinerUConfig(BaseModel):
    """MinerU PDF processor configuration (API-based)."""
    model_config = ConfigDict(str_strip_whitespace=True)

    # API configuration
    api_url: str = Field(default="http://mineru-api:8080", description="MinerU API service URL")
    api_enabled: bool = Field(default=True, description="Enable MinerU API for PDF processing")
    api_timeout: int = Field(default=300, ge=30, le=1800, description="API request timeout in seconds")

    # Feature flags
    extract_images: bool = Field(default=True, description="Extract images from PDFs")
    extract_tables: bool = Field(default=True, description="Extract tables from PDFs")
    ocr_enabled: bool = Field(default=True, description="Enable OCR for scanned documents")

    # Language settings
    language: str = Field(default="auto", description="Document language or 'auto' for detection")

    # Output settings
    output_dir: str = Field(default="./data/mineru_output", description="Directory for MinerU output files")

    # Fallback settings
    enable_fallback: bool = Field(default=True, description="Enable fallback to AdvancedPDFProcessor if MinerU API fails")


class SummarizationConfig(BaseModel):
    """Configuration for the SummarizationService stage."""
    model_config = ConfigDict(str_strip_whitespace=True)

    enabled: bool = Field(default=False, description="Enable document and section summarization")
    mode: str = Field(default="llm", description="Summarization mode: 'llm' or 'extractive'")
    model_name: str = Field(
        default="claude-haiku-4-5-20251001",
        description="LLM model identifier (used when mode='llm')",
    )
    api_provider: str = Field(
        default="anthropic",
        description="LLM API provider: 'anthropic' (default) or 'openai'",
    )
    max_doc_tokens_for_direct_summary: int = Field(
        default=8000,
        ge=1000,
        le=128000,
        description="Max estimated doc tokens before switching to headings+excerpt strategy",
    )
    section_summary_min_tokens: int = Field(
        default=200,
        ge=50,
        le=2000,
        description="Min estimated section tokens to trigger a section-level summary",
    )


class ProcessingConfig(BaseModel):
    """Document processing configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)

    # Processing limits
    max_concurrent_documents: int = Field(default=5, ge=1, le=20, description="Max concurrent document processing")
    processing_timeout_minutes: int = Field(default=30, ge=5, le=120, description="Processing timeout in minutes")

    # Processor configurations
    enable_mineru: bool = Field(default=True, description="Enable MinerU PDF processor")
    enable_markitdown: bool = Field(default=True, description="Enable MarkItDown processor")

    # MinerU specific configuration
    mineru: MinerUConfig = Field(default_factory=MinerUConfig, description="MinerU processor settings")

    # Quality settings
    min_confidence_score: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence score")
    enable_quality_checks: bool = Field(default=True, description="Enable quality validation")

    # Post-processing settings
    enable_chunking: bool = Field(default=True, description="Enable document chunking")
    enable_abbreviation_expansion: bool = Field(default=True, description="Enable abbreviation expansion")
    default_chunk_size: int = Field(default=1000, ge=100, le=5000, description="Default chunk size in characters")

    # Context enrichment settings (Phase 2)
    enable_context_enrichment: bool = Field(default=False, description="Enable LLM-based context enrichment for chunks")
    context_enrichment_model: str = Field(default="gpt-3.5-turbo", description="OpenAI model for context generation")
    context_enrichment_prompt_style: str = Field(default="default", description="Prompt style: default, short, or structured")
    context_enrichment_max_words: int = Field(default=100, ge=20, le=200, description="Max words in generated context")
    context_enrichment_temperature: float = Field(default=0.3, ge=0.0, le=1.0, description="Temperature for context generation")
    default_chunking_strategy: str = Field(default="recursive", description="Default chunking strategy: recursive, fixed_size, or semantic")

    # Summarization configuration (new stage between parsing and chunking)
    summarization: SummarizationConfig = Field(
        default_factory=SummarizationConfig,
        description="Settings for the SummarizationService stage",
    )


class SecurityConfig(BaseModel):
    """Security configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Authentication
    enable_authentication: bool = Field(default=True, description="Enable user authentication")
    session_timeout_hours: int = Field(default=24, ge=1, le=168, description="Session timeout in hours")
    max_login_attempts: int = Field(default=5, ge=1, le=20, description="Maximum login attempts")
    
    # API Security
    enable_rate_limiting: bool = Field(default=True, description="Enable API rate limiting")
    rate_limit_requests_per_minute: int = Field(default=100, ge=10, le=1000, description="Rate limit per minute")
    
    # Data Security
    enable_audit_logging: bool = Field(default=True, description="Enable audit logging")
    data_retention_days: int = Field(default=90, ge=1, le=3650, description="Data retention in days")
    
    # Sensitive data handling
    mask_sensitive_data: bool = Field(default=True, description="Mask sensitive data in logs")
    encryption_key_path: Optional[str] = Field(default=None, description="Path to encryption key file")


class MonitoringConfig(BaseModel):
    """Monitoring and observability configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Logging
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Application log level")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")
    log_file_max_size_mb: int = Field(default=100, ge=1, le=1000, description="Max log file size in MB")
    log_file_backup_count: int = Field(default=5, ge=1, le=50, description="Number of log file backups")
    
    # Metrics
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_collection_interval: int = Field(default=60, ge=10, le=3600, description="Metrics collection interval in seconds")
    
    # Health checks
    enable_health_checks: bool = Field(default=True, description="Enable health checks")
    health_check_interval: int = Field(default=30, ge=10, le=300, description="Health check interval in seconds")
    
    # Performance monitoring
    enable_performance_monitoring: bool = Field(default=True, description="Enable performance monitoring")
    slow_query_threshold_ms: int = Field(default=1000, ge=100, le=10000, description="Slow query threshold in ms")


class Settings(BaseSettings):
    """Main application settings with environment-specific configuration."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Application environment")
    debug: bool = Field(default=True, description="Enable debug mode")
    
    # Application info
    app_name: str = Field(default="Brain MVP", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    
    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    lightrag: LightRAGConfig = Field(default_factory=LightRAGConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
    # Hot-reloadable settings (non-critical)
    hot_reload_enabled: bool = Field(default=True, description="Enable configuration hot-reloading")
    hot_reload_check_interval: int = Field(default=30, ge=10, le=300, description="Hot-reload check interval in seconds")
    
    def __init__(self, **kwargs):
        """Initialize settings with environment-specific defaults."""
        super().__init__(**kwargs)
        self._apply_environment_defaults()
        self._ensure_directories()
        self._last_reload_time = datetime.now(timezone.utc)
    
    def _apply_environment_defaults(self):
        """Apply environment-specific default configurations."""
        if self.environment == Environment.PRODUCTION:
            # Production defaults
            self.debug = False
            self.security.enable_authentication = True
            self.security.enable_audit_logging = True
            self.monitoring.log_level = LogLevel.WARNING
            self.monitoring.enable_metrics = True
            self.storage.enable_encryption = True
            self.hot_reload_enabled = False
            
        elif self.environment == Environment.TESTING:
            # Testing defaults
            self.debug = True
            self.database.url = "sqlite:///data/test.db"
            self.storage.base_dir = "data/test"
            self.security.enable_authentication = False
            self.monitoring.log_level = LogLevel.DEBUG
            self.hot_reload_enabled = False
            
        elif self.environment == Environment.STAGING:
            # Staging defaults
            self.debug = False
            self.security.enable_authentication = True
            self.monitoring.log_level = LogLevel.INFO
            self.monitoring.enable_metrics = True
            
        # Development uses default values
    
    def _ensure_directories(self):
        """Ensure all configured directories exist."""
        directories = [
            self.storage.base_dir,
            self.storage.uploads_dir,
            self.storage.processed_dir,
            self.storage.cache_dir,
            self.storage.logs_dir,
            self.storage.temp_dir,
            self.lightrag.working_dir,
            Path(self.lightrag.vector_db_path).parent,
            # MinerU output directory
            self.processing.mineru.output_dir,
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get_database_url(self) -> str:
        """Get database URL with environment variable override."""
        return os.getenv("DATABASE_URL", self.database.url)
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get sensitive configuration value from environment or file."""
        # First try environment variable
        env_value = os.getenv(key)
        if env_value:
            return env_value
        
        # Try reading from secrets file
        secrets_file = Path("secrets") / f"{key.lower()}.txt"
        if secrets_file.exists():
            try:
                return secrets_file.read_text().strip()
            except Exception as e:
                logger.warning(f"Failed to read secret from {secrets_file}: {e}")
        
        return default
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT
    
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == Environment.TESTING
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration and return validation report."""
        validation_report = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Validate database configuration
        if self.is_production() and "sqlite" in self.database.url.lower():
            validation_report['warnings'].append(
                "Using SQLite in production - consider PostgreSQL for better performance"
            )
        
        # Validate storage configuration
        if self.storage.max_file_size_mb > 500:
            validation_report['warnings'].append(
                f"Large max file size ({self.storage.max_file_size_mb}MB) may impact performance"
            )
        
        # Validate security configuration
        if self.is_production() and not self.security.enable_authentication:
            validation_report['errors'].append(
                "Authentication must be enabled in production"
            )
            validation_report['valid'] = False
        
        if self.is_production() and not self.storage.enable_encryption:
            validation_report['warnings'].append(
                "Consider enabling encryption in production"
            )
        
        # Validate monitoring configuration
        if self.is_production() and self.monitoring.log_level == LogLevel.DEBUG:
            validation_report['warnings'].append(
                "Debug logging in production may impact performance and expose sensitive data"
            )
        
        # Validate directory permissions
        try:
            test_file = Path(self.storage.base_dir) / "test_write_permissions.tmp"
            test_file.write_text("test")
            test_file.unlink()
        except Exception as e:
            validation_report['errors'].append(
                f"Cannot write to storage directory {self.storage.base_dir}: {e}"
            )
            validation_report['valid'] = False
        
        return validation_report
    
    def get_component_config(self, component: str) -> Optional[BaseModel]:
        """Get configuration for a specific component."""
        component_map = {
            'database': self.database,
            'storage': self.storage,
            'lightrag': self.lightrag,
            'processing': self.processing,
            'security': self.security,
            'monitoring': self.monitoring
        }
        return component_map.get(component.lower())
    
    def export_config(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        config_dict = self.model_dump()
        
        if not include_sensitive:
            # Remove sensitive information
            sensitive_keys = ['encryption_key_path', 'database.url']
            for key in sensitive_keys:
                if '.' in key:
                    section, field = key.split('.', 1)
                    if section in config_dict and isinstance(config_dict[section], dict):
                        config_dict[section].pop(field, None)
                else:
                    config_dict.pop(key, None)
        
        return config_dict
    
    def save_config(self, file_path: str, include_sensitive: bool = False):
        """Save configuration to file."""
        config_dict = self.export_config(include_sensitive=include_sensitive)
        
        with open(file_path, 'w') as f:
            json.dump(config_dict, f, indent=2, default=str)
        
        logger.info(f"Configuration saved to {file_path}")
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'Settings':
        """Load configuration from file."""
        try:
            with open(file_path, 'r') as f:
                config_data = json.load(f)
            
            return cls(**config_data)
        except Exception as e:
            logger.error(f"Failed to load configuration from {file_path}: {e}")
            raise
    
    def reload_hot_reloadable_settings(self) -> bool:
        """Reload hot-reloadable settings from environment."""
        if not self.hot_reload_enabled:
            return False
        
        try:
            # Only reload non-critical settings
            old_log_level = self.monitoring.log_level
            old_batch_size = self.lightrag.batch_size
            old_chunk_size = self.processing.default_chunk_size
            
            # Reload from environment
            new_log_level = LogLevel(os.getenv("MONITORING__LOG_LEVEL", old_log_level.value))
            new_batch_size = int(os.getenv("LIGHTRAG__BATCH_SIZE", old_batch_size))
            new_chunk_size = int(os.getenv("PROCESSING__DEFAULT_CHUNK_SIZE", old_chunk_size))
            
            # Apply changes
            changes_made = False
            if new_log_level != old_log_level:
                self.monitoring.log_level = new_log_level
                changes_made = True
                logger.info(f"Hot-reloaded log level: {old_log_level} → {new_log_level}")
            
            if new_batch_size != old_batch_size and 1 <= new_batch_size <= 128:
                self.lightrag.batch_size = new_batch_size
                changes_made = True
                logger.info(f"Hot-reloaded batch size: {old_batch_size} → {new_batch_size}")
            
            if new_chunk_size != old_chunk_size and 100 <= new_chunk_size <= 5000:
                self.processing.default_chunk_size = new_chunk_size
                changes_made = True
                logger.info(f"Hot-reloaded chunk size: {old_chunk_size} → {new_chunk_size}")
            
            if changes_made:
                self._last_reload_time = datetime.now(timezone.utc)
            
            return changes_made
            
        except Exception as e:
            logger.error(f"Failed to reload hot-reloadable settings: {e}")
            return False
    
    # Backward compatibility properties
    @property
    def log_file_path(self) -> str:
        """Get log file path for backward compatibility."""
        return str(Path(self.storage.logs_dir) / "brain_mvp.log")
    
    @property
    def log_level(self) -> str:
        """Get log level for backward compatibility."""
        return self.monitoring.log_level.value
    
    @property
    def upload_dir(self) -> str:
        """Get upload directory for backward compatibility."""
        return self.storage.uploads_dir
    
    @property
    def processed_dir(self) -> str:
        """Get processed directory for backward compatibility."""
        return self.storage.processed_dir
    
    @property
    def lightrag_index_path(self) -> str:
        """Get LightRAG index path for backward compatibility."""
        return self.lightrag.working_dir
    
    @property
    def api_host(self) -> str:
        """Get API host for backward compatibility."""
        return os.getenv("API_HOST", "0.0.0.0")
    
    @property
    def api_port(self) -> int:
        """Get API port for backward compatibility."""
        return int(os.getenv("API_PORT", "8000"))
    
    @property
    def reload(self) -> bool:
        """Get reload setting for backward compatibility."""
        return self.debug and self.environment == Environment.DEVELOPMENT


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment and files."""
    global _settings
    _settings = Settings()
    return _settings


def get_config_for_component(component: str) -> Optional[BaseModel]:
    """Get configuration for a specific component."""
    return get_settings().get_component_config(component)


def validate_current_config() -> Dict[str, Any]:
    """Validate current configuration."""
    return get_settings().validate_configuration()


def create_environment_config_file(environment: Environment, output_path: str):
    """Create example configuration file for specific environment."""
    
    # Create settings with environment-specific defaults
    temp_settings = Settings(environment=environment)
    
    # Save configuration
    temp_settings.save_config(output_path, include_sensitive=False)
    
    logger.info(f"Created {environment.value} configuration template at {output_path}")


# Create global settings instance for direct import
settings = get_settings()