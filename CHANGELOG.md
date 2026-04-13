# CHANGELOG

## v3.2.0 (2023-10-29)

### ✨ Features

-   **Test Asset Codification Engine**: Introduced a powerful new engine to generate test code from external assets:
    -   `phoenix generate har`: Generate API tests from HAR files.
    -   `phoenix generate openapi`: Generate API test skeletons from OpenAPI/Swagger specifications.
    -   `phoenix generate playwright-codegen`: Generate Page Object Model (POM) and data-driven tests from Playwright Codegen scripts.
-   **CLI Enhancements**:
    -   `phoenix doctor`: Added a command to diagnose the environment and check dependencies.
    -   `phoenix env list`: Added a command to list configured environments.

### 🐛 Bug Fixes

-   (None in this release, as it's a new feature release)

### 🧹 Refactor

-   Refactored CLI structure to support new `generate` command group.
-   Improved `api_generator` to handle `postData` more robustly.

### 📚 Documentation

-   Updated `README.md` with v3.2 features and usage.
-   Added `docs/codegen.md` detailing the Test Asset Codification Engine.
-   Ensured all new CLI commands have comprehensive `--help` documentation.

### ⚙️ Chore

-   Initial project setup with `pyproject.toml`, `ruff`, and GitHub Actions CI.
