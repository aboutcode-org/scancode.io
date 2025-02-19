# Release instructions for `ScanCode.io`

### Automated release workflow

- Create a new `release-x.x.x` branch
- Update the version in:
  - `setup.cfg` (2 entries)
  - `scancodeio/__init__.py`
  - `CHANGELOG.rst` (set date)
- Commit and push this branch
- Create a PR and merge once approved
- Tag and push that tag. This will triggers the `pypi-release.yml` GitHub workflow that 
  takes care of building the dist release files and upload those to pypi:
  ```
  VERSION=vx.x.x  # <- Set the new version here
  git tag -a $VERSION -m ""
  git push origin $VERSION
  ```
- Review the GitHub release created by the workflow at 
  https://github.com/aboutcode-org/scancode.io/releases

### Manual build

```
cd scancode.io
source .venv/bin/activate
pip install build
python -m build --sdist --wheel --outdir dist/ .
```

The distribution files will be available in the local `dist/` directory.
