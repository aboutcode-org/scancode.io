# Origin Propagation in ScanCode.io

## Overview

The **Origin Propagation** feature automatically propagates confirmed origin determinations from reviewed files to similar or related files in the same codebase. This significantly reduces manual review effort by intelligently applying known origins to files that share common characteristics.

## Key Concepts

### Propagation Sources
- **Source Origin**: A verified origin determination that can be propagated to other files
- **Requirements for Source**: Must be verified, non-propagated, and have confidence ≥ 0.8
- **Manual Confirmation**: Manually reviewed and verified origins are the most trusted sources

### Propagation Targets
- Files without existing origin determinations
- Files that share characteristics with source origins
- Files identified through path patterns, package membership, or license similarity

### Propagation Methods

#### 1. Package Membership
- **Signal**: Files belonging to the same package
- **Confidence**: Very high (0.95 modifier)
- **Use Case**: All files in a package typically share the same origin
- **Example**: Files in the same npm, Maven, or PyPI package

#### 2. Path Pattern Matching
- **Signal**: Files in the same directory or with similar path structures
- **Confidence**: High for same directory (0.85), medium for similar paths (0.70)
- **Use Case**: Files in the same module or directory often share origins
- **Example**: All .js files in `src/components/widget/`

#### 3. License Similarity
- **Signal**: Files with similar license detection results
- **Confidence**: Medium-high (0.75 modifier)
- **Use Case**: Files with the same licensing likely share origins
- **Example**: Files all licensed under "MIT AND Apache-2.0"

## Database Schema

### Model Fields

The `CodeOriginDetermination` model has been extended with propagation tracking:

```python
# Propagation tracking fields
is_propagated = BooleanField()  # Whether origin was propagated
propagation_source = ForeignKey('self')  # Source origin (if propagated)
propagation_method = CharField()  # Method used for propagation
propagation_confidence = FloatField()  # Confidence of propagation
propagation_metadata = JSONField()  # Additional propagation details
```

### Model Properties

```python
is_manually_confirmed  # True if verified and not propagated
can_be_propagation_source  # True if suitable for use as source
```

## Implementation Locations

### 1. Core Logic: `scanpipe/origin_utils.py`

The main propagation utilities are in the `origin_utils.py` module:

**Key Functions:**

```python
# Finding related files
find_similar_files_by_path(resource, max_results=50)
find_files_in_same_package(resource)
find_files_with_similar_licenses(resource, threshold=0.7)

# Calculating confidence
calculate_propagation_confidence(source_origin, target_resource, method, similarity_score)

# Propagation by method
propagate_origin_by_package_membership(source_origin, max_targets=100)
propagate_origin_by_path_pattern(source_origin, max_targets=100)
propagate_origin_by_license_similarity(source_origin, threshold=0.7, max_targets=100)

# Main propagation coordinator
propagate_origins_for_project(project, methods=None, min_source_confidence=0.8, max_targets_per_source=50)

# Statistics
get_propagation_statistics(project)
```

**File Location:** `e:\scancode.io\scancode.io\scanpipe\origin_utils.py` (Lines 268-700+)

### 2. Pipeline: `scanpipe/pipelines/origin_detection_with_propagation.py`

**Two Pipeline Classes:**

#### `DetectAndPropagateOrigins`
Complete pipeline that:
1. Runs ScanCode scanning
2. Detects origins from packages, URLs, repositories
3. Automatically verifies high-confidence origins
4. Propagates using all three methods
5. Generates comprehensive reports

**Pipeline Steps:**
```python
copy_inputs_to_codebase_directory
collect_codebase_resources
run_scancode_scan
detect_origins_from_packages
detect_origins_from_urls
detect_origins_from_repositories
calculate_confidence_scores
mark_high_confidence_as_verified
propagate_origins_by_package
propagate_origins_by_path
propagate_origins_by_license
generate_propagation_report
```

