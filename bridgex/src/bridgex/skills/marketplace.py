"""
Skill Marketplace - Central registry and discovery for AI execution skills.
Inspired by npm registry and Docker Hub, specialized for AI skills.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin

from pydantic import BaseModel, Field, HttpUrl

from bridgex.utils.exceptions import BridgeXError, SkillNotFoundError

logger = logging.getLogger(__name__)


class SkillMetadata(BaseModel):
    """Metadata for a skill."""
    name: str = Field(..., description="Unique skill name")
    version: str = Field("1.0.0", description="Skill version")
    description: str = Field(..., description="Skill description")
    author: str = Field(..., description="Skill author")
    license: str = Field("MIT", description="License type")
    tags: List[str] = Field(default_factory=list, description="Skill tags")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Skill dependencies")
    parameters_schema: Dict[str, Any] = Field(default_factory=dict, description="Parameter schema")
    return_schema: Dict[str, Any] = Field(default_factory=dict, description="Return schema")
    risk_level: str = Field("low", description="Risk level: low, medium, high")
    requires_approval: bool = Field(False, description="Whether skill requires human approval")
    created_at: str = Field(default_factory=lambda: str(datetime.now().isoformat()))
    updated_at: str = Field(default_factory=lambda: str(datetime.now().isoformat()))


class SkillPackage(BaseModel):
    """Complete skill package."""
    metadata: SkillMetadata
    code: str = Field(..., description="Skill implementation code")
    tests: Optional[str] = Field(None, description="Test code")
    examples: List[Dict[str, Any]] = Field(default_factory=list, description="Usage examples")
    documentation: Optional[str] = Field(None, description="Documentation")
    icon: Optional[str] = Field(None, description="Skill icon")
    
    class Config:
        arbitrary_types_allowed = True


class SkillRegistryEntry(BaseModel):
    """Entry in the skill registry."""
    skill: SkillPackage
    installed: bool = Field(False, description="Whether skill is installed")
    installed_version: Optional[str] = Field(None, description="Installed version")
    last_used: Optional[str] = Field(None, description="Last usage timestamp")
    usage_count: int = Field(0, description="Usage count")
    rating: Optional[float] = Field(None, description="User rating")
    verified: bool = Field(False, description="Whether skill is verified by BridgeX")


class SkillMarketplace:
    """Central skill marketplace and registry.
    
    Features:
    - Skill discovery and search
    - Skill installation and management
    - Version control
    - Dependency resolution
    - Skill verification
    """
    
    def __init__(self, registry_path: Optional[str] = None):
        """Initialize the skill marketplace.
        
        Args:
            registry_path: Path to skill registry storage
        """
        self.registry_path = registry_path or os.path.expanduser("~/.bridgex/skills")
        self.local_registry: Dict[str, SkillRegistryEntry] = {}
        self.remote_registries: List[str] = [
            "https://skills.bridgex.ai/api/v1",
            "https://raw.githubusercontent.com/bridgex-ai/skills/main",
        ]
        
        # Skill categories
        self.categories = {
            "file_operations": ["read", "write", "copy", "move", "delete"],
            "data_processing": ["transform", "filter", "aggregate", "analyze"],
            "api_integration": ["rest", "graphql", "websocket", "rpc"],
            "ai_ml": ["classify", "generate", "summarize", "translate"],
            "system": ["execute", "monitor", "schedule", "notify"],
            "communication": ["email", "slack", "teams", "sms"],
            "business": ["invoice", "payment", "crm", "erp"],
        }
        
        logger.info(f"Skill Marketplace initialized with registry: {self.registry_path}")
    
    async def initialize(self) -> None:
        """Initialize the marketplace."""
        # Create registry directory
        os.makedirs(self.registry_path, exist_ok=True)
        
        # Load local registry
        await self._load_local_registry()
        
        # Sync with remote registries
        await self._sync_remote_registries()
        
        logger.info(f"Skill Marketplace initialized with {len(self.local_registry)} skills")
    
    async def list_skills(self) -> List[SkillRegistryEntry]:
        """List all available skills in the marketplace.
        
        Returns:
            List of all skill registry entries
        """
        return list(self.local_registry.values())
    
    async def has_skill(self, skill_name: str) -> bool:
        """Check if a skill exists in the marketplace.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            True if skill exists
        """
        return skill_name in self.local_registry
    
    async def search_skills(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        verified_only: bool = False,
        limit: int = 50,
    ) -> List[SkillRegistryEntry]:
        """Search for skills in the marketplace.
        
        Args:
            query: Search query string
            category: Skill category
            tags: Filter by tags
            min_rating: Minimum rating
            verified_only: Only return verified skills
            limit: Maximum number of results
            
        Returns:
            List of matching skills
        """
        results = []
        
        for entry in self.local_registry.values():
            skill = entry.skill
            metadata = skill.metadata
            
            # Apply filters
            if verified_only and not entry.verified:
                continue
            
            if min_rating is not None and (entry.rating or 0) < min_rating:
                continue
            
            if category and not any(tag in metadata.tags for tag in self.categories.get(category, [])):
                continue
            
            if tags and not all(tag in metadata.tags for tag in tags):
                continue
            
            if query:
                # Search in name, description, and tags
                search_text = f"{metadata.name} {metadata.description} {' '.join(metadata.tags)}".lower()
                if query.lower() not in search_text:
                    continue
            
            results.append(entry)
        
        # Sort by relevance (rating * usage_count)
        results.sort(key=lambda x: (x.rating or 0) * x.usage_count, reverse=True)
        
        return results[:limit]
    
    async def get_skill(self, skill_name: str) -> Optional[SkillPackage]:
        """Get a skill by name.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Skill package or None if not found
        """
        if skill_name in self.local_registry:
            entry = self.local_registry[skill_name]
            entry.usage_count += 1
            entry.last_used = str(datetime.now().isoformat())
            return entry.skill
        
        # Try to fetch from remote
        try:
            skill = await self._fetch_remote_skill(skill_name)
            if skill:
                await self._register_skill(skill, installed=False)
                return skill
        except Exception as e:
            logger.warning(f"Failed to fetch remote skill {skill_name}: {e}")
        
        return None
    
    async def install_skill(self, skill_name: str, version: Optional[str] = None) -> SkillPackage:
        """Install a skill from the marketplace.
        
        Args:
            skill_name: Name of the skill to install
            version: Specific version to install (default: latest)
            
        Returns:
            Installed skill package
            
        Raises:
            SkillNotFoundError: If skill is not found
        """
        # Check if already installed
        if skill_name in self.local_registry and self.local_registry[skill_name].installed:
            entry = self.local_registry[skill_name]
            if version and entry.skill.metadata.version != version:
                # Need to update version
                return await self._update_skill_version(skill_name, version)
            return entry.skill
        
        # Get skill (will fetch from remote if needed)
        skill = await self.get_skill(skill_name)
        if not skill:
            raise SkillNotFoundError(f"Skill not found: {skill_name}")
        
        # Check version
        if version and skill.metadata.version != version:
            # Try to fetch specific version
            skill = await self._fetch_specific_version(skill_name, version)
            if not skill:
                raise SkillNotFoundError(f"Version {version} not found for skill {skill_name}")
        
        # Install dependencies
        await self._install_dependencies(skill.metadata.dependencies)
        
        # Save skill locally
        skill_path = os.path.join(self.registry_path, skill_name)
        os.makedirs(skill_path, exist_ok=True)
        
        # Save skill package
        package_file = os.path.join(skill_path, "skill.json")
        with open(package_file, "w") as f:
            f.write(skill.json(indent=2))
        
        # Mark as installed
        if skill_name in self.local_registry:
            self.local_registry[skill_name].installed = True
            self.local_registry[skill_name].installed_version = skill.metadata.version
        else:
            self.local_registry[skill_name] = SkillRegistryEntry(
                skill=skill,
                installed=True,
                installed_version=skill.metadata.version,
                last_used=str(datetime.now().isoformat()),
            )
        
        # Save registry
        await self._save_local_registry()
        
        logger.info(f"Skill installed: {skill_name} v{skill.metadata.version}")
        return skill
    
    async def uninstall_skill(self, skill_name: str) -> bool:
        """Uninstall a skill.
        
        Args:
            skill_name: Name of the skill to uninstall
            
        Returns:
            True if uninstalled successfully
        """
        if skill_name not in self.local_registry:
            raise SkillNotFoundError(f"Skill not found: {skill_name}")
        
        # Remove skill files
        skill_path = os.path.join(self.registry_path, skill_name)
        if os.path.exists(skill_path):
            import shutil
            shutil.rmtree(skill_path)
        
        # Update registry
        self.local_registry[skill_name].installed = False
        self.local_registry[skill_name].installed_version = None
        
        await self._save_local_registry()
        
        logger.info(f"Skill uninstalled: {skill_name}")
        return True
    
    async def publish_skill(self, skill: SkillPackage) -> str:
        """Publish a skill to the marketplace.
        
        Args:
            skill: Skill package to publish
            
        Returns:
            Published skill ID
        """
        # Validate skill
        self._validate_skill(skill)
        
        # Register locally
        await self._register_skill(skill, installed=True)
        
        # TODO: Publish to remote registry
        logger.info(f"Skill published locally: {skill.metadata.name}")
        
        return skill.metadata.name
    
    async def verify_skill(self, skill_name: str) -> Dict[str, Any]:
        """Verify a skill for safety and quality.
        
        Args:
            skill_name: Name of the skill to verify
            
        Returns:
            Verification results
        """
        if skill_name not in self.local_registry:
            raise SkillNotFoundError(f"Skill not found: {skill_name}")
        
        entry = self.local_registry[skill_name]
        skill = entry.skill
        
        verification = {
            "skill_name": skill_name,
            "version": skill.metadata.version,
            "checks": [],
            "passed": True,
            "score": 0,
        }
        
        # Check 1: Code safety
        code_checks = self._check_code_safety(skill.code)
        verification["checks"].append({
            "name": "code_safety",
            "passed": code_checks["safe"],
            "details": code_checks["issues"],
        })
        
        if not code_checks["safe"]:
            verification["passed"] = False
        
        # Check 2: Schema validation
        schema_checks = self._check_schema_validity(skill.metadata.parameters_schema)
        verification["checks"].append({
            "name": "schema_validity",
            "passed": schema_checks["valid"],
            "details": schema_checks["issues"],
        })
        
        if not schema_checks["valid"]:
            verification["passed"] = False
        
        # Check 3: Documentation completeness
        doc_checks = self._check_documentation(skill)
        verification["checks"].append({
            "name": "documentation",
            "passed": doc_checks["complete"],
            "details": doc_checks["issues"],
        })
        
        # Check 4: Test coverage
        if skill.tests:
            test_checks = self._check_test_coverage(skill)
            verification["checks"].append({
                "name": "test_coverage",
                "passed": test_checks["adequate"],
                "details": test_checks["issues"],
            })
        
        # Calculate score
        passed_checks = sum(1 for check in verification["checks"] if check["passed"])
        total_checks = len(verification["checks"])
        verification["score"] = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        
        # Update verification status
        if verification["passed"] and verification["score"] >= 80:
            entry.verified = True
        
        return verification
    
    def _validate_skill(self, skill: SkillPackage) -> None:
        """Validate a skill package.
        
        Args:
            skill: Skill package to validate
            
        Raises:
            BridgeXError: If skill is invalid
        """
        # Check required fields
        if not skill.metadata.name:
            raise BridgeXError("Skill name is required")
        
        if not skill.code:
            raise BridgeXError("Skill code is required")
        
        # Check name format
        if not skill.metadata.name.replace("-", "").replace("_", "").isalnum():
            raise BridgeXError("Skill name must be alphanumeric with dashes or underscores")
        
        # Check version format
        import re
        version_pattern = r'^\d+\.\d+\.\d+$'
        if not re.match(version_pattern, skill.metadata.version):
            raise BridgeXError(f"Invalid version format: {skill.metadata.version}. Use semantic versioning (e.g., 1.0.0)")
    
    def _check_code_safety(self, code: str) -> Dict[str, Any]:
        """Check code for safety issues.
        
        Args:
            code: Skill code
            
        Returns:
            Safety check results
        """
        issues = []
        safe = True
        
        # Dangerous patterns to check for
        dangerous_patterns = [
            ("exec(", "Use of exec() is dangerous"),
            ("eval(", "Use of eval() is dangerous"),
            ("__import__", "Dynamic imports are dangerous"),
            ("os.system", "System calls are dangerous"),
            ("subprocess.run", "Subprocess calls are dangerous"),
            ("pickle.loads", "Unpickling untrusted data is dangerous"),
            ("yaml.load", "YAML loading is dangerous without safe loader"),
        ]
        
        for pattern, message in dangerous_patterns:
            if pattern in code:
                issues.append(f"{message}: {pattern}")
                safe = False
        
        return {"safe": safe, "issues": issues}
    
    def _check_schema_validity(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Check parameter schema validity.
        
        Args:
            schema: Parameter schema
            
        Returns:
            Schema validity results
        """
        issues = []
        valid = True
        
        # Basic schema validation
        if not isinstance(schema, dict):
            issues.append("Schema must be a dictionary")
            valid = False
        
        # Check each parameter
        for param_name, param_schema in schema.items():
            if not isinstance(param_schema, dict):
                issues.append(f"Parameter {param_name}: schema must be a dictionary")
                valid = False
                continue
            
            # Check for required fields
            if "type" not in param_schema:
                issues.append(f"Parameter {param_name}: missing 'type' field")
                valid = False
            
            # Check type validity
            valid_types = ["string", "number", "integer", "boolean", "array", "object"]
            if param_schema.get("type") not in valid_types:
                issues.append(f"Parameter {param_name}: invalid type {param_schema.get('type')}")
                valid = False
        
        return {"valid": valid, "issues": issues}
    
    def _check_documentation(self, skill: SkillPackage) -> Dict[str, Any]:
        """Check documentation completeness.
        
        Args:
            skill: Skill package
            
        Returns:
            Documentation check results
        """
        issues = []
        complete = True
        
        metadata = skill.metadata
        
        # Check description
        if not metadata.description or len(metadata.description.strip()) < 10:
            issues.append("Description is too short or missing")
            complete = False
        
        # Check examples
        if not skill.examples:
            issues.append("No usage examples provided")
            complete = False
        
        # Check parameter documentation
        if metadata.parameters_schema and not all(
            param_schema.get("description") for param_schema in metadata.parameters_schema.values()
        ):
            issues.append("Some parameters lack descriptions")
            complete = False
        
        return {"complete": complete, "issues": issues}
    
    def _check_test_coverage(self, skill: SkillPackage) -> Dict[str, Any]:
        """Check test coverage.
        
        Args:
            skill: Skill package
            
        Returns:
            Test coverage results
        """
        issues = []
        adequate = True
        
        # Basic test checks
        if not skill.tests:
            issues.append("No tests provided")
            adequate = False
            return {"adequate": adequate, "issues": issues}
        
        # Check for test functions
        test_functions = ["test_", "def test"]
        has_test_functions = any(func in skill.tests for func in test_functions)
        
        if not has_test_functions:
            issues.append("No test functions found (should start with 'test_')")
            adequate = False
        
        # Check for assertions
        if "assert" not in skill.tests:
            issues.append("Tests should contain assertions")
            adequate = False
        
        return {"adequate": adequate, "issues": issues}
    
    async def _install_dependencies(self, dependencies: Dict[str, str]) -> None:
        """Install skill dependencies.
        
        Args:
            dependencies: Dictionary of package names to versions
        """
        if not dependencies:
            return
        
        import subprocess
        
        for package, version in dependencies.items():
            try:
                # Install using pip
                if version == "*" or version == "latest":
                    cmd = ["pip", "install", package]
                else:
                    cmd = ["pip", "install", f"{package}{version}"]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.warning(f"Failed to install dependency {package}: {result.stderr}")
                else:
                    logger.info(f"Dependency installed: {package}")
                    
            except Exception as e:
                logger.error(f"Error installing dependency {package}: {e}")
    
    async def _fetch_remote_skill(self, skill_name: str) -> Optional[SkillPackage]:
        """Fetch a skill from remote registry.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Skill package or None if not found
        """
        # TODO: Implement actual remote fetching
        # For now, return None to indicate skill needs to be created
        return None
    
    async def _fetch_specific_version(self, skill_name: str, version: str) -> Optional[SkillPackage]:
        """Fetch a specific version of a skill.
        
        Args:
            skill_name: Name of the skill
            version: Specific version
            
        Returns:
            Skill package or None if not found
        """
        # TODO: Implement version-specific fetching
        return None
    
    async def _update_skill_version(self, skill_name: str, version: str) -> SkillPackage:
        """Update a skill to a specific version.
        
        Args:
            skill_name: Name of the skill
            version: Version to update to
            
        Returns:
            Updated skill package
        """
        # Uninstall current version
        await self.uninstall_skill(skill_name)
        
        # Install new version
        return await self.install_skill(skill_name, version)
    
    async def _register_skill(self, skill: SkillPackage, installed: bool = False) -> None:
        """Register a skill in the local registry.
        
        Args:
            skill: Skill package
            installed: Whether the skill is installed
        """
        entry = SkillRegistryEntry(
            skill=skill,
            installed=installed,
            installed_version=skill.metadata.version if installed else None,
            last_used=str(datetime.now().isoformat()) if installed else None,
        )
        
        self.local_registry[skill.metadata.name] = entry
    
    async def _load_local_registry(self) -> None:
        """Load the local registry from disk."""
        registry_file = os.path.join(self.registry_path, "registry.json")
        
        if os.path.exists(registry_file):
            try:
                with open(registry_file, "r") as f:
                    data = json.load(f)
                
                for skill_name, entry_data in data.items():
                    try:
                        skill_data = entry_data["skill"]
                        skill = SkillPackage(**skill_data)
                        entry = SkillRegistryEntry(
                            skill=skill,
                            installed=entry_data.get("installed", False),
                            installed_version=entry_data.get("installed_version"),
                            last_used=entry_data.get("last_used"),
                            usage_count=entry_data.get("usage_count", 0),
                            rating=entry_data.get("rating"),
                            verified=entry_data.get("verified", False),
                        )
                        self.local_registry[skill_name] = entry
                    except Exception as e:
                        logger.warning(f"Failed to load skill {skill_name}: {e}")
                
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
    
    async def _save_local_registry(self) -> None:
        """Save the local registry to disk."""
        registry_file = os.path.join(self.registry_path, "registry.json")
        
        data = {}
        for skill_name, entry in self.local_registry.items():
            data[skill_name] = {
                "skill": entry.skill.dict(),
                "installed": entry.installed,
                "installed_version": entry.installed_version,
                "last_used": entry.last_used,
                "usage_count": entry.usage_count,
                "rating": entry.rating,
                "verified": entry.verified,
            }
        
        try:
            with open(registry_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    async def _sync_remote_registries(self) -> None:
        """Sync with remote registries."""
        # TODO: Implement remote sync
        pass
    
    async def shutdown(self) -> None:
        """Shutdown the marketplace."""
        await self._save_local_registry()
        logger.info("Skill Marketplace shutdown complete")


# Import datetime here to avoid circular import
from datetime import datetime