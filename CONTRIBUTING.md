# Contributing to Raven 🐦‍⬛

First off, thank you for taking the time to contribute! It's people like you who make the open-source community such an amazing place to learn, inspire, and create.

The following guidelines will help you get started with contributing to **Raven**, a modern system monitor for Linux, BSD, macOS, and Windows.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Pull Requests](#pull-requests)
- [Local Development Setup](#local-development-setup)
- [Style & Quality Guidelines](#style--quality-guidelines)
- [Contact & Support](#contact--support)

## Code of Conduct

By participating in this project, you agree to maintain a respectful, welcoming, and inclusive environment. Please be kind, constructive, and collaborative.

## How Can I Contribute?

### Reporting Bugs

If you find a bug or unexpected behavior:
1. **Search existing issues** to check if it has already been reported.
2. If not, **open a new issue** and include:
   - A clear and descriptive title.
   - Steps to reproduce the issue.
   - Expected vs. actual behavior.
   - Your environment details (OS, Python version, Raven version).
   - Any relevant logs, screenshots, or stack traces.

> [!WARNING]
> If you discover a security vulnerability, please do **not** open a public issue. Refer to our [Security Policy](./SECURITY.md) for how to report it securely.

### Suggesting Enhancements

We are always looking for new features, plugins, and performance optimizations:
1. Check if the enhancement has already been proposed in the issues.
2. Open a new issue outlining:
   - What the feature is and why it would be useful.
   - Any design suggestions or implementation thoughts.
   - Mockups or terminal layout ideas, if applicable.

### Pull Requests

To submit your changes:
1. **Fork** the repository and create a branch from `main`.
2. Keep your changes focused. If you want to do multiple unrelated things, submit separate pull requests.
3. Write clean, readable code and follow the [Style & Quality Guidelines](#style--quality-guidelines).
4. Update documentation (`README.md`, comments) if you introduce new features or change CLI commands/configuration options.
5. Submit the pull request (PR) and describe your changes clearly in the PR description.

## Local Development Setup

Follow these steps to set up Raven for development on your machine:

1. **Clone your fork:**
   ```bash
   git clone https://github.com/your-username/raven.git
   cd raven
   ```

2. **Set up a virtual environment (recommended):**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies in editable mode:**
   Install development tools and optional dependencies:
   ```bash
   pip install -e ".[all]"
   ```

4. **Verify the installation:**
   Run the CLI directly to ensure it works:
   ```bash
   raven fetch
   ```

## Style & Quality Guidelines

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting. 

Before committing your changes, please run:

```bash
# Check for lint issues
ruff check

# Format your code
ruff format
```

## 📜 Code of Conduct

Please maintain a respectful and professional tone in all communications.

---

Happy coding! 🌑
