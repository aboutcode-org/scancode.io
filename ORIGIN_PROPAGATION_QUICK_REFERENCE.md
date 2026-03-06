# Origin Propagation: Quick Reference

## Propagation Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORIGIN PROPAGATION FLOW                      │
└─────────────────────────────────────────────────────────────────┘

Step 1: INITIAL SCAN & DETECTION
┌──────────────────────┐
│  Run ScanCode Scan   │
│  - Package data      │
│  - License data      │
│  - URL data          │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Detect Origins      │
│  - From packages     │
│  - From URLs         │
│  - From repositories │
└──────────┬───────────┘
           │
           ▼
┌─────────────────────────────────────────────────┐
│  Origin Determinations Created                  │
│  ┌──────────────────────────────────────────┐  │
│  │ Resource: src/lib/utils.js               │  │
│  │ Origin: pkg:npm/lodash@4.17.21           │  │
│  │ Confidence: 0.85                         │  │
│  │ Method: scancode-package-detection       │  │
│  │ is_verified: False                       │  │
│  │ is_propagated: False                     │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘

Step 2: VERIFICATION (Manual or Automatic)
┌──────────────────────┐
│  Review in UI or     │
│  Auto-verify high    │
│  confidence (≥0.9)   │
└──────────┬───────────┘
           │
           ▼
┌─────────────────────────────────────────────────┐
│  PROPAGATION SOURCES (Verified Origins)         │
│  ┌──────────────────────────────────────────┐  │
│  │ Resource: src/lib/utils.js               │  │
│  │ Origin: pkg:npm/lodash@4.17.21           │  │
│  │ Confidence: 0.90                         │  │
│  │ is_verified: TRUE ✓                      │  │
│  │ is_propagated: FALSE                     │  │
│  │ can_be_propagation_source: TRUE ✓        │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘

Step 3: FIND RELATED FILES

