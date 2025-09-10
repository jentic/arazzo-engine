# Good First Issue Guide

Welcome to the Arazzo Engine project! We're excited to have you contribute during Hacktoberfest and beyond.

## What is a Good First Issue?

Good first issues are beginner-friendly tasks that help you get familiar with our codebase while making meaningful contributions. These issues typically:

- Have clear, step-by-step instructions
- Don't require deep knowledge of the entire codebase
- Can be completed in a few hours
- Have well-defined acceptance criteria

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- Basic familiarity with Python and command line

### Development Setup

1. **Fork the repository**
   ```bash
   # Click the "Fork" button on GitHub, then:
   git clone https://github.com/YOUR_USERNAME/arazzo-engine.git
   cd arazzo-engine/generator
   ```

2. **Set up your development environment**
   ```bash
   # Install PDM (Python Dependency Manager)
   curl -sSL https://pdm.fming.dev/install-pdm.py | python3 -
   
   # Install dependencies
   pdm install
   ```

3. **Configure environment**
   ```bash
   # Copy example environment file
   cp .env.example .env
   
   # Edit .env and add your API keys (optional for most issues)
   ```

4. **Run tests to ensure everything works**
   ```bash
   pdm run test
   ```

### Making Your First Contribution

1. **Find an issue**
   - Look for issues labeled `good first issue` and `hacktoberfest`
   - Read the issue description carefully
   - Comment on the issue to let others know you're working on it

2. **Create a branch**
   ```bash
   git checkout -b fix/issue-description
   ```

3. **Make your changes**
   - Follow the step-by-step instructions in the issue
   - Test your changes locally
   - Follow our coding standards (see below)

4. **Test your changes**
   ```bash
   # Run tests
   pdm run test
   
   # Run linting
   pdm run lint
   
   # Fix formatting if needed
   pdm run lint:fix
   ```

5. **Submit your pull request**
   - Use our PR template
   - Link to the issue you're fixing
   - Provide a clear description of your changes

## Coding Standards

- **Python Style**: We use Black, isort, and Ruff for code formatting
- **Testing**: Add tests for new functionality
- **Documentation**: Update docstrings and README as needed
- **Commit Messages**: Use clear, descriptive commit messages

## Types of Good First Issues

### 📝 Documentation
- Fix typos or grammar errors
- Improve README sections
- Add code examples
- Update outdated documentation

### 🧪 Testing
- Add missing test cases
- Improve test coverage
- Fix flaky tests

### 🐛 Bug Fixes
- Fix small, well-defined bugs
- Handle edge cases
- Improve error messages

### ✨ Small Features
- Add utility functions
- Improve CLI output
- Add configuration options

### 🏗️ Code Quality
- Refactor duplicate code
- Add type hints
- Improve variable names

## Getting Help

- **Discord**: Join our [Discord community](https://discord.gg/yrxmDZWMqB)
- **GitHub Discussions**: Ask questions in our GitHub Discussions
- **Issue Comments**: Comment on the issue if you need clarification

## Recognition

All contributors are recognized in our contributors list. Significant contributions may be highlighted in our release notes and social media.

## Code of Conduct

Please be respectful and inclusive. See our [Code of Conduct](CODE_OF_CONDUCT.md) for details.

## Next Steps

After completing your first issue, you might want to:

- Try a slightly more complex issue
- Help review other contributors' PRs
- Suggest improvements to our documentation
- Become a regular contributor to the project

Thank you for contributing to Arazzo Engine! 🚀