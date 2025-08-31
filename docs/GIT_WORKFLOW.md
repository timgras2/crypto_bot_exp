# Git Workflow - Two Computer Setup

Comprehensive reference for working on the crypto trading bot across multiple computers.

## 🚀 **QUICK REFERENCE** - Complete Workflow

### **Start Work (ALWAYS FIRST):**
```bash
git pull
```

### **End Work (ALWAYS COMPLETE ALL STEPS):**
```bash
git add .
git commit -m "type(scope): description"    # Use proper format!
git push                                     # NEVER skip this!
```

### **Required Commit Format:**
```bash
git commit -m "feat(trading): add new feature"
git commit -m "fix(api): handle timeout errors"  
git commit -m "docs(readme): update instructions"
```

## 🚀 Starting Work (ALWAYS DO THIS FIRST)

```bash
git pull
```

**Why?** Gets the latest changes from your other computer.

**What happens:**
- ✅ **No changes:** You're up to date, start coding
- ⚠️ **Fast-forward merge:** Changes pulled automatically, start coding  
- ⚠️ **Merge needed:** See "Handling Merges" section below

## 💾 Ending Work (ALWAYS DO THIS WHEN DONE)

### ⚠️ CRITICAL: Always Follow Complete Workflow
**NEVER skip the push step!** Your changes must be backed up to the remote server.

### Complete Workflow (Execute Every Step):
```bash
# 1. Stage all changes
git add .

# 2. Commit with REQUIRED format (see format section below)
git commit -m "type(scope): description"

# 3. ALWAYS push to remote (NEVER skip this!)
git push
```

### What Can Happen When Pushing:

**✅ Success:** Changes pushed to remote server, you're done!

**❌ Push Rejected:** Someone else (your other computer) pushed changes
```bash
git pull          # Get remote changes first
# Handle any merge (see below)
git push          # RETRY push after merge - REQUIRED!
```

**💡 Pro Tip:** If you're on a feature branch, the first push needs:
```bash
git push -u origin <branch-name>  # For new branches
git push                          # For subsequent pushes
```

## 📝 Commit Message Format

⚠️ **MANDATORY FORMAT** - Your repository will REJECT commits that don't follow this format:

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### ✅ Required Components:
1. **Type**: What kind of change (see list below)
2. **Scope**: What area of code (see list below)  
3. **Subject**: Brief description (1-50 chars, lowercase, no period)

### 📋 Valid Types:
- `feat` - New feature or functionality
- `fix` - Bug fix or error correction
- `docs` - Documentation changes
- `style` - Code formatting (no functional changes)
- `refactor` - Code restructuring (no functional changes)
- `test` - Adding or modifying tests
- `chore` - Maintenance, dependencies, tooling

### 🎯 Valid Scopes:
- `trading` - Trading logic, algorithms, strategies
- `api` - API interactions, requests, responses
- `market` - Market monitoring, data fetching
- `config` - Configuration files, environment variables
- `tests` - Test files, test utilities
- `docs` - Documentation files, README updates

### ✅ Good Examples:
```bash
git commit -m "feat(trading): add dip buying strategy"
git commit -m "fix(api): handle rate limit errors gracefully"
git commit -m "chore(config): update python dependencies"
git commit -m "docs(readme): add installation instructions"
git commit -m "test(trading): add unit tests for stop loss"
git commit -m "refactor(market): simplify price tracking logic"
```

### ❌ Bad Examples (Will Be Rejected):
```bash
git commit -m "added new feature"           # Missing type and scope
git commit -m "fix: bug fix"                # Missing scope
git commit -m "feat(invalid): new thing"   # Invalid scope
git commit -m "FEAT(trading): NEW FEATURE" # Uppercase not allowed
git commit -m "feat(trading): Add feature." # Period not allowed
```

