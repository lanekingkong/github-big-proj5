"""
Universal Skill Protocol (USP) v1.0 — Core Specification

The USP defines a write-once-run-anywhere format for AI agent skills.
This is the reference implementation of the USP parser and validator.
"""

from __future__ import annotations

import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator, root_validator
from datetime import datetime
import hashlib
import re


class SkillType(str, Enum):
    """Types of skills supported by the USP."""
    CODE_REVIEW = "code-review"
    CODE_GENERATION = "code-generation"
    DATA_ANALYSIS = "data-analysis"
    SYSTEM_OPERATION = "system-operation"
    WEB_SCRAPING = "web-scraping"
    API_INTEGRATION = "api-integration"
    CUSTOM = "custom"


class PlatformCompatibility(BaseModel):
    """Platform compatibility matrix for a skill."""
    claude_code: bool = True
    codex_cli: bool = True
    openclaw: bool = True
    gemini_cli: bool = True
    cursor: bool = True
    custom_agent: bool = True


class SkillMetadata(BaseModel):
    """Core metadata for a USP skill."""
    name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: str = Field(..., min_length=10, max_length=500)
    author: str
    license: str = "MIT"
    type: SkillType = SkillType.CUSTOM
    tags: List[str] = Field(default_factory=list)
    platforms: PlatformCompatibility = Field(default_factory=PlatformCompatibility)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Dependencies
    requires: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    
    # Trust metrics (populated by Trust Engine)
    trust_score: Optional[float] = Field(None, ge=0, le=100)
    security_audit_passed: bool = False
    performance_benchmark: Optional[float] = None  # ops/sec
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "code-reviewer",
                "version": "1.0.0",
                "description": "Automated code review for pull requests",
                "author": "pipecat-ai",
                "type": "code-review",
                "tags": ["github", "security", "quality"],
                "platforms": {
                    "claude_code": True,
                    "codex_cli": True,
                    "openclaw": True,
                    "gemini_cli": True,
                    "cursor": True,
                    "custom_agent": True
                }
            }
        }


class SkillInstruction(BaseModel):
    """The main instruction content of a skill."""
    overview: str
    prerequisites: List[str] = Field(default_factory=list)
    usage_examples: List[str] = Field(default_factory=list)
    
    # Agent behavior configuration
    agent_assumptions: List[str] = Field(default_factory=list)
    tool_requirements: List[str] = Field(default_factory=list)
    error_handling: Dict[str, str] = Field(default_factory=dict)
    
    # Progressive disclosure sections
    quick_start: str = ""
    advanced_usage: str = ""
    troubleshooting: str = ""
    
    # Localization support
    language: str = "en"
    translations: Dict[str, Dict[str, str]] = Field(default_factory=dict)


class SkillImplementation(BaseModel):
    """Implementation details and files for the skill."""
    main_file: str = "SKILL.md"  # The primary skill file
    supporting_files: List[str] = Field(default_factory=list)
    scripts: Dict[str, str] = Field(default_factory=dict)  # name -> path
    assets: Dict[str, str] = Field(default_factory=dict)  # name -> path
    
    # Runtime requirements
    python_version: Optional[str] = None
    node_version: Optional[str] = None
    system_dependencies: List[str] = Field(default_factory=list)
    
    # Test suite
    test_files: List[str] = Field(default_factory=list)
    test_command: Optional[str] = None


