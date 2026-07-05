"""
TrustChain CLI — Command-line interface for TrustChain services.

Provides commands for:
- Skill management (parse, validate, execute)
- Trust scoring (code review, security analysis)
- Memory mesh operations
- Context mapping
- Marketplace operations
- Unified orchestration
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown

# Import core modules
from src.universal_skill.core import USPParser, USPValidator
from src.trust_engine.core import TrustEngine
from src.memory_mesh.core import MemoryMeshAPI
from src.context_mapper.core import ContextMapper
from src.code_review.core import CodeReviewPipeline
from src.marketplace.core import (
    SkillRegistry, SkillDownloader, SkillPublisher,
    ReputationTracker, MarketplaceAPI
)

# Initialize console
console = Console()

# Initialize Typer app
app = typer.Typer(
    name="trustchain",
    help="TrustChain CLI — Unified trust layer for AI agents",
    add_completion=False
)

# Global configuration
config_path = Path.home() / ".trustchain" / "config.json"
config = {
    "storage_path": str(Path.home() / ".trustchain"),
    "trust_engine": {
        "security_weight": 0.35,
        "quality_weight": 0.25,
        "performance_weight": 0.15,
    },
    "memory_mesh": {
        "cache_size": 1000,
        "embedding_model": None,
    },
    "marketplace": {
        "cache_dir": str(Path.home() / ".trustchain" / "marketplace" / "skills"),
        "registry_path": str(Path.home() / ".trustchain" / "marketplace"),
    }
}

# Ensure config directory exists
config_path.parent.mkdir(parents=True, exist_ok=True)
if config_path.exists():
    try:
        user_config = json.loads(config_path.read_text())
        config.update(user_config)
    except:
        pass

# Initialize services
def get_trust_engine():
    return TrustEngine(config=config.get("trust_engine"))

def get_memory_api():
    from src.memory_mesh.core import MemoryManager
    memory_manager = MemoryManager(
        config["storage_path"],
        embedding_model=config["memory_mesh"]["embedding_model"]
    )
    return MemoryMeshAPI(memory_manager)

def get_context_mapper():
    return ContextMapper()

def get_code_review_pipeline():
    return CodeReviewPipeline(config=config.get("code_review"))

def get_marketplace_api():
    skill_registry = SkillRegistry(config["marketplace"]["registry_path"])
    skill_downloader = SkillDownloader(config["marketplace"]["cache_dir"])
    skill_publisher = SkillPublisher(skill_registry, config["marketplace"]["registry_path"])
    reputation_tracker = ReputationTracker()
    
    return MarketplaceAPI(
        skill_registry,
        skill_downloader,
        skill_publisher,
        reputation_tracker
    )


# --- Skill Commands ---

@app.command("skill-parse")
def skill_parse(
    skill_path: str = typer.Argument(..., help="Path to skill file or directory"),
    output: Optional[Path] = typer.Option(None, help="Output file for parsed skill"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output")
):
    """Parse a skill from a file or directory."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Parsing skill...", total=None)
        
        try:
            parser = USPParser(trust_engine=get_trust_engine())
            skill = parser.parse_skill(skill_path)
            
            progress.update(task, completed=1, description="Skill parsed!")
            
            # Display results
            if verbose:
                console.print(Panel.fit(
                    f"[bold green]Skill '{skill.metadata.name}' parsed successfully[/bold green]\n"
                    f"ID: {skill.skill_id}\n"
                    f"Version: {skill.metadata.version}\n"
                    f"Author: {skill.metadata.author}\n"
                    f"Description: {skill.metadata.description[:100]}...",
                    title="Skill Details"
                ))
                
                # Show implementation
                table = Table(title="Implementation Files")
                table.add_column("Type", style="cyan")
                table.add_column("File", style="green")
                table.add_column("Size", style="yellow")
                
                table.add_row("Main", skill.implementation.main_file, "—")
                for script_name, script_path in skill.implementation.scripts.items():
                    table.add_row("Script", script_name, "—")
                for asset_name, asset_path in skill.implementation.assets.items():
                    table.add_row("Asset", asset_name, "—")
                for support_file in skill.implementation.supporting_files:
                    table.add_row("Support", support_file, "—")
                
                console.print(table)
            else:
                console.print(f"[green]✓[/green] Skill '{skill.metadata.name}' parsed successfully")
                console.print(f"  ID: {skill.skill_id}")
                console.print(f"  Version: {skill.metadata.version}")
            
            # Save to file if requested
            if output:
                skill_data = {
                    "skill_id": skill.skill_id,
                    "metadata": skill.metadata.dict(),
                    "implementation": {
                        "main_file": skill.implementation.main_file,
                        "scripts": skill.implementation.scripts,
                        "assets": skill.implementation.assets,
                        "supporting_files": skill.implementation.supporting_files,
                    }
                }
                output.write_text(json.dumps(skill_data, indent=2))
                console.print(f"[blue]ℹ[/blue] Skill data saved to {output}")
            
        except Exception as e:
            console.print(f"[red]✗[/red] Error parsing skill: {e}")
            sys.exit(1)


