# Git Workflow and Commit Strategy

## Branching Strategy

### Main Branches
- `master`: Production-ready code. Always stable and deployable.
- `develop`: Integration branch for features. Used for development builds.

### Supporting Branches
- `feature/*`: New features and enhancements
- `hotfix/*`: Critical bug fixes for production
- `release/*`: Prepare releases (version bumps, final testing)

### Branch Naming Conventions
```
feature/new-listing-detection
feature/improved-trailing-stop
hotfix/rate-limit-bug
release/v1.2.0
```

## Commit Message Format

Using conventional commits with project-specific scopes:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix  
- `docs`: Documentation changes
- `style`: Code formatting (no logic changes)
- `refactor`: Code restructuring (no behavior changes)
- `test`: Adding or updating tests
- `chore`: Build/tooling changes

### Scopes
- `api`: BitvavoAPI, requests_handler
- `trading`: trade_logic, TradeManager
- `market`: market_utils, MarketTracker
- `config`: Configuration management
- `tests`: Test suite changes
- `docs`: Documentation updates

### Examples
```
feat(trading): add trailing stop-loss percentage adjustment

Allow users to modify trailing stop percentage during active trades
through environment variable TRAILING_PCT_DYNAMIC.

Fixes #123
```

```
fix(api): handle rate limit exceeded errors gracefully

Add exponential backoff retry logic when Bitvavo API returns 429.
Previously the bot would crash on rate limit violations.

Closes #456
```

## Workflow Commands

### Feature Development
```bash
# Start new feature
git co -b feature/feature-name develop

# Regular commits during development
git add .
git ci  # Uses commit template

# Push feature branch
git push -u origin feature/feature-name

# Merge back to develop
git co develop
git merge --no-ff feature/feature-name
git branch -d feature/feature-name
```

### Hotfixes
```bash
# Emergency fix from master
git co -b hotfix/critical-bug master

# Fix and commit
git ci -m "fix(trading): prevent division by zero in profit calculation"

# Merge to both master and develop
git co master
git merge --no-ff hotfix/critical-bug
git tag -a v1.1.1 -m "Hotfix release v1.1.1"

git co develop  
git merge --no-ff hotfix/critical-bug
git branch -d hotfix/critical-bug
```

### Release Process
```bash
# Start release branch
git co -b release/v1.2.0 develop

# Finalize version, update docs
git ci -m "chore(release): bump version to v1.2.0"

# Merge to master and tag
git co master
git merge --no-ff release/v1.2.0
git tag -a v1.2.0 -m "Release v1.2.0"

# Merge back to develop
git co develop
git merge --no-ff release/v1.2.0
git branch -d release/v1.2.0
```

## Pre-commit Quality Gates

The pre-commit hooks will run:
- Code formatting (black, isort)
- Linting (flake8)  
- Basic file checks (trailing whitespace, large files)
- JSON validation (excluding personal data files)

Before pushing, tests run automatically:
- Full test suite with pytest
- Only pushes if all tests pass

## Useful Git Aliases

Already configured:
- `git st` = `git status`
- `git co` = `git checkout` 
- `git br` = `git branch`
- `git ci` = `git commit`
- `git unstage` = `git reset HEAD --`
- `git last` = `git log -1 HEAD`
- `git safe-push` = `git push --dry-run`

## Security Considerations

### Protected Files (in .gitignore)
- `.env` - API credentials
- `data/previous_markets.json` - Personal trading history
- `data/active_trades.json` - Current positions
- `__pycache__/`, `*.pyc` - Python cache files
- `*.log` - Log files with potentially sensitive data

### Safe Practices
- Never commit API keys or secrets
- Review diffs before pushing with `git safe-push`
- Use meaningful commit messages for audit trail
- Tag releases for easy rollback
- Keep personal trading data local only

## Emergency Procedures

### Undo Last Commit (not pushed)
```bash
git reset --soft HEAD~1  # Keep changes staged
git reset --hard HEAD~1  # Discard changes
```

### Undo Pushed Commit
```bash
git revert <commit-hash>  # Creates new commit undoing changes
```

### Force Update Remote Branch (dangerous)
```bash
git push --force-with-lease origin branch-name
```

Only use `--force-with-lease` after confirming no one else is working on the branch.