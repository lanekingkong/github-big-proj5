"""
Code Review Pipeline — Multi-agent automated code review system.

This module orchestrates multiple specialized agents to review code:
1. Security Agent: Checks for vulnerabilities and security issues
2. Quality Agent: Reviews code style, complexity, and best practices
3. Logic Agent: Validates business logic and edge cases
4. Performance Agent: Identifies performance bottlenecks
5. Compatibility Agent: Checks platform and dependency compatibility
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import concurrent.futures

from pydantic import BaseModel, Field


class ReviewSeverity(str, Enum):
    """Severity levels for review findings."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ReviewCategory(str, Enum):
    """Categories of review findings."""
    SECURITY = "security"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    LOGIC = "logic"
    COMPATIBILITY = "compatibility"
    STYLE = "style"
    DOCUMENTATION = "documentation"
    TESTING = "testing"


@dataclass
class ReviewFinding:
    """A single finding from code review."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: ReviewCategory = ReviewCategory.QUALITY
    severity: ReviewSeverity = ReviewSeverity.MEDIUM
    title: str = ""
    description: str = ""
    
    # Location
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    column_start: Optional[int] = None
    column_end: Optional[int] = None
    
    # Code snippet
    code_snippet: Optional[str] = None
    
    # Fix suggestions
    fix_suggestion: Optional[str] = None
    fix_example: Optional[str] = None
    
    # Confidence and evidence
    confidence: float = 0.8  # 0.0-1.0
    evidence: List[str] = field(default_factory=list)
    
    # Metadata
    agent_name: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "column_start": self.column_start,
            "column_end": self.column_end,
            "code_snippet": self.code_snippet,
            "fix_suggestion": self.fix_suggestion,
            "fix_example": self.fix_example,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ReviewReport:
    """Complete code review report."""
    review_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    findings: List[ReviewFinding] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Statistics
    total_findings: int = 0
    findings_by_severity: Dict[str, int] = field(default_factory=dict)
    findings_by_category: Dict[str, int] = field(default_factory=dict)
    
    # Trust metrics
    trust_score: Optional[float] = None
    review_duration: Optional[float] = None  # seconds
    
    def add_finding(self, finding: ReviewFinding):
        """Add a finding to the report."""
        self.findings.append(finding)
        self._update_statistics()
    
    def _update_statistics(self):
        """Update statistics based on current findings."""
        self.total_findings = len(self.findings)
        
        # Count by severity
        self.findings_by_severity = {
            severity.value: 0 for severity in ReviewSeverity
        }
        for finding in self.findings:
            self.findings_by_severity[finding.severity.value] += 1
        
        # Count by category
        self.findings_by_category = {
            category.value: 0 for category in ReviewCategory
        }
        for finding in self.findings:
            self.findings_by_category[finding.category.value] += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "review_id": self.review_id,
            "findings": [finding.to_dict() for finding in self.findings],
            "summary": self.summary,
            "metadata": self.metadata,
            "statistics": {
                "total_findings": self.total_findings,
                "findings_by_severity": self.findings_by_severity,
                "findings_by_category": self.findings_by_category
            },
            "trust_score": self.trust_score,
            "review_duration": self.review_duration
        }
    
    def generate_summary(self) -> str:
        """Generate a human-readable summary."""
        lines = []
        
        lines.append(f"Code Review Report: {self.review_id}")
        lines.append("=" * 50)
        lines.append(f"Total Findings: {self.total_findings}")
        lines.append("")
        
        # Severity breakdown
        lines.append("Findings by Severity:")
        for severity in ReviewSeverity:
            count = self.findings_by_severity.get(severity.value, 0)
            if count > 0:
                lines.append(f"  {severity.value.title()}: {count}")
        
        lines.append("")
        
        # Category breakdown
        lines.append("Findings by Category:")
        for category in ReviewCategory:
            count = self.findings_by_category.get(category.value, 0)
            if count > 0:
                lines.append(f"  {category.value.title()}: {count}")
        
        lines.append("")
        
        # Critical findings
        critical_findings = [f for f in self.findings if f.severity == ReviewSeverity.CRITICAL]
        if critical_findings:
            lines.append(f"Critical Findings ({len(critical_findings)}):")
            for i, finding in enumerate(critical_findings[:5], 1):  # Show top 5
                lines.append(f"  {i}. {finding.title}")
                if finding.file_path:
                    lines.append(f"     File: {finding.file_path}:{finding.line_start or '?'}")
            if len(critical_findings) > 5:
                lines.append(f"  ... and {len(critical_findings) - 5} more")
        
        lines.append("")
        
        # Trust score
        if self.trust_score is not None:
            lines.append(f"Trust Score: {self.trust_score}/100")
        
        # Review duration
        if self.review_duration is not None:
            lines.append(f"Review Duration: {self.review_duration:.2f} seconds")
        
        return "\n".join(lines)


class BaseReviewAgent:
    """Base class for all review agents."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
    
    async def review_code(self, code: str, language: str, context: Dict[str, Any]) -> List[ReviewFinding]:
        """Review code and return findings."""
        raise NotImplementedError
    
    def _create_finding(
        self,
        category: ReviewCategory,
        severity: ReviewSeverity,
        title: str,
        description: str,
        **kwargs
    ) -> ReviewFinding:
        """Create a review finding with standard fields."""
        return ReviewFinding(
            category=category,
            severity=severity,
            title=title,
            description=description,
            agent_name=self.name,
            **kwargs
        )


