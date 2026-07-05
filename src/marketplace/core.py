"""
Skill Marketplace — Decentralized skill registry and exchange.

This module provides:
1. Skill discovery with trust-weighted search
2. Decentralized storage options (IPFS, local, GitHub)
3. Automated skill validation and testing
4. Version management and dependency resolution
5. Usage analytics and reputation tracking
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import shutil
import zipfile
import tempfile
import asyncio

import httpx
from pydantic import BaseModel, Field


class StorageBackend(str, Enum):
    """Supported storage backends for skills."""
    LOCAL = "local"
    GITHUB = "github"
    IPFS = "ipfs"
    HTTP = "http"


class SkillStatus(str, Enum):
    """Status of a skill in the marketplace."""
    LISTED = "listed"
    VERIFIED = "verified"
    FEATURED = "featured"
    OUTDATED = "outdated"
    DEPRECATED = "deprecated"
    UNMAINTAINED = "unmaintained"


@dataclass
class SkillListing:
    """A skill listing in the marketplace."""
    
    # Core identity
    skill_id: str
    name: str
    version: str
    author: str
    
    # Description
    description: str
    tags: List[str] = field(default_factory=list)
    category: str = "uncategorized"
    
    # Trust and quality
    trust_score: float = 0.0
    verification_status: SkillStatus = SkillStatus.LISTED
    download_count: int = 0
    star_count: int = 0
    rating: float = 0.0
    
    # Storage
    storage_backend: StorageBackend = StorageBackend.LOCAL
    storage_url: str = ""
    content_hash: str = ""
    size_bytes: int = 0
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    compatible_platforms: List[str] = field(default_factory=list)
    
    # Version history
    previous_versions: List[str] = field(default_factory=list)  # version strings
    created_at: str = ""
    updated_at: str = ""
    
    # Review and feedback
    reviews: List[Dict[str, Any]] = field(default_factory=list)
    security_audit: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "tags": self.tags,
            "category": self.category,
            "trust_score": self.trust_score,
            "verification_status": self.verification_status.value,
            "download_count": self.download_count,
            "star_count": self.star_count,
            "rating": self.rating,
            "storage_backend": self.storage_backend.value,
            "storage_url": self.storage_url,
            "content_hash": self.content_hash,
            "size_bytes": self.size_bytes,
            "dependencies": self.dependencies,
            "compatible_platforms": self.compatible_platforms,
            "previous_versions": self.previous_versions,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "reviews": self.reviews,
            "security_audit": self.security_audit
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SkillListing:
        """Create from dictionary."""
        return cls(
            skill_id=data["skill_id"],
            name=data["name"],
            version=data["version"],
            author=data["author"],
            description=data["description"],
            tags=data.get("tags", []),
            category=data.get("category", "uncategorized"),
            trust_score=data.get("trust_score", 0.0),
            verification_status=SkillStatus(data.get("verification_status", "listed")),
            download_count=data.get("download_count", 0),
            star_count=data.get("star_count", 0),
            rating=data.get("rating", 0.0),
            storage_backend=StorageBackend(data.get("storage_backend", "local")),
            storage_url=data.get("storage_url", ""),
            content_hash=data.get("content_hash", ""),
            size_bytes=data.get("size_bytes", 0),
            dependencies=data.get("dependencies", []),
            compatible_platforms=data.get("compatible_platforms", []),
            previous_versions=data.get("previous_versions", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            reviews=data.get("reviews", []),
            security_audit=data.get("security_audit")
        )


class SkillRegistry:
    """In-memory and persistent skill registry."""
    
    def __init__(self, registry_path: Optional[str] = None):
        self.listings: Dict[str, SkillListing] = {}
        self.registry_path = registry_path
        
        if registry_path:
            self._load_registry()
    
    def register_skill(self, listing: SkillListing) -> bool:
        """Register a skill in the marketplace."""
        if listing.skill_id in self.listings:
            # Update existing
            existing = self.listings[listing.skill_id]
            listing.previous_versions = existing.previous_versions + [existing.version]
            listing.download_count = existing.download_count
            listing.star_count = existing.star_count
            listing.reviews = existing.reviews
        
        self.listings[listing.skill_id] = listing
        
        if self.registry_path:
            self._save_registry()
        
        return True
    
    def get_skill(self, skill_id: str) -> Optional[SkillListing]:
        """Get a skill listing by ID."""
        return self.listings.get(skill_id)
    
    def search_skills(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        author: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_trust_score: Optional[float] = None,
        sort_by: str = "trust_score",
        limit: int = 20,
        offset: int = 0
    ) -> List[SkillListing]:
        """Search for skills with various criteria."""
        results = list(self.listings.values())
        
        # Apply filters
        if query:
            query_lower = query.lower()
            results = [
                skill for skill in results
                if query_lower in skill.name.lower()
                or query_lower in skill.description.lower()
                or any(query_lower in tag.lower() for tag in skill.tags)
            ]
        
        if category:
            results = [skill for skill in results if skill.category == category]
        
        if author:
            results = [skill for skill in results if skill.author == author]
        
        if tags:
            results = [
                skill for skill in results
                if all(tag in skill.tags for tag in tags)
            ]
        
        if min_trust_score:
            results = [
                skill for skill in results
                if skill.trust_score >= min_trust_score
            ]
        
        # Sort results
        if sort_by == "trust_score":
            results.sort(key=lambda x: x.trust_score, reverse=True)
        elif sort_by == "downloads":
            results.sort(key=lambda x: x.download_count, reverse=True)
        elif sort_by == "stars":
            results.sort(key=lambda x: x.star_count, reverse=True)
        elif sort_by == "rating":
            results.sort(key=lambda x: x.rating, reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda x: x.created_at, reverse=True)
        elif sort_by == "updated":
            results.sort(key=lambda x: x.updated_at, reverse=True)
        
        # Apply pagination
        paginated = results[offset:offset + limit]
        
        return paginated
    
    def get_featured_skills(self, limit: int = 10) -> List[SkillListing]:
        """Get featured skills."""
        featured = [
            skill for skill in self.listings.values()
            if skill.verification_status == SkillStatus.FEATURED
        ]
        
        featured.sort(key=lambda x: x.trust_score, reverse=True)
        return featured[:limit]
    
    def get_categories(self) -> List[str]:
        """Get available categories."""
        categories = set()
        for listing in self.listings.values():
            categories.add(listing.category)
        return sorted(categories)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get marketplace statistics."""
        total = len(self.listings)
        verified = sum(
            1 for skill in self.listings.values()
            if skill.verification_status in [SkillStatus.VERIFIED, SkillStatus.FEATURED]
        )
        total_downloads = sum(
            skill.download_count for skill in self.listings.values()
        )
        
        categories = {}
        for skill in self.listings.values():
            categories[skill.category] = categories.get(skill.category, 0) + 1
        
        return {
            "total_skills": total,
            "verified_skills": verified,
            "total_downloads": total_downloads,
            "categories": categories,
            "authors": len(set(s.author for s in self.listings.values()))
        }
    
    def _save_registry(self):
        """Save registry to file."""
        if not self.registry_path:
            return
        
        data = {
            skill_id: listing.to_dict()
            for skill_id, listing in self.listings.items()
        }
        
        registry_file = Path(self.registry_path) / "registry.json"
        registry_file.parent.mkdir(parents=True, exist_ok=True)
        registry_file.write_text(json.dumps(data, indent=2))
    
    def _load_registry(self):
        """Load registry from file."""
        if not self.registry_path:
            return
        
        registry_file = Path(self.registry_path) / "registry.json"
        if not registry_file.exists():
            return
        
        try:
            data = json.loads(registry_file.read_text())
            for skill_id, listing_data in data.items():
                self.listings[skill_id] = SkillListing.from_dict(listing_data)
        except Exception as e:
            print(f"Error loading registry: {e}")


