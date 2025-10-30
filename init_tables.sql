Database initialization SQL:

    -- Document lineage table
    CREATE TABLE IF NOT EXISTS document_lineage (
        lineage_uuid TEXT PRIMARY KEY,
        original_filename TEXT NOT NULL,
        created_by TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        current_version INTEGER DEFAULT 1,
        total_versions INTEGER DEFAULT 1,
        is_active BOOLEAN DEFAULT TRUE
    );

    -- Raw document register
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
        labels TEXT DEFAULT '[]',
        is_current BOOLEAN DEFAULT TRUE,
        status TEXT DEFAULT 'active',
        deletion_reason TEXT NULL,
        edit_source_version INTEGER NULL,
        metadata TEXT DEFAULT '{}',
        content TEXT DEFAULT '',
        FOREIGN KEY (lineage_uuid) REFERENCES document_lineage (lineage_uuid),
        UNIQUE(lineage_uuid, version_number)
    );

    -- Post document register
    CREATE TABLE IF NOT EXISTS post_document_register (
        doc_uuid TEXT NOT NULL,
        set_uuid TEXT NOT NULL,
        file_uuid TEXT PRIMARY KEY,
        lineage_uuid TEXT NOT NULL,
        version_number INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        processing_method TEXT NOT NULL,
        processing_version TEXT NOT NULL,
        metadata_record TEXT DEFAULT '{}',
        is_deleted BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (doc_uuid) REFERENCES raw_document_register (doc_uuid),
        FOREIGN KEY (lineage_uuid) REFERENCES document_lineage (lineage_uuid)
    );

    -- Meta document register
    CREATE TABLE IF NOT EXISTS meta_document_register (
        meta_file_uuid TEXT PRIMARY KEY,
        doc_uuid TEXT NOT NULL,
        lineage_uuid TEXT NOT NULL,
        version_number INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        component_type TEXT NOT NULL,
        metadata_record TEXT DEFAULT '{}',
        processing_status TEXT NOT NULL,
        chunking_strategy TEXT,
        post_processing_applied TEXT DEFAULT '[]',
        is_deleted BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (doc_uuid) REFERENCES raw_document_register (doc_uuid),
        FOREIGN KEY (lineage_uuid) REFERENCES document_lineage (lineage_uuid)
    );

    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP NULL
    );

    -- Sessions table
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    );

    -- Audit log
    CREATE TABLE IF NOT EXISTS audit_log (
        id SERIAL PRIMARY KEY,
        event_type TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        action TEXT NOT NULL,
        details TEXT DEFAULT '{}',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Schema version tracking
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        description TEXT
    );

    -- Insert initial schema version
    INSERT INTO schema_version (version, description) 
    VALUES (1, 'Initial Brain MVP schema') 
    ON CONFLICT (version) DO NOTHING;
    