class SecurityAgent(BaseReviewAgent):
    """Agent for security vulnerability detection."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("security_agent", config)
        self.vulnerability_patterns = self._load_vulnerability_patterns()
    
    async def review_code(self, code: str, language: str, context: Dict[str, Any]) -> List[ReviewFinding]:
        """Review code for security vulnerabilities."""
        findings = []
        
        if language == "python":
            findings.extend(self._review_python_security(code, context))
        elif language in ["javascript", "typescript"]:
            findings.extend(self._review_javascript_security(code, context))
        
        return findings
    
    def _review_python_security(self, code: str, context: Dict[str, Any]) -> List[ReviewFinding]:
        """Review Python code for security issues."""
        findings = []
        
        # Check for SQL injection
        if "sql" in code.lower() and any(pattern in code for pattern in ["%s", "format(", "f'", 'f"']):
            # Look for string formatting in SQL queries
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if any(sql_keyword in line.lower() for sql_keyword in ["select", "insert", "update", "delete"]):
                    if any(pattern in line for pattern in ["%s", "format(", "f'", 'f"']):
                        findings.append(self._create_finding(
                            category=ReviewCategory.SECURITY,
                            severity=ReviewSeverity.CRITICAL,
                            title="Potential SQL Injection",
                            description="String formatting in SQL queries can lead to SQL injection attacks.",
                            file_path=context.get("file_path"),
                            line_start=i,
                            code_snippet=line.strip(),
                            fix_suggestion="Use parameterized queries or ORM methods instead of string formatting.",
                            fix_example="cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
                            confidence=0.8
                        ))
        
        # Check for command injection
        if any(cmd in code.lower() for cmd in ["os.system", "subprocess.run", "subprocess.Popen"]):
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if any(cmd in line for cmd in ["os.system", "subprocess.run", "subprocess.Popen"]):
                    if any(pattern in line for pattern in ["+ ", "format(", "f'", 'f"']):
                        findings.append(self._create_finding(
                            category=ReviewCategory.SECURITY,
                            severity=ReviewSeverity.HIGH,
                            title="Potential Command Injection",
                            description="String concatenation in shell commands can lead to command injection.",
                            file_path=context.get("file_path"),
                            line_start=i,
                            code_snippet=line.strip(),
                            fix_suggestion="Use shlex.quote() or pass arguments as list instead of string.",
                            fix_example="subprocess.run(['ls', '-la'], capture_output=True)",
                            confidence=0.7
                        ))
        
        # Check for hardcoded secrets
        secret_patterns = [
            (r'password\s*=\s*[\'"][^\'"]+[\'"]', "Hardcoded password"),
            (r'api_key\s*=\s*[\'"][^\'"]+[\'"]', "Hardcoded API key"),
            (r'secret\s*=\s*[\'"][^\'"]+[\'"]', "Hardcoded secret"),
            (r'token\s*=\s*[\'"][^\'"]+[\'"]', "Hardcoded token"),
        ]
        
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, title in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(self._create_finding(
                        category=ReviewCategory.SECURITY,
                        severity=ReviewSeverity.HIGH,
                        title=title,
                        description="Secrets should not be hardcoded in source code.",
                        file_path=context.get("file_path"),
                        line_start=i,
                        code_snippet=line.strip(),
                        fix_suggestion="Use environment variables or secret management services.",
                        fix_example="password = os.environ.get('DB_PASSWORD')",
                        confidence=0.9
                    ))
        
        return findings
    
    def _review_javascript_security(self, code: str, context: Dict[str, Any]) -> List[ReviewFinding]:
        """Review JavaScript/TypeScript code for security issues."""
        findings = []
        
        # Check for XSS vulnerabilities
        if "innerHTML" in code or "document.write" in code:
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if "innerHTML" in line or "document.write" in line:
                    if any(pattern in line for pattern in ["+", "${", "template"]):
                        findings.append(self._create_finding(
                            category=ReviewCategory.SECURITY,
                            severity=ReviewSeverity.HIGH,
                            title="Potential XSS Vulnerability",
                            description="Unsanitized user input in innerHTML or document.write can lead to XSS attacks.",
                            file_path=context.get("file_path"),
                            line_start=i,
                            code_snippet=line.strip(),
                            fix_suggestion="Use textContent instead of innerHTML, or sanitize input.",
                            fix_example="element.textContent = userInput;",
                            confidence=0.8
                        ))
        
        # Check for eval() usage
        if "eval(" in code:
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if "eval(" in line:
                    findings.append(self._create_finding(
                        category=ReviewCategory.SECURITY,
                        severity=ReviewSeverity.CRITICAL,
                        title="eval() Usage",
                        description="eval() can execute arbitrary code and is a security risk.",
                        file_path=context.get("file_path"),
                        line_start=i,
                        code_snippet=line.strip(),
                        fix_suggestion="Avoid eval(). Use JSON.parse() for JSON, or Function constructor with caution.",
                        fix_example="const data = JSON.parse(jsonString);",
                        confidence=0.9
                    ))
        
        return findings
    
    def _load_vulnerability_patterns(self) -> Dict[str, List[str]]:
        """Load security vulnerability patterns."""
        return {
            "sql_injection": ["%s", "format(", "f'", 'f"'],
            "command_injection": ["os.system", "subprocess.run", "subprocess.Popen"],
            "xss": ["innerHTML", "document.write"],
            "eval": ["eval("],
            "hardcoded_secrets": ["password", "api_key", "secret", "token"],
        }


class QualityAgent(BaseReviewAgent):
    """Agent for code quality and style review."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("quality_agent", config)
        self.style_guide = self._load_style_guide()
    
    async def review_code(self, code: str, language: str, context: Dict[str, Any]) -> List[ReviewFinding]:
        """Review code for quality and style issues."""
        findings = []
        
        if language == "python":
            findings.extend(self._review_python_quality(code, context))
        elif language in ["javascript", "typescript"]:
            findings.extend(self._review_javascript_quality(code, context))
        
        return findings
    
    def _review_python_quality(self, code: str, context: Dict[str, Any]) -> List[ReviewFinding]:
        """Review Python code for quality issues."""
        findings = []
        
        # Check line length
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line) > 100:  # PEP 8 recommends 79, but 100 is common
                findings.append(self._create_finding(
                    category=ReviewCategory.STYLE,
                    severity=ReviewSeverity.LOW,
                    title="Line Too Long",
                    description=f"Line {i} exceeds 100 characters ({len(line)} chars).",
                    file_path=context.get("file_path"),
                    line_start=i,
                    code_snippet=line[:120] + "..." if len(line) > 120 else line,
                    fix_suggestion="Break the line into multiple lines or refactor.",
                    confidence=0.9
                ))
        
        # Check for TODO comments (disabled for production)
        # for i, line in enumerate(lines, 1):
        #     if "TODO" in line.upper() and not line.strip().startswith("#"):
        #         findings.append(self._create_finding(
        #             category=ReviewCategory.DOCUMENTATION,
        #             severity=ReviewSeverity.INFO,
        #             title="TODO Comment",
        #             description=f"TODO comment found on line {i}.",
        #             file_path=context.get("file_path"),
        #             line_start=i,
        #             code_snippet=line.strip(),
        #             fix_suggestion="Address the TODO or create a ticket for tracking.",
        #             confidence=1.0
        #         ))
        
        # Check for print statements (in production code)
        if context.get("environment") == "production":
            for i, line in enumerate(lines, 1):
                if "print(" in line and not line.strip().startswith("#"):
                    findings.append(self._create_finding(
                        category=ReviewCategory.QUALITY,
                        severity=ReviewSeverity.MEDIUM,
                        title="Print Statement in Production Code",
                        description="print() statements should not be in production code.",
                        file_path=context.get("file_path"),
                        line_start=i,
                        code_snippet=line.strip(),
                        fix_suggestion="Use logging module instead of print().",
                        fix_example="import logging\nlogger = logging.getLogger(__name__)\nlogger.info('Message')",
                        confidence=0.8
                    ))
        
        # Check for bare except
        if "except:" in code or "except Exception:" in code:
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if "except:" in line or "except Exception:" in line:
                    findings.append(self._create_finding(
                        category=ReviewCategory.QUALITY,
                        severity=ReviewSeverity.MEDIUM,
                        title="Bare Except Clause",
                        description="Bare except clauses can hide errors and make debugging difficult.",
                        file_path=context.get("file_path"),
                        line_start=i,
                        code_snippet=line.strip(),
                        fix_suggestion="Catch specific exceptions instead of generic Exception.",
                        fix_example="except ValueError as e:\n    logger.error(f'Value error: {e}')",
                        confidence=0.8
                    ))
        
        return findings
    
    def _review_javascript_quality(self, code: str, context: Dict[str, Any]) -> List[ReviewFinding]:
        """Review JavaScript/TypeScript code for quality issues."""
        findings = []
        
        # Check for console.log in production
        if context.get("environment") == "production":
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if "console.log" in line and not line.strip().startswith("//"):
                    findings.append(self._create_finding(
                        category=ReviewCategory.QUALITY,
                        severity=ReviewSeverity.MEDIUM,
                        title="Console.log in Production Code",
                        description="console.log() should not be in production code.",
                        file_path=context.get("file_path"),
                        line_start=i,
                        code_snippet=line.strip(),
                        fix_suggestion="Use a proper logging library.",
                        confidence=0.8
                    ))
        
        # Check for var usage
        if "var " in code:
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if "var " in line and not line.strip().startswith("//"):
                    findings.append(self._create_finding(
                        category=ReviewCategory.STYLE,
                        severity=ReviewSeverity.LOW,
                        title="var Usage",
                        description="var has function scope and can lead to bugs. Use let or const instead.",
                        file_path=context.get("file_path"),
                        line_start=i,
                        code_snippet=line.strip(),
                        fix_suggestion="Replace var with let or const based on mutability.",
                        fix_example="const name = 'John';\nlet count = 0;",
                        confidence=0.9
                    ))
        
        return findings
    
    def _load_style_guide(self) -> Dict[str, Any]:
        """Load code style guide rules."""
        return {
            "python": {
                "max_line_length": 100,
                "indentation": 4,
                "quote_style": "single",
                "import_order": ["standard", "third_party", "local"]
            },
            "javascript": {
                "max_line_length": 100,
                "indentation": 2,
                "quote_style": "single",
                "semicolons": True
            }
        }


