# Contributing to Lazarus Protocol

Thank you for your interest in contributing to Lazarus Protocol! This guide will help you get started with development and making contributions.

## 🚀 Development Setup

### Prerequisites
- Python 3.10+
- Git
- Basic understanding of cryptography concepts

### Local Development

```bash
# Fork and clone the repository
git clone https://github.com/ravikumarve/lazarus.git
cd lazarus

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-cov black isort

# Set up environment variables (optional)
cp .env.example .env
# Edit .env with your test credentials
```

## 🧪 Testing

We require tests for all contributions. Here's how to run them:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test files
python -m pytest tests/test_encryption.py -v
python -m pytest tests/test_heartbeat.py -v

# Run with coverage report
python -m pytest tests/ --cov=. --cov-report=html

# Run tests for Windows-specific functionality
python -m pytest tests/ -k "windows" -v
```

## 📝 Code Style

We use Black and isort for code formatting:

```bash
# Install formatting tools
pip install black isort

# Format all code
black .
isort .

# Check formatting without applying changes
black . --check
isort . --check-only
```

## 🔧 Making Changes

### Branch Naming Convention

Use descriptive branch names with prefixes:

- `feat/`: New features
- `fix/`: Bug fixes
- `docs/`: Documentation changes
- `test/`: Test additions/improvements
- `refactor/`: Code refactoring
- `chore/`: Maintenance tasks

Examples:
- `feat/ipfs-storage`
- `fix/email-alerts`
- `docs/readme-improvement`

### Commit Messages

We follow [Conventional Commits](https://conventionalcommits.org) format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Formatting, missing semi-colons, etc.
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

Examples:
```
feat(encryption): add AES-256-GCM support
fix(alerts): resolve email delivery timeout issue
docs(readme): add security model section
test(heartbeat): add escalation ladder tests
```

### Pull Request Process

1. **Fork the repository**
2. **Create your feature branch** (`git checkout -b feat/amazing-feature`)
3. **Make your changes** and add tests
4. **Run tests** to ensure everything passes
5. **Commit your changes** using conventional commit format
6. **Push to the branch** (`git push origin feat/amazing-feature`)
7. **Open a Pull Request** with a clear description

### PR Description Template

```markdown
## What does this PR do?

[Brief description of changes]

## Why is this change needed?

[Explanation of the problem being solved]

## How was it tested?

- [ ] Added new tests
- [ ] Ran existing test suite
- [ ] Manual testing steps:
  - [Step 1]
  - [Step 2]

## Screenshots/GIFs (if applicable)

[Visual evidence of the change working]

## Checklist
- [ ] Code follows project style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] All tests pass
```

## 🎯 What We Welcome

### High-Priority Contributions
- **Security improvements**: Enhanced encryption, better key management
- **Test coverage**: Additional tests for edge cases
- **Documentation**: Better explanations, tutorials, examples
- **Performance optimizations**: Faster encryption/decryption
- **Platform support**: Improved Windows/macOS compatibility

### Bug Reports

When reporting bugs, please include:
1. Steps to reproduce the issue
2. Expected behavior
3. Actual behavior
4. Environment details (OS, Python version, etc.)
5. Error messages and stack traces

### Feature Requests

For feature requests, please:
1. Describe the problem you're trying to solve
2. Explain your proposed solution
3. Provide use cases or examples
4. Consider if it aligns with the project's security focus

## ⚠️ Security Considerations

Since this is security software, we have strict guidelines:

- **No breaking changes** to encryption without major version bumps
- **All cryptographic changes** must be reviewed by multiple contributors
- **No external dependencies** without security audit
- **Backward compatibility** must be maintained for user data

## 🛡️ Security Vulnerability Reporting

If you find a security vulnerability, please **DO NOT** create a public issue. Instead:

1. Email: ravikumarve@protonmail.com
2. Use the subject line: "SECURITY: Vulnerability in Lazarus Protocol"
3. Provide detailed description and steps to reproduce
4. We will respond within 48 hours

## 📚 Documentation

We value good documentation. When contributing:

- Update README.md for user-facing changes
- Add docstrings for new functions/classes
- Consider adding examples in `/examples/` directory
- Keep documentation in sync with code changes

## 🌟 Recognition

Great contributions will be recognized by:
- Mention in release notes
- Contributor shout-outs in README
- Potential commit access for consistent contributors

## ❓ Questions?

If you have questions about contributing:
- Check existing issues and discussions
- Join our [GitHub Discussions](https://github.com/ravikumarve/lazarus/discussions)
- Email: ravikumarve@protonmail.com

---

Thank you for helping make Lazarus Protocol more secure and reliable for everyone! 🚀