@app.command("skill-validate")
def skill_validate(
    skill_path: str = typer.Argument(..., help="Path to skill file or directory"),
    strict: bool = typer.Option(False, "--strict", help="Enable strict validation")
):
    """Validate a skill against USP standards."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Validating skill...", total=None)
        
        try:
            parser = USPParser(trust_engine=get_trust_engine())
            validator = USPValidator()
            
            skill = parser.parse_skill(skill_path)
            validation_result = validator.validate(skill, strict=strict)
            
            progress.update(task, completed=1, description="Validation complete!")
            
            # Display results
            if validation_result["valid"]:
                console.print(f"[green]✓[/green] Skill validation passed")
                console.print(f"  Score: {validation_result.get('score', 0)}/100")
                
                if validation_result.get("warnings"):
                    console.print("[yellow]⚠[/yellow] Warnings:")
                    for warning in validation_result["warnings"]:
                        console.print(f"  • {warning}")
            else:
                console.print(f"[red]✗[/red] Skill validation failed")
                console.print(f"  Score: {validation_result.get('score', 0)}/100")
                
                if validation_result.get("errors"):
                    console.print("[red]✗[/red] Errors:")
                    for error in validation_result["errors"]:
                        console.print(f"  • {error}")
                
                if validation_result.get("warnings"):
                    console.print("[yellow]⚠[/yellow] Warnings:")
                    for warning in validation_result["warnings"]:
                        console.print(f"  • {warning}")
            
            # Exit code based on validation result
            sys.exit(0 if validation_result["valid"] else 1)
            
        except Exception as e:
            console.print(f"[red]✗[/red] Error validating skill: {e}")
            sys.exit(1)


# --- Trust Commands ---

@app.command("trust-score")
def trust_score(
    code_path: Optional[Path] = typer.Option(None, "--file", "-f", help="Path to code file"),
    code: Optional[str] = typer.Option(None, "--code", "-c", help="Code string"),
    language: str = typer.Option("python", "--lang", "-l", help="Programming language"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file")
):
    """Score code for trustworthiness."""
    if not code_path and not code:
        console.print("[red]✗[/red] Either --file or --code must be provided")
        sys.exit(1)
    
    if code_path:
        if not code_path.exists():
            console.print(f"[red]✗[/red] File not found: {code_path}")
            sys.exit(1)
        code_content = code_path.read_text()
    else:
        code_content = code
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Scoring code...", total=None)
        
        try:
            trust_engine = get_trust_engine()
            trust_score = trust_engine.score_code(
                code_content,
                language=language,
                filepath=str(code_path) if code_path else None
            )
            
            progress.update(task, completed=1, description="Scoring complete!")
            
            # Display results
            console.print(Panel.fit(
                f"[bold]Trust Score: {trust_score.overall}/100[/bold]\n"
                f"Security: {trust_score.security}/100\n"
                f"Quality: {trust_score.quality}/100\n"
                f"Performance: {trust_score.performance}/100\n"
                f"AI Confidence: {trust_score.ai_confidence}/100",
                title="Trust Analysis"
            ))
            
            # Show breakdown
            if trust_score.breakdown:
                table = Table(title="Score Breakdown")
                table.add_column("Category", style="cyan")
                table.add_column("Score", style="green")
                table.add_column("Weight", style="yellow")
                table.add_column("Contribution", style="blue")
                
                for category, details in trust_score.breakdown.items():
                    table.add_row(
                        category,
                        f"{details['score']}/100",
                        f"{details['weight']*100:.1f}%",
                        f"{details['contribution']:.1f}"
                    )
                
                console.print(table)
            
            # Show issues if any
            if trust_score.issues:
                console.print("[yellow]⚠[/yellow] Issues found:")
                for issue in trust_score.issues[:5]:  # Show top 5
                    console.print(f"  • {issue}")
                if len(trust_score.issues) > 5:
                    console.print(f"  ... and {len(trust_score.issues) - 5} more")
            
            # Save to file if requested
            if output:
                output.write_text(json.dumps(trust_score.to_dict(), indent=2))
                console.print(f"[blue]ℹ[/blue] Trust score saved to {output}")
            
        except Exception as e:
            console.print(f"[red]✗[/red] Error scoring code: {e}")
            sys.exit(1)


@app.command("trust-analyze-deps")
def trust_analyze_deps(
    requirements_path: Path = typer.Argument(..., help="Path to requirements.txt"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file")
):
    """Analyze dependencies for vulnerabilities."""
    if not requirements_path.exists():
        console.print(f"[red]✗[/red] File not found: {requirements_path}")
        sys.exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Analyzing dependencies...", total=None)
        
        try:
            trust_engine = get_trust_engine()
            requirements = requirements_path.read_text()
            analysis = trust_engine.dependency_analyzer.analyze_python_dependencies(requirements)
            
            progress.update(task, completed=1, description="Analysis complete!")
            
            # Display results
            vulnerabilities = analysis.get("vulnerabilities", [])
            outdated = analysis.get("outdated", [])
            
            if not vulnerabilities and not outdated:
                console.print(f"[green]✓[/green] No vulnerabilities or outdated packages found")
            else:
                if vulnerabilities:
                    console.print(f"[red]✗[/red] Found {len(vulnerabilities)} vulnerabilities:")
                    for vuln in vulnerabilities[:5]:  # Show top 5
                        console.print(f"  • {vuln['package']}: {vuln['severity']} - {vuln['description']}")
                    if len(vulnerabilities) > 5:
                        console.print(f"  ... and {len(vulnerabilities) - 5} more")
                
                if outdated:
                    console.print(f"[yellow]⚠[/yellow] Found {len(outdated)} outdated packages:")
                    for package in outdated[:5]:  # Show top 5
                        console.print(f"  • {package['name']}: {package['current']} → {package['latest']}")
                    if len(outdated) > 5:
                        console.print(f"  ... and {len(outdated) - 5} more")
            
            # Save to file if requested
            if output:
                output.write_text(json.dumps(analysis, indent=2))
                console.print(f"[blue]ℹ[/blue] Analysis saved to {output}")
            
        except Exception as e:
            console.print(f"[red]✗[/red] Error analyzing dependencies: {e}")
            sys.exit(1)


# --- Memory Commands ---

@app.command("memory-add")
def memory_add(
    content: str = typer.Argument(..., help="Memory content"),
    memory_type: str = typer.Option("episodic", "--type", "-t", help="Memory type"),
    priority: int = typer.Option(2, "--priority", "-p", help="Priority (1-5)"),
    tags: Optional[List[str]] = typer.Option(None, "--tag", help="Tags for the memory"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file")
):
    """Add a memory to the mesh."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Adding memory...", total=None)
        
        try:
            memory_api = get_memory_api()
            result = memory_api.add_memory_endpoint({
                "content": content,
                "memory_type": memory_type,
                "priority": priority,
                "tags": tags or []
            })
            
            progress.update(task, completed=1, description="Memory added!")
            
            if result["success"]:
                console.print(f"[green]✓[/green] Memory added with ID: {result['memory_id']}")
                
                # Save to file if requested
                if output:
                    output.write_text(json.dumps(result, indent=2))
                    console.print(f"[blue]ℹ[/blue] Memory data saved to {output}")
            else:
                console.print(f"[red]✗[/red] Failed to add memory: {result.get('error')}")
                sys.exit(1)
            
        except Exception as e:
            console.print(f"[red]✗[/red] Error adding memory: {e}")
            sys.exit(1)


