# Contributing to Shark-no-Ninsho-Mon

Thank you for your interest in contributing to Shark-no-Ninsho-Mon! This document provides guidelines and information for contributors.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Security](#security)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

By participating in this project, you agree to abide by our [Security Guidelines](../SECURITY.md). Please read it before contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/Shark-no-Ninsho-Mon.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test thoroughly
6. Submit a pull request

## Development Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.9+ (for local development)
- Tailscale account and node
- Google OAuth2 credentials

### Local Development
```bash
# Clone the repository
git clone https://github.com/HaiNick/Shark-no-Ninsho-Mon.git
cd Shark-no-Ninsho-Mon

# Copy environment template
cp .env.template .env

# Edit .env with your configuration
# Follow the README.md setup instructions

# Build and run
docker-compose up --build
```

## How to Contribute

### Reporting Bugs
- Use the bug report template in GitHub Issues
- Include detailed steps to reproduce
- Provide environment information
- Include relevant logs

### Suggesting Features
- Use the feature request template in GitHub Issues
- Clearly describe the feature and its benefits
- Explain your use case
- Consider implementation complexity

### Code Contributions
1. **Start with an issue** - Either create one or find an existing issue
2. **Fork and branch** - Create a feature branch from `main`
3. **Make changes** - Follow our coding standards
4. **Test thoroughly** - Ensure all functionality works
5. **Document** - Update docs if needed
6. **Submit PR** - Use the pull request template

## Coding Standards

### Python Code
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings for functions and classes
- Keep functions small and focused
- Handle errors gracefully

### Docker
- Use multi-stage builds where appropriate
- Minimize image size
- Use specific tags, avoid `latest` in production
- Follow security best practices

### Configuration
- Use environment variables for configuration
- Provide sensible defaults
- Document all configuration options
- Validate configuration at startup

## Testing

### Required Tests
- All new features must include tests
- Bug fixes should include regression tests
- Test OAuth2 flow integration
- Test Docker container functionality
- Test Tailscale connectivity (where possible)

### Testing Guidelines
```bash
# Run tests locally
cd app
python -m pytest test_app.py -v

# Test Docker build
docker-compose build

# Test full deployment
docker-compose up
```

## Documentation

### Documentation Requirements
- Update README.md for new features
- Update EXTRA-FEATURES.md for advanced configurations
- Add inline code comments for complex logic
- Update configuration examples
- Include security considerations

### Documentation Style
- Use clear, concise language
- Include practical examples
- Provide step-by-step instructions
- Use proper Markdown formatting

## Security

### Security Guidelines
- Never commit secrets or credentials
- Use environment variables for sensitive data
- Follow OAuth2 security best practices
- Validate all user inputs
- Keep dependencies updated
- Report security issues privately

### Security Review Process
All contributions are subject to security review:
- Authentication and authorization changes require extra scrutiny
- Network configuration changes must be carefully reviewed
- Dependencies updates should be tested thoroughly

## Pull Request Process

1. **Create Quality PR**
   - Use the PR template
   - Write clear commit messages
   - Keep PRs focused and small
   - Include tests and documentation

2. **Review Process**
   - Automatic checks must pass
   - At least one maintainer review required
   - Security review for sensitive changes
   - All feedback must be addressed

3. **Merge Requirements**
   - All CI checks pass
   - Code review approved
   - Documentation updated
   - No merge conflicts

## Getting Help

- **Questions**: Open a discussion in GitHub Discussions
- **Bugs**: Use the bug report template
- **Features**: Use the feature request template
- **Security**: Follow responsible disclosure in SECURITY.md

## Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes for significant contributions
- README acknowledgments section

Thank you for contributing to Shark-no-Ninsho-Mon! 🦈