#### `PropagateExistingOrigins`
Lightweight pipeline for existing data:
- Propagates already-detected origins
- Use when you've manually reviewed origins and want to propagate them

**File Location:** `e:\scancode.io\scancode.io\scanpipe\pipelines\origin_detection_with_propagation.py`

### 3. Management Command: `scanpipe/management/commands/propagate-origins.py`

Command-line interface for origin propagation:

```bash
# Basic usage
python manage.py propagate-origins --project myproject

# Specify methods
python manage.py propagate-origins --project myproject \
    --methods package_membership path_pattern

# Configure thresholds
python manage.py propagate-origins --project myproject \
    --min-confidence 0.9 \
    --max-targets 100

# Show detailed report
python manage.py propagate-origins --project myproject --report
```

**File Location:** `e:\scancode.io\scancode.io\scanpipe\management\commands\propagate-origins.py`

### 4. REST API: `scanpipe/api/views.py`

**CodeOriginDeterminationViewSet** has new actions:

#### Bulk Propagation
```http
POST /api/origin-determinations/propagate/
Content-Type: application/json

{
  "project": "myproject",
  "methods": ["package_membership", "path_pattern", "license_similarity"],
  "min_confidence": 0.8,
  "max_targets": 50
}

Response:
{
  "source_origins_count": 25,
  "total_propagated": 150,
  "propagated_by_method": {
    "package_membership": 80,
    "path_pattern": 50,
    "license_similarity": 20
  },
  "errors": []
}
```

#### Single Origin Propagation
```http
POST /api/origin-determinations/{uuid}/propagate_single/
Content-Type: application/json

{
  "methods": ["package_membership", "path_pattern"],
  "max_targets": 50
}

Response:
{
  "propagated_count": 15,
  "propagated_origins": [...]
}
```

**File Location:** `e:\scancode.io\scancode.io\scanpipe\api\views.py` (Lines 650-750+)

### 5. Serializer: `scanpipe/api/serializers.py`

**CodeOriginDeterminationSerializer** includes propagation fields:

```python
# Additional fields in serializer
is_manually_confirmed
can_be_propagation_source
is_propagated
propagation_source_uuid
propagation_source_path
propagation_method
propagation_confidence
propagation_metadata
```

**File Location:** `e:\scancode.io\scancode.io\scanpipe\api\serializers.py` (Lines 604-660)

### 6. Filters: `scanpipe/filters.py`

**OriginDeterminationFilterSet** with propagation filters:

```python
# New filter options
is_propagated  # Filter by propagation status
propagation_method  # Filter by propagation method
is_manually_confirmed  # Filter manually confirmed origins
propagation_confidence_min  # Minimum propagation confidence
propagation_confidence_max  # Maximum propagation confidence
```

**File Location:** `e:\scancode.io\scancode.io\scanpipe\filters.py` (Lines 972-1100+)

### 7. View: `scanpipe/views.py`

**OriginDeterminationListView** updated:
- Added "Source" column to display propagation info
- Enhanced queryset to include propagation source relationships
- Template displays propagation method and confidence

**File Location:** `e:\scancode.io\scancode.io\scanpipe\views.py` (Lines 2842-2870)

### 8. Template: `scanpipe/templates/scanpipe/origin_determination_list.html`

UI enhancements:
- Display propagation badge with method name
- Show propagation confidence
- Link to propagation source file
- Visual indicators for manually confirmed vs. propagated origins

**File Location:** `e:\scancode.io\scancode.io\scanpipe\templates\scanpipe\origin_determination_list.html`

### 9. Model: `scanpipe/models.py`

**CodeOriginDetermination** model with propagation fields and properties:

```python
# Propagation fields
is_propagated
propagation_source
propagation_method
propagation_confidence
propagation_metadata

# Properties
is_manually_confirmed
can_be_propagation_source
```

