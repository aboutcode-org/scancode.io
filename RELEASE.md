# Release instructions for `ScanCode.io`

## 🚀 Automated Release Workflow

Releases are fully automated using **python-semantic-release**.

When commits following the Conventional Commits specification are merged into the `main` branch:

- The next semantic version is computed automatically.
- `pyproject.toml` and `scancodeio/__init__.py` are updated.
- `CHANGELOG.rst` is generated/updated automatically.
- A Git tag is automatically created (vX.Y.Z).
- The tag triggers the existing PyPI publishing workflow.
- The PyPI workflow builds distributions and creates the GitHub Release.

No manual version bumping, branching, or tagging is required.

---

## 📌 Commit Message Requirements

Commits must follow the Conventional Commits format:

- `feat: add new feature`
- `fix: correct issue in pipeline`
- `feat!: introduce breaking change`
- `chore: maintenance update`

The commit type determines the version bump:

- `fix` → patch
- `feat` → minor
- `feat!` or `BREAKING CHANGE:` → major

---

## 🛠 Manual Build (Optional)

If you need to build distribution files locally:
