"""
Context Mapper — Extract implicit business rules and knowledge from legacy codebases.

This module addresses "AI Context Debt" by:
1. Static analysis to extract code patterns and dependencies
2. LLM-powered extraction of business rules and constraints
3. Building a knowledge graph of codebase context
4. Generating context-aware validation rules for AI-generated code
"""

from __future__ import annotations

import ast
import re
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import networkx as nx

import libcst as cst
from tree_sitter import Language, Parser, Node


class ContextType(str, Enum):
    """Types of context extracted from codebases."""
    BUSINESS_RULE = "business_rule"
    ARCHITECTURE_PATTERN = "architecture_pattern"
    DATA_MODEL = "data_model"
    API_CONTRACT = "api_contract"
    SECURITY_CONSTRAINT = "security_constraint"
    PERFORMANCE_REQUIREMENT = "performance_requirement"
    ERROR_HANDLING = "error_handling"
    TEST_PATTERN = "test_pattern"
    DEPLOYMENT_CONFIG = "deployment_config"
    TEAM_CONVENTION = "team_convention"


@dataclass
class ContextRule:
    """A single context rule extracted from the codebase."""
    id: str = field(default_factory=lambda: hashlib.md5().hexdigest()[:16])
    rule_type: ContextType = ContextType.BUSINESS_RULE
    description: str = ""
    
    # Source information
    source_file: Optional[str] = None
    source_line: Optional[int] = None
    source_code: Optional[str] = None
    
    # Confidence and validation
    confidence: float = 0.0  # 0.0-1.0
    validation_required: bool = True
    last_validated: Optional[str] = None
    
    # Relationships
    depends_on: List[str] = field(default_factory=list)
    conflicts_with: List[str] = field(default_factory=list)
    related_rules: List[str] = field(default_factory=list)
    
    # Metadata
    created_by: str = "context_mapper"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # For AI validation
    validation_prompt: Optional[str] = None
    validation_examples: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "rule_type": self.rule_type.value,
            "description": self.description,
            "source_file": self.source_file,
            "source_line": self.source_line,
            "source_code": self.source_code,
            "confidence": self.confidence,
            "validation_required": self.validation_required,
            "last_validated": self.last_validated,
            "depends_on": self.depends_on,
            "conflicts_with": self.conflicts_with,
            "related_rules": self.related_rules,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "validation_prompt": self.validation_prompt,
            "validation_examples": self.validation_examples
        }


