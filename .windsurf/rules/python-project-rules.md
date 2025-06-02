---
trigger: glob
globs: **/*.py
---

- **Development Workflow Orchestration (Taskfile)**
  - The primary tool for managing the development lifecycle is `Taskfile.yml`. It provides commands for environment setup, dependency management, linting, formatting, testing, and pre-commit hook management.
  - **Key `task` commands**:
    - `task init`: Initializes the project (creates venv, installs all dependencies).
    - `task install`: Installs/syncs all dependencies from `requirements.txt` and `requirements-dev.txt`.
    - `task install-dev`: Installs/syncs development dependencies from `requirements-dev.txt`.
    - `task lint`: Runs all configured linters (`flake8`, `black --check`, `isort --check`) and type checker (`mypy`).
    - `task format`: Applies code formatting using `black` and `isort`.
    - `task test`: Runs `pytest` with coverage.
    - `task pre-commit-install`: Installs pre-commit hooks into the local Git repository.
    - `task pre-commit-run`: Manually runs all pre-commit hooks on all project files.
  - Always refer to `Taskfile.yml` for the most up-to-date list of tasks and their specific actions.

- **General Python Best Practices**
  - **PEP 8 Compliance & Code Formatting**: Adhere to PEP 8 style guidelines.
    - `black` is used for auto-formatting and `isort` for import sorting.
    - Apply formatting using `task format`.
    - Check formatting as part of `task lint`.
    - Configuration for these tools is in `pyproject.toml`.
  - **Linting & Type Hinting**:
    - Utilize Python's type hinting for all critical function signatures and variables (e.g., `def func(param: str) -> int:`).
    - `flake8` is used for general linting and `mypy` for static type checking.
    - Run all linting and type checks via `task lint`.
    - Configuration for `flake8` is in `.flake8`; `mypy` is in `pyproject.toml`.
  - **Docstrings**: Write comprehensive docstrings (Google, NumPy, or reST style) for all public modules, classes, and functions.
  - **Logging**: Use the `logging` module for structured logs. Refer to `spec.md` for specific log levels and formatting requirements.
  - **Error Handling**: Implement robust `try-except` blocks, catching specific exceptions. Log errors clearly.
  - **Modularity**: Write modular, reusable code by breaking down logic into small functions and classes.
  - **Pre-commit Hooks**:
    - Pre-commit hooks are configured in [.pre-commit-config.yaml](cci:7://file:///Users/jburns/git/sentiment-tracker/.pre-commit-config.yaml:0:0-0:0) to automatically run linters and formatters before each commit.
    - Install hooks locally using `task pre-commit-install`.
    - Hooks include checks for trailing whitespace, end-of-file fixing, YAML validity, large files, `black`, `isort`, and `flake8`.

- **Environment & Dependencies (Taskfile)**
  - **Virtual Environments**: Managed via `Taskfile.yml`. The environment is created at `.venv/`.
    - Set up and initialize the virtual environment and install dependencies using `task init`.
    - Activate the virtual environment: `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate` (Windows).
    - Ensure `.venv/` is listed in `[.gitignore](cci:7://file:///Users/jburns/git/sentiment-tracker/.gitignore:0:0-0:0)`.
  - **Dependency Management (`requirements.txt` & `requirements-dev.txt`)**:
    - Application dependencies are listed in `requirements.txt`.
    - Development-specific dependencies (linters, test tools) are in `requirements-dev.txt`.
    - Install/update all dependencies using `task install`.
    - Install/update only development dependencies using `task install-dev`.
    - To add a new runtime package: Add it with its version to `requirements.txt`, then run `task install`.
    - To add a new development package: Add it with its version to `requirements-dev.txt`, then run `task install-dev`.
    - Always specify package versions (e.g., `package~=1.2.3` or `package==1.2.3`) for reproducible builds.

- **Project-Specific Rules (Sentiment Tracker Bot - per spec.md)**
  - **Framework**: Use `Bolt for Python` conventions and best practices.
  - **Containerization**: Docker is used for containerization. The `[Dockerfile](cci:7://file:///Users/jburns/git/sentiment-tracker/Dockerfile:0:0-0:0)` defines the image build process. Use `[docker-compose.yml](cci:7://file:///Users/jburns/git/sentiment-tracker/docker-compose.yml:0:0-0:0)` for local Docker-based development if applicable.
  - **Configuration**: All configuration, especially secrets, must be managed via environment variables. Do not hardcode sensitive information. Refer to `[.env.example](cci:7://file:///Users/jburns/git/sentiment-tracker/.env.example:0:0-0:0)`.
  - **In-Memory Data**: Use thread-safe data structures (e.g., dictionaries protected by `threading.Lock`) for session management. Be mindful of concurrency. Adhere to specified session logic from `spec.md`.
  - **AI (OpenAI)**: Handle OpenAI API integration carefully, considering rate limits and error handling. Implement fallback mechanisms if the API is unavailable. Employ good prompt engineering practices.
  - **Security & Privacy**: Prioritize data privacy and anonymization as outlined in `spec.md`. Ensure AI-based rewriting of quotes effectively masks identity. Clear all data from memory after report generation.
  - **Slack Integration**: Ensure correct Slack API permissions are requested and handled. Implement interactive components (buttons, modals) according to Slack guidelines and project requirements.
  - **Workflow**: Code must adhere to the defined bot workflow (trigger, DM, collect, process, report, clear) as specified in `spec.md`.

- **Testing (Pytest with Taskfile)**
  - **Framework**: `pytest` is the testing framework.
  - **Location**: Tests are located in the `tests/` directory (e