Method 1: Package Membership          Method 2: Path Pattern           Method 3: License Similarity
┌──────────────────────┐             ┌──────────────────────┐         ┌──────────────────────┐
│ Find files in same   │             │ Find files in same   │         │ Find files with      │
│ package as source    │             │ directory or similar │         │ similar licenses     │
│                      │             │ path structure       │         │                      │
│ Examples:            │             │                      │         │ Examples:            │
│ - All files in       │             │ Examples:            │         │ - Files with same    │
│   lodash package     │             │ - src/lib/*.js       │         │   license expression │
│ - Files belonging    │             │ - src/components/*   │         │ - MIT AND Apache-2.0 │
│   to same npm module │             │ - Same extension     │         │   detected           │
└──────────┬───────────┘             └──────────┬───────────┘         └──────────┬───────────┘
           │                                    │                                │
           └────────────────────────────────────┴────────────────────────────────┘
                                                │
                                                ▼
                           ┌────────────────────────────────────────┐
                           │     RELATED FILES IDENTIFIED           │
                           │                                        │
                           │  • src/lib/array.js                    │
                           │  • src/lib/object.js                   │
                           │  • src/lib/string.js                   │
                           │  • src/lib/collection.js               │
                           │                                        │
                           │  (All without existing origins)        │
                           └────────────┬───────────────────────────┘
                                        │
                                        ▼

Step 4: CALCULATE PROPAGATION CONFIDENCE
┌─────────────────────────────────────────────────────────────────┐
│  For each target file:                                           │
│                                                                  │
│  propagated_confidence = source_confidence × method_modifier     │
│                                                                  │
│  Method Modifiers:                                               │
│  • package_membership:      0.95                                 │
│  • path_pattern_same_dir:   0.85                                 │
│  • path_pattern_similar:    0.70                                 │
│  • license_similarity:      0.75                                 │
│                                                                  │
│  Example:                                                        │
│  source_confidence = 0.90                                        │
│  method = package_membership (modifier = 0.95)                   │
│  propagated_confidence = 0.90 × 0.95 = 0.855                     │
│                                                                  │
│  Max propagated confidence capped at 0.95                        │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼

Step 5: CREATE PROPAGATED ORIGINS
┌─────────────────────────────────────────────────────────────────────────┐
│  PROPAGATED ORIGIN DETERMINATION                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Resource: src/lib/array.js                                       │  │
│  │ Origin: pkg:npm/lodash@4.17.21  (from source)                    │  │
│  │ Confidence: 0.855               (calculated)                     │  │
│  │ Method: propagated_from_scancode-package-detection               │  │
│  │ is_verified: False              (needs manual verification)     │  │
│  │ is_propagated: TRUE ✓                                            │  │
│  │ propagation_source: → src/lib/utils.js                           │  │
│  │ propagation_method: package_membership                           │  │
│  │ propagation_confidence: 0.855                                    │  │
│  │ propagation_metadata: {                                          │  │
│  │   "reason": "Same package membership",                           │  │
│  │   "source_path": "src/lib/utils.js"                              │  │
│  │ }                                                                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

Step 6: TRACK PROPAGATION CHAIN
┌─────────────────────────────────────────────────────────────────┐
│  Propagation Relationship:                                       │
│                                                                  │
│  SOURCE (Manual/Detected)                                        │
│  src/lib/utils.js                                                │
│  ├─ is_propagated: False                                         │
│  ├─ is_verified: True                                            │
│  └─ can_be_propagation_source: True                              │
│                                                                  │
│          │                                                       │
│          ├──→ PROPAGATED (Package Membership)                    │
│          │    src/lib/array.js                                   │
│          │    ├─ is_propagated: True                             │
│          │    ├─ propagation_source: → utils.js                  │
│          │    └─ propagation_method: package_membership          │
│          │                                                       │
│          ├──→ PROPAGATED (Package Membership)                    │
│          │    src/lib/object.js                                  │
│          │    ├─ is_propagated: True                             │
│          │    ├─ propagation_source: → utils.js                  │
│          │    └─ propagation_method: package_membership          │
│          │                                                       │
│          └──→ PROPAGATED (Path Pattern)                          │
│               src/lib/string.js                                  │
│               ├─ is_propagated: True                             │
│               ├─ propagation_source: → utils.js                  │
│               └─ propagation_method: path_pattern_same_dir       │
│                                                                  │
│  NOTE: Propagated origins CANNOT be propagation sources         │
│        (prevents cascading errors)                               │
└─────────────────────────────────────────────────────────────────┘
```

## Usage Decision Tree

```
START: Do you have origin determinations?
│
├─ NO ──→ Run detection pipeline first
│         python manage.py add-pipeline --project X \
│             --pipeline origin_detection.DetectCodeOrigins
│         python manage.py execute --project X
│         └──→ Continue below
│
└─ YES ─→ Are they verified?
          │
          ├─ NO ──→ Manual review or auto-verify high confidence
          │         │
          │         ├─ Manual: Review in UI at /project/X/origin-determinations/
          │         │   • Check origins with confidence ≥ 0.9
          │         │   • Click "Verify" for correct ones
          │         │
          │         └─ Auto: Run command
          │              python manage.py shell
          │              >>> from scanpipe.models import *
          │              >>> CodeOriginDetermination.objects.filter(
          │              ...     codebase_resource__project__name='X',
          │              ...     detected_origin_confidence__gte=0.9
          │              ... ).update(is_verified=True)
          │
          └─ YES ─→ Ready to propagate!
                    │
                    Choose propagation method:
                    │
                    ├─ Option A: Management Command (Recommended)
                    │   python manage.py propagate-origins \
                    │       --project X \
                    │       --methods package_membership path_pattern \
                    │       --min-confidence 0.8 \
                    │       --report
                    │
                    ├─ Option B: Full Pipeline (All-in-one)
                    │   python manage.py add-pipeline --project X \
                    │       --pipeline origin_detection_with_propagation.DetectAndPropagateOrigins
                    │   python manage.py execute --project X
                    │
                    ├─ Option C: Propagation-Only Pipeline
                    │   python manage.py add-pipeline --project X \
                    │       --pipeline origin_detection_with_propagation.PropagateExistingOrigins
                    │   python manage.py execute --project X
                    │
                    └─ Option D: REST API (Programmatic)
                        curl -X POST http://localhost/api/origin-determinations/propagate/ \
                            -H "Content-Type: application/json" \
                            -d '{"project": "X", "methods": ["package_membership"]}'
```

## Method Selection Guide

```
┌─────────────────────────────────────────────────────────────────────────┐
│  WHICH PROPAGATION METHOD SHOULD YOU USE?                               │
└─────────────────────────────────────────────────────────────────────────┘

┌───────────────────────┬─────────────┬──────────────┬─────────────────┐
│ Method                │ Best For    │ Confidence   │ When to Use     │
├───────────────────────┼─────────────┼──────────────┼─────────────────┤
│ package_membership    │ Packages    │ Very High    │ Always include  │
│                       │ with clear  │ (0.95)       │ for package-    │
│                       │ boundaries  │              │ based codebases │
│                       │             │              │                 │
│ Use when:             │             │              │                 │
│ • npm, PyPI, Maven    │             │              │                 │
│ • All files in        │             │              │                 │
│   package share       │             │              │                 │
│   origin              │             │              │                 │
├───────────────────────┼─────────────┼──────────────┼─────────────────┤
│ path_pattern          │ Organized   │ High-Medium  │ Good for        │
│                       │ directory   │ (0.70-0.85)  │ structured      │
│                       │ structures  │              │ projects        │
│                       │             │              │                 │
│ Use when:             │             │              │                 │
│ • Clear module        │             │              │                 │
│   boundaries          │             │              │                 │
│ • Directory-based     │             │              │                 │
│   organization        │             │              │                 │
├───────────────────────┼─────────────┼──────────────┼─────────────────┤
│ license_similarity    │ Licensing   │ Medium       │ Use as          │
│                       │ signals are │ (0.75)       │ confirmation    │
│                       │ reliable    │              │ signal          │
│                       │             │              │                 │
│ Use when:             │             │              │                 │
│ • Strong license      │             │              │                 │
│   detection           │             │              │                 │
│ • Consistent          │             │              │                 │
│   licensing           │             │              │                 │
└───────────────────────┴─────────────┴──────────────┴─────────────────┘

RECOMMENDATION: Start with all three methods, then adjust based on results
```

## Quick Command Reference

```bash
# 1. DETECT ORIGINS ONLY
python manage.py add-pipeline --project myproject \
    --pipeline origin_detection.DetectCodeOrigins
python manage.py execute --project myproject

# 2. DETECT AND PROPAGATE (ALL-IN-ONE)
python manage.py add-pipeline --project myproject \
    --pipeline origin_detection_with_propagation.DetectAndPropagateOrigins
python manage.py execute --project myproject

# 3. PROPAGATE EXISTING (STANDALONE)
python manage.py propagate-origins --project myproject

# 4. PROPAGATE WITH OPTIONS
python manage.py propagate-origins --project myproject \
    --methods package_membership path_pattern \
    --min-confidence 0.9 \
    --max-targets 100 \
    --report

# 5. CHECK STATISTICS
python manage.py shell
>>> from scanpipe import origin_utils
>>> from scanpipe.models import Project
>>> project = Project.objects.get(name='myproject')
>>> stats = origin_utils.get_propagation_statistics(project)
>>> print(stats)

# 6. VIEW IN UI
# Navigate to: http://localhost/project/myproject/origin-determinations/
# Filter by: is_propagated = Yes

# 7. API PROPAGATION
curl -X POST http://localhost/api/origin-determinations/propagate/ \
  -H "Content-Type: application/json" \
  -d '{
    "project": "myproject",
    "methods": ["package_membership", "path_pattern"],
    "min_confidence": 0.8,
    "max_targets": 50
  }'
```

## Confidence Score Interpretation

```
┌─────────────────────────────────────────────────────────────────┐
│  CONFIDENCE SCORE RANGES                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  0.90 - 0.95  ▓▓▓▓▓▓▓▓▓▓  VERY HIGH                             │
│               • Package membership propagations                  │
│               • Can be auto-verified                             │
│               • Safe for automated decisions                     │
│                                                                  │
│  0.80 - 0.90  ▓▓▓▓▓▓▓▓░░  HIGH                                  │
│               • Same directory path patterns                     │
│               • Strong license similarity                        │
│               • Should review sample                             │
│                                                                  │
│  0.70 - 0.80  ▓▓▓▓▓▓░░░░  MEDIUM                                │
│               • Similar path patterns                            │
│               • Moderate license similarity                      │
│               • Needs manual verification                        │
│                                                                  │
│  < 0.70       ▓▓░░░░░░░░  LOW                                   │
│               • Weak signals                                     │
│               • Requires careful review                          │
│               • Consider re-propagation with higher threshold    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Troubleshooting Quick Checks

```bash
# Problem: No origins propagated
# Check 1: Do you have verified origins?
python manage.py shell
>>> from scanpipe.models import *
>>> project = Project.objects.get(name='myproject')
>>> CodeOriginDetermination.objects.filter(
...     codebase_resource__project=project,
...     is_verified=True
... ).count()
# If 0, verify some origins first!

# Check 2: Are they high enough confidence?
>>> CodeOriginDetermination.objects.filter(
...     codebase_resource__project=project,
...     is_verified=True,
...     detected_origin_confidence__gte=0.8
... ).count()

# Problem: Too many propagations
# Solution: Increase min-confidence threshold
python manage.py propagate-origins --project myproject --min-confidence 0.9

# Problem: Incorrect propagations
# Solution: Clear propagated origins and re-run
>>> CodeOriginDetermination.objects.filter(
...     codebase_resource__project=project,
...     is_propagated=True,
...     propagation_method='path_pattern'  # Clear specific method
... ).delete()

# Then re-run with adjusted parameters
python manage.py propagate-origins --project myproject \
    --methods package_membership  # Only use high-confidence method
```

## API Examples

```python
import requests

BASE_URL = 'http://localhost'

# 1. Get all propagated origins
response = requests.get(
    f'{BASE_URL}/api/origin-determinations/',
    params={'project': 'myproject', 'is_propagated': 'true'}
)
propagated = response.json()['results']

# 2. Get manually confirmed origins (good propagation sources)
response = requests.get(
    f'{BASE_URL}/api/origin-determinations/',
    params={'project': 'myproject', 'is_manually_confirmed': 'true'}
)
sources = response.json()['results']

# 3. Trigger bulk propagation
response = requests.post(
    f'{BASE_URL}/api/origin-determinations/propagate/',
    json={
        'project': 'myproject',
        'methods': ['package_membership'],
        'min_confidence': 0.8,
        'max_targets': 50
    }
)
stats = response.json()
print(f"Propagated {stats['total_propagated']} origins")

# 4. Propagate single origin
origin_uuid = 'your-origin-uuid'
response = requests.post(
    f'{BASE_URL}/api/origin-determinations/{origin_uuid}/propagate_single/',
    json={
        'methods': ['package_membership', 'path_pattern'],
        'max_targets': 50
    }
)
result = response.json()
print(f"Propagated to {result['propagated_count']} files")
```

## Integration with Existing Workflows

```
WORKFLOW 1: CI/CD Integration
├─ 1. Scan on commit
│     python manage.py create-project --name $CI_COMMIT_SHA
│     python manage.py add-input --project $CI_COMMIT_SHA --input-file source.zip
├─ 2. Detect + Propagate
│     python manage.py add-pipeline --project $CI_COMMIT_SHA \
│         --pipeline origin_detection_with_propagation.DetectAndPropagateOrigins
│     python manage.py execute --project $CI_COMMIT_SHA
├─ 3. Review propagated origins with low confidence
│     # Auto-verify high confidence, flag low for review
└─ 4. Generate report
      python manage.py report --project $CI_COMMIT_SHA

WORKFLOW 2: Manual Review Process
├─ 1. Initial detection (no propagation)
│     Run: origin_detection.DetectCodeOrigins pipeline
├─ 2. Review team verifies origins in UI
│     Team members mark origins as verified
├─ 3. Trigger propagation after verification
│     python manage.py propagate-origins --project X --report
└─ 4. Spot-check propagated origins
      Review sample of propagated origins

WORKFLOW 3: Incremental Updates
├─ 1. Initial full scan with propagation
│     (Baseline established)
├─ 2. New files added to project
│     python manage.py add-input --project X --input-file new-files.zip
├─ 3. Run propagation only (reuse existing verified origins)
│     python manage.py propagate-origins --project X
└─ 4. Review newly propagated
      Focus only on new files with propagated origins
```