### 💡 Commit Message Template:
```bash
# Basic commit
git commit -m "feat(trading): add trailing stop adjustment"

# With detailed body (use for complex changes)
git commit -m "feat(trading): add sophisticated dip buying strategy

Implement tiered capital allocation across multiple dip levels.
Includes state persistence and configurable parameters.

- Add DipBuyManager orchestration class  
- Implement DipEvaluator decision engine
- Add state persistence with JSON storage
- Include comprehensive safety controls"
```

## 🔄 Handling Merges (Detailed)

### Scenario 1: Automatic Fast-Forward
```bash
git pull
# Output: "Fast-forward" - automatic success!
# Start coding immediately
```

### Scenario 2: Automatic Merge
```bash
git pull
# Output: "Merge made by the 'recursive' strategy"
# Files merged automatically, start coding
```

### Scenario 3: Merge Commit Required
```bash
git pull
# Output: "Please enter a commit message for the merge"
# Git opens an editor or asks for merge message
git commit -m "chore(merge): merge remote changes"
```

### Scenario 4: Merge Conflicts (Manual Resolution Required)
```bash
git pull
# Output: "Automatic merge failed; fix conflicts and then commit"
git status          # See which files have conflicts
```

**Resolve conflicts:**
1. Open conflicted files in your editor
2. Look for conflict markers:
   ```
   <<<<<<< HEAD
   Your changes
   =======
   Remote changes  
   >>>>>>> branch-name
   ```
3. Choose which version to keep (or combine both)
4. Remove all conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
5. Save the file
6. Continue:
   ```bash
   git add .
   git commit -m "fix(merge): resolve merge conflicts"
   git push
   ```

## 🔄 Push Scenarios (When Things Go Wrong)

### Push Rejected - Need to Pull First
```bash
git push
# Error: "Updates were rejected because the remote contains work..."

# Solution:
git pull                    # Get remote changes
# Handle merge if needed (see above)
git push                    # Now push your changes
```

### Push After Failed Merge
```bash
git pull
# Merge conflicts occurred, you resolved them
git add .
git commit -m "fix(merge): resolve conflicts in trade_logic.py"
git push                    # Push both your changes and the merge
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

## 🚨 CRITICAL: Why You MUST Always Push

### ⚠️ **NEVER End a Session Without Pushing!**

**What happens if you don't push:**
- ❌ Changes only exist on current computer
- ❌ Other computers won't see your work
- ❌ Risk of losing work if computer crashes
- ❌ Creates messy merge conflicts later
- ❌ Breaks the two-computer workflow

### ✅ **Benefits of Always Pushing:**
- ✅ Work is backed up to GitHub immediately
- ✅ Other computers get your changes instantly
- ✅ Team members can see your progress
- ✅ Creates clean, linear git history
- ✅ Enables safe experimentation (can always revert)

### 🔧 **Troubleshooting Push Issues:**

**"Push rejected - non-fast-forward":**
```bash
git pull          # Get remote changes first
git push          # Retry push after merge
```

**"Failed to push some refs":**
```bash
git status        # Check what's wrong
git pull          # Usually need to pull first
git push          # Retry after pull
```

**"Permission denied" or "Authentication failed":**
```bash
# Check if you're logged into GitHub
git remote -v     # Verify remote URL
# May need to re-authenticate with GitHub
```

### 💡 **Push Verification:**
After `git push`, you should see:
```
To https://github.com/username/repo.git
   abc1234..def5678  branch-name -> branch-name
