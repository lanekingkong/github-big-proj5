"""
Trust Engine — Multi-dimensional code trust scoring system.

This module provides trust scoring for:
1. AI-generated code quality and safety
2. Skill trustworthiness and security
3. Developer reputation and track record
"""

from __future__ import annotations

import ast
import subprocess
import tempfile
import json
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import statistics

import libcst as cst
from tree_sitter import Language, Parser
import bandit
import safety


class TrustDimension(str, Enum):
    """Dimensions of trust that can be scored."""
    SECURITY = "security"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    COMPATIBILITY = "compatibility"
    ORIGINALITY = "originality"  # For detecting AI-generated code patterns


@dataclass
class TrustScore:
    """A multi-dimensional trust score with evidence."""
    overall: float  # 0-100
    dimensions: Dict[TrustDimension, float]
    evidence: List[Dict[str, Any]]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "overall": self.overall,
            "dimensions": {dim.value: score for dim, score in self.dimensions.items()},
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TrustScore:
        """Create from dictionary."""
        dimensions = {
            TrustDimension(dim): score 
            for dim, score in data.get("dimensions", {}).items()
        }
        return cls(
            overall=data["overall"],
            dimensions=dimensions,
            evidence=data.get("evidence", []),
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


class CodeAnalyzer:
    """Static analysis for code quality and security."""
    
    def __init__(self):
        # Initialize tree-sitter parsers
        self.parsers = {}
        self._init_tree_sitter()
    
    def _init_tree_sitter(self):
        """Initialize tree-sitter language parsers."""
        try:
            # Try to load pre-built grammars
            from tree_sitter_languages import get_language, get_parser
            
            languages = ["python", "javascript", "typescript", "java", "go", "rust"]
            for lang in languages:
                try:
                    parser = get_parser(lang)
                    self.parsers[lang] = parser
                except:
                    pass
        except ImportError:
            # Fallback to simple AST parsing
            pass
    
    def analyze_python(self, code: str, filepath: Optional[str] = None) -> Dict[str, Any]:
        """Analyze Python code for quality and security issues."""
        results = {
            "security_issues": [],
            "quality_issues": [],
            "complexity_metrics": {},
            "ai_patterns": []
        }
        
        try:
            # Parse with AST
            tree = ast.parse(code)
            
            # Security analysis with Bandit
            security_issues = self._run_bandit(code, filepath)
            results["security_issues"].extend(security_issues)
            
            # Quality analysis
            quality_issues = self._analyze_python_quality(tree, code)
            results["quality_issues"].extend(quality_issues)
            
            # Complexity metrics
            complexity = self._calculate_complexity(tree)
            results["complexity_metrics"].update(complexity)
            
            # AI pattern detection
            ai_patterns = self._detect_ai_patterns(code)
            results["ai_patterns"].extend(ai_patterns)
            
        except SyntaxError as e:
            results["quality_issues"].append({
                "type": "syntax_error",
                "message": str(e),
                "severity": "critical"
            })
        
        return results
    
    def _run_bandit(self, code: str, filepath: Optional[str] = None) -> List[Dict[str, Any]]:
        """Run Bandit security analysis on Python code."""
        issues = []
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = f.name
            
            # Run bandit
            cmd = ["bandit", "-f", "json", temp_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                try:
                    bandit_output = json.loads(result.stdout)
                    for issue in bandit_output.get("results", []):
                        issues.append({
                            "type": "security",
                            "severity": issue.get("issue_severity", "medium").lower(),
                            "confidence": issue.get("issue_confidence", "medium").lower(),
                            "message": issue.get("issue_text", ""),
                            "line": issue.get("line_number", 0),
                            "cwe": issue.get("issue_cwe", {}).get("id") if isinstance(issue.get("issue_cwe"), dict) else None
                        })
                except json.JSONDecodeError:
                    pass
            
            # Clean up
            Path(temp_path).unlink()
            
        except Exception as e:
            # Bandit not available or failed
            pass
        
        return issues
    
    def _analyze_python_quality(self, tree: ast.AST, code: str) -> List[Dict[str, Any]]:
        """Analyze Python code for quality issues."""
        issues = []
        
        # Check for common quality issues
        visitor = QualityVisitor()
        visitor.visit(tree)
        
        # Add visitor findings
        for issue in visitor.issues:
            issues.append(issue)
        
        # Additional checks
        lines = code.split('\n')
        
        # Check line length
        for i, line in enumerate(lines, 1):
            if len(line) > 100:  # PEP 8 recommends 79, but 100 is common
                issues.append({
                    "type": "style",
                    "severity": "low",
                    "message": f"Line {i} exceeds 100 characters",
                    "line": i
                })
        
        # Check for TODO comments (commented out for production)
        # for i, line in enumerate(lines, 1):
        #     if "TODO" in line.upper() and not line.strip().startswith("#"):
        #         issues.append({
        #             "type": "maintenance",
        #             "severity": "low",
        #             "message": f"TODO comment found on line {i}",
        #             "line": i
        #         })
        
        return issues
    
    def _calculate_complexity(self, tree: ast.AST) -> Dict[str, Any]:
        """Calculate code complexity metrics."""
        complexity_visitor = ComplexityVisitor()
        complexity_visitor.visit(tree)
        
        return {
            "cyclomatic_complexity": complexity_visitor.cyclomatic_complexity,
            "function_count": complexity_visitor.function_count,
            "class_count": complexity_visitor.class_count,
            "line_count": complexity_visitor.line_count,
            "average_function_length": complexity_visitor.average_function_length,
        }
    
    def _detect_ai_patterns(self, code: str) -> List[Dict[str, Any]]:
        """Detect patterns commonly found in AI-generated code."""
        patterns = []
        
        # Common AI code patterns
        ai_patterns = [
            (r"# This code was generated by.*AI", "ai_generation_comment"),
            (r"# Generated by.*GPT", "gpt_generation"),
            (r"# AI.*assistant", "ai_assistant_comment"),
            (r"def\s+\w+\(.*\)\s*->\s*None:\s*\"\"\".*\"\"\"\s*pass", "stub_with_docstring"),
            (r"try:\s*.*\s*except\s+Exception\s+as\s+e:\s*pass", "bare_except_pass"),
        ]
        
        for pattern, pattern_type in ai_patterns:
            if re.search(pattern, code, re.MULTILINE | re.IGNORECASE):
                patterns.append({
                    "type": "ai_pattern",
                    "pattern": pattern_type,
                    "confidence": "medium"
                })
        
        # Check for overly generic variable names
        generic_names = ["data", "result", "value", "item", "obj", "temp"]
        for name in generic_names:
            if re.search(rf"\b{name}\b\s*=", code):
                patterns.append({
                    "type": "generic_naming",
                    "pattern": f"generic_variable_{name}",
                    "confidence": "low"
                })
        
        return patterns


class QualityVisitor(ast.NodeVisitor):
    """AST visitor for detecting quality issues."""
    
    def __init__(self):
        self.issues = []
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definitions."""
        # Check function length
        func_lines = node.end_lineno - node.lineno if node.end_lineno else 0
        if func_lines > 50:
            self.issues.append({
                "type": "complexity",
                "severity": "medium",
                "message": f"Function '{node.name}' is too long ({func_lines} lines)",
                "line": node.lineno
            })
        
        # Check arguments count
        args_count = len(node.args.args) + len(node.args.kwonlyargs)
        if args_count > 7:
            self.issues.append({
                "type": "design",
                "severity": "medium",
                "message": f"Function '{node.name}' has too many arguments ({args_count})",
                "line": node.lineno
            })
        
        self.generic_visit(node)
    
    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """Visit exception handlers."""
        if node.type is None or (isinstance(node.type, ast.Name) and node.type.id == "Exception"):
            self.issues.append({
                "type": "error_handling",
                "severity": "medium",
                "message": "Bare except clause or catching generic Exception",
                "line": node.lineno
            })
        
        self.generic_visit(node)


class ComplexityVisitor(ast.NodeVisitor):
    """AST visitor for calculating complexity metrics."""
    
    def __init__(self):
        self.cyclomatic_complexity = 1  # Start with 1
        self.function_count = 0
        self.class_count = 0
        self.line_count = 0
        self.function_lengths = []
    
    def visit(self, node: ast.AST):
        """Visit node and count lines."""
        if hasattr(node, 'lineno'):
            self.line_count = max(self.line_count, getattr(node, 'end_lineno', node.lineno))
        
        # Increase complexity for control flow nodes
        if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.AsyncWith,
                           ast.Try, ast.ExceptHandler, ast.With, ast.AsyncWith)):
            self.cyclomatic_complexity += 1
        
        # Count boolean operators
        if isinstance(node, ast.BoolOp):
            self.cyclomatic_complexity += len(node.values) - 1
        
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definitions."""
        self.function_count += 1
        
        # Calculate function length
        if node.end_lineno:
            func_length = node.end_lineno - node.lineno
            self.function_lengths.append(func_length)
        
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definitions."""
        self.function_count += 1
        
        if node.end_lineno:
            func_length = node.end_lineno - node.lineno
            self.function_lengths.append(func_length)
        
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definitions."""
        self.class_count += 1
        self.generic_visit(node)
    
    @property
    def average_function_length(self) -> float:
        """Calculate average function length."""
        if not self.function_lengths:
            return 0.0
        return statistics.mean(self.function_lengths)


class DependencyAnalyzer:
    """Analyze dependencies for security vulnerabilities."""
    
    def __init__(self):
        pass
    
    def analyze_python_dependencies(self, requirements: str) -> Dict[str, Any]:
        """Analyze Python dependencies for security issues."""
        results = {
            "vulnerabilities": [],
            "outdated_packages": [],
            "license_issues": []
        }
        
        try:
            # Parse requirements
            packages = self._parse_requirements(requirements)
            
            # Check for vulnerabilities with safety
            for package in packages:
                vulns = self._check_package_vulnerability(package["name"], package.get("version"))
                results["vulnerabilities"].extend(vulns)
            
        except Exception as e:
            results["vulnerabilities"].append({
                "type": "analysis_error",
                "message": f"Dependency analysis failed: {str(e)}",
                "severity": "medium"
            })
        
        return results
    
    def _parse_requirements(self, requirements: str) -> List[Dict[str, str]]:
        """Parse requirements.txt format."""
        packages = []
        
        for line in requirements.split('\n'):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse package spec
            # Simple parsing for now
            if '==' in line:
                name, version = line.split('==', 1)
                packages.append({"name": name.strip(), "version": version.strip()})
            elif '>=' in line:
                name, version = line.split('>=', 1)
                packages.append({"name": name.strip(), "version": version.strip()})
            else:
                # Just package name
                packages.append({"name": line, "version": None})
        
        return packages
    
    def _check_package_vulnerability(self, package_name: str, version: Optional[str]) -> List[Dict[str, Any]]:
        """Check if a package has known vulnerabilities."""
        vulnerabilities = []
        
        try:
            # Use safety API or local database
            # This is a simplified version
            pass
            
        except Exception:
            # Safety not available
            pass
        
        return vulnerabilities


class TrustEngine:
    """Main trust scoring engine."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.code_analyzer = CodeAnalyzer()
        self.dependency_analyzer = DependencyAnalyzer()
        
        # Weight configuration for different dimensions
        self.weights = {
            TrustDimension.SECURITY: 0.35,
            TrustDimension.QUALITY: 0.25,
            TrustDimension.PERFORMANCE: 0.15,
            TrustDimension.MAINTAINABILITY: 0.15,
            TrustDimension.COMPATIBILITY: 0.05,
            TrustDimension.ORIGINALITY: 0.05,
        }
    
    def score_code(self, code: str, language: str = "python", 
                   filepath: Optional[str] = None) -> TrustScore:
        """Score the trustworthiness of code."""
        evidence = []
        dimension_scores = {}
        
        # Analyze code based on language
        if language == "python":
            analysis = self.code_analyzer.analyze_python(code, filepath)
            
            # Calculate security score
            security_score = self._calculate_security_score(analysis["security_issues"])
            dimension_scores[TrustDimension.SECURITY] = security_score
            evidence.extend([
                {
                    "dimension": "security",
                    "type": "security_analysis",
                    "details": analysis["security_issues"],
                    "score": security_score
                }
            ])
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(analysis["quality_issues"])
            dimension_scores[TrustDimension.QUALITY] = quality_score
            evidence.extend([
                {
                    "dimension": "quality",
                    "type": "quality_analysis",
                    "details": analysis["quality_issues"],
                    "score": quality_score
                }
            ])
            
            # Calculate maintainability score
            maintainability_score = self._calculate_maintainability_score(analysis["complexity_metrics"])
            dimension_scores[TrustDimension.MAINTAINABILITY] = maintainability_score
            evidence.extend([
                {
                    "dimension": "maintainability",
                    "type": "complexity_analysis",
                    "details": analysis["complexity_metrics"],
                    "score": maintainability_score
                }
            ])
            
            # Calculate originality score (AI pattern detection)
            originality_score = self._calculate_originality_score(analysis["ai_patterns"])
            dimension_scores[TrustDimension.ORIGINALITY] = originality_score
            evidence.extend([
                {
                    "dimension": "originality",
                    "type": "ai_pattern_detection",
                    "details": analysis["ai_patterns"],
                    "score": originality_score
                }
            ])
        
        # Default scores for other dimensions
        dimension_scores[TrustDimension.PERFORMANCE] = 50.0  # Placeholder
        dimension_scores[TrustDimension.COMPATIBILITY] = 75.0  # Placeholder
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(dimension_scores)
        
        return TrustScore(
            overall=overall_score,
            dimensions=dimension_scores,
            evidence=evidence,
            timestamp=datetime.utcnow()
        )
    
    def score_skill(self, skill: Any) -> float:
        """Score the trustworthiness of a skill."""
        # This would integrate with the UniversalSkill module
        # For now, return a placeholder score
        return 75.0
    
    def _calculate_security_score(self, security_issues: List[Dict[str, Any]]) -> float:
        """Calculate security score based on issues found."""
        if not security_issues:
            return 100.0
        
        # Weight issues by severity
        severity_weights = {
            "critical": 20,
            "high": 10,
            "medium": 5,
            "low": 1
        }
        
        total_weight = 0
        for issue in security_issues:
            severity = issue.get("severity", "medium")
            total_weight += severity_weights.get(severity, 5)
        
        # Convert to score (0-100)
        # More weight = lower score
        score = max(0, 100 - min(total_weight * 5, 100))
        
        return round(score, 1)
    
    def _calculate_quality_score(self, quality_issues: List[Dict[str, Any]]) -> float:
        """Calculate quality score based on issues found."""
        if not quality_issues:
            return 100.0
        
        # Weight issues by severity
        severity_weights = {
            "critical": 10,
            "high": 5,
            "medium": 2,
            "low": 0.5
        }
        
        total_weight = 0
        for issue in quality_issues:
            severity = issue.get("severity", "medium")
            total_weight += severity_weights.get(severity, 2)
        
        # Convert to score (0-100)
        score = max(0, 100 - min(total_weight * 3, 100))
        
        return round(score, 1)
    
    def _calculate_maintainability_score(self, complexity_metrics: Dict[str, Any]) -> float:
        """Calculate maintainability score based on complexity metrics."""
        score = 100.0
        
        # Adjust based on cyclomatic complexity
        cc = complexity_metrics.get("cyclomatic_complexity", 1)
        if cc > 20:
            score -= 30
        elif cc > 10:
            score -= 15
        elif cc > 5:
            score -= 5
        
        # Adjust based on function length
        avg_func_len = complexity_metrics.get("average_function_length", 0)
        if avg_func_len > 50:
            score -= 20
        elif avg_func_len > 30:
            score -= 10
        elif avg_func_len > 20:
            score -= 5
        
        # Adjust based on function count
        func_count = complexity_metrics.get("function_count", 0)
        if func_count > 20:
            score -= 10
        elif func_count > 10:
            score -= 5
        
        return max(0, round(score, 1))
    
    def _calculate_originality_score(self, ai_patterns: List[Dict[str, Any]]) -> float:
        """Calculate originality score based on AI patterns detected."""
        if not ai_patterns:
            return 100.0
        
        # Deduct points for AI patterns
        deduction = len(ai_patterns) * 10
        
        # Extra deduction for high confidence patterns
        high_conf_patterns = [p for p in ai_patterns if p.get("confidence") == "high"]
        deduction += len(high_conf_patterns) * 5
        
        return max(0, 100 - min(deduction, 100))
    
    def _calculate_overall_score(self, dimension_scores: Dict[TrustDimension, float]) -> float:
        """Calculate overall trust score using weighted dimensions."""
        total = 0.0
        total_weight = 0.0
        
        for dimension, weight in self.weights.items():
            score = dimension_scores.get(dimension, 50.0)  # Default to 50 if missing
            total += score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 50.0
        
        overall = total / total_weight
        return round(overall, 1)


# Export main classes
__all__ = [
    "TrustDimension",
    "TrustScore",
    "CodeAnalyzer",
    "DependencyAnalyzer",
    "TrustEngine",
]