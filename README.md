# TrustChain — Universal AI Trust & Quality Infrastructure

<p align="center">
  <img src="assets/trustchain-logo.svg" alt="TrustChain Logo" width="280">
</p>

<p align="center">
  <strong>The open-source infrastructure that brings trust, portability, and persistence to the AI Agent ecosystem.</strong>
</p>

<p align="center">
  <a href="https://github.com/lanekingkong/trustchain/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%2B-green.svg" alt="Python"></a>
  <a href="https://nodejs.org/"><img src="https://img.shields.io/badge/Node.js-20%2B-brightgreen.svg" alt="Node.js"></a>
  <a href="#contributing"><img src="https://img.shields.io/badge/PRs-Welcome-brightgreen.svg" alt="PRs Welcome"></a>
</p>

---

## 🎯 What Problem Does TrustChain Solve?

In 2026, AI agents have become central to software development, but the ecosystem faces **five fundamental crises**:

| Crisis | Severity | Impact |
|--------|----------|--------|
| **Code Trust Crisis** | 🔴 Critical | 96% of developers don't trust AI-generated code for production |
| **Skills Fragmentation** | 🔴 Critical | Agent skills are locked to single platforms (Claude Code ≠ Codex ≠ Cursor) |
| **Context Amnesia** | 🟠 Severe | 65% of developers lose context between sessions |
| **Review Bottleneck** | 🟠 Severe | AI generates code 10x faster than humans can review it |
| **Context Debt** | 🟡 Growing | Legacy codebases have implicit knowledge AI can never access |

**TrustChain is the unified solution.** Five integrated modules work together to rebuild trust in the AI-powered development lifecycle.

---

## 🏗️ 5W1H Framework

### WHAT — Five Integrated Modules

```
┌─────────────────────────────────────────────────────────────┐
│                     TrustChain Platform                      │
├─────────────┬─────────────┬──────────────┬─────────────────┤
│ Universal   │  Trust      │  Memory      │  Context        │
│ Skill       │  Engine     │  Mesh        │  Mapper         │
│ Protocol    │             │              │                 │
├─────────────┴─────────────┴──────────────┴─────────────────┤
│                   Code Review Pipeline                      │
├─────────────────────────────────────────────────────────────┤
│              Marketplace & Community Layer                   │
└─────────────────────────────────────────────────────────────┘
```

### WHY — The Mission

The AI agent ecosystem suffers from a fundamental trust deficit: **code is generated faster than it can be verified, skills don't travel across agents, and memory evaporates between sessions.** TrustChain exists to close this trust gap — making AI-generated code auditable, verifiable, and production-ready at scale.

### WHO — For Whom?

- **Developers** who need to trust AI-generated code before merging
- **Skill Creators** wanting write-once-run-anywhere portability
- **Engineering Teams** drowning in unreviewed AI code
- **Enterprises** needing compliance-grade AI code verification
- **Open Source Maintainers** flooded with AI-generated PRs

### WHEN — The Urgency

The crisis is accelerating: GitHub reports AI-generated code now accounts for 42% of all new commits. Without infrastructure like TrustChain, the **"AI Code Trust Gap"** will widen irreversibly by late 2026.

### WHERE — Integration Points

TrustChain integrates at every layer of the development stack:
- **IDE**: VS Code, JetBrains, Cursor plugins
- **CI/CD**: GitHub Actions, GitLab CI, Jenkins
- **CLI**: Direct terminal integration
- **Agent**: SDK for Claude Code, Codex, OpenClaw, Gemini CLI

### HOW — Technical Implementation

Each module is a standalone, composable service connected via a unified gRPC + REST API:

| Module | Core Tech | Key Innovation |
|--------|-----------|----------------|
| **Universal Skill Protocol** | USP Spec v1.0, YAML/JSON Schema | Write once, run on any agent — zero-config portability |
| **Trust Engine** | ML-based scoring, AST analysis, sandbox testing | Multi-dimensional trust scoring (0-100) with explainable results |
| **Memory Mesh** | Vector DB + graph store, delta sync | Cross-session, cross-agent persistent memory |
| **Context Mapper** | Static analysis + LLM extraction | Automatically documents implicit business rules from code |
| **Code Review Pipeline** | Multi-agent orchestration | Parallel review by security, style, logic, performance agents |
| **Marketplace** | Decentralized registry, P2P sharing | Discover, rate, and fork skills with built-in trust metrics |

---

## 🚀 Installation & Usage

### Installation

### Prerequisites

- Python 3.10+
- Node.js 20+
- Docker & Docker Compose (optional)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/lanekingkong/trustchain.git
cd trustchain

# Install with one command
./scripts/install.sh

# Or manually:
pip install -e .
npm install -g trustchain-cli

# Verify installation
trustchain --version
```

### 5-Minute Quick Demo

```bash
# 1. Start the TrustChain server
trustchain serve

# 2. Register a skill (write-once, run-anywhere)
trustchain skill create ./my-skill

# 3. Validate AI-generated code
trustchain validate ./generated_code.py

# 4. Check trust score
trustchain trust-score ./project/

# 5. Persist session context
trustchain memory save "Refactoring auth module — halfway through"
```

---

## 🏗️ Architecture

TrustChain follows a modular microservices architecture where each module communicates via unified gRPC + REST API.

| Module | Description | Documentation |
|--------|-------------|---------------|
| USP | Universal Skill Protocol Specification | [docs/usp-spec.md](docs/usp-spec.md) |
| Trust Engine | Multi-dimensional code trust scoring | [docs/trust-engine.md](docs/trust-engine.md) |
| Memory Mesh | Cross-session persistent memory | [docs/memory-mesh.md](docs/memory-mesh.md) |
| Context Mapper | Legacy code knowledge extraction | [docs/context-mapper.md](docs/context-mapper.md) |
| Code Review | Multi-agent review pipeline | [docs/code-review.md](docs/code-review.md) |
| Marketplace | Decentralized skill registry | [docs/marketplace.md](docs/marketplace.md) |

---

## 🔌 Integration Examples

### VS Code Extension

```json
// .vscode/settings.json
{
  "trustchain.enabled": true,
  "trustchain.autoValidate": "onSave",
  "trustchain.minTrustScore": 75,
  "trustchain.memorySync": true
}
```

### GitHub Actions

```yaml
name: TrustChain Validation
on: [pull_request]
jobs:
  trust-check:
    runs-on: ubuntu-latest
    steps:
      - uses: lanekingkong/trustchain-action@v1
        with:
          min-score: 80
          generate-report: true
```

### CLI Commands

```bash
# Core
trustchain init              # Initialize project
trustchain serve             # Start server
trustchain status            # System status

# Skills
trustchain skill create      # Create new skill
trustchain skill publish     # Publish to marketplace
trustchain skill install     # Install from marketplace

# Trust
trustchain validate          # Validate code
trustchain trust-score       # Calculate trust score
trustchain audit             # Full security audit

# Memory
trustchain memory save       # Save context
trustchain memory restore    # Restore context
trustchain memory search     # Search memory