class UniversalSkill(BaseModel):
    """Complete Universal Skill definition."""
    metadata: SkillMetadata
    instruction: SkillInstruction
    implementation: SkillImplementation
    
    # Internal tracking
    skill_id: str = Field(default_factory=lambda: hashlib.sha256().hexdigest()[:16])
    file_hash: Optional[str] = None
    validated_at: Optional[datetime] = None
    
    @root_validator(pre=True)
    def generate_skill_id(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a deterministic skill ID based on name, author, and version."""
        if "skill_id" not in values:
            name = values.get("metadata", {}).get("name", "")
            author = values.get("metadata", {}).get("author", "")
            version = values.get("metadata", {}).get("version", "")
            
            if name and author and version:
                skill_str = f"{name}:{author}:{version}"
                values["skill_id"] = hashlib.sha256(skill_str.encode()).hexdigest()[:16]
        
        return values
    
    @validator("metadata.tags")
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Ensure tags are lowercase and alphanumeric with hyphens."""
        validated_tags = []
        for tag in v:
            # Convert to lowercase, replace spaces with hyphens
            clean_tag = tag.lower().replace(" ", "-")
            # Remove any non-alphanumeric or hyphen characters
            clean_tag = re.sub(r"[^a-z0-9-]", "", clean_tag)
            if clean_tag and clean_tag not in validated_tags:
                validated_tags.append(clean_tag)
        return validated_tags


class USPParser:
    """Parser for USP skill files and directories."""
    
    def __init__(self, trust_engine: Optional[Any] = None):
        self.trust_engine = trust_engine
    
    def parse_skill(self, skill_path: Union[str, Path]) -> UniversalSkill:
        """Parse a skill directory or single skill file."""
        skill_path = Path(skill_path)
        
        if skill_path.is_dir():
            return self._parse_skill_directory(skill_path)
        elif skill_path.is_file():
            return self._parse_skill_file(skill_path)
        else:
            raise FileNotFoundError(f"Skill path not found: {skill_path}")
    
    def _parse_skill_directory(self, directory: Path) -> UniversalSkill:
        """Parse a skill directory containing SKILL.md and supporting files."""
        skill_file = directory / "SKILL.md"
        if not skill_file.exists():
            # Look for any .md file as the main skill file
            md_files = list(directory.glob("*.md"))
            if not md_files:
                raise ValueError(f"No SKILL.md or .md file found in {directory}")
            skill_file = md_files[0]
        
        return self._parse_skill_file(skill_file, directory)
    
    def _parse_skill_file(
        self, 
        skill_file: Path, 
        base_dir: Optional[Path] = None
    ) -> UniversalSkill:
        """Parse a skill markdown file with YAML frontmatter."""
        base_dir = base_dir or skill_file.parent
        
        content = skill_file.read_text(encoding="utf-8")
        
        # Parse YAML frontmatter (between --- markers)
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                yaml_content = parts[1].strip()
                markdown_content = parts[2].strip()
            else:
                raise ValueError("Invalid YAML frontmatter format")
        else:
            # No frontmatter, treat entire file as markdown
            yaml_content = ""
            markdown_content = content
        
        # Parse YAML
        metadata_dict = yaml.safe_load(yaml_content) if yaml_content else {}
        
        # Extract metadata
        metadata = SkillMetadata(**metadata_dict)
        
        # Parse markdown content for instruction sections
        instruction = self._parse_markdown_instruction(markdown_content)
        
        # Scan for supporting files
        implementation = self._scan_implementation_files(base_dir, skill_file)
        
        # Create the skill
        skill = UniversalSkill(
            metadata=metadata,
            instruction=instruction,
            implementation=implementation
        )
        
        # Calculate file hash
        skill.file_hash = self._calculate_file_hash(skill_file, base_dir)
        
        # Run trust validation if trust engine is available
        if self.trust_engine:
            skill.metadata.trust_score = self.trust_engine.score_skill(skill)
            skill.validated_at = datetime.utcnow()
        
        return skill
    
    def _parse_markdown_instruction(self, markdown: str) -> SkillInstruction:
        """Parse markdown content into structured instruction sections."""
        # Simple parsing based on headings
        lines = markdown.split("\n")
        sections = {}
        current_section = None
        current_content = []
        
        for line in lines:
            if line.startswith("# "):
                # Main title, skip
                continue
            elif line.startswith("## "):
                # Save previous section
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                
                # Start new section
                current_section = line[3:].lower().replace(" ", "_")
                current_content = []
            elif current_section is not None:
                current_content.append(line)
            else:
                # Content before first section is overview
                if "overview" not in sections:
                    sections["overview"] = ""
                sections["overview"] += line + "\n"
        
        # Save last section
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()
        
        # Map sections to SkillInstruction fields
        return SkillInstruction(
            overview=sections.get("overview", ""),
            prerequisites=self._parse_list_section(sections.get("prerequisites", "")),
            usage_examples=self._parse_list_section(sections.get("usage_examples", "")),
            agent_assumptions=self._parse_list_section(sections.get("agent_assumptions", "")),
            tool_requirements=self._parse_list_section(sections.get("tool_requirements", "")),
            error_handling=self._parse_error_handling(sections.get("error_handling", "")),
            quick_start=sections.get("quick_start", ""),
            advanced_usage=sections.get("advanced_usage", ""),
            troubleshooting=sections.get("troubleshooting", "")
        )
    
    def _parse_list_section(self, content: str) -> List[str]:
        """Parse a markdown list section into a list of strings."""
        items = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                items.append(line[2:].strip())
            elif line.startswith("1. "):
                items.append(line[3:].strip())
        return items
    
    def _parse_error_handling(self, content: str) -> Dict[str, str]:
        """Parse error handling section into a dictionary."""
        errors = {}
        current_error = None
        current_description = []
        
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("### "):
                # Save previous error
                if current_error:
                    errors[current_error] = "\n".join(current_description).strip()
                
                # Start new error
                current_error = line[4:].strip()
                current_description = []
            elif current_error and line:
                current_description.append(line)
        
        # Save last error
        if current_error:
            errors[current_error] = "\n".join(current_description).strip()
        
        return errors
    
    def _scan_implementation_files(
        self, 
        base_dir: Path, 
        skill_file: Path
    ) -> SkillImplementation:
        """Scan directory for supporting implementation files."""
        supporting_files = []
        scripts = {}
        assets = {}
        test_files = []
        
        for file_path in base_dir.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(base_dir)
                
                # Skip the main skill file
                if file_path.samefile(skill_file):
                    continue
                
                # Categorize files
                if file_path.suffix in [".py", ".js", ".ts", ".sh", ".bat"]:
                    if "test" in file_path.stem.lower():
                        test_files.append(str(rel_path))
                    else:
                        scripts[file_path.stem] = str(rel_path)
                elif file_path.suffix in [".png", ".jpg", ".svg", ".gif"]:
                    assets[file_path.stem] = str(rel_path)
                else:
                    supporting_files.append(str(rel_path))
        
        # Try to detect Python/Node version requirements
        python_version = None
        node_version = None
        
        pyproject_path = base_dir / "pyproject.toml"
        package_json_path = base_dir / "package.json"
        
        if pyproject_path.exists():
            try:
                import tomli
                with open(pyproject_path, "rb") as f:
                    pyproject = tomli.load(f)
                python_version = pyproject.get("project", {}).get("requires-python")
            except:
                pass
        
        if package_json_path.exists():
            try:
                package_json = json.loads(package_json_path.read_text())
                node_version = package_json.get("engines", {}).get("node")
            except:
                pass
        
        return SkillImplementation(
            main_file=str(skill_file.relative_to(base_dir)),
            supporting_files=supporting_files,
            scripts=scripts,
            assets=assets,
            python_version=python_version,
            node_version=node_version,
            test_files=test_files
        )
    
    def _calculate_file_hash(self, skill_file: Path, base_dir: Path) -> str:
        """Calculate a hash of all skill files for integrity checking."""
        hasher = hashlib.sha256()
        
        # Include the main skill file
        hasher.update(skill_file.read_bytes())
        
        # Include all supporting files
        for file_path in base_dir.rglob("*"):
            if file_path.is_file() and not file_path.samefile(skill_file):
                hasher.update(str(file_path.relative_to(base_dir)).encode())
                hasher.update(file_path.read_bytes())
        
        return hasher.hexdigest()


class USPValidator:
    """Validator for USP compliance and quality."""
    
    def __init__(self):
        self.checks = [
            self._check_required_fields,
            self._check_naming_conventions,
            self._check_version_format,
            self._check_platform_compatibility,
            self._check_security_issues,
            self._check_performance_indicators,
        ]
    
    def validate(self, skill: UniversalSkill) -> Dict[str, Any]:
        """Validate a skill and return detailed results."""
        results = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "score": 0,
            "checks": []
        }
        
        for check in self.checks:
            try:
                check_result = check(skill)
                results["checks"].append(check_result)
                
                if check_result["status"] == "error":
                    results["valid"] = False
                    results["errors"].extend(check_result["issues"])
                elif check_result["status"] == "warning":
                    results["warnings"].extend(check_result["issues"])
            except Exception as e:
                results["valid"] = False
                results["errors"].append(f"Check failed: {str(e)}")
        
        # Calculate overall score
        if results["valid"]:
            passed_checks = sum(1 for c in results["checks"] if c["status"] == "pass")
            results["score"] = int((passed_checks / len(self.checks)) * 100)
        
        return results
    
    def _check_required_fields(self, skill: UniversalSkill) -> Dict[str, Any]:
        """Check that all required fields are present and valid."""
        issues = []
        
        # Check metadata fields
        if not skill.metadata.name:
            issues.append("Skill name is required")
        
        if not skill.metadata.description:
            issues.append("Skill description is required")
        elif len(skill.metadata.description) < 10:
            issues.append("Skill description should be at least 10 characters")
        
        if not skill.metadata.author:
            issues.append("Skill author is required")
        
        # Check instruction fields
        if not skill.instruction.overview:
            issues.append("Skill overview is required")
        
        status = "error" if issues else "pass"
        return {
            "name": "required_fields",
            "status": status,
            "issues": issues
        }
    
    def _check_naming_conventions(self, skill: UniversalSkill) -> Dict[str, Any]:
        """Check naming conventions for skill name and tags."""
        issues = []
        
        # Skill name should be kebab-case
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", skill.metadata.name):
            issues.append("Skill name should be in kebab-case (lowercase with hyphens)")
        
        # Tags should be lowercase alphanumeric with hyphens
        for tag in skill.metadata.tags:
            if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", tag):
                issues.append(f"Tag '{tag}' should be lowercase alphanumeric with hyphens")
        
        status = "warning" if issues else "pass"
        return {
            "name": "naming_conventions",
            "status": status,
            "issues": issues
        }
    
    def _check_version_format(self, skill: UniversalSkill) -> Dict[str, Any]:
        """Check that version follows semantic versioning."""
        issues = []
        
        if not re.match(r"^\d+\.\d+\.\d+$", skill.metadata.version):
            issues.append("Version should follow semantic versioning (X.Y.Z)")
        
        status = "error" if issues else "pass"
        return {
            "name": "version_format",
            "status": status,
            "issues": issues
        }
    
    def _check_platform_compatibility(self, skill: UniversalSkill) -> Dict[str, Any]:
        """Check that skill declares platform compatibility."""
        issues = []
        
        platforms = skill.metadata.platforms
        compatible_platforms = [
            name for name, value in platforms.dict().items() 
            if value is True
        ]
        
        if not compatible_platforms:
            issues.append("Skill should be compatible with at least one platform")
        
        status = "warning" if issues else "pass"
        return {
            "name": "platform_compatibility",
            "status": status,
            "issues": issues
        }
    
    def _check_security_issues(self, skill: UniversalSkill) -> Dict[str, Any]:
        """Check for potential security issues in skill implementation."""
        issues = []
        
        # Check for dangerous patterns in scripts
        for script_name, script_path in skill.implementation.scripts.items():
            if script_path.endswith(".sh") or script_path.endswith(".bat"):
                # This would require actual file content analysis
                # For now, just flag for manual review
                issues.append(f"Shell script '{script_name}' should be reviewed for security")
        
        status = "warning" if issues else "pass"
        return {
            "name": "security_issues",
            "status": status,
            "issues": issues
        }
    
    def _check_performance_indicators(self, skill: UniversalSkill) -> Dict[str, Any]:
        """Check for performance-related indicators."""
        issues = []
        
        # Check if skill has performance benchmark
        if skill.metadata.performance_benchmark is None:
            issues.append("Consider adding performance benchmarks for better trust scoring")
        
        status = "warning" if issues else "pass"
        return {
            "name": "performance_indicators",
            "status": status,
            "issues": issues
        }


# Export main classes
__all__ = [
    "SkillType",
    "PlatformCompatibility",
    "SkillMetadata",
    "SkillInstruction",
    "SkillImplementation",
    "UniversalSkill",
    "USPParser",
    "USPValidator",
]