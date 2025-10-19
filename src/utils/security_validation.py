"""Input validation and sanitization for security."""

import re
import html
import logging
import hashlib
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path
import mimetypes
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Input validation error."""
    pass


class SecurityLevel(str, Enum):
    """Security validation levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    STRICT = "strict"


@dataclass
class ValidationRule:
    """Input validation rule."""
    name: str
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    allowed_chars: Optional[str] = None
    forbidden_chars: Optional[str] = None
    custom_validator: Optional[Callable] = None
    sanitizer: Optional[Callable] = None
    required: bool = True


class InputValidator:
    """Comprehensive input validation and sanitization."""
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.MEDIUM):
        """Initialize input validator."""
        self.security_level = security_level
        self.validation_rules: Dict[str, ValidationRule] = {}
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default validation rules."""
        # Common validation patterns
        patterns = {
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            'filename': r'^[a-zA-Z0-9._-]+$',
            'alphanumeric': r'^[a-zA-Z0-9]+$',
            'safe_string': r'^[a-zA-Z0-9\s._-]+$',
            'sql_safe': r'^[a-zA-Z0-9\s._-]+$',  # No SQL injection characters
            'path_safe': r'^[a-zA-Z0-9/._-]+$',
            'url_safe': r'^[a-zA-Z0-9:/?#\[\]@!$&\'()*+,;=._-]+$'
        }
        
        # Default rules based on security level
        if self.security_level in [SecurityLevel.HIGH, SecurityLevel.STRICT]:
            # Strict validation rules
            self.add_rule('document_id', ValidationRule(
                name='document_id',
                pattern=patterns['uuid'],
                max_length=36,
                required=True
            ))
            
            self.add_rule('filename', ValidationRule(
                name='filename',
                pattern=patterns['filename'],
                min_length=1,
                max_length=255,
                forbidden_chars='<>:"|?*',
                sanitizer=self._sanitize_filename,
                required=True
            ))
            
            self.add_rule('user_input', ValidationRule(
                name='user_input',
                max_length=10000,
                forbidden_chars='<script>',
                sanitizer=self._sanitize_html,
                required=False
            ))
        
        else:
            # Medium security rules
            self.add_rule('document_id', ValidationRule(
                name='document_id',
                pattern=patterns['alphanumeric'],
                min_length=1,
                max_length=50,
                required=True
            ))
            
            self.add_rule('filename', ValidationRule(
                name='filename',
                max_length=255,
                forbidden_chars='<>:"|?*',
                sanitizer=self._sanitize_filename,
                required=True
            ))
    
    def add_rule(self, field_name: str, rule: ValidationRule):
        """Add validation rule for a field."""
        self.validation_rules[field_name] = rule
        logger.debug(f"Added validation rule for field: {field_name}")
    
    def validate_field(self, field_name: str, value: Any) -> Any:
        """Validate and sanitize a single field."""
        if field_name not in self.validation_rules:
            logger.warning(f"No validation rule found for field: {field_name}")
            return value
        
        rule = self.validation_rules[field_name]
        
        # Check if required
        if rule.required and (value is None or value == ""):
            raise ValidationError(f"Field '{field_name}' is required")
        
        # Skip validation for None/empty optional fields
        if not rule.required and (value is None or value == ""):
            return value
        
        # Convert to string for validation
        str_value = str(value) if value is not None else ""
        
        # Length validation
        if rule.min_length is not None and len(str_value) < rule.min_length:
            raise ValidationError(f"Field '{field_name}' must be at least {rule.min_length} characters")
        
        if rule.max_length is not None and len(str_value) > rule.max_length:
            raise ValidationError(f"Field '{field_name}' must be at most {rule.max_length} characters")
        
        # Pattern validation
        if rule.pattern and not re.match(rule.pattern, str_value):
            raise ValidationError(f"Field '{field_name}' does not match required pattern")
        
        # Character validation
        if rule.allowed_chars:
            if not all(c in rule.allowed_chars for c in str_value):
                raise ValidationError(f"Field '{field_name}' contains invalid characters")
        
        if rule.forbidden_chars:
            if any(c in rule.forbidden_chars for c in str_value):
                raise ValidationError(f"Field '{field_name}' contains forbidden characters")
        
        # Custom validation
        if rule.custom_validator:
            try:
                if not rule.custom_validator(str_value):
                    raise ValidationError(f"Field '{field_name}' failed custom validation")
            except Exception as e:
                raise ValidationError(f"Field '{field_name}' validation error: {e}")
        
        # Sanitization
        sanitized_value = str_value
        if rule.sanitizer:
            try:
                sanitized_value = rule.sanitizer(str_value)
            except Exception as e:
                logger.error(f"Sanitization failed for field '{field_name}': {e}")
                raise ValidationError(f"Field '{field_name}' sanitization failed")
        
        return sanitized_value
    
    def validate_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize a dictionary of fields."""
        validated_data = {}
        
        for field_name, value in data.items():
            try:
                validated_data[field_name] = self.validate_field(field_name, value)
            except ValidationError as e:
                logger.warning(f"Validation failed for field '{field_name}': {e}")
                raise
        
        return validated_data
    
    def _sanitize_html(self, value: str) -> str:
        """Sanitize HTML content."""
        # Remove script tags and their content
        value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove dangerous attributes
        dangerous_attrs = ['onclick', 'onload', 'onerror', 'onmouseover', 'javascript:']
        for attr in dangerous_attrs:
            value = re.sub(f'{attr}[^>]*', '', value, flags=re.IGNORECASE)
        
        # Escape HTML entities
        value = html.escape(value)
        
        return value
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage."""
        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # Remove dangerous characters
        dangerous_chars = '<>:"|?*'
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Ensure not empty
        if not filename:
            filename = 'unnamed_file'
        
        # Limit length
        if len(filename) > 255:
            name, ext = Path(filename).stem, Path(filename).suffix
            max_name_len = 255 - len(ext)
            filename = name[:max_name_len] + ext
        
        return filename
    
    def validate_file_upload(self, filename: str, content: bytes, 
                           allowed_types: Optional[List[str]] = None,
                           max_size: Optional[int] = None) -> Dict[str, Any]:
        """Validate file upload."""
        validation_result = {
            'valid': True,
            'filename': filename,
            'size': len(content),
            'mime_type': None,
            'errors': []
        }
        
        try:
            # Validate filename
            sanitized_filename = self.validate_field('filename', filename)
            validation_result['filename'] = sanitized_filename
            
            # Check file size
            if max_size and len(content) > max_size:
                validation_result['valid'] = False
                validation_result['errors'].append(f"File size {len(content)} exceeds maximum {max_size}")
            
            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(sanitized_filename)
            validation_result['mime_type'] = mime_type
            
            # Validate file type
            if allowed_types:
                file_ext = Path(sanitized_filename).suffix.lower()
                if file_ext not in allowed_types and mime_type not in allowed_types:
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"File type not allowed: {file_ext}")
            
            # Check for malicious content patterns
            if self._contains_malicious_content(content):
                validation_result['valid'] = False
                validation_result['errors'].append("File contains potentially malicious content")
            
        except ValidationError as e:
            validation_result['valid'] = False
            validation_result['errors'].append(str(e))
        
        return validation_result
    
    def _contains_malicious_content(self, content: bytes) -> bool:
        """Check for malicious content patterns."""
        # Convert to string for pattern matching (handle encoding errors)
        try:
            content_str = content.decode('utf-8', errors='ignore')
        except:
            content_str = str(content)
        
        # Malicious patterns to detect
        malicious_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'eval\s*\(',
            r'document\.cookie',
            r'document\.write',
            r'window\.location'
        ]
        
        for pattern in malicious_patterns:
            if re.search(pattern, content_str, re.IGNORECASE):
                logger.warning(f"Malicious pattern detected: {pattern}")
                return True
        
        return False
    
    def validate_sql_input(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate SQL query parameters to prevent injection."""
        validated_params = {}
        
        for key, value in query_params.items():
            if value is None:
                validated_params[key] = None
                continue
            
            str_value = str(value)
            
            # Check for SQL injection patterns
            sql_injection_patterns = [
                r"'.*'",  # Single quotes
                r'".*"',  # Double quotes
                r'--',    # SQL comments
                r'/\*.*\*/',  # Multi-line comments
                r'\bunion\b',  # UNION statements
                r'\bselect\b',  # SELECT statements
                r'\binsert\b',  # INSERT statements
                r'\bupdate\b',  # UPDATE statements
                r'\bdelete\b',  # DELETE statements
                r'\bdrop\b',   # DROP statements
                r'\bexec\b',   # EXEC statements
                r'\bxp_\w+',   # Extended procedures
                r'\bsp_\w+',   # Stored procedures
            ]
            
            for pattern in sql_injection_patterns:
                if re.search(pattern, str_value, re.IGNORECASE):
                    raise ValidationError(f"Potentially malicious SQL pattern detected in parameter '{key}'")
            
            validated_params[key] = str_value
        
        return validated_params


