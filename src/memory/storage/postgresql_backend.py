"""
PostgreSQL Backend for Memory Storage
Handles relational data with replication support
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column, DateTime, Float, Integer, String, Text, JSON, Boolean,
    create_engine, desc, func, and_, or_
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

Base = declarative_base()


class MemoryEntryModel(Base):
    """PostgreSQL model for memory entries"""
    __tablename__ = "memory_entries"
    
    id = Column(String, primary_key=True)
    tier = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    meta_data = Column(JSON)
    agent = Column(String, index=True)
    project = Column(String, index=True)
    tags = Column(JSON, index=True)
    relevance_score = Column(Float, default=1.0)
    access_count = Column(Integer, default=0)
    relationships = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_accessed_at = Column(DateTime, default=datetime.utcnow, index=True)
    retention_policy = Column(String, nullable=True)  # Custom retention policy
    expires_at = Column(DateTime, nullable=True, index=True)  # Manual expiration
    deleted_at = Column(DateTime, nullable=True, index=True)  # Soft delete
    version = Column(Integer, default=1)  # For migration tracking
    compressed = Column(Boolean, default=False)  # Compression flag
    compression_ratio = Column(Float, nullable=True)  # Compression ratio
    backup_id = Column(String, nullable=True)  # Backup reference


class MemoryBackupModel(Base):
    """PostgreSQL model for memory backups"""
    __tablename__ = "memory_backups"
    
    id = Column(String, primary_key=True)
    entry_id = Column(String, nullable=False, index=True)
    backup_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    reason = Column(String)  # Reason for backup (deletion, migration, etc.)


class PostgreSQLBackend:
    """PostgreSQL backend for memory storage"""
    
    def __init__(self, database_url: str, pool_size: int = 10, max_overflow: int = 20):
        """
        Initialize PostgreSQL backend.
        
        Args:
            database_url: PostgreSQL connection URL
            pool_size: Connection pool size
            max_overflow: Maximum overflow connections
        """
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Verify connections before using
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        logger.info("PostgreSQL backend initialized")
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.Session()
    
    def store(self, entry_data: Dict[str, Any]) -> bool:
        """Store memory entry"""
        session = self.get_session()
        try:
            entry = MemoryEntryModel(**entry_data)
            session.add(entry)
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store entry: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def retrieve(
        self,
        entry_id: Optional[str] = None,
        tier: Optional[str] = None,
        agent: Optional[str] = None,
        project: Optional[str] = None,
        tags: Optional[List[str]] = None,
        include_deleted: bool = False,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve memory entries"""
        session = self.get_session()
        try:
            query = session.query(MemoryEntryModel)
            
            # Filter deleted entries
            if not include_deleted:
                query = query.filter(MemoryEntryModel.deleted_at.is_(None))
            
            # Apply filters
            if entry_id:
                query = query.filter(MemoryEntryModel.id == entry_id)
            if tier:
                query = query.filter(MemoryEntryModel.tier == tier)
            if agent:
                query = query.filter(MemoryEntryModel.agent == agent)
            if project:
                query = query.filter(MemoryEntryModel.project == project)
            if tags:
                # PostgreSQL JSONB contains query
                for tag in tags:
                    query = query.filter(MemoryEntryModel.tags.contains([tag]))
            
            query = query.limit(limit)
            entries = query.all()
            
            return [self._entry_to_dict(entry) for entry in entries]
        except Exception as e:
            logger.error(f"Failed to retrieve entries: {e}")
            return []
        finally:
            session.close()
    
    def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update memory entry"""
        session = self.get_session()
        try:
            entry = session.query(MemoryEntryModel).filter(
                MemoryEntryModel.id == entry_id,
                MemoryEntryModel.deleted_at.is_(None)
            ).first()
            
            if not entry:
                return False
            
            for key, value in updates.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)
            
            if "last_accessed_at" not in updates:
                entry.last_accessed_at = datetime.utcnow()
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update entry: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def soft_delete(self, entry_id: str, backup: bool = True) -> bool:
        """Soft delete memory entry"""
        session = self.get_session()
        try:
            entry = session.query(MemoryEntryModel).filter(
                MemoryEntryModel.id == entry_id,
                MemoryEntryModel.deleted_at.is_(None)
            ).first()
            
            if not entry:
                return False
            
            # Create backup before deletion
            if backup:
                backup_entry = MemoryBackupModel(
                    id=f"backup_{entry_id}_{datetime.utcnow().timestamp()}",
                    entry_id=entry_id,
                    backup_data=self._entry_to_dict(entry),
                    reason="soft_delete"
                )
                session.add(backup_entry)
                entry.backup_id = backup_entry.id
            
            entry.deleted_at = datetime.utcnow()
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to soft delete entry: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def restore(self, entry_id: str) -> bool:
        """Restore soft-deleted entry"""
        session = self.get_session()
        try:
            entry = session.query(MemoryEntryModel).filter(
                MemoryEntryModel.id == entry_id,
                MemoryEntryModel.deleted_at.isnot(None)
            ).first()
            
            if not entry:
                return False
            
            entry.deleted_at = None
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to restore entry: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def hard_delete(self, entry_id: str) -> bool:
        """Permanently delete memory entry"""
        session = self.get_session()
        try:
            entry = session.query(MemoryEntryModel).filter(
                MemoryEntryModel.id == entry_id
            ).first()
            
            if not entry:
                return False
            
            # Create backup before hard delete
            backup_entry = MemoryBackupModel(
                id=f"backup_{entry_id}_{datetime.utcnow().timestamp()}",
                entry_id=entry_id,
                backup_data=self._entry_to_dict(entry),
                reason="hard_delete"
            )
            session.add(backup_entry)
            
            session.delete(entry)
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to hard delete entry: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics"""
        session = self.get_session()
        try:
            total = session.query(func.count(MemoryEntryModel.id)).filter(
                MemoryEntryModel.deleted_at.is_(None)
            ).scalar()
            
            deleted = session.query(func.count(MemoryEntryModel.id)).filter(
                MemoryEntryModel.deleted_at.isnot(None)
            ).scalar()
            
            by_tier = {}
            for tier in ["short_term", "medium_term", "long_term"]:
                count = session.query(func.count(MemoryEntryModel.id)).filter(
                    MemoryEntryModel.tier == tier,
                    MemoryEntryModel.deleted_at.is_(None)
                ).scalar()
                by_tier[tier] = count
            
            return {
                "total_entries": total,
                "deleted_entries": deleted,
                "by_tier": by_tier,
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
        finally:
            session.close()
    
    def _entry_to_dict(self, entry: MemoryEntryModel) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "id": entry.id,
            "tier": entry.tier,
            "type": entry.type,
            "content": entry.content,
            "summary": entry.summary,
            "meta_data": entry.meta_data,
            "agent": entry.agent,
            "project": entry.project,
            "tags": entry.tags,
            "relevance_score": entry.relevance_score,
            "access_count": entry.access_count,
            "relationships": entry.relationships,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "last_accessed_at": entry.last_accessed_at.isoformat() if entry.last_accessed_at else None,
            "retention_policy": entry.retention_policy,
            "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
            "deleted_at": entry.deleted_at.isoformat() if entry.deleted_at else None,
            "version": entry.version,
            "compressed": entry.compressed,
            "compression_ratio": entry.compression_ratio,
        }