**File Location:** `e:\scancode.io\scancode.io\scanpipe\models.py` (Lines 5070-5210+)

### 10. Migration: `scanpipe/migrations/0002_add_origin_propagation.py`

Database migration to add propagation fields with indexes.

**File Location:** `e:\scancode.io\scancode.io\scanpipe\migrations\0002_add_origin_propagation.py`

## Usage Workflows

### Workflow 1: Automated Pipeline Run

```bash
# 1. Create project
python manage.py create-project --name myproject

# 2. Add input files
python manage.py add-input --project myproject --input-file /path/to/code.zip

# 3. Run detection and propagation pipeline
python manage.py add-pipeline --project myproject \
    --pipeline origin_detection_with_propagation.DetectAndPropagateOrigins

python manage.py execute --project myproject
```

### Workflow 2: Manual Review Then Propagation

```bash
# 1. Run initial detection only
python manage.py add-pipeline --project myproject \
    --pipeline origin_detection.DetectCodeOrigins

python manage.py execute --project myproject

# 2. Review and verify origins in UI
#    (Visit http://localhost/project/myproject/origin-determinations/)

# 3. Propagate verified origins
python manage.py propagate-origins --project myproject --report
```

### Workflow 3: API-Driven Propagation

```python
import requests

# 1. Get origins that need review
response = requests.get(
    'http://localhost/api/origin-determinations/',
    params={'project': 'myproject', 'is_verified': 'false'}
)

# 2. Verify some origins
for origin in response.json()['results'][:10]:
    if origin['detected_origin_confidence'] > 0.85:
        requests.patch(
            f"http://localhost/api/origin-determinations/{origin['uuid']}/",
            json={'is_verified': True}
        )

# 3. Run propagation
response = requests.post(
    'http://localhost/api/origin-determinations/propagate/',
    json={
        'project': 'myproject',
        'methods': ['package_membership', 'path_pattern'],
        'min_confidence': 0.8
    }
)

print(f"Propagated {response.json()['total_propagated']} origins")
```

## Confidence Calculation

Propagation confidence is calculated as:

```
propagated_confidence = base_confidence × method_modifier
```

If a similarity score is available:
```
propagated_confidence = (base_confidence × method_modifier + similarity_score) / 2
```

**Method Modifiers:**
- `package_membership`: 0.95
- `path_pattern_same_dir`: 0.85
- `path_pattern_similar`: 0.70
- `license_similarity`: 0.75
- `combined_signals`: 0.80

**Maximum propagated confidence is capped at 0.95** to distinguish from manually confirmed origins.

## Best Practices

### 1. Start with High-Confidence Sources
- Verify origins with confidence ≥ 0.9 first
- Use these as propagation sources for maximum accuracy

### 2. Use Multiple Signals
- Combine package membership + path patterns for best results
- License similarity as additional confirmation

### 3. Review Propagated Origins
- Spot-check propagated origins, especially lower confidence ones
- Fix any incorrect propagations to prevent cascading errors

### 4. Iterative Approach
```bash
# Round 1: High confidence only
python manage.py propagate-origins --project myproject --min-confidence 0.9

# Round 2: Review and verify some propagated origins

# Round 3: Medium confidence
python manage.py propagate-origins --project myproject --min-confidence 0.8
```

### 5. Monitor Statistics
```bash
# Always check the report
python manage.py propagate-origins --project myproject --report
```

Look for:
- High propagation rate (indicates good source origins)
- High average propagation confidence
- Low error count

## Monitoring and Debugging

### Get Statistics

```python
from scanpipe import origin_utils
from scanpipe.models import Project

project = Project.objects.get(name='myproject')

# Overall origin stats
stats = origin_utils.get_origin_statistics(project)
print(f"Total origins: {stats['total']}")
print(f"Verified: {stats['verified']}")

# Propagation stats
prop_stats = origin_utils.get_propagation_statistics(project)
print(f"Propagated: {prop_stats['propagated_origins']}")
print(f"Manual: {prop_stats['manual_origins']}")
print(f"Methods: {prop_stats['propagated_by_method']}")
```

