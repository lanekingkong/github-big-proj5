# Contributing to TrustChain

## Welcome!

TrustChain is built for the community, by the community. We're thrilled you want to contribute.

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code.

## How Can I Contribute?

### 🐛 Reporting Bugs

Before submitting a bug report:
1. Check the [issue tracker](https://github.com/lanekingkong/trustchain/issues) for duplicates
2. Use the bug report template
3. Include: OS, Python/Node version, steps to reproduce, expected vs actual behavior

### 💡 Feature Requests

1. Check existing feature requests first
2. Describe the problem your feature solves
3. Provide use cases and examples
4. Tag with `enhancement` label

### 🔧 Pull Requests

#### Development Workflow

```bash
# 1. Fork and clone
git clone https://github.com/your-username/trustchain.git
cd trustchain

# 2. Create a branch
git checkout -b feature/your-feature-name

# 3. Set up dev environment
pip install -e ".[dev]"
pre-commit install

# 4. Make changes
# Write code + tests

# 5. Run checks
pytest tests/
black src/
ruff check src/
mypy src/

# 6. Commit using conventional commits
git commit -m "feat: add cross-platform skill validation"

# 7. Push and create PR
git push origin feature/your-feature-name
```

#### PR Requirements

- [ ] Tests pass: `pytest tests/`
- [ ] Linting passes: `ruff check src/`
- [ ] Type checking: `mypy src/`
- [ ] Documentation updated
- [ ] Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
- [ ] Branch is up-to-date with `main`

### 📝 Documentation

Documentation lives in `docs/`. For changes to the USP specification, update `docs/usp-spec.md`.

### 🎨 Code Style

- Python: PEP 8, type hints required
- TypeScript: ESLint + Prettier
- Docstrings: Google style for Python

## Project Structure Philosophy

```
src/core/          → Don't put logic here. This is the orchestrator only.
src/universal_skill/ → USP parser, validator, transpiler
src/trust_engine/  → Scoring algorithms, AST analysis, sandboxing
src/memory_mesh/   → Vector store, graph DB, sync protocol
src/context_mapper/ → Static analysis, LLM extraction, rule inference
src/code_review/   → Review agents, pipeline, findings aggregation
src/marketplace/   → Registry, P2P discovery, rating system
src/api/           → REST + gRPC endpoints
src/cli/           → Click-based CLI
```

### Key Design Principles

1. **Modularity**: Each module is independently deployable
2. **Composability**: Modules combine via well-defined interfaces
3. **No vendor lock-in**: USP spec is fully open and multi-vendor
4. **Privacy-first**: All trust scoring and memory runs locally by default
5. **Transparency**: Every trust score comes with explainable evidence

## Getting Help

- Open a [Discussion](https://github.com/lanekingkong/trustchain/discussions)
- Tag maintainers: `@lanekingkong`
- 中文提问也完全欢迎！

## Recognition

All contributors will be listed in [CONTRIBUTORS.md](CONTRIBUTORS.md). Significant contributions earn commit access.

---

Thank you for helping make AI-generated code trustworthy.