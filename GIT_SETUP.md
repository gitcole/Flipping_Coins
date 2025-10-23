# Git Configuration and Workflow Setup

This document describes the git configuration and development workflow setup for the Crypto Trading Bot project.

## Repository Information

- **Default Branch**: `main` (modern naming convention)
- **Repository Type**: Python-based crypto trading application
- **Target Audience**: Developers working on algorithmic trading systems

## Git Configuration

### Core Settings
```bash
# View current configuration
git config --list

# Key configurations applied:
core.autocrlf = false          # Prevents line ending issues on different OS
core.quotepath = false         # Prevents quoting of non-ASCII filenames
push.default = simple          # Safer push strategy for collaboration
merge.ff = false              # Prevents fast-forward merges for clearer history
```

### Recommended User Configuration
```bash
# Set up your personal git configuration
git config --global user.name "Your Full Name"
git config --global user.email "your.email@example.com"
git config --global core.editor "vim"  # or your preferred editor
```

## Git Hooks

### Pre-commit Hook (`.git/hooks/pre-commit`)
**Purpose**: Validates code before allowing commits

**Features**:
- ✅ **Security Check**: Scans for accidentally committed secrets (API keys, tokens, passwords)
- ✅ **Python Syntax Validation**: Checks Python syntax for all staged `.py` files
- ✅ **Test Execution**: Runs pytest test suite if available
- ✅ **File Size Monitoring**: Warns about large files (>10MB)
- ✅ **TODO/FIXME Detection**: Warns about unresolved TODO comments

**Exit Codes**:
- `0`: Commit allowed to proceed
- `1`: Commit blocked due to issues

**Bypass**: Use `git commit --no-verify` to skip (not recommended)

### Pre-push Hook (`.git/hooks/pre-push`)
**Purpose**: Final validation before pushing to remote repository

**Features**:
- ✅ **Branch Awareness**: Special handling for production branches (main, master, production)
- ✅ **Commit Message Analysis**: Checks for sensitive information in recent commits
- ✅ **Production Warnings**: Alerts when pushing to production-like branches
- ✅ **Commit Structure Validation**: Ensures proper commit organization

## .gitignore Configuration

The project includes a comprehensive `.gitignore` file with:

### Python-specific ignores:
- `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`
- Virtual environments (`venv/`, `.env`, `ENV/`)
- Distribution files (`build/`, `dist/`, `*.egg-info/`)
- Testing artifacts (`.coverage`, `.pytest_cache/`, `htmlcov/`)

### Security-focused ignores:
- Configuration files (`config/*.env`, `*.key`, `*.pem`)
- API credentials (`api_keys.json`, `secrets.json`)
- Authentication tokens (`auth_tokens.json`, `robinhood_tokens.json`)

### Development environment ignores:
- IDE files (`.vscode/`, `.idea/`, `*.swp`)
- OS-specific files (`.DS_Store`, `Thumbs.db`)
- Logs and temporary files (`logs/`, `*.log`, `tmp/`)

### Trading-specific ignores:
- Market data files (`data/`, `*.csv`, `market_data/`)
- Trading results (`trading_results/`, `backtest_results/`)
- Portfolio data (`*.portfolio`, `portfolio_snapshots/`)

## Development Workflow

### Daily Development
```bash
# 1. Check status and add changes
git status
git add .

# 2. Commit with pre-commit validation
git commit -m "feat: add new trading strategy"

# 3. Push with pre-push validation
git push origin feature-branch
```

### Working with Feature Branches
```bash
# Create and switch to new feature branch
git checkout -b feature/new-strategy

# Develop and commit
git add .
git commit -m "feat: implement new strategy logic"

# Push feature branch
git push origin feature/new-strategy

# Create pull request and merge
git checkout main
git pull origin main
git merge feature/new-strategy
git push origin main
```

### Updating from Remote
```bash
# Update local main branch
git checkout main
git pull origin main

# Update feature branch with latest changes
git checkout feature-branch
git rebase main
```

## Security Best Practices

### Never Commit Secrets
- ✅ Use environment variables for API keys and credentials
- ✅ Keep `.env` files in `.gitignore`
- ✅ Use secret management systems for production
- ✅ Pre-commit hook automatically blocks commits with potential secrets

### Branch Protection
- ✅ Production branches should require pull request reviews
- ✅ Use protected branches on GitHub/GitLab
- ✅ Require status checks to pass before merging

## Troubleshooting

### Hook Issues
```bash
# Make hooks executable (if needed)
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push

# Skip hooks temporarily
git commit --no-verify
git push --no-verify
```

### Common Issues
1. **"Secrets found in commit"**: Remove any hardcoded credentials
2. **"Python syntax error"**: Fix syntax issues in Python files
3. **"Tests failed"**: Ensure all tests pass before committing
4. **"Large files detected"**: Consider if large files are necessary

### Getting Help
```bash
# View git configuration
git config --list

# Check hook status
ls -la .git/hooks/

# View recent commits
git log --oneline -10
```

## Git Aliases (Optional)

Add these to your `~/.gitconfig` for convenience:
```bash
[alias]
    st = status -sb
    ci = commit
    co = checkout
    br = branch
    df = diff
    lg = log --oneline --graph --decorate --all
    ll = log --oneline -10
```

## Repository Structure
```
crypto-trading-bot/
├── .git/                    # Git repository data
│   ├── hooks/
│   │   ├── pre-commit      # ✅ Security and quality checks
│   │   └── pre-push        # ✅ Final validation
│   ├── info/
│   └── objects/
├── .gitignore              # ✅ Comprehensive ignore rules
├── .gitconfig.example      # ✅ Configuration template
├── src/                    # Source code
├── tests/                  # Test suite
├── config/                 # Configuration files
├── docs/                   # Documentation
└── README.md              # Project documentation
```

## Contributing Guidelines

1. **Create Feature Branches**: Always create feature branches for new work
2. **Write Tests**: Ensure new features include appropriate tests
3. **Update Documentation**: Keep docs in sync with code changes
4. **Security First**: Never commit credentials or sensitive data
5. **Code Quality**: Ensure Python syntax is correct and tests pass
6. **Meaningful Commits**: Write clear, descriptive commit messages

## Emergency Procedures

### If you accidentally commit secrets:
```bash
# Remove from history (destructive - use carefully)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch <file-with-secrets>' \
  --prune-empty --tag-name-filter cat -- --all

# Force push the cleaned history
git push origin --force --all
```

### If hooks are blocking legitimate commits:
```bash
# Temporarily disable hooks
git commit --no-verify -m "emergency fix"
git push --no-verify
```

---

**Last Updated**: $(date)
**Git Version**: $(git --version)