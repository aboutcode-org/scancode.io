# Release instructions for `aboutcode.pipeline`

### Automated release workflow

- Create a new `aboutcode.pipeline-release-x.x.x` branch
- Update the version in:
  - `pipeline-pyproject.toml`
  - `aboutcode/pipeline/__init__.py`
- Commit and push this branch
- Create a PR and merge once approved
- Tag and push to trigger the `pypi-release-aboutcode-pipeline.yml` workflow that 
  takes care of building the distribution archives and upload those to pypi::
  ```
  VERSION=x.x.x  # <- Set the new version here
  TAG=aboutcode.pipeline/$VERSION
  git tag -a $TAG -m ""
  git push origin $TAG
  ```

### Manual build

```
cd scancode.io
source .venv/bin/activate
pip install flot
flot --pyproject pipeline-pyproject.toml --sdist --wheel --output-dir dist/
```

The distribution archives will be available in the local `dist/` directory.