"""
TrustChain API Server — REST API for all TrustChain services.

Provides endpoints for:
- Skill management (parse, validate, execute)
- Trust scoring (code review, security analysis)
- Memory mesh operations
- Context mapping
- Marketplace operations
- Unified agent orchestration
"""

from __future__ import annotations

import json
import uuid
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import core modules
from ..universal_skill.core import USPParser, USPValidator, UniversalSkill
from ..trust_engine.core import TrustEngine, TrustScore
from ..memory_mesh.core import MemoryManager, MemoryMeshAPI
from ..context_mapper.core import ContextMapper
from ..code_review.core import CodeReviewPipeline
from ..marketplace.core import (
    SkillRegistry, SkillDownloader, SkillPublisher,
    ReputationTracker, MarketplaceAPI
)


# --- API Models ---

class SkillParseRequest(BaseModel):
    """Request to parse a skill."""
    skill_path: str
    
class SkillValidateRequest(BaseModel):
    """Request to validate a skill."""
    skill_path: str

class CodeReviewRequest(BaseModel):
    """Request to review code."""
    code: str
    language: str = "python"
    context: Optional[Dict[str, Any]] = None

class ContextMapRequest(BaseModel):
    """Request to map codebase context."""
    directory: str
    
class MemoryAddRequest(BaseModel):
    """Request to add a memory."""
    content: str
    memory_type: str = "episodic"
    priority: int = 2
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MemorySearchRequest(BaseModel):
    """Request to search memories."""
    query: Optional[str] = None
    memory_type: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: int = 10
    offset: int = 0

class MarketplaceSearchRequest(BaseModel):
    """Request to search marketplace."""
    query: Optional[str] = None
    category: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    min_trust_score: Optional[float] = None
    sort_by: str = "trust_score"
    limit: int = 20
    offset: int = 0

class MarketplacePublishRequest(BaseModel):
    """Request to publish a skill."""
    skill_path: str
    metadata: Dict[str, Any]

class OrchestrationRequest(BaseModel):
    """Request to orchestrate multiple TrustChain services."""
    task: str
    services: List[str] = Field(
        default_factory=lambda: ["trust", "context", "review"]
    )
    code: Optional[str] = None
    language: str = "python"
    context: Optional[Dict[str, Any]] = None


# --- Response Models ---

class APIResponse(BaseModel):
    """Standard API response."""
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# --- Initialize Services ---

# Configuration
config = {
    "storage_path": os.path.join(os.path.expanduser("~"), ".trustchain"),
    "trust_engine": {
        "security_weight": 0.35,
        "quality_weight": 0.25,
        "performance_weight": 0.15,
    },
    "memory_mesh": {
        "cache_size": 1000,
        "embedding_model": None,  # Will use hash-based fallback
    },
    "marketplace": {
        "cache_dir": os.path.join(os.path.expanduser("~"), ".trustchain", "marketplace", "skills"),
        "registry_path": os.path.join(os.path.expanduser("~"), ".trustchain", "marketplace"),
    }
}

# Ensure storage paths exist
os.makedirs(config["storage_path"], exist_ok=True)
os.makedirs(config["marketplace"]["registry_path"], exist_ok=True)
os.makedirs(config["marketplace"]["cache_dir"], exist_ok=True)

# Initialize services
trust_engine = TrustEngine(config=config.get("trust_engine"))
memory_manager = MemoryManager(
    config["storage_path"],
    embedding_model=config["memory_mesh"]["embedding_model"]
)
memory_api = MemoryMeshAPI(memory_manager)
context_mapper = ContextMapper()
code_review_pipeline = CodeReviewPipeline(
    config=config.get("code_review")
)

# Initialize marketplace
skill_registry = SkillRegistry(config["marketplace"]["registry_path"])
skill_downloader = SkillDownloader(config["marketplace"]["cache_dir"])
skill_publisher = SkillPublisher(skill_registry, config["marketplace"]["registry_path"])
reputation_tracker = ReputationTracker()
marketplace_api = MarketplaceAPI(
    skill_registry,
    skill_downloader,
    skill_publisher,
    reputation_tracker
)

# Initialize skill parser
usp_parser = USPParser(trust_engine=trust_engine)
usp_validator = USPValidator()


# --- FastAPI App ---

