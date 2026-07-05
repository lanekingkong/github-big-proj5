"""
Memory Mesh — Cross-session, cross-agent persistent memory system.

This module provides persistent memory for AI agents that:
1. Survives across sessions and agent restarts
2. Can be shared across multiple agents
3. Supports semantic search and timeline reconstruction
4. Integrates with vector DB and graph store
"""

from __future__ import annotations

import json
import uuid
import hashlib
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON, Integer, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import chromadb
from chromadb.config import Settings


class MemoryType(str, Enum):
    """Types of memories stored in the mesh."""
    EPISODIC = "episodic"      # Specific events or interactions
    SEMANTIC = "semantic"      # Facts, knowledge, concepts
    PROCEDURAL = "procedural"  # Skills, procedures, how-to
    TEMPORAL = "temporal"      # Time-based events
    CONTEXTUAL = "contextual"  # Session/context information


class MemoryPriority(int, Enum):
    """Priority levels for memory retention."""
    LOW = 1      # Can be evicted under memory pressure
    MEDIUM = 2   # Standard retention
    HIGH = 3     # Important, keep longer
    CRITICAL = 4 # Never evict, system-critical


@dataclass
class MemoryEntry:
    """A single memory entry in the mesh."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    memory_type: MemoryType = MemoryType.EPISODIC
    priority: MemoryPriority = MemoryPriority.MEDIUM
    
    # Metadata
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    tool_name: Optional[str] = None
    task_id: Optional[str] = None
    
    # Embedding and search
    embedding: Optional[np.ndarray] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    # Relationships
    parent_id: Optional[str] = None
    related_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "priority": self.priority.value,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "tool_name": self.tool_name,
            "task_id": self.task_id,
            "embedding": self.embedding.tolist() if self.embedding is not None else None,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "parent_id": self.parent_id,
            "related_ids": self.related_ids
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryEntry:
        """Create from dictionary."""
        embedding = None
        if data.get("embedding"):
            embedding = np.array(data["embedding"])
        
        expires_at = None
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"])
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data.get("content", ""),
            memory_type=MemoryType(data.get("memory_type", "episodic")),
            priority=MemoryPriority(data.get("priority", 2)),
            agent_id=data.get("agent_id"),
            session_id=data.get("session_id"),
            tool_name=data.get("tool_name"),
            task_id=data.get("task_id"),
            embedding=embedding,
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat())),
            accessed_at=datetime.fromisoformat(data.get("accessed_at", datetime.utcnow().isoformat())),
            expires_at=expires_at,
            parent_id=data.get("parent_id"),
            related_ids=data.get("related_ids", [])
        )


class MemoryManager:
    """Main manager for the memory mesh."""
    
    def __init__(self, storage_path: Union[str, Path], embedding_model=None):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize SQLite for structured storage
        self.db_path = self.storage_path / "memory_mesh.db"
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.Session = sessionmaker(bind=self.engine)
        self.Base = declarative_base()
        
        # Initialize ChromaDB for vector search
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.storage_path / "chroma"),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Embedding model (optional)
        self.embedding_model = embedding_model
        
        # Create tables
        self._create_tables()
        
        # In-memory cache for frequently accessed memories
        self.cache: Dict[str, MemoryEntry] = {}
        self.cache_size = 1000
        
        # Statistics
        self.stats = {
            "total_memories": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "searches": 0,
            "writes": 0
        }
    
    def _create_tables(self):
        """Create database tables for memory storage."""
        
        class DBMemoryEntry(self.Base):
            __tablename__ = "memory_entries"
            
            id = Column(String, primary_key=True)
            content = Column(Text, nullable=False)
            memory_type = Column(String, nullable=False)
            priority = Column(Integer, nullable=False)
            
            agent_id = Column(String, index=True)
            session_id = Column(String, index=True)
            tool_name = Column(String, index=True)
            task_id = Column(String, index=True)
            
            embedding = Column(JSON)  # Store as JSON array
            tags = Column(JSON, default=list)
            metadata = Column(JSON, default=dict)
            
            created_at = Column(DateTime, nullable=False)
            updated_at = Column(DateTime, nullable=False)
            accessed_at = Column(DateTime, nullable=False)
            expires_at = Column(DateTime)
            
            parent_id = Column(String, index=True)
            related_ids = Column(JSON, default=list)
        
        self.DBMemoryEntry = DBMemoryEntry
        self.Base.metadata.create_all(self.engine)
    
    def add_memory(self, memory: MemoryEntry) -> str:
        """Add a memory to the mesh."""
        self.stats["writes"] += 1
        
        # Generate embedding if not provided
        if memory.embedding is None and self.embedding_model:
            memory.embedding = self._generate_embedding(memory.content)
        
        # Set default expiration based on priority
        if memory.expires_at is None:
            memory.expires_at = self._calculate_expiration(memory.priority)
        
        # Store in SQLite
        db_session = self.Session()
        try:
            db_entry = self.DBMemoryEntry(**memory.to_dict())
            db_session.add(db_entry)
            db_session.commit()
            
            # Store in ChromaDB for vector search
            if memory.embedding is not None:
                collection = self._get_chroma_collection(memory.agent_id or "global")
                collection.add(
                    embeddings=[memory.embedding.tolist()],
                    documents=[memory.content],
                    metadatas=[{
                        "id": memory.id,
                        "type": memory.memory_type.value,
                        "agent_id": memory.agent_id,
                        "session_id": memory.session_id,
                        "created_at": memory.created_at.isoformat()
                    }],
                    ids=[memory.id]
                )
            
            # Add to cache
            if len(self.cache) < self.cache_size:
                self.cache[memory.id] = memory
            else:
                # Evict least recently accessed
                oldest_id = min(self.cache.keys(), key=lambda k: self.cache[k].accessed_at)
                del self.cache[oldest_id]
                self.cache[memory.id] = memory
            
            self.stats["total_memories"] += 1
            return memory.id
            
        except Exception as e:
            db_session.rollback()
            raise
        finally:
            db_session.close()
    
    def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory by ID."""
        # Check cache first
        if memory_id in self.cache:
            self.stats["cache_hits"] += 1
            memory = self.cache[memory_id]
            memory.accessed_at = datetime.utcnow()
            return memory
        
        self.stats["cache_misses"] += 1
        
        # Retrieve from database
        db_session = self.Session()
        try:
            db_entry = db_session.query(self.DBMemoryEntry).filter_by(id=memory_id).first()
            if db_entry:
                memory = self._db_entry_to_memory(db_entry)
                
                # Update accessed time
                memory.accessed_at = datetime.utcnow()
                db_entry.accessed_at = memory.accessed_at
                db_session.commit()
                
                # Add to cache
                if len(self.cache) < self.cache_size:
                    self.cache[memory_id] = memory
                
                return memory
            return None
        finally:
            db_session.close()
    
    def search_memories(
        self,
        query: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[MemoryEntry]:
        """Search memories using various criteria."""
        self.stats["searches"] += 1
        
        db_session = self.Session()
        try:
            query_obj = db_session.query(self.DBMemoryEntry)
            
            # Apply filters
            if memory_type:
                query_obj = query_obj.filter_by(memory_type=memory_type.value)
            if agent_id:
                query_obj = query_obj.filter_by(agent_id=agent_id)
            if session_id:
                query_obj = query_obj.filter_by(session_id=session_id)
            if tool_name:
                query_obj = query_obj.filter_by(tool_name=tool_name)
            if tags:
                for tag in tags:
                    query_obj = query_obj.filter(self.DBMemoryEntry.tags.contains([tag]))
            
            # Apply expiration filter
            query_obj = query_obj.filter(
                (self.DBMemoryEntry.expires_at.is_(None)) |
                (self.DBMemoryEntry.expires_at > datetime.utcnow())
            )
            
            # Order by priority and recency
            query_obj = query_obj.order_by(
                self.DBMemoryEntry.priority.desc(),
                self.DBMemoryEntry.accessed_at.desc()
            )
            
            # Apply pagination
            query_obj = query_obj.offset(offset).limit(limit)
            
            # Execute query
            db_entries = query_obj.all()
            
            # Convert to MemoryEntry objects
            memories = [self._db_entry_to_memory(entry) for entry in db_entries]
            
            # Update accessed times
            for memory in memories:
                memory.accessed_at = datetime.utcnow()
            
            # Batch update accessed times
            for entry in db_entries:
                entry.accessed_at = datetime.utcnow()
            db_session.commit()
            
            # Semantic search if query provided
            if query and self.embedding_model:
                semantic_results = self._semantic_search(query, agent_id, limit)
                memories = self._merge_search_results(memories, semantic_results)
            
            return memories[:limit]
            
        finally:
            db_session.close()
    
    def _semantic_search(
        self, 
        query: str, 
        agent_id: Optional[str] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Perform semantic search using vector embeddings."""
        if not self.embedding_model:
            return []
        
        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        
        # Search in ChromaDB
        collection_name = agent_id or "global"
        try:
            collection = self.chroma_client.get_collection(collection_name)
        except:
            return []
        
        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=limit * 2  # Get more for filtering
        )
        
        # Convert results to MemoryEntry objects
        memories = []
        if results and results["ids"]:
            for i in range(len(results["ids"][0])):
                memory_id = results["ids"][0][i]
                memory = self.get_memory(memory_id)
                if memory:
                    # Add relevance score
                    memory.metadata["relevance_score"] = results["distances"][0][i]
                    memories.append(memory)
        
        return memories
    
    def _merge_search_results(
        self, 
        keyword_results: List[MemoryEntry], 
        semantic_results: List[MemoryEntry]
    ) -> List[MemoryEntry]:
        """Merge keyword and semantic search results."""
        merged = []
        seen_ids = set()
        
        # Add semantic results first (they're more relevant to the query)
        for memory in semantic_results:
            if memory.id not in seen_ids:
                merged.append(memory)
                seen_ids.add(memory.id)
        
        # Add keyword results that aren't already included
        for memory in keyword_results:
            if memory.id not in seen_ids:
                merged.append(memory)
                seen_ids.add(memory.id)
        
        return merged
    
    def get_timeline(
        self,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50
    ) -> List[MemoryEntry]:
        """Get memories in chronological order (timeline)."""
        db_session = self.Session()
        try:
            query_obj = db_session.query(self.DBMemoryEntry)
            
            # Apply filters
            if agent_id:
                query_obj = query_obj.filter_by(agent_id=agent_id)
            if session_id:
                query_obj = query_obj.filter_by(session_id=session_id)
            if start_time:
                query_obj = query_obj.filter(self.DBMemoryEntry.created_at >= start_time)
            if end_time:
                query_obj = query_obj.filter(self.DBMemoryEntry.created_at <= end_time)
            
            # Order chronologically
            query_obj = query_obj.order_by(self.DBMemoryEntry.created_at)
            
            # Apply limit
            query_obj = query_obj.limit(limit)
            
            # Execute query
            db_entries = query_obj.all()
            
            return [self._db_entry_to_memory(entry) for entry in db_entries]
            
        finally:
            db_session.close()
    
    def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing memory."""
        db_session = self.Session()
        try:
            db_entry = db_session.query(self.DBMemoryEntry).filter_by(id=memory_id).first()
            if not db_entry:
                return False
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(db_entry, key):
                    setattr(db_entry, key, value)
            
            db_entry.updated_at = datetime.utcnow()
            db_session.commit()
            
            # Update cache
            if memory_id in self.cache:
                memory = self.cache[memory_id]
                for key, value in updates.items():
                    if hasattr(memory, key):
                        setattr(memory, key, value)
                memory.updated_at = db_entry.updated_at
            
            return True
            
        except Exception as e:
            db_session.rollback()
            return False
        finally:
            db_session.close()
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory from the mesh."""
        db_session = self.Session()
        try:
            db_entry = db_session.query(self.DBMemoryEntry).filter_by(id=memory_id).first()
            if not db_entry:
                return False
            
            # Delete from SQLite
            db_session.delete(db_entry)
            db_session.commit()
            
            # Delete from ChromaDB
            try:
                collection = self._get_chroma_collection(db_entry.agent_id or "global")
                collection.delete(ids=[memory_id])
            except:
                pass
            
            # Remove from cache
            if memory_id in self.cache:
                del self.cache[memory_id]
            
            self.stats["total_memories"] = max(0, self.stats["total_memories"] - 1)
            return True
            
        except Exception as e:
            db_session.rollback()
            return False
        finally:
            db_session.close()
    
    def cleanup_expired(self) -> int:
        """Clean up expired memories and return count removed."""
        db_session = self.Session()
        try:
            # Find expired memories
            expired = db_session.query(self.DBMemoryEntry).filter(
                self.DBMemoryEntry.expires_at.isnot(None),
                self.DBMemoryEntry.expires_at <= datetime.utcnow()
            ).all()
            
            count = len(expired)
            
            # Delete from SQLite
            for entry in expired:
                db_session.delete(entry)
            
            # Delete from ChromaDB
            for entry in expired:
                try:
                    collection = self._get_chroma_collection(entry.agent_id or "global")
                    collection.delete(ids=[entry.id])
                except:
                    pass
            
                # Remove from cache
                if entry.id in self.cache:
                    del self.cache[entry.id]
            
            db_session.commit()
            
            # Update stats
            self.stats["total_memories"] = max(0, self.stats["total_memories"] - count)
            
            return count
            
        finally:
            db_session.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory mesh statistics."""
        db_session = self.Session()
        try:
            total = db_session.query(self.DBMemoryEntry).count()
            
            # Count by type
            type_counts = {}
            for memory_type in MemoryType:
                count = db_session.query(self.DBMemoryEntry).filter_by(
                    memory_type=memory_type.value
                ).count()
                type_counts[memory_type.value] = count
            
            # Count by agent
            agent_counts = {}
            agents = db_session.query(self.DBMemoryEntry.agent_id).distinct().all()
            for (agent_id,) in agents:
                if agent_id:
                    count = db_session.query(self.DBMemoryEntry).filter_by(
                        agent_id=agent_id
                    ).count()
                    agent_counts[agent_id] = count
            
            return {
                "total_memories": total,
                "type_distribution": type_counts,
                "agent_distribution": agent_counts,
                "cache_size": len(self.cache),
                "cache_hit_rate": (
                    self.stats["cache_hits"] / (self.stats["cache_hits"] + self.stats["cache_misses"])
                    if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0 else 0
                ),
                "operations": self.stats.copy()
            }
        finally:
            db_session.close()
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        if self.embedding_model:
            # Use provided embedding model
            return self.embedding_model.encode(text)
        else:
            # Simple hash-based embedding for demo
            # In production, use a proper embedding model
            hash_val = hashlib.sha256(text.encode()).hexdigest()
            # Convert to 384-dim vector (like sentence-transformers)
            np.random.seed(int(hash_val[:8], 16))
            return np.random.randn(384).astype(np.float32)
    
    def _calculate_expiration(self, priority: MemoryPriority) -> datetime:
        """Calculate expiration time based on priority."""
        now = datetime.utcnow()
        
        if priority == MemoryPriority.LOW:
            return now + timedelta(days=1)
        elif priority == MemoryPriority.MEDIUM:
            return now + timedelta(days=7)
        elif priority == MemoryPriority.HIGH:
            return now + timedelta(days=30)
        elif priority == MemoryPriority.CRITICAL:
            return now + timedelta(days=365)  # 1 year
        else:
            return now + timedelta(days=7)
    
    def _get_chroma_collection(self, name: str):
        """Get or create a ChromaDB collection."""
        try:
            return self.chroma_client.get_collection(name)
        except:
            return self.chroma_client.create_collection(name)
    
    def _db_entry_to_memory(self, db_entry) -> MemoryEntry:
        """Convert database entry to MemoryEntry object."""
        embedding = None
        if db_entry.embedding:
            embedding = np.array(db_entry.embedding)
        
        return MemoryEntry(
            id=db_entry.id,
            content=db_entry.content,
            memory_type=MemoryType(db_entry.memory_type),
            priority=MemoryPriority(db_entry.priority),
            agent_id=db_entry.agent_id,
            session_id=db_entry.session_id,
            tool_name=db_entry.tool_name,
            task_id=db_entry.task_id,
            embedding=embedding,
            tags=db_entry.tags or [],
            metadata=db_entry.metadata or {},
            created_at=db_entry.created_at,
            updated_at=db_entry.updated_at,
            accessed_at=db_entry.accessed_at,
            expires_at=db_entry.expires_at,
            parent_id=db_entry.parent_id,
            related_ids=db_entry.related_ids or []
        )


class MemoryMeshAPI:
    """REST API wrapper for the Memory Mesh."""
    
    def __init__(self, memory_manager: MemoryManager):
        self.mm = memory_manager
    
    def add_memory_endpoint(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """API endpoint to add a memory."""
        try:
            memory = MemoryEntry.from_dict(memory_data)
            memory_id = self.mm.add_memory(memory)
            return {
                "success": True,
                "memory_id": memory_id,
                "message": "Memory added successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def search_memories_endpoint(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """API endpoint to search memories."""
        try:
            memories = self.mm.search_memories(
                query=search_params.get("query"),
                memory_type=(
                    MemoryType(search_params["memory_type"]) 
                    if search_params.get("memory_type") else None
                ),
                agent_id=search_params.get("agent_id"),
                session_id=search_params.get("session_id"),
                tool_name=search_params.get("tool_name"),
                tags=search_params.get("tags"),
                limit=search_params.get("limit", 10),
                offset=search_params.get("offset", 0)
            )
            
            return {
                "success": True,
                "memories": [memory.to_dict() for memory in memories],
                "count": len(memories)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_timeline_endpoint(self, timeline_params: Dict[str, Any]) -> Dict[str, Any]:
        """API endpoint to get timeline."""
        try:
            start_time = None
            if timeline_params.get("start_time"):
                start_time = datetime.fromisoformat(timeline_params["start_time"])
            
            end_time = None
            if timeline_params.get("end_time"):
                end_time = datetime.fromisoformat(timeline_params["end_time"])
            
            memories = self.mm.get_timeline(
                agent_id=timeline_params.get("agent_id"),
                session_id=timeline_params.get("session_id"),
                start_time=start_time,
                end_time=end_time,
                limit=timeline_params.get("limit", 50)
            )
            
            return {
                "success": True,
                "timeline": [memory.to_dict() for memory in memories],
                "count": len(memories)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Export main classes
__all__ = [
    "MemoryType",
    "MemoryPriority",
    "MemoryEntry",
    "MemoryManager",
    "MemoryMeshAPI",
]