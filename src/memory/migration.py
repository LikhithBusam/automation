"""
Memory Migration Strategy
Handles version updates and data migrations
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class MemoryMigration:
    """Handles memory system migrations"""
    
    def __init__(self, postgres_backend):
        """Initialize migration handler"""
        self.postgres = postgres_backend
        self.logger = logging.getLogger("memory.migration")
    
    def get_current_version(self) -> int:
        """Get current database version"""
        session = self.postgres.get_session()
        try:
            # Check if version table exists
            from sqlalchemy import inspect
            inspector = inspect(self.postgres.engine)
            if "schema_version" not in [t.name for t in inspector.get_table_names()]:
                return 0
            
            result = session.execute(
                "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
            ).fetchone()
            return result[0] if result else 0
        except Exception as e:
            self.logger.error(f"Failed to get version: {e}")
            return 0
        finally:
            session.close()
    
    def migrate(self, target_version: int) -> bool:
        """Migrate to target version"""
        current_version = self.get_current_version()
        
        if current_version >= target_version:
            self.logger.info(f"Already at version {current_version}, no migration needed")
            return True
        
        self.logger.info(f"Migrating from version {current_version} to {target_version}")
        
        # Run migrations in order
        for version in range(current_version + 1, target_version + 1):
            if not self._run_migration(version):
                self.logger.error(f"Migration to version {version} failed")
                return False
        
        self.logger.info(f"Migration to version {target_version} completed")
        return True
    
    def _run_migration(self, version: int) -> bool:
        """Run specific migration version"""
        session = self.postgres.get_session()
        try:
            # Get migration script
            migration_func = getattr(self, f"_migrate_to_v{version}", None)
            if not migration_func:
                self.logger.warning(f"No migration script for version {version}")
                return True  # Skip if no migration needed
            
            # Run migration
            migration_func(session)
            
            # Update version
            session.execute(
                f"INSERT INTO schema_version (version, migrated_at) VALUES ({version}, NOW())"
            )
            session.commit()
            
            return True
        except Exception as e:
            self.logger.error(f"Migration {version} failed: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def _migrate_to_v1(self, session):
        """Migration to version 1: Add soft delete support"""
        session.execute("""
            ALTER TABLE memory_entries 
            ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP
        """)
        session.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_entries_deleted_at 
            ON memory_entries(deleted_at)
        """)
    
    def _migrate_to_v2(self, session):
        """Migration to version 2: Add retention policies"""
        session.execute("""
            ALTER TABLE memory_entries 
            ADD COLUMN IF NOT EXISTS retention_policy VARCHAR(255),
            ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP
        """)
        session.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_entries_expires_at 
            ON memory_entries(expires_at)
        """)
    
    def _migrate_to_v3(self, session):
        """Migration to version 3: Add compression support"""
        session.execute("""
            ALTER TABLE memory_entries 
            ADD COLUMN IF NOT EXISTS compressed BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS compression_ratio FLOAT
        """)
    
    def backup_before_migration(self, version: int) -> str:
        """Create backup before migration"""
        from src.memory.storage.postgresql_backend import MemoryEntryModel, MemoryBackupModel
        
        backup_id = f"migration_backup_v{version}_{datetime.utcnow().timestamp()}"
        
        # Export all data
        session = self.postgres.get_session()
        try:
            entries = session.query(MemoryEntryModel).all()
            backup_data = {
                "version": version,
                "timestamp": datetime.utcnow().isoformat(),
                "entries": [self.postgres._entry_to_dict(entry) for entry in entries]
            }
            
            # Store backup
            backup_entry = MemoryBackupModel(
                id=backup_id,
                entry_id="migration",
                backup_data=backup_data,
                reason=f"migration_to_v{version}"
            )
            session.add(backup_entry)
            session.commit()
            
            self.logger.info(f"Created migration backup: {backup_id}")
            return backup_id
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            session.rollback()
            raise
        finally:
            session.close()