app = FastAPI(
    title="TrustChain API",
    description="Unified trust layer for AI agents. Skills, trust scoring, memory, and context.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health & Status ---

@app.get("/", response_model=APIResponse)
async def root():
    return APIResponse(
        success=True,
        message="TrustChain API is running",
        data={
            "version": "1.0.0",
            "services": ["skill", "trust", "memory", "context", "review", "marketplace"],
            "docs": "/docs"
        }
    )

@app.get("/health", response_model=APIResponse)
async def health_check():
    health_data = {
        "trust_engine": "running",
        "memory_mesh": "running",
        "total_memories": memory_manager.stats["total_memories"],
        "marketplace": f"{len(skill_registry.listings)} skills registered",
        "code_review": "running",
        "context_mapper": "running"
    }
    
    return APIResponse(
        success=True,
        message="All services healthy",
        data=health_data
    )


# --- Skill Management Endpoints ---

@app.post("/skills/parse", response_model=APIResponse)
async def parse_skill(request: SkillParseRequest):
    """Parse a skill from a file or directory."""
    try:
        skill = usp_parser.parse_skill(request.skill_path)
        
        return APIResponse(
            success=True,
            message=f"Skill '{skill.metadata.name}' parsed successfully",
            data={
                "skill_id": skill.skill_id,
                "metadata": skill.metadata.dict(),
                "implementation": {
                    "main_file": skill.implementation.main_file,
                    "scripts": list(skill.implementation.scripts.keys()),
                    "assets": list(skill.implementation.assets.keys()),
                    "supporting_files": skill.implementation.supporting_files,
                }
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/skills/validate", response_model=APIResponse)
async def validate_skill(request: SkillValidateRequest):
    """Validate a skill against USP standards."""
    try:
        skill = usp_parser.parse_skill(request.skill_path)
        validation_result = usp_validator.validate(skill)
        
        return APIResponse(
            success=validation_result["valid"],
            message=f"Skill validation {'passed' if validation_result['valid'] else 'failed'}",
            data=validation_result
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/skills/list", response_model=APIResponse)
async def list_skills():
    """List all registered skills."""
    try:
        skills_list = [
            listing.to_dict() 
            for listing in skill_registry.listings.values()
        ]
        
        return APIResponse(
            success=True,
            message=f"Found {len(skills_list)} skills",
            data={"skills": skills_list}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Trust Scoring Endpoints ---

@app.post("/trust/score-code", response_model=APIResponse)
async def score_code(request: CodeReviewRequest):
    """Score code for trustworthiness."""
    try:
        trust_score = trust_engine.score_code(
            request.code,
            language=request.language,
            filepath=request.context.get("file_path") if request.context else None
        )
        
        return APIResponse(
            success=True,
            message=f"Trust score: {trust_score.overall}/100",
            data=trust_score.to_dict()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trust/analyze-deps", response_model=APIResponse)
async def analyze_dependencies(requirements: str):
    """Analyze dependencies for vulnerabilities."""
    try:
        analysis = trust_engine.dependency_analyzer.analyze_python_dependencies(requirements)
        
        return APIResponse(
            success=True,
            message=f"Found {len(analysis.get('vulnerabilities', []))} vulnerabilities",
            data=analysis
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Memory Mesh Endpoints ---

@app.post("/memory/add", response_model=APIResponse)
async def add_memory(request: MemoryAddRequest):
    """Add a memory to the mesh."""
    try:
        result = memory_api.add_memory_endpoint({
            "content": request.content,
            "memory_type": request.memory_type,
            "priority": request.priority,
            "tags": request.tags,
            "metadata": request.metadata
        })
        
        return APIResponse(
            success=result["success"],
            message=result.get("message", "Memory added"),
            data={"memory_id": result.get("memory_id")}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/{memory_id}", response_model=APIResponse)
async def get_memory(memory_id: str):
    """Get a memory by ID."""
    try:
        memory = memory_manager.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return APIResponse(
            success=True,
            message="Memory retrieved",
            data={"memory": memory.to_dict()}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/search", response_model=APIResponse)
async def search_memories(request: MemorySearchRequest):
    """Search for memories."""
    try:
        result = memory_api.search_memories_endpoint({
            "query": request.query,
            "memory_type": request.memory_type,
            "tags": request.tags,
            "limit": request.limit,
            "offset": request.offset
        })
        
        return APIResponse(
            success=result["success"],
            message=f"Found {result.get('count', 0)} memories",
            data={"memories": result.get("memories", [])}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/timeline", response_model=APIResponse)
async def get_timeline(
    limit: int = Query(default=50),
    agent_id: Optional[str] = Query(default=None)
):
    """Get memory timeline."""
    try:
        result = memory_api.get_timeline_endpoint({
            "agent_id": agent_id,
            "limit": limit
        })
        
        return APIResponse(
            success=result["success"],
            message=f"Retrieved {result.get('count', 0)} timeline entries",
            data={"timeline": result.get("timeline", [])}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/stats", response_model=APIResponse)
async def get_memory_stats():
    """Get memory mesh statistics."""
    try:
        stats = memory_manager.get_stats()
        
        return APIResponse(
            success=True,
            message="Memory stats retrieved",
            data=stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Context Mapping Endpoints ---

@app.post("/context/map", response_model=APIResponse)
async def map_context(request: ContextMapRequest):
    """Map context from a codebase directory."""
    try:
        directory = Path(request.directory)
        if not directory.exists():
            raise HTTPException(status_code=404, detail="Directory not found")
        
        context_graph = context_mapper.map_codebase(directory)
        
        return APIResponse(
            success=True,
            message=f"Mapped {len(context_graph.rules)} context rules",
            data={
                "rules_count": len(context_graph.rules),
                "rule_types": {
                    rule_type.value: sum(
                        1 for r in context_graph.rules.values()
                        if r.rule_type.value == rule_type.value
                    )
                    for rule_type in set(r.rule_type for r in context_graph.rules.values())
                }
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/context/validate", response_model=APIResponse)
async def validate_context(
    code: str,
    file_path: str = Query(default=""),
    line_number: int = Query(default=1)
):
    """Validate code against context rules."""
    try:
        result = context_mapper.validate_code(code, file_path, line_number)
        
        return APIResponse(
            success=result["valid"],
            message=f"Validation {'passed' if result['valid'] else 'failed'} — "
                     f"{len(result['violations'])} violations, {len(result['warnings'])} warnings",
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Code Review Endpoints ---

@app.post("/review/code", response_model=APIResponse)
async def review_code(request: CodeReviewRequest):
    """Run multi-agent code review."""
    try:
        report = await code_review_pipeline.review(
            request.code,
            language=request.language,
            context=request.context or {}
        )
        
        return APIResponse(
            success=report.summary.get("overall_status") == "pass",
            message=f"Review complete — {report.total_findings} findings, trust score: {report.trust_score}/100",
            data=report.to_dict()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/review/file", response_model=APIResponse)
async def review_file(
    file_path: str = Query(default=""),
    language: str = Query(default="")
):
    """Review a file."""
    try:
        path = Path(file_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        report = code_review_pipeline.review_file(
            path,
            language=language or None
        )
        
        return APIResponse(
            success=report.summary.get("overall_status") == "pass",
            message=f"Review complete — {report.total_findings} findings",
            data=report.to_dict()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Marketplace Endpoints ---

@app.post("/marketplace/search", response_model=APIResponse)
async def marketplace_search(request: MarketplaceSearchRequest):
    """Search for skills in the marketplace."""
    try:
        result = await marketplace_api.search({
            "query": request.query,
            "category": request.category,
            "author": request.author,
            "tags": request.tags,
            "min_trust_score": request.min_trust_score,
            "sort_by": request.sort_by,
            "limit": request.limit,
            "offset": request.offset
        })
        
        return APIResponse(
            success=result["success"],
            message=f"Found {result.get('count', 0)} skills",
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/marketplace/download/{skill_id}", response_model=APIResponse)
async def marketplace_download(skill_id: str):
    """Download a skill from the marketplace."""
    try:
        result = await marketplace_api.download(skill_id)
        return APIResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/marketplace/publish", response_model=APIResponse)
async def marketplace_publish(request: MarketplacePublishRequest):
    """Publish a skill to the marketplace."""
    try:
        result = marketplace_api.publish(
            request.skill_path,
            request.metadata
        )
        return APIResponse(
            success=True,
            message=f"Skill '{request.metadata.get('name')}' published",
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/marketplace/stats", response_model=APIResponse)
async def marketplace_stats():
    """Get marketplace statistics."""
    try:
        stats = marketplace_api.get_stats()
        return APIResponse(
            success=True,
            message="Marketplace stats retrieved",
            data=stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/marketplace/categories", response_model=APIResponse)
async def marketplace_categories():
    """Get marketplace categories."""
    try:
        categories = marketplace_api.get_categories()
        return APIResponse(
            success=True,
            message=f"Found {len(categories.get('categories', []))} categories",
            data=categories
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Orchestration Endpoint ---

@app.post("/orchestrate", response_model=APIResponse)
async def orchestrate(request: OrchestrationRequest):
    """Orchestrate multiple TrustChain services in one request."""
    results = {}
    
    try:
        tasks = []
        
        for service in request.services:
            if service == "trust" and request.code:
                trust_score = trust_engine.score_code(
                    request.code,
                    language=request.language
                )
                results["trust"] = trust_score.to_dict()
            
            elif service == "context" and request.context:
                context_prompt = context_mapper.generate_validation_prompt(request.task)
                results["context"] = {"validation_prompt": context_prompt}
            
            elif service == "review" and request.code:
                report = await code_review_pipeline.review(
                    request.code,
                    language=request.language,
                    context=request.context or {}
                )
                results["review"] = report.to_dict()
            
            elif service == "memory":
                memory_entry = memory_api.add_memory_endpoint({
                    "content": request.task,
                    "memory_type": "procedural",
                    "priority": 2
                })
                results["memory"] = memory_entry
        
        combined_trust = 0
        count = 0
        for key, value in results.items():
            if isinstance(value, dict) and "overall" in value:
                combined_trust += value["overall"]
                count += 1
        
        overall_trust = combined_trust / count if count > 0 else None
        
        return APIResponse(
            success=True,
            message=f"Orchestrated {len(results)} services",
            data={
                "services": results,
                "overall_trust_score": overall_trust
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Main entry point ---

def start_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the TrustChain API server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()