class LogicAgent(BaseReviewAgent):
    """Agent for business logic and edge case review."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("logic_agent", config)
    
    async def review_code(self, code: str, language: str, context: Dict[str, Any]) -> List[ReviewFinding]:
        """Review code for logic errors and edge cases."""
        findings = []
        
        # Check for null/undefined handling
        if language == "python":
            findings.extend(self._review_python_logic(code, context))
        elif language in ["javascript", "typescript"]:
            findings.extend(self._review_javascript_logic(code, context))
        
        return findings
    
    def _review_python_logic(self, code: str, context: Dict[str, Any]) -> List[ReviewFinding]:
        """Review Python code for logic issues."""
        findings = []
        
        # Check for None comparisons
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            if "== None" in line or "!= None" in line:
                findings.append(self._create_finding(
                    category=ReviewCategory.LOGIC,
                    severity=ReviewSeverity.LOW,
                    title="None Comparison with ==",
                    description="Use 'is None' or 'is not None' instead of '== None' or '!= None'.",
                    file_path=context.get("file_path"),
                    line_start=i,
                    code_snippet=line.strip(),
                    fix_suggestion="Replace '== None' with 'is None' and '!= None' with 'is not None'.",
                    fix_example="if value is None:\n    return default",
                    confidence=0.9
                ))
        
        # Check for mutable default arguments
        if "def " in code:
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if "def " in line and "=[]" in line or "={}" in line:
                    findings.append(self._create_finding(
                        category=ReviewCategory.LOGIC,
                        severity=ReviewSeverity.MEDIUM,
                        title="Mutable Default Argument",
                        description="Mutable default arguments are shared across function calls.",
                        file_path=context.get("file_path"),
                        line_start=i,
                        code_snippet=line.strip(),
                        fix_suggestion="Use None as default and create mutable object inside function.",
                        fix_example="def func(items=None):\n    if items is None:\n        items = []",
                        confidence=0.9
                    ))
        
        return findings
    
    def _review_javascript_logic(self, code: str, context: Dict[str, Any]) -> List[ReviewFinding]:
        """Review JavaScript/TypeScript code for logic issues."""
        findings = []
        
        # Check for == vs ===
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            if "==" in line and "===" not in line and "!==" not in line:
                # Check if it's a comparison (not assignment or other use)
                if "if " in line or "while " in line or "for " in line or "? " in line:
                    findings.append(self._create_finding(
                        category=ReviewCategory.LOGIC,
                        severity=ReviewSeverity.LOW,
                        title="Loose Equality Comparison",
                        description="== performs type coercion, which can lead to unexpected results.",
                        file_path=context.get("file_path"),
                        line_start=i,
                        code_snippet=line.strip(),
                        fix_suggestion="Use === for strict equality comparison.",
                        fix_example="if (value === null) { ... }",
                        confidence=0.8
                    ))
        
        # Check for undefined/null handling
        for i, line in enumerate(lines, 1):
            if any(pattern in line for pattern in ["undefined", "null"]):
                if "==" in line or "!=" in line:
                    findings.append(self._create_finding(
                        category=ReviewCategory.LOGIC,
                        severity=ReviewSeverity.MEDIUM,
                        title="Undefined/Null Comparison Issue",
                        description="JavaScript has both undefined and null, handle them carefully.",
                        file_path=context.get("file_path"),
                        line_start=i,
                        code_snippet=line.strip(),
                        fix_suggestion="Consider using optional chaining or nullish coalescing.",
                        fix_example="const value = obj?.prop ?? defaultValue;",
                        confidence=0.7
                    ))
        
        return findings


class PerformanceAgent(BaseReviewAgent):
    """Agent for performance issue detection."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("performance_agent", config)
    
    async def review_code(self, code: str, language: str, context: Dict[str, Any]) -> List[ReviewFinding]:
        """Review code for performance issues."""
        findings = []
        
        if language == "python":
            findings.extend(self._review_python_performance(code, context))
        elif language in ["javascript", "typescript"]:
            findings.extend(self._review_javascript_performance(code, context))
        
        return findings
    
    def _review_python_performance(self, code: str, context: Dict[str, Any]) -> List[ReviewFinding]:
        """Review Python code for performance issues."""
        findings = []
        
        # Check for string concatenation in loops
        lines = code.split('\n')
        in_loop = False
        loop_start = 0
        
        for i, line in enumerate(lines, 1):
            # Detect loops
            if any(keyword in line for keyword in ["for ", "while "]):
                in_loop = True
                loop_start = i
            
            # Check for string concatenation in loops
            if in_loop and "+=" in line and any(quote in line for quote in ["'", '"']):
                findings.append(self._create_finding(
                    category=ReviewCategory.PERFORMANCE,
                    severity=ReviewSeverity.MEDIUM,
                    title="String Concatenation in Loop",
                    description="String concatenation in loops creates many intermediate strings.",
                    file_path=context.get("file_path"),
                    line_start=i,
                    code_snippet=line.strip(),
                    fix_suggestion="Use list comprehension with join() instead.",
                    fix_example="result = ''.join(str(x) for x in items)",
                    confidence=0.8
                ))
            
            # Detect end of loop (simplified)
            if line.strip() == "" and i > loop_start + 5:  # Simple heuristic
                in_loop = False
        
        # Check for expensive operations in loops
        for i, line in enumerate(lines, 1):
            if any(op in line for op in [".append(", ".insert(0,", ".sort("]):
                # Check if it's in a loop (simplified)
                for j in range(max(0, i-10), min(len(lines), i+10)):
                    if any(keyword in lines[j] for keyword in ["for ", "while "]):
                        findings.append(self._create_finding(
                            category=ReviewCategory.PERFORMANCE,
                            severity=ReviewSeverity.LOW,
                            title="Potential Performance Issue in Loop",
                            description="Some operations can be expensive when repeated in loops.",
                            file_path=context.get("file_path"),
                            line_start=i,
                            code_snippet=line.strip(),
                            fix_suggestion="Consider moving expensive operations outside loops.",
                            confidence=0.6
                        ))
                        break
        
        return findings
    
    def _review_javascript_performance(self, code: str, context: Dict[str, Any]) -> List[ReviewFinding]:
        """Review JavaScript/TypeScript code for performance issues."""
        findings = []
        
        # Check for DOM manipulation in loops
        lines = code.split('\n')
        in_loop = False
        
        for i, line in enumerate(lines, 1):
            # Detect loops
            if any(keyword in line for keyword in ["for ", "while ", "forEach", ".map("]):
                in_loop = True
            
            # Check for DOM manipulation in loops
            if in_loop and any(dom_op in line for dom_op in [".innerHTML", ".appendChild", ".style."]):
                findings.append(self._create_finding(
                    category=ReviewCategory.PERFORMANCE,
                    severity=ReviewSeverity.MEDIUM,
                    title="DOM Manipulation in Loop",
                    description="DOM manipulation is expensive. Batch updates when possible.",
                    file_path=context.get("file_path"),
                    line_start=i,
                    code_snippet=line.strip(),
                    fix_suggestion="Use DocumentFragment or update innerHTML once after loop.",
                    fix_example="const fragment = document.createDocumentFragment();\nitems.forEach(item => {\n    fragment.appendChild(createElement(item));\n});\nelement.appendChild(fragment);",
                    confidence=0.8
                ))
            
            # Simple loop end detection
            if line.strip().endswith("}"):
                in_loop = False
        
        return findings


