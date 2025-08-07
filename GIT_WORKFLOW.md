# Git Workflow - Two Computer Setup

Quick reference for working on the crypto trading bot across multiple computers.

## 🚀 Starting Work (ALWAYS DO THIS FIRST)

```bash
git pull
```

**Why?** Gets the latest changes from your other computer.

## 💾 Ending Work (ALWAYS DO THIS WHEN DONE)

```bash
git add .
git commit -m "feat(scope): describe your changes"
git push
```

## 📝 Commit Message Format

Your repository requires this specific format:

```
<type>(scope): description
```

### Types:
- `feat` - New feature
- `fix` - Bug fix  
- `docs` - Documentation
- `style` - Code formatting
- `refactor` - Code restructuring
- `test` - Adding tests
- `chore` - Maintenance tasks

### Scopes:
- `trading` - Trading logic
- `api` - API interactions
- `market` - Market monitoring
- `config` - Configuration
- `tests` - Test files
- `docs` - Documentation

### Examples:
```bash
git commit -m "feat(trading): add trailing stop-loss feature"
git commit -m "fix(api): handle rate limit errors gracefully"  
git commit -m "chore(config): update dependencies"
git commit -m "docs(readme): add installation instructions"
```

## 🔄 If You Forgot to Pull First

If `git push` fails with "fetch first" error:

```bash
git pull
# If merge needed:
git commit -m "chore(merge): merge remote changes"
git push
```

## ⚠️ Important Notes

- **NEVER run the bot on both computers simultaneously** (trading conflicts)
- **ALWAYS pull before starting work**
- **ALWAYS push when done working**  
- Runtime data files are ignored (each computer keeps its own trading state)
- Small, frequent commits are better than large ones

## 📁 Files That DON'T Sync (Ignored)

These files stay local to each computer:
- `data/active_trades.json` - Current trading positions
- `data/completed_trades.json` - Trade history  
- `logs/*.log` - Bot activity logs
- `.env` - API credentials

## 🛠️ Quick Commands Reference

```bash
# Check what changed
git status

# See recent commits  
git log --oneline -5

# See what will be committed
git diff --staged

# Undo unstaged changes
git restore filename.py

# Undo last commit (keep changes)
git reset HEAD~1
```

## 🚨 Emergency: Conflicts

If you get merge conflicts:

1. Open the conflicted files
2. Look for `<<<<<<< HEAD` markers
3. Choose which version to keep
4. Remove the conflict markers
5. `git add .`
6. `git commit -m "fix(merge): resolve conflicts"`
7. `git push`

---

**💡 Pro Tip:** Bookmark this file and refer to it every time you switch computers!