class SecuritySanitizer:
    """Security-focused data sanitization."""
    
    @staticmethod
    def sanitize_log_data(data: Any) -> str:
        """Sanitize data for safe logging."""
        if data is None:
            return "None"
        
        str_data = str(data)
        
        # Remove sensitive patterns
        sensitive_patterns = [
            (r'password["\']?\s*[:=]\s*["\']?([^"\'\\s,}]+)', 'password=***'),
            (r'token["\']?\s*[:=]\s*["\']?([^"\'\\s,}]+)', 'token=***'),
            (r'key["\']?\s*[:=]\s*["\']?([^"\'\\s,}]+)', 'key=***'),
            (r'secret["\']?\s*[:=]\s*["\']?([^"\'\\s,}]+)', 'secret=***'),
            (r'api_key["\']?\s*[:=]\s*["\']?([^"\'\\s,}]+)', 'api_key=***'),
        ]
        
        for pattern, replacement in sensitive_patterns:
            str_data = re.sub(pattern, replacement, str_data, flags=re.IGNORECASE)
        
        # Limit length for logs
        if len(str_data) > 1000:
            str_data = str_data[:997] + "..."
        
        return str_data
    
    @staticmethod
    def sanitize_error_message(error_msg: str) -> str:
        """Sanitize error messages to prevent information disclosure."""
        # Remove file paths
        error_msg = re.sub(r'/[^\s]+', '[PATH]', error_msg)
        error_msg = re.sub(r'[A-Z]:\\[^\s]+', '[PATH]', error_msg)
        
        # Remove SQL details
        error_msg = re.sub(r'SQL.*?:', 'SQL Error:', error_msg, flags=re.IGNORECASE)
        
        # Remove stack traces in production
        if 'Traceback' in error_msg:
            lines = error_msg.split('\n')
            # Keep only the first and last line of traceback
            if len(lines) > 3:
                error_msg = lines[0] + '\n[Stack trace hidden]\n' + lines[-1]
        
        return error_msg
    
    @staticmethod
    def hash_sensitive_data(data: str, salt: Optional[str] = None) -> str:
        """Hash sensitive data for storage."""
        if salt is None:
            salt = "docforge_default_salt"  # Should be configurable
        
        combined = f"{salt}{data}"
        return hashlib.sha256(combined.encode()).hexdigest()


# Global validator instance
input_validator = InputValidator()


# Decorator for input validation
def validate_input(validation_rules: Optional[Dict[str, ValidationRule]] = None):
    """Decorator for automatic input validation."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Validate kwargs if rules provided
            if validation_rules:
                temp_validator = InputValidator()
                for field_name, rule in validation_rules.items():
                    temp_validator.add_rule(field_name, rule)
                
                validated_kwargs = temp_validator.validate_dict(kwargs)
                kwargs.update(validated_kwargs)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Convenience functions
def validate_document_id(doc_id: str) -> str:
    """Validate document ID."""
    return input_validator.validate_field('document_id', doc_id)


def validate_filename(filename: str) -> str:
    """Validate and sanitize filename."""
    return input_validator.validate_field('filename', filename)


def validate_user_input(user_input: str) -> str:
    """Validate and sanitize user input."""
    return input_validator.validate_field('user_input', user_input)


def sanitize_for_logs(data: Any) -> str:
    """Sanitize data for logging."""
    return SecuritySanitizer.sanitize_log_data(data)


def sanitize_error_message(error_msg: str) -> str:
    """Sanitize error message."""
    return SecuritySanitizer.sanitize_error_message(error_msg)