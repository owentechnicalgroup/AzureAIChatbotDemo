name: "Commit Azure OpenAI Chatbot Implementation"
description: |
  PRP for committing the current Azure OpenAI chatbot implementation to git repository,
  ensuring proper staging of files and comprehensive commit documentation.

## Goal
Commit the existing Azure OpenAI CLI chatbot implementation with complete infrastructure, source code, and documentation to establish a clean baseline for future feature development.

## Why
- **Repository Management**: Establish clean git history for the Azure OpenAI chatbot implementation
- **Version Control**: Create a stable checkpoint before adding new features
- **Collaboration**: Enable team collaboration with committed baseline code
- **Documentation**: Ensure all implementation artifacts are properly tracked

## What
A comprehensive git commit that includes:
- Azure OpenAI chatbot PRP documentation
- Terraform infrastructure code for Azure resources
- Python CLI application source code
- Configuration files and environment templates
- Deployment scripts and testing framework
- Updated project documentation

### Success Criteria
- [ ] All relevant Azure OpenAI implementation files are staged for commit
- [ ] Sensitive files (.env, credentials) are excluded from commit
- [ ] Commit message follows project standards with proper attribution
- [ ] Repository maintains clean working directory after commit
- [ ] All infrastructure and application files are properly tracked

## All Needed Context

### IMPORTANT: Repository Information
**CRITICAL**: This implementation should be committed to the correct repository:
- **Target Repository**: https://github.com/owentechnicalgroup/AzureAIChatbotDemo.git
- **Note**: The current working directory may be pointing to an old/incorrect repository
- **Action Required**: Verify git remote is set to the correct repository before committing

### Current Repository State
```bash
# Modified files needing review:
- .claude/settings.local.json (Claude configuration updates)
- CLAUDE.md (Project instructions and guidelines)
- INITIAL.md (Project feature documentation)
- INITIAL_EXAMPLE.md (Example documentation)
- README.md (Main project documentation)

# New untracked files for Azure OpenAI implementation:
- PRPs/azure-openai-cli-chatbot.md (Main implementation PRP)
- infrastructure/ (Terraform infrastructure code)
- src/ (Python application source code)
- scripts/ (Deployment and utility scripts)
- tests/ (Unit and integration tests)
- requirements.txt (Python dependencies)
- .env.example (Environment variable template)
```

### Files to EXCLUDE from commit
```bash
# Sensitive/local files that should NOT be committed:
- .env (contains actual credentials)
- .env.backup.* (backup environment files)
- logs/ (runtime log files)
- debug_test.log (debug output)
- *.docx (Word documents)
- pypi_test.html (temporary test files)
```

## Implementation Blueprint

### List of Tasks to Complete

```yaml
Task 0:
VERIFY correct repository remote:
  - CHECK current git remote with: git remote -v
  - UPDATE remote if needed to: https://github.com/owentechnicalgroup/AzureAIChatbotDemo.git
  - CONFIRM connection to correct repository before proceeding

Task 1:
REVIEW all uncommitted changes:
  - EXAMINE each modified file for appropriateness
  - VERIFY no sensitive credentials are included
  - CONFIRM all changes align with Azure OpenAI implementation

Task 2:
STAGE appropriate files for commit:
  - ADD all implementation files (src/, infrastructure/, scripts/, tests/)
  - ADD documentation updates (PRPs/, README.md, CLAUDE.md, INITIAL.md)
  - ADD configuration templates (.env.example, requirements.txt)
  - EXCLUDE sensitive files (.env, .env.backup.*, logs/, debug files)

Task 3:
CREATE comprehensive commit message:
  - SUMMARIZE the Azure OpenAI chatbot implementation
  - INCLUDE infrastructure and application components
  - MENTION key features and capabilities
  - FOLLOW project commit message standards

Task 4:
EXECUTE git commit:
  - COMMIT staged files with proper message
  - INCLUDE Claude Code attribution
  - VERIFY commit success
  - CONFIRM clean working directory state
```

### Commit Message Template
```
Add Azure OpenAI CLI chatbot implementation with infrastructure

- Complete Terraform infrastructure for Azure OpenAI, Key Vault, and logging
- Python CLI application with LangChain integration and conversation memory  
- Structured logging with Azure Application Insights compatibility
- Environment-based configuration with secure credential management
- Comprehensive testing framework and deployment scripts
- Updated project documentation and PRP specifications

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Validation Loop

### Level 0: Repository Verification
```bash
# Verify correct repository remote
git remote -v              # Check current remote URLs
git remote get-url origin  # Confirm origin URL
# Expected: https://github.com/owentechnicalgroup/AzureAIChatbotDemo.git
```

### Level 1: File Review
```bash
# Review each category of changes
git diff --name-only HEAD  # See all changed files
git diff CLAUDE.md         # Review documentation changes
git status                 # Confirm staging status
```

### Level 2: Security Check
```bash
# Ensure no sensitive data is being committed
grep -r "api_key\|password\|secret" --include="*.py" --include="*.md" src/
grep -r "AZURE_OPENAI_API_KEY" .env.example  # Should only be in template
```

### Level 3: Commit Validation
```bash
# Verify commit includes expected files
git log --name-only -1     # Show files in latest commit
git status                 # Confirm clean working directory
```

## Final Validation Checklist
- [ ] **Git remote verified as https://github.com/owentechnicalgroup/AzureAIChatbotDemo.git**
- [ ] All Azure OpenAI implementation files are staged
- [ ] No sensitive credentials included in commit
- [ ] Commit message is comprehensive and follows standards
- [ ] Repository working directory is clean after commit
- [ ] All documentation updates are included
- [ ] Infrastructure and application code properly tracked

---

## Anti-Patterns to Avoid
- ❌ Don't commit sensitive files (.env with real credentials)
- ❌ Don't commit temporary or debug files
- ❌ Don't use generic commit messages - be specific about the implementation
- ❌ Don't commit without reviewing all staged changes first
- ❌ Don't forget to include Claude Code attribution in commit message