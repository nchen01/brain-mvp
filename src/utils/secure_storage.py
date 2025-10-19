"""Secure file handling and storage system."""

import os
import shutil
import hashlib
import logging
from typing import Dict, Any, Optional, List, BinaryIO, Union
from pathlib import Path
from datetime import datetime, timezone
import tempfile
import mimetypes
from dataclasses import dataclass
from enum import Enum
import stat

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    CRYPTO_AVAILABLE = True
except ImportError:
    Fernet = None
    CRYPTO_AVAILABLE = False

from .security_validation import input_validator, validate_filename

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Secure storage error."""
    pass


class EncryptionLevel(str, Enum):
    """File encryption levels."""
    NONE = "none"
    BASIC = "basic"
    STRONG = "strong"


@dataclass
class FileMetadata:
    """Secure file metadata."""
    file_id: str
    original_filename: str
    stored_filename: str
    file_size: int
    mime_type: Optional[str]
    checksum: str
    encryption_level: EncryptionLevel
    created_at: datetime
    accessed_at: datetime
    permissions: str
    owner: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'file_id': self.file_id,
            'original_filename': self.original_filename,
            'stored_filename': self.stored_filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'checksum': self.checksum,
            'encryption_level': self.encryption_level.value,
            'created_at': self.created_at.isoformat(),
            'accessed_at': self.accessed_at.isoformat(),
            'permissions': self.permissions,
            'owner': self.owner,
            'tags': self.tags or {}
        }


class SecureFileEncryption:
    """File encryption and decryption utilities."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize encryption system."""
        if not CRYPTO_AVAILABLE:
            logger.warning("Cryptography library not available. Encryption disabled.")
            self.encryption_enabled = False
            return
        
        self.encryption_enabled = True
        
        if encryption_key:
            self.key = encryption_key.encode()
        else:
            # Generate a key from environment or use default (should be configurable)
            password = os.getenv('DOCFORGE_ENCRYPTION_KEY', 'default-key-change-in-production').encode()
            salt = os.getenv('DOCFORGE_ENCRYPTION_SALT', 'default-salt').encode()
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            self.key = base64.urlsafe_b64encode(kdf.derive(password))
        
        self.cipher = Fernet(self.key)
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data."""
        if not self.encryption_enabled:
            return data
        
        try:
            return self.cipher.encrypt(data)
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise StorageError(f"Failed to encrypt data: {e}")
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data."""
        if not self.encryption_enabled:
            return encrypted_data
        
        try:
            return self.cipher.decrypt(encrypted_data)
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise StorageError(f"Failed to decrypt data: {e}")
    
    def encrypt_file(self, input_path: str, output_path: str):
        """Encrypt a file."""
        if not self.encryption_enabled:
            shutil.copy2(input_path, output_path)
            return
        
        try:
            with open(input_path, 'rb') as infile, open(output_path, 'wb') as outfile:
                data = infile.read()
                encrypted_data = self.encrypt_data(data)
                outfile.write(encrypted_data)
        except Exception as e:
            logger.error(f"File encryption failed: {e}")
            raise StorageError(f"Failed to encrypt file: {e}")
    
    def decrypt_file(self, input_path: str, output_path: str):
        """Decrypt a file."""
        if not self.encryption_enabled:
            shutil.copy2(input_path, output_path)
            return
        
        try:
            with open(input_path, 'rb') as infile, open(output_path, 'wb') as outfile:
                encrypted_data = infile.read()
                data = self.decrypt_data(encrypted_data)
                outfile.write(data)
        except Exception as e:
            logger.error(f"File decryption failed: {e}")
            raise StorageError(f"Failed to decrypt file: {e}")