### Query Propagation Chains

```python
from scanpipe.models import CodeOriginDetermination

# Find all origins propagated from a specific source
source = CodeOriginDetermination.objects.get(uuid='...')
propagated = source.propagated_to.all()

print(f"Propagated to {propagated.count()} files:")
for origin in propagated:
    print(f"  - {origin.codebase_resource.path}")
    print(f"    Method: {origin.propagation_method}")
    print(f"    Confidence: {origin.propagation_confidence}")
```

### Filter by Propagation Method

```python
# Get all package-membership propagations
package_props = CodeOriginDetermination.objects.filter(
    codebase_resource__project=project,
    is_propagated=True,
    propagation_method='package_membership'
)

# Get low-confidence propagations for review
low_conf = CodeOriginDetermination.objects.filter(
    codebase_resource__project=project,
    is_propagated=True,
    propagation_confidence__lt=0.7
)
```

## Integration Points

### Custom Pipeline Integration

Add propagation to your custom pipeline:

```python
from scanpipe.pipelines import Pipeline
from scanpipe import origin_utils

class MyCustomPipeline(Pipeline):
    @classmethod
    def steps(cls):
        return (
            cls.my_custom_step,
            cls.detect_origins,
            cls.propagate_origins,  # Add this step
        )
    
    def propagate_origins(self):
        """Propagate verified origins."""
        stats = origin_utils.propagate_origins_for_project(
            self.project,
            methods=['package_membership', 'path_pattern'],
            min_source_confidence=0.85,
        )
        
        self.project.add_info(
            f"Propagated {stats['total_propagated']} origins"
        )
```

### Webhook Integration

Trigger propagation via webhook after manual verification:

```python
# In your webhook handler
from scanpipe import origin_utils

def handle_origin_verified(project_slug, origin_uuid):
    """Called when an origin is verified via UI."""
    origin = CodeOriginDetermination.objects.get(uuid=origin_uuid)
    
    if origin.can_be_propagation_source:
        # Automatically propagate this verified origin
        propagated = origin_utils.propagate_origin_by_package_membership(
            origin, max_targets=100
        )
        
        return f"Propagated to {len(propagated)} files"
```

## Troubleshooting

### No Origins Being Propagated

**Possible causes:**
1. No verified origins (check `is_verified=True` count)
2. Source confidence too low (< 0.8)
3. All similar files already have origins

**Solution:**
```bash
# Check verified origins
python manage.py shell
>>> from scanpipe.models import *
>>> project = Project.objects.get(name='myproject')
>>> CodeOriginDetermination.objects.filter(
...     codebase_resource__project=project,
...     is_verified=True
... ).count()
```

### Low Propagation Confidence

**Possible causes:**
1. Source origins have low confidence
2. Weak similarity signals

**Solution:**
- Manually review and verify more origins
- Adjust confidence thresholds
- Use combined methods

### Incorrect Propagations

**Possible causes:**
1. False positive package membership
2. Misleading path patterns

**Solution:**
```bash
# Find and review propagated origins
>>> incorrect = CodeOriginDetermination.objects.filter(
...     uuid='...',  # The incorrect one
... )
>>> incorrect.update(
...     is_propagated=False,
...     propagation_source=None,
...     is_verified=False
... )
```

## Performance Considerations

- **Batch Size**: Use `max_targets_per_source` to limit propagation volume
- **Database Queries**: Propagation uses `select_related` for efficiency
- **Large Projects**: Consider running propagation in pipeline tasks (async)

## Future Enhancements

Potential improvements:
1. Machine learning-based similarity scoring
2. Content hash-based propagation3. Git history analysis for origin tracking
4. Automated confidence adjustment based on verification feedback
5. Propagation preview/dry-run mode
