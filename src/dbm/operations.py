"""Basic CRUD operations for dummy DBM."""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from .connection import get_db_connection

logger = logging.getLogger(__name__)


class DummyDBOperations:
    """Basic database operations for MVP."""
    
    def __init__(self):
        self.db = get_db_connection()
    
    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """Execute a SQL query."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch:
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            else:
                conn.commit()
                return None
                
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
    
    def insert(self, table: str, data: Dict[str, Any]) -> bool:
        """Insert data into a table."""
        try:
            columns = list(data.keys())
            placeholders = ["?" for _ in columns]
            values = [
                json.dumps(v) if isinstance(v, (dict, list)) else v
                for v in data.values()
            ]
            
            query = f"""
                INSERT INTO {table} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            """
            
            self.execute_query(query, tuple(values))
            logger.info(f"Inserted data into {table}")
            return True
            
        except Exception as e:
            logger.error(f"Insert failed for table {table}: {e}")
            return False
    
    def select(
        self,
        table: str,
        where_clause: Optional[str] = None,
        params: Optional[Tuple] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Select data from a table."""
        try:
            query = f"SELECT * FROM {table}"
            
            if where_clause:
                query += f" WHERE {where_clause}"
            
            if limit:
                query += f" LIMIT {limit}"
            
            results = self.execute_query(query, params, fetch=True)
            
            # Parse JSON fields back to objects
            if results:
                for row in results:
                    for key, value in row.items():
                        if isinstance(value, str) and key in [
                            'labels', 'roles', 'permissions', 'metadata_record',
                            'post_processing_applied', 'metadata'
                        ]:
                            try:
                                row[key] = json.loads(value) if value else {}
                            except (json.JSONDecodeError, TypeError):
                                # For empty or invalid JSON, provide sensible defaults
                                if key in ['labels', 'post_processing_applied']:
                                    row[key] = []
                                elif key in ['metadata', 'metadata_record', 'roles', 'permissions']:
                                    row[key] = {}
                                else:
                                    pass  # Keep as string if not valid JSON
            
            return results or []
            
        except Exception as e:
            logger.error(f"Select failed for table {table}: {e}")
            return []
    
    def update(
        self,
        table: str,
        data: Dict[str, Any],
        where_clause: str,
        params: Optional[Tuple] = None
    ) -> bool:
        """Update data in a table."""
        try:
            set_clauses = []
            values = []
            
            for key, value in data.items():
                set_clauses.append(f"{key} = ?")
                if isinstance(value, (dict, list)):
                    values.append(json.dumps(value))
                else:
                    values.append(value)
            
            query = f"""
                UPDATE {table}
                SET {', '.join(set_clauses)}
                WHERE {where_clause}
            """
            
            if params:
                values.extend(params)
            
            self.execute_query(query, tuple(values))
            logger.info(f"Updated data in {table}")
            return True
            
        except Exception as e:
            logger.error(f"Update failed for table {table}: {e}")
            return False
    
    def delete(
        self,
        table: str,
        where_clause: str,
        params: Optional[Tuple] = None
    ) -> bool:
        """Delete data from a table."""
        try:
            query = f"DELETE FROM {table} WHERE {where_clause}"
            self.execute_query(query, params)
            logger.info(f"Deleted data from {table}")
            return True
            
        except Exception as e:
            logger.error(f"Delete failed for table {table}: {e}")
            return False
    
    def soft_delete(
        self,
        table: str,
        identifier_column: str,
        identifier_value: str,
        reason: Optional[str] = None
    ) -> bool:
        """Soft delete a record by setting status = 'deleted'."""
        try:
            # Use different fields based on table
            if table == "raw_document_register":
                data = {
                    "status": "deleted",
                    "deletion_reason": reason,
                    "is_current": False
                }
            else:
                # For other tables that still use is_deleted
                data = {
                    "is_deleted": True,
                    "deletion_reason": reason
                }
            
            return self.update(
                table,
                data,
                f"{identifier_column} = ?",
                (identifier_value,)
            )
            
        except Exception as e:
            logger.error(f"Soft delete failed for {table}: {e}")
            return False
    
    def restore(
        self,
        table: str,
        identifier_column: str,
        identifier_value: str
    ) -> bool:
        """Restore a soft-deleted record."""
        try:
            # Use different fields based on table
            if table == "raw_document_register":
                data = {
                    "status": "active",
                    "deletion_reason": None
                }
            else:
                # For other tables that still use is_deleted
                data = {
                    "is_deleted": False,
                    "deletion_reason": None
                }
            
            return self.update(
                table,
                data,
                f"{identifier_column} = ?",
                (identifier_value,)
            )
            
        except Exception as e:
            logger.error(f"Restore failed for {table}: {e}")
            return False
    
    def count(
        self,
        table: str,
        where_clause: Optional[str] = None,
        params: Optional[Tuple] = None
    ) -> int:
        """Count records in a table."""
        try:
            query = f"SELECT COUNT(*) as count FROM {table}"
            
            if where_clause:
                query += f" WHERE {where_clause}"
            
            result = self.execute_query(query, params, fetch=True)
            return result[0]["count"] if result else 0
            
        except Exception as e:
            logger.error(f"Count failed for table {table}: {e}")
            return 0


# Global operations instance
_db_operations: Optional[DummyDBOperations] = None


def get_db_operations() -> DummyDBOperations:
    """Get global database operations instance."""
    global _db_operations
    if not _db_operations:
        _db_operations = DummyDBOperations()
    return _db_operations