class CompatibilityAgent(BaseReviewAgent):
    """Agent for platform and dependency compatibility review."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("compatibility_agent", config)
    
    async def review_code(self, code: str, language: str, context: Dict[str, Any]) -> List[ReviewFinding]:
        """Review code for compatibility issues."""
        findings = []
        
        # Check for modern language features that might not be supported
        if language == "python":
            findings.extend(self._review_python_compatibility(code, context))
        elif language in ["javascript", "typescript"]:
            findings.extend(self._review_javascript_compatibility(code, context))
        
        return findings
    
    def _review_python_compatibility(self, code: str, context: Dict[str, Any]) -> List[ReviewFinding]:
        """Review Python code for compatibility issues."""
        findings = []
        
        # Check for Python version specific features
        python_version = context.get("python_version", "3.8")
        
        # Check for walrus operator (Python 3.8+)
        if ":=" in code and python_version < "3.8":
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if ":=" in line:
                    findings.append(self._create_finding(
                        category=ReviewCategory.COMPATIBILITY,
                        severity=ReviewSeverity.MEDIUM,
                        title="Walrus Operator Requires Python 3.8+",
                        description="The := (walrus) operator was introduced in Python 3.8.",
                        file_path=context.get("file_path"),
                        line_start=i,
                        code_snippet=line.strip(),
                        fix_suggestion="Use traditional assignment if supporting Python < 3.8.",
                        fix_example="value = get_value()\nif value:\n    process(value)",
                        confidence=1.0
                    ))
        
        # Check for f-strings (Python 3.6+)
        if ("f'" in code or 'f"' in code) and python_version < "3.6":
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if "f'" in line or 'f"' in line:
                    findings.append(self._create_finding(
                        category=ReviewCategory.COMPATIBILITY,
                        severity=ReviewSeverity.MEDIUM,
                        title="f-strings Require Python 3.6+",
                        description="f-strings were introduced in Python 3.6.",
                        file_path=context.get("file_path"),
                        line_start=i,
                        code_snippet=line.strip(),
                        fix_suggestion="Use str.format() or % formatting for older Python.",
                        fix_example="name = 'John'\nprint('Hello, {}'.format(name))",
                        confidence=1.0
                    ))
        
        return findings
    
    def _review_javascript_compatibility(self, code: str, context: Dict[str, Any]) -> List[ReviewFinding]:
        """Review JavaScript/TypeScript code for compatibility issues."""
        findings = []
        
        # Check for ES6+ features
        es_version = context.get("es_version", "es5")
        
        # Check for arrow functions (ES6)
        if "=>" in code and es_version < "es6":
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if "=>" in line:
                    findings.append(self._create_finding(
                        category=ReviewCategory.COMPATIBILITY,
                        severity=ReviewSeverity.MEDIUM,
                        title="Arrow Functions Require ES6+",
                        description="Arrow functions were introduced in ES6.",
                        file_path=context.get("file_path"),
                        line_start=i,
                        code_snippet=line.strip(),
                        fix_suggestion="Use traditional function expressions for ES5 compatibility.",
                        fix_example="const func = function(x) { return x * 2; };",
                        confidence=1.0
                    ))
        
        # Check for let/const (ES6)
        if any(keyword in code for keyword in ["let ", "const "]) and es_version < "es6":
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if "let " in line or "const " in line:
                    findings.append(self._create_finding(
                        category=ReviewCategory.COMPATIBILITY,
                        severity=ReviewSeverity.MEDIUM,
                        title="let/const Require ES6+",
                        description="let and const were introduced in ES6.",
                        file_path=context.get("file_path"),
                        line_start=i,
                        code_snippet=line.strip(),
                        fix_suggestion="Use var for ES5 compatibility.",
                        confidence=1.0
                    ))
        
        return findings


class CodeReviewPipeline:
    """Orchestrator for multi-agent code review."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.agents = self._initialize_agents()
    
    def _initialize_agents(self) -> Dict[str, BaseReviewAgent]:
        """Initialize all review agents."""
        return {
            "security": SecurityAgent(self.config.get("security", {})),
            "quality": QualityAgent(self.config.get("quality", {})),
            "logic": LogicAgent(self.config.get("logic", {})),
            "performance": PerformanceAgent(self.config.get("performance", {})),
            "compatibility": CompatibilityAgent(self.config.get("compatibility", {})),
        }
    
    async def review(
        self,
        code: str,
        language: str = "python",
        context: Optional[Dict[str, Any]] = None
    ) -> ReviewReport:
        """Run multi-agent code review."""
        start_time = datetime.utcnow()
        
        context = context or {}
        context.update({
            "language": language,
            "review_timestamp": start_time.isoformat()
        })
        
        # Create report
        report = ReviewReport()
        report.metadata = {
            "language": language,
            "code_length": len(code),
            "context": context
        }
        
        # Run agents in parallel
        tasks = []
        for agent_name, agent in self.agents.items():
            task = agent.review_code(code, language, context)
            tasks.append((agent_name, task))
        
        # Wait for all agents to complete
        agent_results = await asyncio.gather(*[task for _, task in tasks])
        
        # Collect findings
        for (agent_name, _), findings in zip(tasks, agent_results):
            for finding in findings:
                finding.agent_name = agent_name
                report.add_finding(finding)
        
        # Calculate trust score
        report.trust_score = self._calculate_trust_score(report)
        
        # Calculate duration
        end_time = datetime.utcnow()
        report.review_duration = (end_time - start_time).total_seconds()
        
        # Generate summary
        report.summary = {
            "overall_status": "pass" if report.total_findings == 0 else "needs_attention",
            "critical_findings": len([f for f in report.findings if f.severity == ReviewSeverity.CRITICAL]),
            "agent_count": len(self.agents),
            "language": language
        }
        
        return report
    
    def _calculate_trust_score(self, report: ReviewReport) -> float:
        """Calculate trust score based on review findings."""
        if report.total_findings == 0:
            return 100.0
        
        # Weight findings by severity
        severity_weights = {
            ReviewSeverity.CRITICAL: 20,
            ReviewSeverity.HIGH: 10,
            ReviewSeverity.MEDIUM: 5,
            ReviewSeverity.LOW: 2,
            ReviewSeverity.INFO: 0.5
        }
        
        total_weight = 0
        for finding in report.findings:
            weight = severity_weights.get(finding.severity, 5)
            total_weight += weight * finding.confidence
        
        # Convert to score (0-100)
        # More weight = lower score
        score = max(0, 100 - min(total_weight * 2, 100))
        
        return round(score, 1)
    
    def review_file(
        self,
        file_path: Path,
        language: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ReviewReport:
        """Review a file and return report."""
        # Determine language from file extension if not provided
        if language is None:
            ext = file_path.suffix.lower()
            language_map = {
                ".py": "python",
                ".js": "javascript",
                ".ts": "typescript",
                ".java": "java",
                ".go": "go",
                ".rs": "rust",
                ".cpp": "cpp",
                ".c": "c",
            }
            language = language_map.get(ext, "unknown")
        
        # Read file content
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            # Create error report
            report = ReviewReport()
            report.findings.append(ReviewFinding(
                category=ReviewCategory.QUALITY,
                severity=ReviewSeverity.CRITICAL,
                title="File Read Error",
                description=f"Could not read file: {str(e)}",
                file_path=str(file_path),
                agent_name="pipeline"
            ))
            return report
        
        # Update context
        context = context or {}
        context.update({
            "file_path": str(file_path),
            "file_size": len(content)
        })
        
        # Run review
        return asyncio.run(self.review(content, language, context))
    
    def review_directory(
        self,
        directory: Path,
        language: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, ReviewReport]:
        """Review all files in a directory."""
        reports = {}
        
        # Supported file extensions
        supported_extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
        }
        
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in supported_extensions:
                    file_language = language or supported_extensions[ext]
                    report = self.review_file(file_path, file_language, context)
                    reports[str(file_path)] = report
        
        return reports


# Export main classes
__all__ = [
    "ReviewSeverity",
    "ReviewCategory",
    "ReviewFinding",
    "ReviewReport",
    "BaseReviewAgent",
    "SecurityAgent",
    "QualityAgent",
    "LogicAgent",
    "PerformanceAgent",
    "CompatibilityAgent",
    "CodeReviewPipeline",
]