class SecureFileStorage:
    """Secure file storage system with encryption and access control."""
    
    def __init__(self, 
                 storage_root: str = "secure_storage",
                 encryption_level: EncryptionLevel = EncryptionLevel.BASIC,
                 max_file_size: int = 100 * 1024 * 1024,  # 100MB
                 allowed_extensions: Optional[List[str]] = None):
        """Initialize secure file storage."""
        self.storage_root = Path(storage_root)
        self.encryption_level = encryption_level
        self.max_file_size = max_file_size
        self.allowed_extensions = allowed_extensions or [
            '.pdf', '.txt', '.docx', '.md', '.rtf', '.odt'
        ]
        
        # Create storage directories
        self._setup_storage_directories()
        
        # Initialize encryption
        self.encryptor = SecureFileEncryption()
        
        # File metadata storage (in production, use database)
        self.metadata_store: Dict[str, FileMetadata] = {}
    
    def _setup_storage_directories(self):
        """Setup secure storage directory structure."""
        directories = [
            self.storage_root,
            self.storage_root / "files",
            self.storage_root / "temp",
            self.storage_root / "quarantine",
            self.storage_root / "metadata"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
            # Set secure permissions (owner read/write only)
            try:
                os.chmod(directory, stat.S_IRWXU)  # 700 permissions
            except OSError as e:
                logger.warning(f"Could not set secure permissions on {directory}: {e}")
    
    def _generate_file_id(self, filename: str, content_hash: str) -> str:
        """Generate unique file ID."""
        timestamp = datetime.now(timezone.utc).isoformat()
        combined = f"{filename}_{content_hash}_{timestamp}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate file checksum."""
        hash_sha256 = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Checksum calculation failed: {e}")
            raise StorageError(f"Failed to calculate checksum: {e}")
    
    def _validate_file_security(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Perform security validation on file."""
        validation_result = {
            'safe': True,
            'issues': []
        }
        
        try:
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                validation_result['safe'] = False
                validation_result['issues'].append(f"File size {file_size} exceeds limit {self.max_file_size}")
            
            # Check file extension
            file_ext = Path(filename).suffix.lower()
            if self.allowed_extensions and file_ext not in self.allowed_extensions:
                validation_result['safe'] = False
                validation_result['issues'].append(f"File extension {file_ext} not allowed")
            
            # Check MIME type
            mime_type, _ = mimetypes.guess_type(filename)
            if mime_type:
                # Additional MIME type validation could be added here
                pass
            
            # Scan for malicious content
            with open(file_path, 'rb') as f:
                content_sample = f.read(8192)  # Read first 8KB
                
                # Check for executable signatures
                executable_signatures = [
                    b'\x4d\x5a',  # PE executable
                    b'\x7f\x45\x4c\x46',  # ELF executable
                    b'\xfe\xed\xfa',  # Mach-O executable
                ]
                
                for signature in executable_signatures:
                    if content_sample.startswith(signature):
                        validation_result['safe'] = False
                        validation_result['issues'].append("File appears to be executable")
                        break
        
        except Exception as e:
            validation_result['safe'] = False
            validation_result['issues'].append(f"Security validation failed: {e}")
        
        return validation_result
    
    def store_file(self, 
                   file_path: str, 
                   original_filename: str,
                   owner: Optional[str] = None,
                   tags: Optional[Dict[str, str]] = None,
                   permissions: str = "600") -> str:
        """Store file securely with encryption and metadata."""
        try:
            # Validate filename
            sanitized_filename = validate_filename(original_filename)
            
            # Security validation
            security_check = self._validate_file_security(file_path, sanitized_filename)
            if not security_check['safe']:
                # Move to quarantine
                quarantine_path = self.storage_root / "quarantine" / sanitized_filename
                shutil.move(file_path, quarantine_path)
                raise StorageError(f"File failed security validation: {security_check['issues']}")
            
            # Calculate checksum
            checksum = self._calculate_checksum(file_path)
            
            # Generate file ID
            file_id = self._generate_file_id(sanitized_filename, checksum)
            
            # Determine storage filename
            file_ext = Path(sanitized_filename).suffix
            stored_filename = f"{file_id}{file_ext}"
            
            # Storage path
            storage_path = self.storage_root / "files" / stored_filename
            
            # Encrypt and store file
            if self.encryption_level != EncryptionLevel.NONE:
                self.encryptor.encrypt_file(file_path, storage_path)
            else:
                shutil.copy2(file_path, storage_path)
            
            # Set secure permissions
            try:
                os.chmod(storage_path, int(permissions, 8))
            except OSError as e:
                logger.warning(f"Could not set file permissions: {e}")
            
            # Create metadata
            file_size = os.path.getsize(file_path)
            mime_type, _ = mimetypes.guess_type(sanitized_filename)
            
            metadata = FileMetadata(
                file_id=file_id,
                original_filename=sanitized_filename,
                stored_filename=stored_filename,
                file_size=file_size,
                mime_type=mime_type,
                checksum=checksum,
                encryption_level=self.encryption_level,
                created_at=datetime.now(timezone.utc),
                accessed_at=datetime.now(timezone.utc),
                permissions=permissions,
                owner=owner,
                tags=tags
            )
            
            # Store metadata
            self.metadata_store[file_id] = metadata
            self._save_metadata(file_id, metadata)
            
            logger.info(f"File stored securely: {file_id}")
            return file_id
            
        except Exception as e:
            logger.error(f"File storage failed: {e}")
            raise StorageError(f"Failed to store file: {e}")
    
    def retrieve_file(self, 
                      file_id: str, 
                      output_path: Optional[str] = None,
                      requester: Optional[str] = None) -> str:
        """Retrieve and decrypt file."""
        try:
            # Get metadata
            metadata = self.get_file_metadata(file_id)
            if not metadata:
                raise StorageError(f"File not found: {file_id}")
            
            # Check access permissions (basic implementation)
            if requester and metadata.owner and requester != metadata.owner:
                logger.warning(f"Access denied for user {requester} to file {file_id}")
                raise StorageError("Access denied")
            
            # Storage path
            storage_path = self.storage_root / "files" / metadata.stored_filename
            
            if not storage_path.exists():
                raise StorageError(f"Stored file not found: {metadata.stored_filename}")
            
            # Output path
            if output_path is None:
                temp_dir = self.storage_root / "temp"
                output_path = temp_dir / metadata.original_filename
            
            # Decrypt and retrieve file
            if metadata.encryption_level != EncryptionLevel.NONE:
                self.encryptor.decrypt_file(storage_path, output_path)
            else:
                shutil.copy2(storage_path, output_path)
            
            # Update access time
            metadata.accessed_at = datetime.now(timezone.utc)
            self.metadata_store[file_id] = metadata
            self._save_metadata(file_id, metadata)
            
            logger.info(f"File retrieved: {file_id}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"File retrieval failed: {e}")
            raise StorageError(f"Failed to retrieve file: {e}")
    
    def delete_file(self, file_id: str, requester: Optional[str] = None, secure_delete: bool = True):
        """Securely delete file."""
        try:
            # Get metadata
            metadata = self.get_file_metadata(file_id)
            if not metadata:
                raise StorageError(f"File not found: {file_id}")
            
            # Check permissions
            if requester and metadata.owner and requester != metadata.owner:
                logger.warning(f"Delete access denied for user {requester} to file {file_id}")
                raise StorageError("Delete access denied")
            
            # Storage path
            storage_path = self.storage_root / "files" / metadata.stored_filename
            
            if storage_path.exists():
                if secure_delete:
                    self._secure_delete_file(storage_path)
                else:
                    os.remove(storage_path)
            
            # Remove metadata
            if file_id in self.metadata_store:
                del self.metadata_store[file_id]
            
            # Remove metadata file
            metadata_path = self.storage_root / "metadata" / f"{file_id}.json"
            if metadata_path.exists():
                os.remove(metadata_path)
            
            logger.info(f"File deleted: {file_id}")
            
        except Exception as e:
            logger.error(f"File deletion failed: {e}")
            raise StorageError(f"Failed to delete file: {e}")
    
    def _secure_delete_file(self, file_path: Path):
        """Securely delete file by overwriting with random data."""
        try:
            file_size = file_path.stat().st_size
            
            # Overwrite with random data multiple times
            with open(file_path, 'r+b') as f:
                for _ in range(3):  # 3 passes
                    f.seek(0)
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            # Finally remove the file
            os.remove(file_path)
            
        except Exception as e:
            logger.error(f"Secure deletion failed: {e}")
            # Fallback to regular deletion
            try:
                os.remove(file_path)
            except:
                pass
    
    def get_file_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """Get file metadata."""
        if file_id in self.metadata_store:
            return self.metadata_store[file_id]
        
        # Try to load from disk
        metadata_path = self.storage_root / "metadata" / f"{file_id}.json"
        if metadata_path.exists():
            try:
                import json
                with open(metadata_path, 'r') as f:
                    data = json.load(f)
                
                metadata = FileMetadata(
                    file_id=data['file_id'],
                    original_filename=data['original_filename'],
                    stored_filename=data['stored_filename'],
                    file_size=data['file_size'],
                    mime_type=data['mime_type'],
                    checksum=data['checksum'],
                    encryption_level=EncryptionLevel(data['encryption_level']),
                    created_at=datetime.fromisoformat(data['created_at']),
                    accessed_at=datetime.fromisoformat(data['accessed_at']),
                    permissions=data['permissions'],
                    owner=data.get('owner'),
                    tags=data.get('tags')
                )
                
                self.metadata_store[file_id] = metadata
                return metadata
                
            except Exception as e:
                logger.error(f"Failed to load metadata for {file_id}: {e}")
        
        return None
    
    def _save_metadata(self, file_id: str, metadata: FileMetadata):
        """Save metadata to disk."""
        try:
            metadata_path = self.storage_root / "metadata" / f"{file_id}.json"
            
            import json
            with open(metadata_path, 'w') as f:
                json.dump(metadata.to_dict(), f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save metadata for {file_id}: {e}")
    
    def list_files(self, owner: Optional[str] = None, tags: Optional[Dict[str, str]] = None) -> List[FileMetadata]:
        """List files with optional filtering."""
        files = []
        
        for file_id, metadata in self.metadata_store.items():
            # Filter by owner
            if owner and metadata.owner != owner:
                continue
            
            # Filter by tags
            if tags:
                if not metadata.tags:
                    continue
                
                match = True
                for key, value in tags.items():
                    if metadata.tags.get(key) != value:
                        match = False
                        break
                
                if not match:
                    continue
            
            files.append(metadata)
        
        return files
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        total_files = len(self.metadata_store)
        total_size = sum(metadata.file_size for metadata in self.metadata_store.values())
        
        # Count by encryption level
        encryption_counts = {}
        for metadata in self.metadata_store.values():
            level = metadata.encryption_level.value
            encryption_counts[level] = encryption_counts.get(level, 0) + 1
        
        return {
            'total_files': total_files,
            'total_size_bytes': total_size,
            'encryption_counts': encryption_counts,
            'storage_root': str(self.storage_root),
            'encryption_enabled': self.encryptor.encryption_enabled
        }


# Global secure storage instance
secure_storage = SecureFileStorage()


# Convenience functions
def store_file_securely(file_path: str, filename: str, owner: Optional[str] = None) -> str:
    """Store file securely."""
    return secure_storage.store_file(file_path, filename, owner)


def retrieve_file_securely(file_id: str, requester: Optional[str] = None) -> str:
    """Retrieve file securely."""
    return secure_storage.retrieve_file(file_id, requester=requester)


def delete_file_securely(file_id: str, requester: Optional[str] = None):
    """Delete file securely."""
    secure_storage.delete_file(file_id, requester, secure_delete=True)


def get_file_info(file_id: str) -> Optional[Dict[str, Any]]:
    """Get file information."""
    metadata = secure_storage.get_file_metadata(file_id)
    return metadata.to_dict() if metadata else None