# Context
trustchain context map       # Map codebase context
trustchain context extract   # Extract business rules
trustchain context verify    # Verify AI code against context
```

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Development Setup

```bash
git clone https://github.com/lanekingkong/trustchain.git
cd trustchain
pip install -e ".[dev]"
npm install
pre-commit install
```

### Project Structure

```
trustchain/
├── src/
│   ├── core/                  # Core orchestrator
│   ├── universal_skill/       # USP specification & engine
│   ├── trust_engine/          # Trust scoring & validation
│   ├── memory_mesh/           # Persistent memory system
│   ├── context_mapper/        # Code context extraction
│   ├── code_review/           # Multi-agent review pipeline
│   ├── marketplace/           # Decentralized skill registry
│   ├── api/                   # REST + gRPC API server
│   └── cli/                   # Command-line interface
├── docs/                      # Documentation
├── tests/                     # Test suites
├── examples/                  # Example skills & integrations
├── scripts/                   # Build & deployment scripts
├── config/                    # Configuration templates
└── .github/                   # GitHub Actions workflows
```

---

## 📊 Comparison with Existing Solutions

| Feature | TrustChain | ECC | Hermes Agent | Superpowers | CodeGraph |
|---------|------------|-----|--------------|-------------|-----------|
| **Cross-platform skills** | ✅ USP v1.0 | ❌ | ❌ | ⚠️ SKILL.md only | ❌ |
| **Automated trust scoring** | ✅ Multi-dimensional | ❌ | ❌ | ❌ | ❌ |
| **Persistent memory** | ✅ Vector + Graph | ❌ | ✅ | ⚠️ | ❌ |
| **Context extraction** | ✅ Static + LLM | ❌ | ❌ | ❌ | ⚠️ Code graph |
| **Multi-agent review** | ✅ Parallel pipeline | ⚠️ | ⚠️ | ❌ | ❌ |
| **Decentralized marketplace** | ✅ P2P registry | ❌ | ❌ | ✅ Centralized | ❌ |
| **IDE integration** | ✅ VS Code/JetBrains | ⚠️ | ❌ | ❌ | ✅ |
| **CI/CD integration** | ✅ GitHub Actions | ❌ | ❌ | ❌ | ❌ |

---

## 🛡️ Security

Security is a core design principle of TrustChain. See [SECURITY.md](SECURITY.md) for our security policy and responsible disclosure process.

---

## 📄 License

TrustChain is released under the [MIT License](LICENSE).

Built with ❤️ for the open-source community by [@lanekingkong](https://github.com/lanekingkong).

---

# TrustChain — 通用 AI 信任与质量基础设施（中文版）

## 🎯 TrustChain 解决什么问题？

2026年，AI Agent 已成为软件开发的核心，但整个生态系统面临**五大根本危机**：

| 危机 | 严重程度 | 影响 |
|------|---------|------|
| **代码信任危机** | 🔴 致命 | 96%的开发者不信任AI生成的代码用于生产环境 |
| **技能市场碎片化** | 🔴 致命 | Agent技能被锁定在单一平台（Claude Code ≠ Codex ≠ Cursor） |
| **上下文失忆** | 🟠 严重 | 65%的开发者因跨会话记忆丢失导致效率骤降 |
| **代码审核瓶颈** | 🟠 严重 | AI生成代码的速度是人工审核的10倍以上 |
| **上下文负债** | 🟡 加剧 | 老旧代码库存在AI永远无法获取的隐知识 |

**TrustChain 是统一解决方案。** 五大集成模块协同工作，在AI驱动的开发生命周期中重建信任。

---

## 🗺️ 路线图

- [x] **Phase 1 (Current)**: Core architecture, USP v1.0, Trust Engine MVP
- [ ] **Phase 2 (Q3 2026)**: Memory Mesh GA, Context Mapper Beta
- [ ] **Phase 3 (Q4 2026)**: Decentralized Marketplace, P2P Discovery
- [ ] **Phase 4 (Q1 2027)**: Enterprise SSO, Compliance Reporting, SLA Guarantees

---

## 🌟 Star History

If you find TrustChain valuable, please consider giving it a star ⭐ — it helps us reach more developers fighting the same trust crisis.

---

## 📞 Community

- **Discussions**: [GitHub Discussions](https://github.com/lanekingkong/trustchain/discussions)
- **Issues**: [Bug Reports & Feature Requests](https://github.com/lanekingkong/trustchain/issues)
- **中文社区**: 欢迎在 Issues 中使用中文提交问题和建议