class SkillDownloader:
    """Downloader for skills from various storage backends."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or str(Path.home() / ".trustchain" / "skills")
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
    
    async def download_skill(
        self,
        listing: SkillListing,
        force: bool = False
    ) -> Optional[str]:
        """Download a skill from its storage backend."""
        # Check cache
        cache_path = Path(self.cache_dir) / f"{listing.skill_id}_{listing.version}"
        if cache_path.exists() and not force:
            return str(cache_path)
        
        # Download based on storage backend
        if listing.storage_backend == StorageBackend.LOCAL:
            if listing.storage_url:
                return await self._download_local(listing.storage_url, cache_path)
        elif listing.storage_backend == StorageBackend.GITHUB:
            return await self._download_github(listing.storage_url, cache_path)
        elif listing.storage_backend == StorageBackend.IPFS:
            return await self._download_ipfs(listing.storage_url, cache_path)
        elif listing.storage_backend == StorageBackend.HTTP:
            return await self._download_http(listing.storage_url, cache_path)
        
        return None
    
    async def _download_local(self, url: str, cache_path: Path) -> Optional[str]:
        """Download from local file system."""
        source = Path(url)
        if not source.exists():
            return None
        
        try:
            if source.is_file():
                # Unzip if it's a zip file
                if source.suffix == ".zip":
                    with zipfile.ZipFile(source, 'r') as zipf:
                        zipf.extractall(cache_path)
                    return str(cache_path)
                else:
                    shutil.copy2(source, cache_path / source.name)
                    return str(cache_path)
            elif source.is_dir():
                return str(source)
            
            return None
        except Exception as e:
            print(f"Error downloading from local: {e}")
            return None
    
    async def _download_github(self, url: str, cache_path: Path) -> Optional[str]:
        """Download from GitHub."""
        try:
            # Clone or download repository
            async with httpx.AsyncClient() as client:
                # GitHub returns zip archive
                response = await client.get(url, follow_redirects=True)
                
                if response.status_code == 200:
                    # Save and extract
                    zip_path = cache_path / "repo.zip"
                    zip_path.parent.mkdir(parents=True, exist_ok=True)
                    zip_path.write_bytes(response.content)
                    
                    with zipfile.ZipFile(zip_path, 'r') as zipf:
                        zipf.extractall(cache_path)
                    
                    zip_path.unlink()  # Clean up zip
                    return str(cache_path)
            
            return None
        except Exception as e:
            print(f"Error downloading from GitHub: {e}")
            return None
    
    async def _download_ipfs(self, url: str, cache_path: Path) -> Optional[str]:
        """Download from IPFS."""
        try:
            async with httpx.AsyncClient() as client:
                # Try local IPFS gateway first
                local_url = f"http://localhost:8080/ipfs/{url}"
                try:
                    response = await client.get(local_url, timeout=5)
                    if response.status_code == 200:
                        content = response.content
                        # Determine if it's a zip or directory
                        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as tmp:
                            tmp.write(content)
                            tmp_path = Path(tmp.name)
                        
                        if content[:2] == b'PK':  # ZIP file
                            with zipfile.ZipFile(tmp_path, 'r') as zipf:
                                zipf.extractall(cache_path)
                            tmp_path.unlink()
                            return str(cache_path)
                        else:
                            # Single file
                            output_file = cache_path / "skill.md"
                            output_file.write_bytes(content)
                            return str(cache_path)
                except:
                    pass
                
                # Try public IPFS gateway
                public_url = f"https://ipfs.io/ipfs/{url}"
                response = await client.get(public_url)
                
                if response.status_code == 200:
                    with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as tmp:
                        tmp.write(response.content)
                        tmp_path = Path(tmp.name)
                    
                    if response.content[:2] == b'PK':  # ZIP file
                        with zipfile.ZipFile(tmp_path, 'r') as zipf:
                            zipf.extractall(cache_path)
                        tmp_path.unlink()
                        return str(cache_path)
            
            return None
        except Exception as e:
            print(f"Error downloading from IPFS: {e}")
            return None
    
    async def _download_http(self, url: str, cache_path: Path) -> Optional[str]:
        """Download via HTTP."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as tmp:
                        tmp.write(response.content)
                        tmp_path = Path(tmp.name)
                    
                    if response.content[:2] == b'PK':  # ZIP file
                        with zipfile.ZipFile(tmp_path, 'r') as zipf:
                            zipf.extractall(cache_path)
                        tmp_path.unlink()
                        return str(cache_path)
                    else:
                        # Single file
                        output_file = cache_path / "skill.md"
                        output_file.write_bytes(response.content)
                        return str(cache_path)
            
            return None
        except Exception as e:
            print(f"Error downloading via HTTP: {e}")
            return None
    
    def clear_cache(self, skill_id: Optional[str] = None):
        """Clear download cache."""
        if skill_id:
            # Clear specific skill
            for cache_dir in Path(self.cache_dir).iterdir():
                if cache_dir.name.startswith(skill_id):
                    shutil.rmtree(cache_dir)
        else:
            # Clear all
            shutil.rmtree(self.cache_dir)
            Path(self.cache_dir).mkdir(parents=True, exist_ok=True)


