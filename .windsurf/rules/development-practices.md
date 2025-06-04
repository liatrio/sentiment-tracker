---
trigger: always_on
---

# Project Development Guidelines: Sentiment Tracker

This document outlines key development practices for the Sentiment Tracker project to ensure quality and consistency.

## 1. Core Principles
- **Small Batch Delivery**: Break work into small, deliverable units. Commit frequently. Ensure `main` is always deployable. Use feature branches.
- **Continuous Documentation**: Keep `README.md` and other project documents (e.g., `spec.md`) updated as changes occur.

## 2. Version Control & Commits
- **Git Workflow**:
    - Develop in feature branches (e.g., `feat/feature-name`, `fix/bug-fix`).
    - Use Pull Requests (PRs) for merging to `main` (if applicable, ensure review).
    - Prefer rebasing feature branches onto `main` before merging for a clean, linear history.
- **Conventional Commits**:
    - Adhere strictly to [Conventional Commits specification](https://www.conventionalcommits.org/).
    - **Format**: `<type>(<scope>): <subject>` (e.g., `feat(auth): add OTP login`).
    - **Common Types**: `feat`, `fix`, `chore`, `docs`, `style`, `refactor`, `test`, `build`.
    - **Subject**: Concise, present tense, imperative mood (e.g., "implement user registration").
    - Use commit body for details, and footer for `BREAKING CHANGE:` or issue references.

## 3. Code Quality & Standards
- **Code Comments**:
    - Explain complex logic or the *reasoning* behind decisions.
    - Use `TODO:` or `FIXME:` for pending work, ideally linked to an issue/task.
    - Avoid commenting on obvious code.
- **Python Best Practices**:
    - **PEP 8**: Mandatory. Enforced by Black via pre-commit hooks.
    - **Type Hinting**: Use for all function signatures, class attributes, and important variables.
    - **Docstrings**: Write clear, comprehensive docstrings for all public modules, classes, functions, and methods.

## 4. Development Workflow & Tooling (`Taskfile.yml`)
`Taskfile.yml` automates common development tasks.
- **Environment Setup**:
    - Use the project virtual environment: `task venv` then `source .venv/bin/activate`.
    - Install/update dependencies: `task install-dev`.
- **Linting & Formatting (via Pre-commit)**:
    - Pre-commit hooks (Black, isort, Flake8) are the primary quality gate.
    - Install hooks (once per clone): `task pre-commit-install`.
    - Hooks run automatically on `git commit`.
    - Manually run all hooks: `task pre-commit-run`.
    - Ad-hoc formatting/linting: `task format`, `task lint`.
- **Unit Testing**:
    - Run tests frequently: `task test` (includes coverage report).
    - **All tests MUST pass** before committing or creating a PR.

## 5. Testing Strategy
- **Unit Tests**: Write for all new functions and significant logic changes. Mock external services (Slack, OpenAI).
- **Test Coverage**: Aim for >80-90%. Review coverage report from `task test` to identify gaps.

## 6. Dependencies & Configuration
- **Dependency Management**:
    - Application: `requirements.txt`.
    - Development: `requirements-dev.txt`.
    - Update/install via `task install-dev` or `task install`.
- **Configuration Management**:
    - **Environment Variables ONLY**: No hardcoded settings or secrets.
    - Local Development: Use `.env` file (gitignored).
    - Documentation: All required environment variables MUST be documented in `.env.example` with placeholders.
