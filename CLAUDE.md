### 🔄 Project Awareness & Context
- **Always read `PLANNING.md`** at the start of a new conversation to understand the project's architecture, goals, style, and constraints.
- **Check `TASK.md`** before starting a new task. If the task isn’t listed, add it with a brief description and today's date.
- **Use consistent naming conventions, file structure, and architecture patterns** as described in `PLANNING.md`.
- **Use venv_linux** (the virtual environment) whenever executing Python commands, including for unit tests.

### 🧱 Code Structure & Modularity
- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Organize code into clearly separated modules**, grouped by feature or responsibility.
  For agents this looks like:
    - `agent.py` - Main agent definition and execution logic 
    - `tools.py` - Tool functions used by the agent 
    - `prompts.py` - System prompts
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use python_dotenv and load_env()** for environment variables.

### Technical Architecture
- **langchain-opena** for Azure OpenAI integration
- **azure-identity** for authentication
- **structlog** for JSON logging
- **python-dotenv** for configuration management
- **click** for CLI interface
- **rich** for enhanced console output

### 🚀 Environment Setup & Configuration
- **Always update `.\scripts\setup-env.ps1`** when adding new environment variables to the application.
- **Environment variables must be added in 3 places:**
  1. `infrastructure/outputs.tf` - Add to the `environment_variables` output section
  2. `scripts/setup-env.ps1` - Add to the `New-EnvContent` function with proper documentation
  3. `src/config/settings.py` - Add as pydantic settings fields with proper types and defaults
- **The setup-env.ps1 script** extracts Terraform outputs and generates the `.env` file automatically.
- **Never manually edit the generated `.env` file** - it gets overwritten by the setup script.

### 🔍 Logging Standards
- **All logs must include a `log_type` property** at the top level (not in customDimensions) for Azure Log Analytics categorization.
- **Use these 5 standardized log_type values:**
  - `CONVERSATION` - Chat interactions, message processing, conversation flow
  - `AZURE_OPENAI` - Azure OpenAI API calls, responses, token usage
  - `PERFORMANCE` - Response times, throughput metrics, resource usage
  - `SECURITY` - Authentication, Key Vault operations, credential management
  - `SYSTEM` - Application lifecycle, configuration, health checks, errors
- **Add log_type when creating loggers**: `logger.bind(log_type="CATEGORY")`
- **Use structured logging helpers** in `utils/logging_helpers.py` which automatically set appropriate log_type values

### 🧪 Testing & Reliability
- **Always create Pytest unit tests for new features** (functions, classes, routes, etc).
- **After updating any logic**, check whether existing unit tests need to be updated. If so, do it.
- **Tests should live in a `/tests` folder** mirroring the main app structure.
  - Include at least:
    - 1 test for expected use
    - 1 edge case
    - 1 failure case

### ✅ Task Completion
- **Mark completed tasks in `TASK.md`** immediately after finishing them.
- Add new sub-tasks or TODOs discovered during development to `TASK.md` under a “Discovered During Work” section.

### 📎 Style & Conventions
- **Use Python** as the primary language.
- **Follow PEP8**, use type hints, and format with `black`.
- **Use `pydantic` for data validation**.
- Use `FastAPI` for APIs and `SQLAlchemy` or `SQLModel` for ORM if applicable.
- Write **docstrings for every function** using the Google style:
  ```python
  def example():
      """
      Brief summary.

      Args:
          param1 (type): Description.

      Returns:
          type: Description.
      """
  ```

### 📚 Documentation & Explainability
- **Update `README.md`** when new features are added, dependencies change, or setup steps are modified.
- **Comment non-obvious code** and ensure everything is understandable to a mid-level developer.
- When writing complex logic, **add an inline `# Reason:` comment** explaining the why, not just the what.

### 🧠 AI Behavior Rules
- **Never assume missing context. Ask questions if uncertain.**
- **Never hallucinate libraries or functions** – only use known, verified Python packages.
- **Always confirm file paths and module names** exist before referencing them in code or tests.
- **Never delete or overwrite existing code** unless explicitly instructed to or if part of a task from `TASK.md`.