```

## 🚨 Common Issues & Solutions

### Issue 1: "Your branch is behind"
```bash
git pull
# Always pull before starting work
```

### Issue 2: "Your branch is ahead"  
```bash
git push
# Push your local commits to remote
```

### Issue 3: "Your branch has diverged"
```bash
git pull
# This will create a merge commit
git push
```

### Issue 4: Forgot to commit before pulling
```bash
git stash           # Save your uncommitted changes
git pull           # Get remote changes
git stash pop      # Restore your changes
# Resolve any conflicts, then:
git add .
git commit -m "feat(scope): your changes"
git push
```

### Issue 5: Accidentally committed to wrong branch
```bash
# If you haven't pushed yet:
git reset HEAD~1   # Undo last commit, keep changes
# Make your changes and commit properly
```

## 📊 When to Push vs. Just Commit

### ✅ Always Push When:
- Ending work session (switching computers)
- Completing a feature or bug fix
- Before taking a break from coding
- At end of each day

### 📝 Just Commit (Don't Push Yet) When:
- Making incremental progress on a feature
- Saving work-in-progress state
- Creating checkpoint before trying risky changes
- Working on experimental code

**Rule of thumb:** If you might switch computers or want others to see your work, push it!

## 🔄 Advanced Workflows

### Working on a Big Feature:
```bash
# Day 1:
git pull
# Code, code, code...
git add .
git commit -m "feat(trading): start implementing advanced stop loss"
git push                    # End of day - always push

# Day 2 (different computer):
git pull                    # Get yesterday's work
# Code, code, code...
git add .  
git commit -m "feat(trading): add stop loss calculation logic"
git push                    # End of day - always push

# Day 3 (any computer):
git pull                    # Get all previous work
# Code, code, code...
git add .
git commit -m "feat(trading): complete advanced stop loss feature"
git push                    # Feature complete!
```

### Making Quick Fixes:
```bash
git pull                    # Always start with pull
# Fix the bug...
git add .
git commit -m "fix(trading): handle edge case in price calculation"
git push                    # Push immediately for small fixes
```

### Experimental Changes:
```bash
git pull
# Try something new...
git add .
git commit -m "feat(experimental): test new trading algorithm"
# Don't push yet - test first!

# If it works:
git push

# If it doesn't work:
git reset HEAD~1           # Undo the commit
# or
git revert HEAD            # Create a new commit that undoes changes
```

## 🛠️ Extended Commands Reference

### Viewing History:
```bash
git log --oneline -10      # Last 10 commits, one line each
git log --graph --oneline  # Visual branch history
git show HEAD              # Details of last commit
git show HEAD~1            # Details of commit before last
```

### Checking Status:
```bash
git status                 # What's changed
git status -s              # Short status
git diff                   # See unstaged changes  
git diff --staged          # See staged changes
git diff HEAD~1            # Compare with previous commit
```

### Undoing Changes:
```bash
git restore filename.py    # Undo changes to a file
git restore .              # Undo all unstaged changes
git reset HEAD filename.py # Unstage a file
git reset HEAD~1           # Undo last commit, keep changes
git reset --hard HEAD~1    # Undo last commit, lose changes (DANGER!)
```

### Branch Management:
```bash
git branch                 # List branches
git branch -v              # List with last commits
git branch feature-name    # Create new branch
git checkout feature-name  # Switch to branch
git checkout -b feature-name # Create and switch to branch
git merge feature-name     # Merge branch into current branch
```

## 🚨 Emergency Recovery

### "I messed up everything!"
```bash
git status                 # See what's wrong
git stash                  # Save current mess
git pull                   # Get clean remote version
git stash drop             # Throw away the mess
# Start over from clean state
```

### "I need the version from 3 commits ago!"
```bash
git log --oneline -10      # Find the commit hash
git checkout abc1234       # Go to that commit (replace abc1234)
# Copy the files you need
git checkout master        # Go back to latest
```

### "I accidentally deleted important code!"
```bash
git log --oneline          # Find when you last had the code
git show abc1234:filename.py # See the file from that commit
# Copy what you need back
```

---

**💡 Pro Tips:**
- Bookmark this file and refer to it every time you switch computers!
- Keep commits small and focused - easier to understand and merge
- Write descriptive commit messages - you'll thank yourself later
- When in doubt, `git status` is your friend
- Practice the workflow a few times to build muscle memory