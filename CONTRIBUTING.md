# Contributing to Raven 🐦‍⬛

Thank you for your interest in contributing to **Raven**! We welcome contributions, bug reports, feature requests, and security improvements from the community.

---

## 🛠 Setting Up Your Development Environment

Raven uses [uv](https://github.com/astral-sh/uv) to manage python dependencies, virtual environments, and workspace configurations.

### Prerequisites

- **Python**: `3.11`, `3.12`, or `3.13`.
- **uv**: Install via curl or your package manager (see [uv installation](https://github.com/astral-sh/uv#installation)).

### Setup Steps

1. **Fork and clone** the repository:
   ```bash
   git clone https://github.com/your-username/raven.git
   cd raven
   ```

2. **Sync the workspace dependencies and virtual environment**:
   ```bash
   uv sync --all-extras --dev
   ```
   This command automatically creates a virtual environment `.venv` and installs all dependencies, including development tools (`pytest`, `ruff`, etc.).

---

## 🎨 Coding Style & Guidelines

To maintain code quality and consistency across the repository, we use **Ruff** for formatting and linting.

### Formatting & Linting Rules

- Line length limit: **100 characters**.
- Target Python version: **3.11**.
- We select rules: `E` (errors), `F` (linting/imports), `W` (warnings), `I` (isort import ordering), `UP` (pyupgrade), and `B` (flake8-bugbear).

### Quality Checks

Before committing your changes, always run lint, format, and type checks locally:

```bash
# Run the linter
uv run ruff check

# Run the format check
uv run ruff format --check

# Run static type checking
uv run mypy
```

To automatically fix import order and lint errors, and auto-format your code:

```bash
# Auto-fix linting issues
uv run ruff check --fix

# Auto-format the code
uv run ruff format
```

---

## 🧪 Testing

We use **pytest** for testing. All new features and bug fixes should include corresponding tests.

Run the test suite with coverage using `uv`:

```bash
uv run pytest --cov
```

Our test suite includes:
- Unit tests for configuration, exporters, models, and utility functions.
- Integration tests verifying remote client/server communication using FastAPI's test client.
- UI/TUI tests validating Textual widgets and application lifecycle.
- Feature and regression tests for edge cases and plugin robustness.

---

## 🚀 Pull Request Process

When you are ready to submit your changes, please follow these steps:

1. **Create a branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```
2. **Make your changes** and ensure they adhere to coding style guidelines.
3. **Write/update tests** for your changes.
4. **Verify everything passes** locally:
   ```bash
   uv run ruff check
   uv run ruff format --check
   uv run mypy
   uv run pytest --cov
   ```
5. **Commit your changes** with a clear and descriptive commit message.
6. **Push your branch** to your fork and **open a Pull Request** against the `main` branch of the original repository.
7. Fill out the Pull Request template provided in the repository.

---

Happy coding! 🐦‍⬛