class SkillPublisher:
    """Publisher for skills to the marketplace."""
    
    def __init__(
        self,
        registry: SkillRegistry,
        storage_path: str
    ):
        self.registry = registry
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def publish_skill(
        self,
        skill_path: Path,
        metadata: Dict[str, Any],
        trust_engine: Optional[Any] = None
    ) -> Optional[SkillListing]:
        """Publish a skill to the marketplace."""
        
        # Copy skill to storage
        skill_id = hashlib.sha256(
            f"{metadata['name']}:{metadata['version']}".encode()
        ).hexdigest()[:16]
        
        storage_dir = self.storage_path / skill_id / metadata["version"]
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy skill files
        if skill_path.is_dir():
            shutil.copytree(skill_path, storage_dir, dirs_exist_ok=True)
        else:
            shutil.copy2(skill_path, storage_dir)
        
        # Calculate size
        total_size = sum(
            f.stat().st_size
            for f in storage_dir.rglob("*")
            if f.is_file()
        )
        
        # Calculate content hash
        content_hash = self._calculate_hash(storage_dir)
        
        # Calculate trust score
        trust_score = 0.0
        if trust_engine:
            try:
                # This would call the trust engine's skill scoring
                trust_score = trust_engine.score_skill({
                    "name": metadata["name"],
                    "version": metadata["version"],
                    "path": str(storage_dir)
                })
            except:
                trust_score = 50.0  # Default score
        
        # Create listing
        listing = SkillListing(
            skill_id=skill_id,
            name=metadata["name"],
            version=metadata["version"],
            author=metadata["author"],
            description=metadata["description"],
            tags=metadata.get("tags", []),
            category=metadata.get("category", "uncategorized"),
            trust_score=trust_score,
            verification_status=SkillStatus.LISTED,
            storage_backend=StorageBackend.LOCAL,
            storage_url=str(storage_dir),
            content_hash=content_hash,
            size_bytes=total_size,
            dependencies=metadata.get("dependencies", []),
            compatible_platforms=metadata.get("platforms", []),
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            security_audit=metadata.get("security_audit")
        )
        
        # Register in marketplace
        self.registry.register_skill(listing)
        
        return listing
    
    def _calculate_hash(self, directory: Path) -> str:
        """Calculate content hash of a directory."""
        hasher = hashlib.sha256()
        
        for file_path in sorted(directory.rglob("*")):
            if file_path.is_file():
                hasher.update(str(file_path.relative_to(directory)).encode())
                hasher.update(file_path.read_bytes())
        
        return hasher.hexdigest()
    
    def update_skill(
        self,
        skill_id: str,
        new_skill_path: Path,
        metadata: Dict[str, Any]
    ) -> Optional[SkillListing]:
        """Update an existing skill to a new version."""
        existing = self.registry.get_skill(skill_id)
        if not existing:
            return None
        
        # Publish new version
        return self.publish_skill(new_skill_path, metadata)


