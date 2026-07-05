# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.x     | ✅ Fully supported |
| 0.x     | ❌ End of life     |

## Reporting a Vulnerability

**DO NOT open a public issue for security vulnerabilities.**

Instead, send a detailed report to: **security@trustchain.dev**

### What to Include

1. Description of the vulnerability
2. Steps to reproduce
3. Affected versions
4. Potential impact
5. Suggested fix (if any)

### Response Timeline

| Phase | Timeline |
|-------|----------|
| Acknowledgment | Within 24 hours |
| Triage | Within 72 hours |
| Fix Development | Within 7 days |
| Public Disclosure | 30 days after fix (or coordinated) |

### Scope

Security issues in:
- Trust Engine sandbox escape
- Memory Mesh data leakage
- USP parser injection vulnerabilities
- API authentication bypass
- CLI privilege escalation

### Out of Scope

- Issues in example code
- Issues in user-generated skills
- DoS attacks against self-hosted instances
- Social engineering

## Security Design Principles

TrustChain follows these principles:

1. **Zero Trust**: Every inter-module call is authenticated
2. **Sandbox First**: All code validation runs in isolated environments
3. **Encryption by Default**: Memory Mesh data is encrypted at rest
4. **Minimal Surface**: API endpoints require explicit authorization
5. **Audit Trail**: Every trust score change is logged immutably

## Responsible Disclosure Hall of Fame

We maintain a hall of fame for researchers who responsibly disclose vulnerabilities. Contact us to be added.