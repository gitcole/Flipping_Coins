# Contributing to Crypto Trading Bot

Thank you for your interest in contributing to our cryptocurrency trading bot! We welcome contributions from the community and are grateful for your help in making this project better.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Community Guidelines](#community-guidelines)

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.11 or higher
- Git
- Redis Server (for local development)
- Docker (optional, but recommended)

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork**:
   ```bash
   git clone https://github.com/your-username/crypto-trading-bot.git
   cd crypto-trading-bot
   ```

3. **Set up the development environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Install development dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

5. **Set up pre-commit hooks**:
   ```bash
   pre-commit install
   ```

6. **Configure your environment**:
   ```bash
   cp config/.env.example config/.env
   # Edit config/.env with your development settings
   ```

## Development Workflow

### Creating a Feature Branch

Always create a new branch for your work:

```bash
git checkout -b feature/amazing-feature
# or
git checkout -b fix/bug-description
# or
git checkout -b docs/update-readme
```

### Making Changes

1. **Write clear, descriptive commit messages**:
   ```bash
   git commit -m "feat: add new risk management strategy"
   git commit -m "fix: resolve websocket reconnection issue"
   git commit -m "docs: update API documentation"
   ```

2. **Follow conventional commit format**:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `style:` for code style changes
   - `refactor:` for code refactoring
   - `test:` for adding or updating tests
   - `chore:` for maintenance tasks

3. **Keep commits atomic** - each commit should represent one logical change

## Code Standards

### Python Code Style

We follow PEP 8 and use several tools to maintain code quality:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

### Code Quality Checks

Run these commands before submitting your changes:

```bash
# Format code
black src/ tests/
isort src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/

# Security scanning
bandit -r src/
```

### Type Hints

All new code should include proper type hints:

```python
from typing import Dict, List, Optional
from decimal import Decimal

def calculate_position_size(
    capital: Decimal,
    risk_percentage: float,
    stop_loss: Decimal
) -> Decimal:
    """Calculate position size based on risk management rules."""
    pass
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src

# Run specific test file
pytest tests/unit/test_trading_engine.py

# Run tests for a specific component
pytest tests/ -k "test_risk_manager"
```

### Writing Tests

1. **Follow the existing test structure**:
   - `tests/unit/` for unit tests
   - `tests/integration/` for integration tests
   - `tests/e2e/` for end-to-end tests

2. **Test naming conventions**:
   - `test_function_name` for unit tests
   - `test_class_name.py` for class-specific tests
   - Use descriptive test names that explain what's being tested

3. **Test coverage requirements**:
   - Minimum 80% code coverage for new code
   - All new features must include tests
   - Bug fixes should include regression tests

Example test structure:

```python
import pytest
from decimal import Decimal

class TestPositionManager:
    """Test cases for position management functionality."""

    def test_calculate_position_size(self):
        """Test position size calculation with various inputs."""
        # Arrange
        capital = Decimal("10000")
        risk_percentage = 0.02
        stop_loss = Decimal("0.05")

        # Act
        result = calculate_position_size(capital, risk_percentage, stop_loss)

        # Assert
        assert result == Decimal("400")  # 10000 * 0.02 / 0.05
```

## Documentation

### Docstring Standards

All public functions, classes, and methods should have docstrings:

```python
def complex_trading_strategy(
    symbol: str,
    capital: Decimal,
    risk_level: str = "medium"
) -> Dict[str, any]:
    """
    Execute a complex multi-indicator trading strategy.

    This strategy combines technical analysis, market sentiment,
    and risk management to determine optimal entry and exit points.

    Args:
        symbol: Trading pair symbol (e.g., 'BTC/USDT')
        capital: Available capital for the trade
        risk_level: Risk tolerance level ('low', 'medium', 'high')

    Returns:
        Dictionary containing trade details and execution plan

    Raises:
        ValueError: If symbol is not supported or capital is insufficient
        ConnectionError: If exchange API is unavailable

    Example:
        >>> strategy = complex_trading_strategy("ETH/USDT", Decimal("1000"))
        >>> print(strategy['action'])  # 'buy' or 'sell'
    """
    pass
```

### Updating Documentation

When adding new features:

1. Update inline documentation
2. Add examples to docstrings
3. Update README.md if needed
4. Update API documentation
5. Add usage examples

## Submitting Changes

### Creating a Pull Request

1. **Ensure your branch is up to date**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run the full test suite**:
   ```bash
   pytest
   ```

3. **Check code quality**:
   ```bash
   black --check src/ tests/
   isort --check-only src/ tests/
   flake8 src/ tests/
   mypy src/
   ```

4. **Push your changes**:
   ```bash
   git push origin feature/amazing-feature
   ```

5. **Create a pull request** on GitHub

### Pull Request Requirements

- **Descriptive title** that follows conventional commit format
- **Detailed description** explaining:
  - What changes were made
  - Why the changes are necessary
  - How the changes affect existing functionality
  - Any breaking changes

- **Tests** for new functionality
- **Documentation updates** if needed
- **Screenshots** for UI changes (if applicable)

### Code Review Process

- All submissions require review from maintainers
- Address review feedback promptly
- Be prepared to make additional changes
- Maintain a positive and collaborative attitude

## Community Guidelines

### Communication

- Be respectful and inclusive
- Use welcoming and inclusive language
- Be collaborative and open to different viewpoints
- Focus on what is best for the community

### Reporting Issues

When reporting bugs or requesting features:

1. **Check existing issues** to avoid duplicates
2. **Use issue templates** when available
3. **Provide detailed information**:
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details
   - Error messages and logs

4. **Include examples** and use cases for feature requests

### Getting Help

- **Check the documentation** first
- **Search existing issues** and discussions
- **Ask questions** in GitHub Discussions
- **Join our community chat** (if available)

## Recognition

Contributors who make significant improvements may be:

- Added to the contributors list
- Invited to become maintainers
- Recognized in release notes
- Thanked in the README

---

Thank you for contributing to our cryptocurrency trading bot! Your help makes this project better for everyone. 🚀