class ReputationTracker:
    """Track author reputation based on skill quality."""
    
    def __init__(self):
        self.reputations: Dict[str, Dict[str, Any]] = {}
    
    def calculate_reputation(
        self,
        skills: List[SkillListing]
    ) -> float:
        """Calculate author reputation based on their skills."""
        if not skills:
            return 0.0
        
        score = 0.0
        
        for skill in skills:
            # Factors in reputation
            # 1. Skill quality (trust score)
            score += skill.trust_score * 0.3
            
            # 2. Community acceptance (downloads/stars)
            if skill.download_count > 0:
                score += min(10, skill.download_count / 100) * 0.2
            
            if skill.star_count > 0:
                score += min(10, skill.star_count / 10) * 0.2
            
            # 3. Review ratings
            if skill.rating > 0:
                score += skill.rating * 0.3
        
        # Normalize by number of skills
        avg_score = score / len(skills)
        
        return round(min(100, avg_score), 1)
    
    def update_author_stats(self, author: str, listing: SkillListing):
        """Update author statistics."""
        if author not in self.reputations:
            self.reputations[author] = {
                "skill_count": 0,
                "total_downloads": 0,
                "total_stars": 0,
                "average_trust_score": 0.0,
                "reputation_score": 0.0
            }
        
        stats = self.reputations[author]
        stats["skill_count"] += 1
        stats["total_downloads"] += listing.download_count
        stats["total_stars"] += listing.star_count
        
        # Update average trust score
        author_skills = [
            s for s in self.registry.listings.values() if s.author == author
        ]
        if author_skills:
            stats["average_trust_score"] = sum(
                s.trust_score for s in author_skills
            ) / len(author_skills)
        
        stats["reputation_score"] = self.calculate_reputation(
            [s for s in self.registry.listings.values() if s.author == author]
        )