class CodebaseAnalyzer:
    """Static analyzer for extracting context from codebases."""
    
    def __init__(self):
        self.parsers = {}
        self._init_parsers()
        
        # Pattern databases
        self.business_patterns = self._load_business_patterns()
        self.security_patterns = self._load_security_patterns()
        self.architecture_patterns = self._load_architecture_patterns()
    
    def _init_parsers(self):
        """Initialize language parsers."""
        try:
            from tree_sitter_languages import get_parser
            
            languages = ["python", "javascript", "typescript", "java", "go"]
            for lang in languages:
                try:
                    parser = get_parser(lang)
                    self.parsers[lang] = parser
                except:
                    pass
        except ImportError:
            # Fallback to simple parsing
            pass
    
    def analyze_directory(self, directory: Path) -> List[ContextRule]:
        """Analyze an entire directory and extract context rules."""
        rules = []
        
        # Supported file extensions
        supported_extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby'
        }
        
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in supported_extensions:
                    language = supported_extensions[ext]
                    file_rules = self.analyze_file(file_path, language)
                    rules.extend(file_rules)
        
        return rules
    
    def analyze_file(self, file_path: Path, language: str = "python") -> List[ContextRule]:
        """Analyze a single file and extract context rules."""
        rules = []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            if language == "python":
                rules.extend(self._analyze_python_file(content, file_path))
            elif language in ["javascript", "typescript"]:
                rules.extend(self._analyze_javascript_file(content, file_path))
            elif language == "java":
                rules.extend(self._analyze_java_file(content, file_path))
            
            # Universal pattern matching
            rules.extend(self._match_universal_patterns(content, file_path))
            
        except Exception as e:
            # Log error but continue
            print(f"Error analyzing {file_path}: {e}")
        
        return rules
    
    def _analyze_python_file(self, content: str, file_path: Path) -> List[ContextRule]:
        """Analyze Python file for context rules."""
        rules = []
        
        try:
            # Parse with AST
            tree = ast.parse(content)
            
            # Business rule extraction
            business_rules = self._extract_python_business_rules(tree, content, file_path)
            rules.extend(business_rules)
            
            # Architecture pattern detection
            architecture_rules = self._detect_python_architecture(tree, content, file_path)
            rules.extend(architecture_rules)
            
            # Security constraint detection
            security_rules = self._detect_python_security(tree, content, file_path)
            rules.extend(security_rules)
            
            # Error handling patterns
            error_rules = self._extract_python_error_handling(tree, content, file_path)
            rules.extend(error_rules)
            
            # Data model extraction
            data_rules = self._extract_python_data_models(tree, content, file_path)
            rules.extend(data_rules)
            
        except SyntaxError:
            # Invalid Python syntax, skip
            pass
        
        return rules
    
    def _extract_python_business_rules(self, tree: ast.AST, content: str, file_path: Path) -> List[ContextRule]:
        """Extract business rules from Python code."""
        rules = []
        
        # Look for business logic in function/method names
        business_keywords = [
            "validate", "check", "verify", "calculate", "compute",
            "process", "handle", "transform", "convert", "format",
            "sanitize", "normalize", "authorize", "authenticate"
        ]
        
        class BusinessRuleVisitor(ast.NodeVisitor):
            def __init__(self, content: str, file_path: Path):
                self.content = content
                self.file_path = file_path
                self.rules = []
            
            def visit_FunctionDef(self, node: ast.FunctionDef):
                # Check if function name contains business keywords
                func_name = node.name.lower()
                for keyword in business_keywords:
                    if keyword in func_name:
                        # Extract function body for context
                        start_line = node.lineno
                        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                        
                        # Get function source
                        lines = self.content.split('\n')
                        func_source = '\n'.join(lines[start_line-1:end_line])
                        
                        # Create context rule
                        rule = ContextRule(
                            rule_type=ContextType.BUSINESS_RULE,
                            description=f"Business logic in function '{node.name}'",
                            source_file=str(self.file_path),
                            source_line=start_line,
                            source_code=func_source[:500],  # Limit length
                            confidence=0.7
                        )
                        
                        # Add validation prompt
                        rule.validation_prompt = (
                            f"When generating code that interacts with {node.name}, "
                            f"ensure it follows the business logic defined in this function. "
                            f"Key considerations: {self._extract_key_considerations(func_source)}"
                        )
                        
                        self.rules.append(rule)
                
                self.generic_visit(node)
            
            def _extract_key_considerations(self, code: str) -> str:
                """Extract key considerations from function code."""
                considerations = []
                
                # Look for validation logic
                if any(keyword in code.lower() for keyword in ["if", "assert", "raise", "except"]):
                    considerations.append("validation logic")
                
                # Look for data transformations
                if any(op in code for op in ["=", "+=", "-=", "*=", "/="]):
                    considerations.append("data transformation")
                
                # Look for external calls
                if any(pattern in code for pattern in ["import", "from ", "def ", "class "]):
                    considerations.append("dependencies on other modules")
                
                return ", ".join(considerations) if considerations else "unknown business logic"
        
        visitor = BusinessRuleVisitor(content, file_path)
        visitor.visit(tree)
        return visitor.rules
    
    def _detect_python_architecture(self, tree: ast.AST, content: str, file_path: Path) -> List[ContextRule]:
        """Detect architecture patterns in Python code."""
        rules = []
        
        class ArchitectureVisitor(ast.NodeVisitor):
            def __init__(self, content: str, file_path: Path):
                self.content = content
                self.file_path = file_path
                self.rules = []
                self.imports = set()
                self.decorators = set()
            
            def visit_Import(self, node: ast.Import):
                for alias in node.names:
                    self.imports.add(alias.name)
                self.generic_visit(node)
            
            def visit_ImportFrom(self, node: ast.ImportFrom):
                if node.module:
                    self.imports.add(node.module)
                self.generic_visit(node)
            
            def visit_FunctionDef(self, node: ast.FunctionDef):
                # Check decorators
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        self.decorators.add(decorator.id)
                    elif isinstance(decorator, ast.Attribute):
                        self.decorators.add(decorator.attr)
                
                self.generic_visit(node)
            
            def visit_ClassDef(self, node: ast.ClassDef):
                # Check class inheritance
                if node.bases:
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_name = base.id
                            # Detect common patterns
                            if "Model" in base_name:
                                rule = ContextRule(
                                    rule_type=ContextType.ARCHITECTURE_PATTERN,
                                    description=f"ORM/Model class '{node.name}' inherits from {base_name}",
                                    source_file=str(self.file_path),
                                    source_line=node.lineno,
                                    confidence=0.8
                                )
                                self.rules.append(rule)
                            elif "View" in base_name or "API" in base_name:
                                rule = ContextRule(
                                    rule_type=ContextType.API_CONTRACT,
                                    description=f"API/View class '{node.name}'",
                                    source_file=str(self.file_path),
                                    source_line=node.lineno,
                                    confidence=0.8
                                )
                                self.rules.append(rule)
                
                self.generic_visit(node)
            
            def generic_visit(self, node: ast.AST):
                # Detect framework patterns
                if "django" in self.imports:
                    self._detect_django_patterns(node)
                elif "flask" in self.imports:
                    self._detect_flask_patterns(node)
                elif "fastapi" in self.imports:
                    self._detect_fastapi_patterns(node)
                
                super().generic_visit(node)
            
            def _detect_django_patterns(self, node: ast.AST):
                # Django-specific patterns
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            if base.id in ["Model", "View", "Form"]:
                                rule = ContextRule(
                                    rule_type=ContextType.ARCHITECTURE_PATTERN,
                                    description=f"Django {base.id} class '{node.name}'",
                                    source_file=str(self.file_path),
                                    source_line=node.lineno,
                                    confidence=0.9
                                )
                                self.rules.append(rule)
            
            def _detect_flask_patterns(self, node: ast.AST):
                # Flask-specific patterns
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if isinstance(decorator.func, ast.Attribute):
                                if decorator.func.attr == "route":
                                    rule = ContextRule(
                                        rule_type=ContextType.API_CONTRACT,
                                        description=f"Flask route '{node.name}'",
                                        source_file=str(self.file_path),
                                        source_line=node.lineno,
                                        confidence=0.9
                                    )
                                    self.rules.append(rule)
            
            def _detect_fastapi_patterns(self, node: ast.AST):
                # FastAPI-specific patterns
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if isinstance(decorator.func, ast.Attribute):
                                if decorator.func.attr in ["get", "post", "put", "delete", "patch"]:
                                    rule = ContextRule(
                                        rule_type=ContextType.API_CONTRACT,
                                        description=f"FastAPI {decorator.func.attr.upper()} endpoint '{node.name}'",
                                        source_file=str(self.file_path),
                                        source_line=node.lineno,
                                        confidence=0.9
                                    )
                                    self.rules.append(rule)
        
        visitor = ArchitectureVisitor(content, file_path)
        visitor.visit(tree)
        return visitor.rules
    
    def _detect_python_security(self, tree: ast.AST, content: str, file_path: Path) -> List[ContextRule]:
        """Detect security constraints in Python code."""
        rules = []
        
        # Security patterns to look for
        security_patterns = [
            (r"password|secret|key|token", "sensitive_data_handling"),
            (r"hash|encrypt|decrypt", "cryptography"),
            (r"auth|login|logout|session", "authentication"),
            (r"permission|role|access", "authorization"),
            (r"sanitize|escape|validate", "input_validation"),
            (r"ssl|tls|https", "transport_security"),
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            for pattern, rule_type in security_patterns:
                if re.search(pattern, line_lower):
                    rule = ContextRule(
                        rule_type=ContextType.SECURITY_CONSTRAINT,
                        description=f"Security pattern '{rule_type}' detected",
                        source_file=str(file_path),
                        source_line=i,
                        source_code=line.strip(),
                        confidence=0.6
                    )
                    rules.append(rule)
                    break
        
        return rules
    
    def _extract_python_error_handling(self, tree: ast.AST, content: str, file_path: Path) -> List[ContextRule]:
        """Extract error handling patterns from Python code."""
        rules = []
        
        class ErrorHandlingVisitor(ast.NodeVisitor):
            def __init__(self, content: str, file_path: Path):
                self.content = content
                self.file_path = file_path
                self.rules = []
            
            def visit_Try(self, node: ast.Try):
                # Extract try-except patterns
                start_line = node.lineno
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                
                lines = self.content.split('\n')
                try_source = '\n'.join(lines[start_line-1:end_line])
                
                # Analyze exception handlers
                exception_types = []
                for handler in node.handlers:
                    if handler.type:
                        if isinstance(handler.type, ast.Name):
                            exception_types.append(handler.type.id)
                        elif isinstance(handler.type, ast.Tuple):
                            for elt in handler.type.elts:
                                if isinstance(elt, ast.Name):
                                    exception_types.append(elt.id)
                
                if exception_types:
                    rule = ContextRule(
                        rule_type=ContextType.ERROR_HANDLING,
                        description=f"Error handling for exceptions: {', '.join(exception_types)}",
                        source_file=str(self.file_path),
                        source_line=start_line,
                        source_code=try_source[:500],
                        confidence=0.8
                    )
                    self.rules.append(rule)
                
                self.generic_visit(node)
        
        visitor = ErrorHandlingVisitor(content, file_path)
        visitor.visit(tree)
        return visitor.rules
    
    def _extract_python_data_models(self, tree: ast.AST, content: str, file_path: Path) -> List[ContextRule]:
        """Extract data models from Python code."""
        rules = []
        
        class DataModelVisitor(ast.NodeVisitor):
            def __init__(self, content: str, file_path: Path):
                self.content = content
                self.file_path = file_path
                self.rules = []
            
            def visit_ClassDef(self, node: ast.ClassDef):
                # Check for data model patterns
                is_data_model = False
                
                # Check class name
                if any(keyword in node.name.lower() for keyword in ["model", "schema", "dto", "entity"]):
                    is_data_model = True
                
                # Check for common data model attributes
                for item in node.body:
                    if isinstance(item, ast.AnnAssign):
                        # Type annotations suggest data model
                        is_data_model = True
                        break
                    elif isinstance(item, ast.Assign):
                        # Class-level assignments
                        is_data_model = True
                        break
                
                if is_data_model:
                    rule = ContextRule(
                        rule_type=ContextType.DATA_MODEL,
                        description=f"Data model class '{node.name}'",
                        source_file=str(self.file_path),
                        source_line=node.lineno,
                        confidence=0.7
                    )
                    self.rules.append(rule)
                
                self.generic_visit(node)
        
        visitor = DataModelVisitor(content, file_path)
        visitor.visit(tree)
        return visitor.rules
    
    def _analyze_javascript_file(self, content: str, file_path: Path) -> List[ContextRule]:
        """Analyze JavaScript/TypeScript file for context rules."""
        rules = []
        
        # Simple pattern matching for JS/TS
        js_patterns = [
            (r"export\s+(?:default\s+)?class\s+(\w+)", "class_definition"),
            (r"export\s+(?:default\s+)?function\s+(\w+)", "function_definition"),
            (r"export\s+(?:const|let|var)\s+(\w+)\s*=", "constant_definition"),
            (r"router\.(get|post|put|delete|patch)\(", "api_endpoint"),
            (r"mongoose\.model\(", "mongodb_model"),
            (r"sequelize\.define\(", "sql_model"),
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, rule_type in js_patterns:
                match = re.search(pattern, line)
                if match:
                    if rule_type == "class_definition":
                        rule = ContextRule(
                            rule_type=ContextType.DATA_MODEL,
                            description=f"JavaScript class '{match.group(1)}'",
                            source_file=str(file_path),
                            source_line=i,
                            confidence=0.6
                        )
                        rules.append(rule)
                    elif rule_type == "api_endpoint":
                        rule = ContextRule(
                            rule_type=ContextType.API_CONTRACT,
                            description=f"API endpoint on line {i}",
                            source_file=str(file_path),
                            source_line=i,
                            confidence=0.7
                        )
                        rules.append(rule)
        
        return rules
    
    def _analyze_java_file(self, content: str, file_path: Path) -> List[ContextRule]:
        """Analyze Java file for context rules."""
        rules = []
        
        # Java patterns
        java_patterns = [
            (r"@Entity\b", "jpa_entity"),
            (r"@RestController\b", "spring_controller"),
            (r"@Service\b", "spring_service"),
            (r"@Repository\b", "spring_repository"),
            (r"class\s+(\w+)\s+extends", "class_inheritance"),
            (r"interface\s+(\w+)", "interface_definition"),
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, rule_type in java_patterns:
                if re.search(pattern, line):
                    if rule_type == "jpa_entity":
                        rule = ContextRule(
                            rule_type=ContextType.DATA_MODEL,
                            description="JPA Entity class",
                            source_file=str(file_path),
                            source_line=i,
                            confidence=0.9
                        )
                        rules.append(rule)
                    elif rule_type == "spring_controller":
                        rule = ContextRule(
                            rule_type=ContextType.API_CONTRACT,
                            description="Spring REST Controller",
                            source_file=str(file_path),
                            source_line=i,
                            confidence=0.9
                        )
                        rules.append(rule)
        
        return rules
    
    def _match_universal_patterns(self, content: str, file_path: Path) -> List[ContextRule]:
        """Match universal patterns across all languages."""
        rules = []
        
        # Configuration patterns
        config_patterns = [
            (r"port\s*[:=]\s*\d+", "port_configuration"),
            (r"host\s*[:=]\s*[\"'].+?[\"']", "host_configuration"),
            (r"database|db\s*[:=]", "database_configuration"),
            (r"timeout\s*[:=]\s*\d+", "timeout_configuration"),
            (r"retry\s*[:=]\s*\d+", "retry_configuration"),
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, rule_type in config_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    rule = ContextRule(
                        rule_type=ContextType.DEPLOYMENT_CONFIG,
                        description=f"Configuration: {rule_type}",
                        source_file=str(file_path),
                        source_line=i,
                        source_code=line.strip(),
                        confidence=0.8
                    )
                    rules.append(rule)
        
        return rules
    
    def _load_business_patterns(self) -> Dict[str, List[str]]:
        """Load common business logic patterns."""
        return {
            "validation": ["validate", "check", "verify", "assert"],
            "calculation": ["calculate", "compute", "sum", "total", "average"],
            "transformation": ["transform", "convert", "format", "parse"],
            "authorization": ["authorize", "permit", "allow", "deny"],
            "authentication": ["authenticate", "login", "logout", "session"],
        }
    
    def _load_security_patterns(self) -> Dict[str, List[str]]:
        """Load common security patterns."""
        return {
            "cryptography": ["hash", "encrypt", "decrypt", "sign", "verify"],
            "input_validation": ["sanitize", "escape", "clean", "filter"],
            "access_control": ["permission", "role", "access", "privilege"],
            "sensitive_data": ["password", "secret", "key", "token", "credential"],
        }
    
    def _load_architecture_patterns(self) -> Dict[str, List[str]]:
        """Load common architecture patterns."""
        return {
            "orm": ["Model", "Entity", "Schema", "Table"],
            "api": ["Controller", "View", "Endpoint", "Route", "API"],
            "service": ["Service", "Manager", "Handler", "Processor"],
            "repository": ["Repository", "DAO", "DataAccess"],
        }


class ContextGraph:
    """Knowledge graph of context rules and their relationships."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.rules: Dict[str, ContextRule] = {}
    
    def add_rule(self, rule: ContextRule) -> None:
        """Add a context rule to the graph."""
        self.rules[rule.id] = rule
        self.graph.add_node(rule.id, **rule.to_dict())
        
        # Add edges for relationships
        for dep_id in rule.depends_on:
            if dep_id in self.rules:
                self.graph.add_edge(rule.id, dep_id, relationship="depends_on")
        
        for conflict_id in rule.conflicts_with:
            if conflict_id in self.rules:
                self.graph.add_edge(rule.id, conflict_id, relationship="conflicts_with")
        
        for related_id in rule.related_rules:
            if related_id in self.rules:
                self.graph.add_edge(rule.id, related_id, relationship="related_to")
    
    def find_conflicts(self, new_rule: ContextRule) -> List[ContextRule]:
        """Find rules that conflict with the new rule."""
        conflicts = []
        
        for rule_id, rule in self.rules.items():
            if rule.id in new_rule.conflicts_with or new_rule.id in rule.conflicts_with:
                conflicts.append(rule)
            elif self._rules_conflict(rule, new_rule):
                conflicts.append(rule)
        
        return conflicts
    
    def _rules_conflict(self, rule1: ContextRule, rule2: ContextRule) -> bool:
        """Determine if two rules conflict."""
        # Check rule types
        if rule1.rule_type != rule2.rule_type:
            return False
        
        # Check for contradictory descriptions
        contradictions = [
            ("must", "must not"),
            ("always", "never"),
            ("required", "prohibited"),
            ("enable", "disable"),
        ]
        
        desc1 = rule1.description.lower()
        desc2 = rule2.description.lower()
        
        for positive, negative in contradictions:
            if positive in desc1 and negative in desc2:
                return True
            if negative in desc1 and positive in desc2:
                return True
        
        return False
    
    def get_validation_context(self, file_path: str, line_number: int) -> List[ContextRule]:
        """Get context rules relevant for validating code at a specific location."""
        relevant_rules = []
        
        for rule in self.rules.values():
            if rule.source_file == file_path:
                # Check if rule is near the line number
                if rule.source_line:
                    distance = abs(rule.source_line - line_number)
                    if distance <= 50:  # Within 50 lines
                        relevant_rules.append(rule)
            elif rule.rule_type in [ContextType.BUSINESS_RULE, ContextType.SECURITY_CONSTRAINT]:
                # Always include important business and security rules
                relevant_rules.append(rule)
        
        return relevant_rules
    
    def to_json(self) -> str:
        """Export graph to JSON format."""
        data = {
            "rules": {rule_id: rule.to_dict() for rule_id, rule in self.rules.items()},
            "graph": {
                "nodes": list(self.graph.nodes()),
                "edges": list(self.graph.edges(data=True))
            }
        }
        return json.dumps(data, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> ContextGraph:
        """Load graph from JSON format."""
        data = json.loads(json_str)
        graph = cls()
        
        # Load rules
        for rule_id, rule_data in data["rules"].items():
            rule = ContextRule(
                id=rule_data["id"],
                rule_type=ContextType(rule_data["rule_type"]),
                description=rule_data["description"],
                source_file=rule_data.get("source_file"),
                source_line=rule_data.get("source_line"),
                source_code=rule_data.get("source_code"),
                confidence=rule_data.get("confidence", 0.0),
                validation_required=rule_data.get("validation_required", True),
                last_validated=rule_data.get("last_validated"),
                depends_on=rule_data.get("depends_on", []),
                conflicts_with=rule_data.get("conflicts_with", []),
                related_rules=rule_data.get("related_rules", []),
                created_by=rule_data.get("created_by", "context_mapper"),
                created_at=rule_data.get("created_at"),
                updated_at=rule_data.get("updated_at"),
                validation_prompt=rule_data.get("validation_prompt"),
                validation_examples=rule_data.get("validation_examples", [])
            )
            graph.add_rule(rule)
        
        return graph


class ContextMapper:
    """Main context mapping system."""
    
    def __init__(self, llm_client=None):
        self.analyzer = CodebaseAnalyzer()
        self.context_graph = ContextGraph()
        self.llm_client = llm_client
    
    def map_codebase(self, directory: Path) -> ContextGraph:
        """Map an entire codebase and extract context rules."""
        print(f"Mapping codebase: {directory}")
        
        # Extract rules through static analysis
        rules = self.analyzer.analyze_directory(directory)
        
        # Add rules to graph
        for rule in rules:
            self.context_graph.add_rule(rule)
        
        # Use LLM to refine and add missing context
        if self.llm_client:
            self._enhance_with_llm(directory)
        
        print(f"Mapped {len(rules)} context rules")
        return self.context_graph
    
    def _enhance_with_llm(self, directory: Path):
        """Use LLM to enhance context rules with semantic understanding."""
        # This would use the LLM client to analyze code and extract
        # higher-level business rules and constraints
        # For now, it's a placeholder
        pass
    
    def validate_code(self, code: str, file_path: str, line_number: int) -> Dict[str, Any]:
        """Validate code against context rules."""
        relevant_rules = self.context_graph.get_validation_context(file_path, line_number)
        
        violations = []
        warnings = []
        
        for rule in relevant_rules:
            validation_result = self._validate_against_rule(code, rule)
            if validation_result["violates"]:
                violations.append({
                    "rule": rule.to_dict(),
                    "message": validation_result["message"]
                })
            elif validation_result["warning"]:
                warnings.append({
                    "rule": rule.to_dict(),
                    "message": validation_result["message"]
                })
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "relevant_rules_count": len(relevant_rules)
        }
    
    def _validate_against_rule(self, code: str, rule: ContextRule) -> Dict[str, Any]:
        """Validate code against a specific context rule."""
        # Simple pattern matching for now
        # In production, this would use more sophisticated validation
        
        code_lower = code.lower()
        rule_desc_lower = rule.description.lower()
        
        # Check for security constraints
        if rule.rule_type == ContextType.SECURITY_CONSTRAINT:
            security_keywords = ["password", "secret", "key", "token"]
            for keyword in security_keywords:
                if keyword in rule_desc_lower and keyword in code_lower:
                    # Check if it's being handled securely
                    secure_patterns = ["hash", "encrypt", "env", "config"]
                    if not any(pattern in code_lower for pattern in secure_patterns):
                        return {
                            "violates": True,
                            "warning": False,
                            "message": f"Potential insecure handling of {keyword} detected"
                        }
        
        # Check for business rules
        if rule.rule_type == ContextType.BUSINESS_RULE:
            # Look for contradictory patterns
            contradictions = [
                ("must", "must not"),
                ("always", "never"),
                ("required", "optional"),
            ]
            
            for positive, negative in contradictions:
                if positive in rule_desc_lower and negative in code_lower:
                    return {
                        "violates": True,
                        "warning": False,
                        "message": f"Code contradicts business rule: {positive} vs {negative}"
                    }
        
        return {
            "violates": False,
            "warning": False,
            "message": "No issues found"
        }
    
    def generate_validation_prompt(self, task: str) -> str:
        """Generate a validation prompt for AI code generation."""
        relevant_rules = []
        
        # Find rules relevant to the task
        task_lower = task.lower()
        for rule in self.context_graph.rules.values():
            rule_desc_lower = rule.description.lower()
            
            # Simple keyword matching
            if any(keyword in task_lower for keyword in ["api", "endpoint", "route"]):
                if rule.rule_type == ContextType.API_CONTRACT:
                    relevant_rules.append(rule)
            elif any(keyword in task_lower for keyword in ["model", "schema", "data"]):
                if rule.rule_type == ContextType.DATA_MODEL:
                    relevant_rules.append(rule)
            elif any(keyword in task_lower for keyword in ["auth", "security", "permission"]):
                if rule.rule_type == ContextType.SECURITY_CONSTRAINT:
                    relevant_rules.append(rule)
            elif any(keyword in task_lower for keyword in ["business", "logic", "rule"]):
                if rule.rule_type == ContextType.BUSINESS_RULE:
                    relevant_rules.append(rule)
        
        # Build prompt
        prompt = "When generating code for this task, consider the following context rules:\n\n"
        
        for i, rule in enumerate(relevant_rules[:10], 1):  # Limit to 10 rules
            prompt += f"{i}. {rule.description}\n"
            if rule.validation_prompt:
                prompt += f"   Note: {rule.validation_prompt}\n"
            prompt += "\n"
        
        if not relevant_rules:
            prompt += "No specific context rules found. Use standard best practices.\n"
        
        prompt += "\nEnsure generated code adheres to these constraints and patterns."
        
        return prompt


# Export main classes
__all__ = [
    "ContextType",
    "ContextRule",
    "CodebaseAnalyzer",
    "ContextGraph",
    "ContextMapper",
]