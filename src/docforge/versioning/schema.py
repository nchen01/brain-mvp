"""Database schema definitions for document versioning system."""

from typing import Dict, List


class VersioningSchema:
    """Database schema definitions for the versioning system."""
    
    @staticmethod
    def get_table_definitions() -> Dict[str, str]:
        """Get all table definitions for the versioning system."""
        return {
            "document_lineage": """
                CREATE TABLE IF NOT EXISTS document_lineage (
                    lineage_uuid TEXT PRIMARY KEY,
                    original_filename TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    current_version INTEGER DEFAULT 1,
                    total_versions INTEGER DEFAULT 1,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """,
            
            "raw_document_register": """
                CREATE TABLE IF NOT EXISTS raw_document_register (
                    doc_uuid TEXT PRIMARY KEY,
                    lineage_uuid TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    parent_version INTEGER NULL,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT NOT NULL,
                    labels TEXT DEFAULT '[]',  -- JSON array
                    is_current BOOLEAN DEFAULT TRUE,
                    status TEXT DEFAULT 'active',  -- active, deleted, archived
                    deletion_reason TEXT NULL,
                    edit_source_version INTEGER NULL,
                    metadata TEXT DEFAULT '{}',  -- JSON object
                    FOREIGN KEY (lineage_uuid) REFERENCES document_lineage (lineage_uuid),
                    UNIQUE(lineage_uuid, version_number)
                )
            """,
            
            "post_document_register": """
                CREATE TABLE IF NOT EXISTS post_document_register (
                    doc_uuid TEXT NOT NULL,
                    set_uuid TEXT NOT NULL,
                    file_uuid TEXT PRIMARY KEY,
                    lineage_uuid TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    processing_method TEXT NOT NULL,
                    processing_version TEXT NOT NULL,
                    metadata_record TEXT DEFAULT '{}',  -- JSON object
                    is_deleted BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doc_uuid) REFERENCES raw_document_register (doc_uuid),
                    FOREIGN KEY (lineage_uuid) REFERENCES document_lineage (lineage_uuid)
                )
            """,
            
            "meta_document_register": """
                CREATE TABLE IF NOT EXISTS meta_document_register (
                    meta_file_uuid TEXT PRIMARY KEY,
                    doc_uuid TEXT NOT NULL,
                    lineage_uuid TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    component_type TEXT NOT NULL,
                    metadata_record TEXT DEFAULT '{}',  -- JSON object
                    processing_status TEXT NOT NULL,
                    chunking_strategy TEXT,
                    post_processing_applied TEXT DEFAULT '[]',  -- JSON array
                    is_deleted BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doc_uuid) REFERENCES raw_document_register (doc_uuid),
                    FOREIGN KEY (lineage_uuid) REFERENCES document_lineage (lineage_uuid)
                )
            """,
            
            "audit_log": """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,  -- deletion, restoration, creation, etc.
                    entity_type TEXT NOT NULL,  -- version, lineage, etc.
                    entity_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT DEFAULT '{}',  -- JSON object
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            
            "schema_version": """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """
        }
    
    @staticmethod
    def get_index_definitions() -> Dict[str, str]:
        """Get all index definitions for performance optimization."""
        return {
            # Raw document register indexes
            "idx_raw_doc_lineage": "CREATE INDEX IF NOT EXISTS idx_raw_doc_lineage ON raw_document_register(lineage_uuid)",
            "idx_raw_doc_status": "CREATE INDEX IF NOT EXISTS idx_raw_doc_status ON raw_document_register(status)",
            "idx_raw_doc_hash": "CREATE INDEX IF NOT EXISTS idx_raw_doc_hash ON raw_document_register(file_hash)",
            "idx_raw_doc_user": "CREATE INDEX IF NOT EXISTS idx_raw_doc_user ON raw_document_register(user_id)",
            "idx_raw_doc_current": "CREATE INDEX IF NOT EXISTS idx_raw_doc_current ON raw_document_register(is_current)",
            "idx_raw_doc_timestamp": "CREATE INDEX IF NOT EXISTS idx_raw_doc_timestamp ON raw_document_register(timestamp)",
            
            # Document lineage indexes
            "idx_lineage_active": "CREATE INDEX IF NOT EXISTS idx_lineage_active ON document_lineage(is_active)",
            "idx_lineage_created_by": "CREATE INDEX IF NOT EXISTS idx_lineage_created_by ON document_lineage(created_by)",
            
            # Post document register indexes
            "idx_post_doc_lineage": "CREATE INDEX IF NOT EXISTS idx_post_doc_lineage ON post_document_register(lineage_uuid)",
            "idx_post_doc_uuid": "CREATE INDEX IF NOT EXISTS idx_post_doc_uuid ON post_document_register(doc_uuid)",
            "idx_post_doc_method": "CREATE INDEX IF NOT EXISTS idx_post_doc_method ON post_document_register(processing_method)",
            
            # Meta document register indexes
            "idx_meta_doc_lineage": "CREATE INDEX IF NOT EXISTS idx_meta_doc_lineage ON meta_document_register(lineage_uuid)",
            "idx_meta_doc_uuid": "CREATE INDEX IF NOT EXISTS idx_meta_doc_uuid ON meta_document_register(doc_uuid)",
            "idx_meta_doc_component": "CREATE INDEX IF NOT EXISTS idx_meta_doc_component ON meta_document_register(component_type)",
            "idx_meta_doc_status": "CREATE INDEX IF NOT EXISTS idx_meta_doc_status ON meta_document_register(processing_status)",
            
            # Audit log indexes
            "idx_audit_entity": "CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id)",
            "idx_audit_user": "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)",
            "idx_audit_timestamp": "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)",
            "idx_audit_event_type": "CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type)",
            
            # Users and sessions indexes (from existing schema)
            "idx_users_username": "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
            "idx_users_email": "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "idx_users_active": "CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)",
            "idx_sessions_user": "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)",
            "idx_sessions_active": "CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active)",
            "idx_sessions_expires": "CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)"
        }
    
    @staticmethod
    def get_view_definitions() -> Dict[str, str]:
        """Get view definitions for common queries."""
        return {
            "document_version_history": """
                CREATE VIEW IF NOT EXISTS document_version_history AS
                SELECT 
                    dl.lineage_uuid,
                    dl.original_filename,
                    dl.created_by as lineage_created_by,
                    dl.created_at as lineage_created_at,
                    dl.current_version,
                    dl.total_versions,
                    dl.is_active as lineage_active,
                    rdr.doc_uuid,
                    rdr.version_number,
                    rdr.parent_version,
                    rdr.filename,
                    rdr.file_type,
                    rdr.file_hash,
                    rdr.file_size,
                    rdr.timestamp as version_created_at,
                    rdr.user_id as version_created_by,
                    rdr.labels,
                    rdr.is_current,
                    rdr.status,
                    rdr.deletion_reason,
                    rdr.edit_source_version,
                    rdr.metadata
                FROM document_lineage dl
                JOIN raw_document_register rdr ON dl.lineage_uuid = rdr.lineage_uuid
                ORDER BY dl.lineage_uuid, rdr.version_number
            """,
            
            "active_documents": """
                CREATE VIEW IF NOT EXISTS active_documents AS
                SELECT *
                FROM document_version_history
                WHERE lineage_active = 1 AND status = 'active'
            """,
            
            "current_versions": """
                CREATE VIEW IF NOT EXISTS current_versions AS
                SELECT *
                FROM document_version_history
                WHERE is_current = 1 AND status = 'active'
            """,
            
            "deleted_documents": """
                CREATE VIEW IF NOT EXISTS deleted_documents AS
                SELECT *
                FROM document_version_history
                WHERE status = 'deleted'
            """
        }
    
    @staticmethod
    def get_trigger_definitions() -> Dict[str, str]:
        """Get trigger definitions for data integrity."""
        return {
            "update_lineage_on_version_insert": """
                CREATE TRIGGER IF NOT EXISTS update_lineage_on_version_insert
                AFTER INSERT ON raw_document_register
                BEGIN
                    UPDATE document_lineage 
                    SET total_versions = total_versions + 1,
                        current_version = NEW.version_number
                    WHERE lineage_uuid = NEW.lineage_uuid;
                END
            """,
            
            "prevent_duplicate_current_version": """
                CREATE TRIGGER IF NOT EXISTS prevent_duplicate_current_version
                BEFORE UPDATE ON raw_document_register
                WHEN NEW.is_current = 1 AND OLD.is_current = 0
                BEGIN
                    UPDATE raw_document_register 
                    SET is_current = 0 
                    WHERE lineage_uuid = NEW.lineage_uuid AND doc_uuid != NEW.doc_uuid;
                END
            """,
            
            "audit_version_changes": """
                CREATE TRIGGER IF NOT EXISTS audit_version_changes
                AFTER UPDATE ON raw_document_register
                WHEN OLD.status != NEW.status
                BEGIN
                    INSERT INTO audit_log (
                        event_type, entity_type, entity_id, user_id, action, details
                    ) VALUES (
                        'status_change',
                        'version',
                        NEW.doc_uuid,
                        NEW.user_id,
                        'status_changed_from_' || OLD.status || '_to_' || NEW.status,
                        json_object(
                            'old_status', OLD.status,
                            'new_status', NEW.status,
                            'deletion_reason', NEW.deletion_reason
                        )
                    );
                END
            """
        }
    
    @staticmethod
    def validate_schema() -> List[str]:
        """Validate the database schema and return any issues found."""
        issues = []
        
        # This would contain validation logic for:
        # - Foreign key constraints
        # - Index existence
        # - Data type consistency
        # - Required columns
        
        return issues
    
    @staticmethod
    def get_schema_documentation() -> Dict[str, Dict[str, str]]:
        """Get comprehensive schema documentation."""
        return {
            "document_lineage": {
                "description": "Tracks document families and version chains",
                "lineage_uuid": "Unique identifier for the document lineage",
                "original_filename": "Original filename when first uploaded",
                "created_by": "User ID who created the lineage",
                "created_at": "Lineage creation timestamp",
                "current_version": "Current active version number",
                "total_versions": "Total number of versions created",
                "is_active": "Whether the lineage is active (not deleted)"
            },
            
            "raw_document_register": {
                "description": "Individual document versions within lineages",
                "doc_uuid": "Unique identifier for this document version",
                "lineage_uuid": "Lineage this version belongs to",
                "version_number": "Version number within the lineage",
                "parent_version": "Parent version if this is a branch",
                "filename": "Filename for this version",
                "file_path": "Storage path for the document file",
                "file_type": "File type/extension",
                "file_hash": "SHA-256 hash for integrity verification",
                "file_size": "File size in bytes",
                "timestamp": "Version creation timestamp",
                "user_id": "User who created this version",
                "labels": "JSON array of user-defined labels",
                "is_current": "Whether this is the current version",
                "status": "Version status (active, deleted, archived)",
                "deletion_reason": "Reason for deletion if deleted",
                "edit_source_version": "Source version if created by editing",
                "metadata": "JSON object for additional metadata"
            },
            
            "audit_log": {
                "description": "Audit trail for all document operations",
                "id": "Auto-incrementing primary key",
                "event_type": "Type of event (deletion, restoration, etc.)",
                "entity_type": "Type of entity (version, lineage, etc.)",
                "entity_id": "ID of the affected entity",
                "user_id": "User who performed the action",
                "action": "Specific action performed",
                "details": "JSON object with additional details",
                "timestamp": "When the event occurred"
            }
        }