# Arazzo Engine

[![Discord](https://img.shields.io/badge/JOIN%20OUR%20DISCORD-COMMUNITY-7289DA?style=plastic&logo=discord&logoColor=white)](https://discord.gg/TdbWXZsUSm)
[![Hacktoberfest](https://img.shields.io/badge/Hacktoberfest-2025-ff6b6b?style=plastic)](https://hacktoberfest.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=plastic)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=plastic&logo=python)](https://python.org)
[![CI](https://img.shields.io/github/actions/workflow/status/jentic/arazzo-engine/ci.yml?branch=main&style=plastic&label=CI)](https://github.com/jentic/arazzo-engine/actions)

A comprehensive, open-source toolkit for working with **[Arazzo Specification](https://www.openapis.org/arazzo-specification)** workflows - the new standard from the OpenAPI Initiative for describing and executing complex API orchestrations.

---

## 🎃 Hacktoberfest 2025

**We're participating in Hacktoberfest!** Join thousands of developers contributing to open source this October.

- 🏷️ **20+ beginner-friendly issues** labeled `good first issue` and `hacktoberfest`
- 📚 **Comprehensive contribution guide** with step-by-step instructions
- 💬 **Active community support** on Discord
- 🚀 **Meaningful impact** on the future of API orchestration

**New to open source?** Check out our [Good First Issue Guide](good_first_issue.md) to get started!

[**Find issues to work on →**](https://github.com/jentic/arazzo-engine/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22+label%3Ahacktoberfest)

---

## What is Arazzo?

Arazzo is an official specification from the **OpenAPI Initiative**, joining the well-known OpenAPI Specification (OAS) and the Overlay Specification. While OAS describes individual APIs, **Arazzo defines workflows that orchestrate calls across one or more APIs**.

### Why Arazzo Matters

- **Standardized API Orchestration**: Language-agnostic workflow definitions
- **Human & Machine Readable**: Clear documentation that tools can execute
- **Ecosystem Ready**: Enables automation, testing, and AI-driven API interactions

### Real-World Applications

- Interactive workflow documentation
- Automated testing and validation
- Code and SDK generation
- AI agent API interactions
- DevOps automation pipelines

---

## Projects

This monorepo contains two complementary tools for the Arazzo ecosystem:

### 🏃 [Arazzo Runner](./runner/)

Execute Arazzo workflows with full specification compliance.

```bash
# Execute a workflow
arazzo-runner execute workflow.arazzo.yaml --input '{"userId": 123}'
```

**Features:**
- Complete Arazzo 1.0 specification support
- Authentication handling (OAuth2, API keys, etc.)
- Conditional logic and error handling
- Extensive validation and debugging
- Python library and CLI tool

[**Explore the Runner →**](./runner/)

### ⚙️ [Arazzo Generator](./generator/)

Generate Arazzo workflows from OpenAPI specifications using AI-powered analysis.

```bash
# Generate workflows from OpenAPI spec
arazzo-generator generate https://api.example.com/openapi.json -o workflows.arazzo.yaml
```

**Features:**
- LLM-powered workflow identification
- OpenAPI 3.0 and 3.1 support
- Multiple output formats (JSON/YAML)
- Batch processing capabilities
- FastAPI web interface

[**Explore the Generator →**](./generator/)

---

## Quick Start

### Prerequisites

- Python 3.11 or higher
- [PDM](https://pdm.fming.dev/) (recommended) or pip

### Installation

Choose your preferred installation method:

#### Option 1: Install from PyPI
```bash
# Install both tools
pip install arazzo-runner arazzo-generator

# Or install individually
pip install arazzo-runner
pip install arazzo-generator
```

#### Option 2: Development Setup
```bash
# Clone the repository
git clone https://github.com/jentic/arazzo-engine.git
cd arazzo-engine

# Setup development environment
./scripts/setup.sh

# Or setup manually
cd generator && pdm install && cd ..
cd runner && pdm install && cd ..
```

### Your First Workflow

1. **Generate a workflow from an OpenAPI spec:**
   ```bash
   arazzo-generator generate https://petstore.swagger.io/v2/swagger.json -o petstore.arazzo.yaml
   ```

2. **Execute the workflow:**
   ```bash
   arazzo-runner execute petstore.arazzo.yaml --input '{"status": "available"}'
   ```

3. **View results:**
   ```bash
   cat execution_results.json
   ```

---

## Contributing

We welcome contributions from developers of all skill levels! Whether you're fixing typos or implementing major features, your contributions help make API orchestration better for everyone.

### 🎯 Quick Contribution Guide

1. **Find an issue** labeled `good first issue` for beginners
2. **Fork the repository** and create a feature branch
3. **Make your changes** following our coding standards
4. **Add tests** and ensure they pass
5. **Submit a pull request** using our template

### 🛠️ Development Workflow

```bash
# Run tests for all projects
./scripts/test-all.sh

# Lint all code
./scripts/lint-all.sh

# Run tests for specific project
cd generator && pdm run test
cd runner && pdm run test
```

### 📚 Resources

- [Good First Issue Guide](good_first_issue.md) - Step-by-step contribution instructions
- [Contributing Guidelines](CONTRIBUTING.md) - Detailed development process
- [Code of Conduct](CODE_OF_CONDUCT.md) - Community standards
- [Discord Community](https://discord.gg/TdbWXZsUSm) - Get help and connect

---

## Community & Support

### 💬 Join the Conversation

- **Discord**: [Join our community](https://discord.gg/TdbWXZsUSm) for real-time discussions
- **GitHub Discussions**: Share ideas and ask questions
- **Issues**: Report bugs or request features

### 🤝 Ways to Contribute

| Type | Examples | Difficulty |
|------|----------|------------|
| 📝 **Documentation** | Fix typos, improve guides, add examples | Beginner |
| 🧪 **Testing** | Add test cases, improve coverage | Beginner |
| 🐛 **Bug Fixes** | Fix reported issues, edge cases | Intermediate |
| ✨ **Features** | New functionality, enhancements | Intermediate |
| 🏗️ **Architecture** | Performance, design improvements | Advanced |

### 🏆 Recognition

All contributors are recognized in our:
- [Contributors list](CONTRIBUTORS.md)
- Release notes for significant contributions  
- Social media highlights
- Annual community awards

---

## Project Status

### 🚀 Current Status

- **Arazzo Runner**: ✅ Stable (v1.0+) - Production ready
- **Arazzo Generator**: 🚧 Beta (v0.2+) - Active development
- **Specification Compliance**: ✅ Arazzo 1.0.1 fully supported

### 📋 Roadmap

**Q4 2024:**
- Enhanced error handling and debugging
- Performance optimizations
- Extended authentication support

**Q1 2025:**
- Visual workflow editor
- Cloud execution platform
- Enterprise features

**Q2 2025:**
- Multi-language SDKs
- Advanced AI integrations
- Workflow marketplace

[**View detailed roadmap →**](https://github.com/jentic/arazzo-engine/projects)

---

## Related Projects

### Official Arazzo Resources
- [Arazzo Specification](https://github.com/OAI/Arazzo-Specification) - Official spec repository
- [OpenAPI Initiative](https://www.openapis.org/) - Specification governance

### Community Tools
- [Arazzo Examples](https://github.com/jentic/arazzo-examples) - Sample workflows and use cases
- [Arazzo Validator](https://github.com/jentic/arazzo-validator) - Standalone validation tool

---

## License & Legal

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

### 📄 Third-Party Licenses

This project uses several open-source libraries. See [NOTICE](NOTICE) for detailed attribution.

### 🔒 Security

For security concerns, please see our [Security Policy](SECURITY.md) or contact security@jentic.com.

---

## Metrics & Analytics

![GitHub Stars](https://img.shields.io/github/stars/jentic/arazzo-engine?style=social)
![GitHub Forks](https://img.shields.io/github/forks/jentic/arazzo-engine?style=social)
![GitHub Issues](https://img.shields.io/github/issues/jentic/arazzo-engine)
![GitHub Pull Requests](https://img.shields.io/github/issues-pr/jentic/arazzo-engine)

**Monthly Downloads:** ![PyPI Downloads](https://img.shields.io/pypi/dm/arazzo-runner)

---

*Built with ❤️ by the Jentic team and amazing open-source contributors worldwide.*

*Let's build the future of API orchestration together!*