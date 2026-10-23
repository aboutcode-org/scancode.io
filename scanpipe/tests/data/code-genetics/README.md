# Code Genetics origin test data set

Small synthetic codebases, one origin case each, to measure origin detection and determination. The ground truth is known by construction: every third-party file was taken from the official release artifact at its `download_url`.

| Case | Content | Expected origin |
|---|---|---|
| `exact-copy` | Unmodified `six.py` vendored in an application | `pkg:pypi/six@1.17.0` |
| `vendored-copy` | `six.py` copied from urllib3, which vendors six reformatted with black | `pkg:pypi/six@1.16.0`, copied from `pkg:pypi/urllib3@1.26.20` |
| `modified-copy` | inih with a local patch: `ini.h` unchanged, `ini.c` with changed lines and an added function | `pkg:github/benhoyt/inih@r62` |
| `snippet` | lodash `debounce` function copied into an application file | `pkg:npm/lodash@4.17.21` |
| `embedded-package` | Complete ms npm package in a vendor directory | `pkg:npm/ms@2.1.3` |
| `no-origin` | Original application code | None |

## Layout

Each case directory contains:

- `codebase/`: the input to scan. It only contains the case files, without `.ABOUT` or other provenance files, as they would be detected by the scanners.
- `expected.json`: the ground truth.
- `matchcode-results.json`: the MatchCode.io match results, reduced to the fields used by the importer.
- `scanoss-results.json`: the SCANOSS raw results, with paths relative to `codebase/`.

## expected.json

- `resources`: one entry per file of `codebase/`.
  - `path`: path relative to `codebase/`.
  - `match_type`: `exact`, `modified`, `snippet` or `none`, compared to the origin file.
  - `origin`: the original file (`purl`, `download_url`, `path` inside the downloaded archive, `sha1`), or `null` when there is no origin.
  - `copied_from`: the file actually copied, when it differs from the origin (vendored copy of a vendored copy).
  - `line_ranges`: for `modified` and `snippet` only, the `lines` of the codebase file that come from the `origin_lines` of the origin file. Ranges are inclusive.
- `packages`: complete packages embedded in the codebase, with their directory `path`.

## Tool results

The tool results are real outputs, not handwritten:

- MatchCode.io results come from a local PurlDB indexing only the six reference packages of this data set (`pkg:pypi/six@1.16.0`, `pkg:pypi/six@1.17.0`, `pkg:pypi/urllib3@1.26.20`, `pkg:github/benhoyt/inih@r62`, `pkg:npm/lodash@4.17.21`, `pkg:npm/ms@2.1.3`), with the file and directory fingerprints computed by ScanCode.io.
- SCANOSS results come from the free osskb.org service (knowledge base 26.10.19), which reports a single best match per file.