class MarketplaceAPI:
    """API for the Skill Marketplace."""
    
    def __init__(
        self,
        registry: SkillRegistry,
        downloader: SkillDownloader,
        publisher: SkillPublisher,
        reputation_tracker: ReputationTracker
    ):
        self.registry = registry
        self.downloader = downloader
        self.publisher = publisher
        self.reputation = reputation_tracker
    
    async def search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for skills."""
        results = self.registry.search_skills(
            query=params.get("query"),
            category=params.get("category"),
            author=params.get("author"),
            tags=params.get("tags"),
            min_trust_score=params.get("min_trust_score"),
            sort_by=params.get("sort_by", "trust_score"),
            limit=params.get("limit", 20),
            offset=params.get("offset", 0)
        )
        
        return {
            "success": True,
            "results": [skill.to_dict() for skill in results],
            "count": len(results),
            "total": len(self.registry.listings)
        }
    
    async def download(self, skill_id: str) -> Dict[str, Any]:
        """Download a skill."""
        listing = self.registry.get_skill(skill_id)
        if not listing:
            return {"success": False, "error": "Skill not found"}
        
        # Increment download count
        listing.download_count += 1
        self.registry._save_registry()
        
        # Download skill
        path = await self.downloader.download_skill(listing)
        if not path:
            return {"success": False, "error": "Download failed"}
        
        return {
            "success": True,
            "skill_id": skill_id,
            "path": path,
            "version": listing.version
        }
    
    async def publish(self, skill_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Publish a skill."""
        listing = self.publisher.publish_skill(
            Path(skill_path),
            metadata
        )
        
        if not listing:
            return {"success": False, "error": "Publishing failed"}
        
        # Update author reputation
        self.reputation.update_author_stats(metadata["author"], listing)
        
        return {
            "success": True,
            "skill_id": listing.skill_id,
            "listing": listing.to_dict()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get marketplace statistics."""
        return self.registry.get_stats()
    
    def get_categories(self) -> Dict[str, Any]:
        """Get available categories."""
        return {
            "success": True,
            "categories": self.registry.get_categories()
        }


# Export main classes
__all__ = [
    "StorageBackend",
    "SkillStatus",
    "SkillListing",
    "SkillRegistry",
    "SkillDownloader",
    "SkillPublisher",
    "ReputationTracker",
    "MarketplaceAPI",
]