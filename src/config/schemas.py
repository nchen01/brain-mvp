"""Configuration schema definitions for validation."""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path

try:
    from pydantic import BaseModel, Field, field_validator, model_validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    # Fallback for when pydantic is not available
    class BaseModel:
        pass
    def Field(**kwargs):
        return None
    def field_validator(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def model_validator(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    PYDANTIC_AVAILABLE = False


class DatabaseConfig(BaseModel):
    """Database configuration schema."""
    
    if PYDANTIC_AVAILABLE:
        host: str = Field(default="localhost", description="Database host")
        port: int = Field(default=5432, ge=1, le=65535, description="Database port")
        name: str = Field(..., description="Database name")
        user: str = Field(..., description="Database user")
        password: str = Field(..., description="Database password")
        pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
        max_overflow: int = Field(default=20, ge=0, le=100, description="Max pool overflow")
        pool_timeout: int = Field(default=30, ge=1, description="Pool timeout in seconds")
        pool_recycle: int = Field(default=3600, ge=300, description="Pool recycle time in seconds")
        echo: bool = Field(default=False, description="Enable SQL echo")
        
        @field_validator('name')
        @classmethod
        def validate_name(cls, v):
            if not v or not v.strip():
                raise ValueError('Database name cannot be empty')
            return v.strip()
        
        @field_validator('user')
        @classmethod
        def validate_user(cls, v):
            if not v or not v.strip():
                raise ValueError('Database user cannot be empty')
            return v.strip()


class StorageConfig(BaseModel):
    """Storage configuration schema."""
    
    if PYDANTIC_AVAILABLE:
        base_path: str = Field(default="storage", description="Base storage path")
        max_file_size: int = Field(default=100*1024*1024, ge=1024, description="Max file size in bytes")
        allowed_extensions: List[str] = Field(
            default=[".pdf", ".txt", ".docx", ".md"],
            description="Allowed file extensions"
        )
        temp_dir: str = Field(default="temp", description="Temporary directory")
        backup_enabled: bool = Field(default=True, description="Enable backups")
        backup_retention_days: int = Field(default=30, ge=1, description="Backup retention in days")
        
        @field_validator('base_path')
        @classmethod
        def validate_base_path(cls, v):
            path = Path(v)
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValueError(f'Cannot create storage path {v}: {e}')
            return str(path.absolute())
        
        @field_validator('allowed_extensions')
        @classmethod
        def validate_extensions(cls, v):
            if not v:
                raise ValueError('At least one file extension must be allowed')
            return [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in v]


class ProcessingConfig(BaseModel):
    """Processing configuration schema."""
    
    if PYDANTIC_AVAILABLE:
        max_workers: int = Field(default=4, ge=1, le=32, description="Max worker processes")
        timeout: int = Field(default=300, ge=30, description="Processing timeout in seconds")
        chunk_size: int = Field(default=1000, ge=100, description="Text chunk size")
        chunk_overlap: int = Field(default=200, ge=0, description="Chunk overlap size")
        enable_ocr: bool = Field(default=True, description="Enable OCR processing")
        ocr_language: str = Field(default="eng", description="OCR language")
        
        @field_validator('chunk_overlap')
        @classmethod
        def validate_chunk_overlap(cls, v, info):
            if info.data and 'chunk_size' in info.data and v >= info.data['chunk_size']:
                raise ValueError('Chunk overlap must be less than chunk size')
            return v


class RAGConfig(BaseModel):
    """RAG (Retrieval Augmented Generation) configuration schema."""
    
    if PYDANTIC_AVAILABLE:
        embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="Embedding model")
        embedding_dimension: int = Field(default=384, ge=1, description="Embedding dimension")
        vector_store_type: str = Field(default="faiss", description="Vector store type")
        similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")
        max_results: int = Field(default=10, ge=1, le=100, description="Max search results")
        rerank_enabled: bool = Field(default=True, description="Enable result reranking")
        
        @field_validator('vector_store_type')
        @classmethod
        def validate_vector_store(cls, v):
            allowed_stores = ['faiss', 'chroma', 'pinecone', 'weaviate']
            if v.lower() not in allowed_stores:
                raise ValueError(f'Vector store must be one of: {allowed_stores}')
            return v.lower()


class SecurityConfig(BaseModel):
    """Security configuration schema."""
    
    if PYDANTIC_AVAILABLE:
        secret_key: str = Field(..., min_length=32, description="Application secret key")
        jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
        jwt_expiration: int = Field(default=3600, ge=300, description="JWT expiration in seconds")
        password_min_length: int = Field(default=8, ge=6, description="Minimum password length")
        max_login_attempts: int = Field(default=5, ge=1, description="Max login attempts")
        lockout_duration: int = Field(default=900, ge=60, description="Lockout duration in seconds")
        enable_2fa: bool = Field(default=False, description="Enable two-factor authentication")
        
        @field_validator('secret_key')
        @classmethod
        def validate_secret_key(cls, v):
            if len(v) < 32:
                raise ValueError('Secret key must be at least 32 characters long')
            return v


class LoggingConfig(BaseModel):
    """Logging configuration schema."""
    
    if PYDANTIC_AVAILABLE:
        level: str = Field(default="INFO", description="Log level")
        format: str = Field(default="detailed", description="Log format")
        file_enabled: bool = Field(default=True, description="Enable file logging")
        console_enabled: bool = Field(default=True, description="Enable console logging")
        max_file_size: int = Field(default=10*1024*1024, ge=1024, description="Max log file size")
        backup_count: int = Field(default=5, ge=1, description="Log file backup count")
        log_dir: str = Field(default="logs", description="Log directory")
        
        @field_validator('level')
        @classmethod
        def validate_level(cls, v):
            allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if v.upper() not in allowed_levels:
                raise ValueError(f'Log level must be one of: {allowed_levels}')
            return v.upper()
        
        @field_validator('format')
        @classmethod
        def validate_format(cls, v):
            allowed_formats = ['simple', 'detailed', 'json', 'performance']
            if v.lower() not in allowed_formats:
                raise ValueError(f'Log format must be one of: {allowed_formats}')
            return v.lower()


class MonitoringConfig(BaseModel):
    """Monitoring configuration schema."""
    
    if PYDANTIC_AVAILABLE:
        enabled: bool = Field(default=True, description="Enable monitoring")
        metrics_port: int = Field(default=8080, ge=1024, le=65535, description="Metrics port")
        health_check_interval: int = Field(default=30, ge=5, description="Health check interval in seconds")
        performance_tracking: bool = Field(default=True, description="Enable performance tracking")
        alert_thresholds: Dict[str, float] = Field(
            default={
                "cpu_usage": 80.0,
                "memory_usage": 85.0,
                "disk_usage": 90.0,
                "response_time": 5.0
            },
            description="Alert thresholds"
        )
        
        @field_validator('alert_thresholds')
        @classmethod
        def validate_thresholds(cls, v):
            for key, value in v.items():
                if not isinstance(value, (int, float)) or value <= 0:
                    raise ValueError(f'Alert threshold for {key} must be a positive number')
            return v


class ExternalServicesConfig(BaseModel):
    """External services configuration schema."""
    
    if PYDANTIC_AVAILABLE:
        openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
        openai_model: str = Field(default="gpt-3.5-turbo", description="OpenAI model")
        anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
        huggingface_token: Optional[str] = Field(default=None, description="HuggingFace token")
        timeout: int = Field(default=30, ge=5, description="Request timeout in seconds")
        max_retries: int = Field(default=3, ge=0, description="Max retry attempts")
        retry_delay: float = Field(default=1.0, ge=0.1, description="Retry delay in seconds")


class CacheConfig(BaseModel):
    """Cache configuration schema."""
    
    if PYDANTIC_AVAILABLE:
        enabled: bool = Field(default=True, description="Enable caching")
        backend: str = Field(default="memory", description="Cache backend")
        ttl: int = Field(default=3600, ge=60, description="Default TTL in seconds")
        max_size: int = Field(default=1000, ge=10, description="Max cache size")
        redis_url: Optional[str] = Field(default=None, description="Redis URL for Redis backend")
        
        @field_validator('backend')
        @classmethod
        def validate_backend(cls, v):
            allowed_backends = ['memory', 'redis', 'memcached']
            if v.lower() not in allowed_backends:
                raise ValueError(f'Cache backend must be one of: {allowed_backends}')
            return v.lower()


class AppConfig(BaseModel):
    """Main application configuration schema."""
    
    if PYDANTIC_AVAILABLE:
        name: str = Field(default="DocForge", description="Application name")
        version: str = Field(default="1.0.0", description="Application version")
        debug: bool = Field(default=False, description="Debug mode")
        host: str = Field(default="0.0.0.0", description="Server host")
        port: int = Field(default=8000, ge=1024, le=65535, description="Server port")
        workers: int = Field(default=1, ge=1, description="Number of workers")
        
        # Nested configurations
        database: DatabaseConfig = Field(default_factory=DatabaseConfig)
        storage: StorageConfig = Field(default_factory=StorageConfig)
        processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
        rag: RAGConfig = Field(default_factory=RAGConfig)
        security: SecurityConfig = Field(default_factory=lambda: SecurityConfig(secret_key="change-me-in-production"))
        logging: LoggingConfig = Field(default_factory=LoggingConfig)
        monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
        external_services: ExternalServicesConfig = Field(default_factory=ExternalServicesConfig)
        cache: CacheConfig = Field(default_factory=CacheConfig)
        
        @model_validator(mode='after')
        def validate_production_settings(self):
            """Validate production-specific settings."""
            if not self.debug and self.security:  # Production mode
                if hasattr(self.security, 'secret_key') and self.security.secret_key == "change-me-in-production":
                    raise ValueError('Secret key must be changed in production')
            
            return self


# Schema registry for easy access
SCHEMA_REGISTRY = {
    'app': AppConfig,
    'database': DatabaseConfig,
    'storage': StorageConfig,
    'processing': ProcessingConfig,
    'rag': RAGConfig,
    'security': SecurityConfig,
    'logging': LoggingConfig,
    'monitoring': MonitoringConfig,
    'external_services': ExternalServicesConfig,
    'cache': CacheConfig
}


def get_schema(section: str) -> Optional[BaseModel]:
    """Get configuration schema for a section."""
    return SCHEMA_REGISTRY.get(section)


def validate_config_section(section: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate configuration section against its schema."""
    if not PYDANTIC_AVAILABLE:
        return config_data
    
    schema = get_schema(section)
    if schema:
        validated = schema.parse_obj(config_data)
        return validated.dict()
    
    return config_data


def get_default_config() -> Dict[str, Any]:
    """Get default configuration with all sections."""
    if not PYDANTIC_AVAILABLE:
        return {}
    
    default_app = AppConfig()
    return default_app.dict()