@app.command("memory-search")
def memory_search(
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search query"),
    memory_type: Optional[str] = typer.Option(None, "--type", "-t", help="Memory type filter"),
    tags: Optional[List[str]] = typer.Option(None, "--tag", help="Tags filter"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum results"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file")
):
    """Search for memories."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Searching memories...", total=None)
        
        try:
            memory_api = get_memory_api()
            result = memory_api.search_memories_endpoint({
                "query": query,
                "memory_type": memory_type,
                "tags": tags,
                "limit": limit,
                "offset": 0
            })
            
            progress.update(task, completed=1, description="Search complete!")
            
            if result["success"]:
                memories = result.get("memories", [])
                console.print(f"[green]✓[/green] Found {result.get('count', 0)} memories")
                
                if memories:
                    table = Table(title="Search Results")
                    table.add_column("ID", style="cyan")
                    table.add_column("Type", style="green")
                    table.add_column("Content", style="white")
                    table.add_column("Tags", style="yellow")
                    
                    for memory in memories[:10]:  # Show top 10
                        content_preview = (
                            memory["content"][:50] + "..."
                            if len(memory["content"]) > 50
                            else memory["content"]
                        )
                        tags_str = ", ".join(memory.get("tags", []))[:20]
                        table.add_row(
                            memory["id"][:8],
                            memory["type"],
                            content_preview,
                            tags_str
                        )
                    
                    console.print(table)
                
                # Save to file if requested
                if output:
                    output.write_text(json.dumps(result, indent=2))
                    console.print(f"[blue]ℹ[/blue] Search results saved to {output}")
            else:
                console.print(f"[red]✗[/red] Search failed: {result.get('error')}")
                sys.exit(1)
            
        except Exception as e:
            console.print(f"[red]✗[/red] Error searching memories: {e}")
            sys.exit(1)


# --- Context Commands ---

@app.command("context-map")
def context_map(
    directory: Path = typer.Argument(..., help="Directory to map"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file")
):
    """Map context from a codebase directory."""
    if not directory.exists():
        console.print(f"[red]✗[/red] Directory not found: {directory}")
        sys.exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Mapping context...", total=None)
        
        try:
            context_mapper = get_context_mapper()
            context_graph = context_mapper.map_codebase(directory)
            
            progress.update(task, completed=1, description="Mapping complete!")
            
            # Display results
            rule_types = {}
            for rule in context_graph.rules.values():
                rule_type = rule.rule_type.value
                rule_types[rule_type] = rule_types.get(rule_type, 0) + 1
            
            console.print(f"[green]✓[/green] Mapped {len(context_graph.rules)} context rules")
            
            table = Table(title="Context Rules by Type")
            table.add_column("Rule Type", style="cyan")
            table.add_column("Count", style="green")
            
            for rule_type, count in sorted(rule_types.items(), key=lambda x: x[1], reverse=True):
                table.add_row(rule_type, str(count))
            
            console.print(table)
            
            # Save to file if requested
            if output:
                graph_json = context_graph.to_json()
                output.write_text(graph_json)
                console.print(f"[blue]ℹ[/blue] Context graph saved to {output}")
            
        except Exception as e:
            console.print(f"[red]✗[/red] Error mapping context: {e}")
            sys.exit(1)


# --- Review Commands ---

@app.command("review-code")
def review_code(
    code_path: Optional[Path] = typer.Option(None, "--file", "-f", help="Path to code file"),
    code: Optional[str] = typer.Option(None, "--code", "-c", help="Code string"),
    language: str = typer.Option("python", "--lang", "-l", help="Programming language"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file")
):
    """Run multi-agent code review."""
    if not code_path and not code:
        console.print("[red]✗[/red] Either --file or --code must be provided")
        sys.exit(1)
    
    if code_path:
        if not code_path.exists():
            console.print(f"[red]✗[/red] File not found: {code_path}")
            sys.exit(1)
        code_content = code_path.read_text()
    else:
        code_content = code
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Reviewing code...", total=None)
        
        try:
            review_pipeline = get_code_review_pipeline()
            report = asyncio.run(review_pipeline.review(
                code_content,
                language=language
            ))
            
            progress.update(task, completed=1, description="Review complete!")
            
            # Display results
            console.print(Panel.fit(
                f"[bold]Code Review Report[/bold]\n"
                f"Trust Score: {report.trust_score}/100\n"
                f"Total Findings: {report.total_findings}\n"
                f"Critical: {report.findings_by_severity.get('critical', 0)}\n"
                f"High: {report.findings_by_severity.get('high', 0)}\n"
                f"Medium: {report.findings_by_severity.get('medium', 0)}",
                title="Review Summary"
            ))
            
            # Show critical/high findings
            critical_findings = [
                f for f in report.findings
                if f.severity.value in ["critical", "high"]
            ]
            
            if critical_findings:
                console.print("[red]⚠[/red] Critical/High Findings:")
                for i, finding in enumerate(critical_findings[:5], 1):
                    console.print(f"  {i}. [{finding.severity.value.upper()}] {finding.title}")
                    if finding.file_path:
                        console.print(f"     File: {finding.file_path}:{finding.line_start or '?'}")
                    if finding.fix_suggestion:
                        console.print(f"     Fix: {finding.fix_suggestion[:100]}...")
            
            # Show statistics
            table = Table(title="Review Statistics")
            table.add_column("Agent", style="cyan")
            table.add_column("Findings", style="green")
            
            agent_counts = {}
            for finding in report.findings:
                agent_counts[finding.agent_name] = agent_counts.get(finding.agent_name, 0) + 1
            
            for agent, count in agent_counts.items():
                table.add_row(agent, str(count))
            
            console.print(table)
            
            # Save to file if requested
            if output:
                output.write_text(json.dumps(report.to_dict(), indent=2))
                console.print(f"[blue]ℹ[/blue] Review report saved to {output}")
            
        except Exception as e:
            console.print(f"[red]✗[/red] Error reviewing code: {e}")
            sys.exit(1)


# --- Marketplace Commands ---

@app.command("marketplace-search")
def marketplace_search(
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search query"),
    category: Optional[str] = typer.Option(None, "--category", help="Category filter"),
    author: Optional[str] = typer.Option(None, "--author", help="Author filter"),
    tags: Optional[List[str]] = typer.Option(None, "--tag", help="Tags filter"),
    min_trust: float = typer.Option(0.0, "--min-trust", help="Minimum trust score"),
    sort_by: str = typer.Option("trust_score", "--sort", help="Sort field"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum results"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file")
):
    """Search for skills in the marketplace."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Searching marketplace...", total=None)
        
        try:
            marketplace = get_marketplace_api()
            result = asyncio.run(marketplace.search({
                "query": query,
                "category": category,
                "author": author,
                "tags": tags,
                "min_trust_score": min_trust,
                "sort_by": sort_by,
                "limit": limit,
                "offset": 0
            }))
            
            progress.update(task, completed=1, description="Search complete!")
            
            if result["success"]:
                skills = result.get("results", [])
                console.print(f"[green]✓[/green] Found {result.get('count', 0)} skills")
                
                if skills:
                    table = Table(title="Marketplace Skills")
                    table.add_column("Name", style="cyan")
                    table.add_column("Author", style="green")
                    table.add_column("Trust", style="yellow")
                    table.add_column("Downloads", style="blue")
                    table.add_column("Description", style="white")
                    
                    for skill in skills[:10]:  # Show top 10
                        desc_preview = (
                            skill["description"][:50] + "..."
                            if len(skill["description"]) > 50
                            else skill["description"]
                        )
                        table.add_row(
                            skill["name"],
                            skill["author"],
                            f"{skill['trust_score']:.1f}",
                            str(skill["download_count"]),
                            desc_preview
                        )
                    
                    console.print(table)
                
                # Save to file if requested
                if output:
                    output.write_text(json.dumps(result, indent=2))
                    console.print(f"[blue]ℹ[/blue] Search results saved to {output}")
            else:
                console.print(f"[red]✗[/red] Search failed: {result.get('error')}")
                sys.exit(1)
            
        except Exception as e:
            console.print(f"[red]✗[/red] Error searching marketplace: {e}")
            sys.exit(1)


# --- Configuration Commands ---

@app.command("config-show")
def config_show():
    """Show current configuration."""
    console.print(Panel.fit(
        json.dumps(config, indent=2),
        title="TrustChain Configuration"
    ))


@app.command("config-set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key (e.g., trust_engine.security_weight)"),
    value: str = typer.Argument(..., help="Value to set")
):
    """Set a configuration value."""
    try:
        # Parse value (try JSON first, then string)
        try:
            parsed_value = json.loads(value)
        except:
            parsed_value = value
        
        # Update config
        keys = key.split(".")
        current = config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = parsed_value
        
        # Save to file
        config_path.write_text(json.dumps(config, indent=2))
        console.print(f"[green]✓[/green] Configuration updated: {key} = {parsed_value}")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error setting configuration: {e}")
        sys.exit(1)


# --- Main entry point ---

def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()