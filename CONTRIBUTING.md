# Contributing to CAB (CodeAssistBench)

Thank you for your interest in contributing to CAB! This document provides guidelines and information for contributors.

## 🎯 How to Contribute

### Reporting Issues
- Use the GitHub issue tracker to report bugs or request features
- Search existing issues before creating new ones
- Provide clear, detailed descriptions and reproduction steps
- Include relevant system information (OS, Python version, etc.)

### Suggesting Enhancements
- Use the "Enhancement" issue template
- Clearly describe the proposed feature or improvement
- Explain the use case and potential impact
- Consider implementation complexity and maintenance burden

### Code Contributions
- Fork the repository and create a feature branch
- Follow the coding standards and style guidelines
- Add tests for new functionality
- Update documentation as needed
- Submit a pull request with a clear description

## 🛠️ Development Setup

### Prerequisites
- Python 3.8 or higher
- Git
- GitHub account

### Setup Steps
1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/CodeAssistBench.git
   cd CodeAssistBench
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For development
   ```
5. Setup configuration:
   ```bash
   python cab_cli.py setup
   ```

### Running Tests
```bash
# Run all tests
python cab_cli.py test

# Run specific test file
python -m pytest test_pipeline.py -v

# Run with coverage
python -m pytest --cov=pipeline_core --cov=pipeline_steps
```

## 📝 Coding Standards

### Python Style
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write docstrings for all public functions and classes
- Keep functions focused and reasonably sized

### Code Organization
- Place related functionality in appropriate modules
- Use meaningful variable and function names
- Add comments for complex logic
- Follow the existing project structure

### Error Handling
- Use appropriate exception types
- Provide meaningful error messages
- Log errors with sufficient context
- Handle edge cases gracefully

## 🧪 Testing Guidelines

### Test Coverage
- Aim for high test coverage (>80%)
- Test both success and failure cases
- Include integration tests for critical paths
- Mock external dependencies appropriately

### Test Structure
- Use descriptive test names
- Follow the Arrange-Act-Assert pattern
- Keep tests focused and independent
- Clean up resources in teardown methods

### Example Test
```python
def test_repository_collection_step():
    """Test repository collection step execution."""
    # Arrange
    step = RepositoryCollectionStep()
    context = create_test_context()
    
    # Act
    result = await step.execute(context)
    
    # Assert
    assert result.status == StepStatus.COMPLETED
    assert "repositories" in result.output_data
```

## 📚 Documentation

### Code Documentation
- Write clear docstrings for all public APIs
- Include parameter descriptions and return values
- Provide usage examples where helpful
- Keep documentation up to date with code changes

### User Documentation
- Update README.md for user-facing changes
- Add examples for new features
- Update configuration documentation
- Include troubleshooting information

## 🔄 Pull Request Process

### Before Submitting
1. Ensure all tests pass
2. Update documentation as needed
3. Add appropriate tests for new functionality
4. Follow the coding standards
5. Rebase on the latest main branch

### Pull Request Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

### Review Process
- All PRs require at least one review
- Address feedback promptly and constructively
- Keep PRs focused and reasonably sized
- Update PR description if scope changes

## 🏷️ Release Process

### Versioning
- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Update version in setup.py and __init__.py
- Create release notes for significant changes

### Release Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Version numbers updated
- [ ] Release notes prepared
- [ ] Tag created on GitHub

## 🤝 Community Guidelines

### Communication
- Be respectful and constructive
- Use inclusive language
- Provide helpful feedback
- Ask questions when unclear

### Getting Help
- Check existing documentation first
- Search issues and discussions
- Ask questions in GitHub Discussions
- Join community channels if available

## 📋 Issue Templates

### Bug Report Template
```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior.

**Expected behavior**
What you expected to happen.

**Environment**
- OS: [e.g., Ubuntu 20.04]
- Python version: [e.g., 3.9.0]
- CAB version: [e.g., 1.0.0]

**Additional context**
Any other relevant information.
```

### Feature Request Template
```markdown
**Is your feature request related to a problem?**
A clear description of what the problem is.

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Alternative solutions or workarounds.

**Additional context**
Any other context about the feature request.
```

## 🎉 Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes for significant contributions
- Project documentation
- Community acknowledgments

Thank you for contributing to CAB and helping make AI coding assistant evaluation more accessible and reliable!
