# Contributing to ScanCode.io

## Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/) to automate our release process.
This specification is **mandatory** for all commits.

### Format
```
<type>(<scope>): <subject>
<BLANK LINE>
<body>
```

### Allowed Types
-   **feat**: A new feature (triggers MINOR release)
-   **fix**: A bug fix (triggers PATCH release)
-   **docs**: Documentation only changes
-   **style**: Changes that do not affect the meaning of the code (white-space, formatting, etc)
-   **refactor**: A code change that neither fixes a bug nor adds a feature
-   **perf**: A code change that improves performance
-   **test**: Adding missing tests or correcting existing tests
-   **build**: Changes that affect the build system or external dependencies
-   **ci**: Changes to our CI configuration files and scripts
-   **chore**: Other changes that don't modify src or test files

### Breaking Changes
To indicate a breaking change, add `!` after the type/scope or add `BREAKING CHANGE:` in the footer. This triggers a MAJOR release.

Example:
```
feat(api)!: remove support for v1 endpoints
```

### Pre-commit Hooks
We recommend installing pre-commit hooks to ensure your commits are valid before pushing:

```bash
pip install pre-commit
pre-commit install --hook-type commit-msg
```
