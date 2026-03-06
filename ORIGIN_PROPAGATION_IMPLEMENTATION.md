# Origin Propagation Implementation Summary

## Overview

I've implemented a comprehensive origin propagation system for ScanCode.io that takes confirmed origin determinations from reviewed files and propagates them to similar/related files using multiple signals (path patterns, package membership, and license similarity).

## What Was Implemented

### 1. Database Model Extensions

**File:** `scanpipe/models.py` (Lines 5070-5210)

**Added fields to `CodeOriginDetermination` model:**
- `is_propagated` - Boolean flag indicating if origin was propagated
- `propagation_source` - ForeignKey to source origin
- `propagation_method` - String describing the propagation method used
- `propagation_confidence` - Float confidence score for propagation
- `propagation_metadata` - JSON field for additional propagation details

**Added model properties:**
- `is_manually_confirmed` - True if verified and not propagated
- `can_be_propagation_source` - True if suitable as propagation source (verified, high confidence, not propagated)

**Migration files created:**
- `scanpipe/migrations/0001_add_origin_determination.py` - Initial origin model
- `scanpipe/migrations/0002_add_origin_propagation.py` - Propagation fields

### 2. Core Propagation Logic

**File:** `scanpipe/origin_utils.py` (Lines 268-700+)

**Finding related files:**
```python
find_similar_files_by_path(resource, max_results=50)
find_files_in_same_package(resource)
find_files_with_similar_licenses(resource, threshold=0.7)
```

**Confidence calculation:**
```python
calculate_propagation_confidence(source_origin, target_resource, method, similarity_score)
```

**Propagation by method:**
```python
propagate_origin_by_package_membership(source_origin, max_targets=100)
propagate_origin_by_path_pattern(source_origin, max_targets=100)
propagate_origin_by_license_similarity(source_origin, threshold=0.7, max_targets=100)
```

**Main coordinator:**
```python
propagate_origins_for_project(project, methods=None, min_source_confidence=0.8, max_targets_per_source=50)
```

**Statistics:**
```python
get_propagation_statistics(project)
```

### 3. Pipeline Implementation

**File:** `scanpipe/pipelines/origin_detection_with_propagation.py`

**Two pipelines:**

1. **DetectAndPropagateOrigins** - Full pipeline:
   - Runs ScanCode scanning
   - Detects origins from packages/URLs/repositories
   - Auto-verifies high-confidence origins
   - Propagates using all three methods
   - Generates reports

2. **PropagateExistingOrigins** - Lightweight:
   - Only propagates existing verified origins
   - Use when manually reviewed origins already exist

**Pipeline steps showing propagation:**
```python
mark_high_confidence_as_verified  # Auto-verify for propagation
propagate_origins_by_package      # Package membership propagation
propagate_origins_by_path         # Path pattern propagation
propagate_origins_by_license      # License similarity propagation
generate_propagation_report       # Statistics and reporting
```

### 4. Management Command

**File:** `scanpipe/management/commands/propagate-origins.py`

Command-line interface for origin propagation:

```bash
# Basic usage
python manage.py propagate-origins --project myproject

# With options
python manage.py propagate-origins --project myproject \
    --methods package_membership path_pattern license_similarity \
    --min-confidence 0.8 \
    --max-targets 50 \
    --report
```

Options:
- `--methods` - Choose propagation methods
- `--min-confidence` - Minimum source confidence (default: 0.8)
- `--max-targets` - Max targets per source (default: 50)
- `--report` - Show detailed statistics

### 5. REST API Endpoints

**File:** `scanpipe/api/views.py` (Lines 650-750)

**Added to `CodeOriginDeterminationViewSet`:**

1. **Bulk Propagation:**
   - Endpoint: `POST /api/origin-determinations/propagate/`
   - Propagates all verified origins in a project
   - Returns statistics

2. **Single Origin Propagation:**
   - Endpoint: `POST /api/origin-determinations/{uuid}/propagate_single/`
   - Propagates one specific origin
   - Returns propagated origins

### 6. API Serializer Updates

**File:** `scanpipe/api/serializers.py` (Lines 604-660)

**Added fields to `CodeOriginDeterminationSerializer`:**
- `is_manually_confirmed` (read-only)
- `can_be_propagation_source` (read-only)
- `is_propagated`
- `propagation_source_uuid` (read-only)
- `propagation_source_path` (read-only)
- `propagation_method`
- `propagation_confidence`
- `propagation_metadata`

### 7. Filtering Enhancements

**File:** `scanpipe/filters.py` (Lines 972-1100)

**Added to `OriginDeterminationFilterSet`:**
- `is_propagated` - Filter by propagation status
- `propagation_method` - Filter by method (package_membership, path_pattern, etc.)
- `is_manually_confirmed` - Filter manually confirmed origins
- `propagation_confidence_min/max` - Filter by propagation confidence range

### 8. UI Enhancements

**File:** `scanpipe/views.py` (Lines 2842-2870)

Updated `OriginDeterminationListView`:
- Added "Source" column to table
- Updated queryset to select_related propagation_source

**File:** `scanpipe/templates/scanpipe/origin_determination_list.html`

UI shows:
- Propagation badge with method name
- Propagation confidence score
- Link to source origin (on hover)
- Visual differentiation between manual/detected/propagated

### 9. Documentation

**Files created:**
- `docs/ORIGIN_PROPAGATION_GUIDE.md` - Complete user guide
- This summary document

## How to Use It

### Option 1: Run Complete Pipeline

```bash
# Create and configure project
python manage.py create-project --name myproject
python manage.py add-input --project myproject --input-file /path/to/code.zip

# Add pipeline
python manage.py add-pipeline --project myproject \
    --pipeline origin_detection_with_propagation.DetectAndPropagateOrigins

# Execute
python manage.py execute --project myproject
```

### Option 2: Propagate Existing Origins

```bash
# After manually reviewing and verifying origins in the UI
python manage.py propagate-origins --project myproject --report
```

### Option 3: Use API

```python
import requests

# Propagate all verified origins
response = requests.post(
    'http://localhost/api/origin-determinations/propagate/',
    json={
        'project': 'myproject',
        'methods': ['package_membership', 'path_pattern'],
        'min_confidence': 0.8,
        'max_targets': 50
    }
)

print(response.json())
# {'source_origins_count': 25, 'total_propagated': 150, ...}
```

### Option 4: Integrate into Custom Pipeline

```python
from scanpipe.pipelines import Pipeline
from scanpipe import origin_utils

class MyPipeline(Pipeline):
    @classmethod
    def steps(cls):
        return (
            cls.my_detection_step,
            cls.run_propagation,
        )
    
    def run_propagation(self):
        stats = origin_utils.propagate_origins_for_project(
            self.project,
            methods=['package_membership', 'path_pattern'],
            min_source_confidence=0.85,
        )
        self.project.add_info(f"Propagated {stats['total_propagated']} origins")
```

## Propagation Methods Explained

### 1. Package Membership (Highest Confidence)
- **How it works:** Files in the same package get the same origin
- **Confidence modifier:** 0.95
- **Best for:** npm, PyPI, Maven packages where all files share origin

### 2. Path Pattern (High-Medium Confidence)  
- **How it works:** Files in same directory or with similar paths
- **Confidence modifier:** 0.85 (same dir), 0.70 (similar)
- **Best for:** Modular codebases with clear directory structure

### 3. License Similarity (Medium Confidence)
- **How it works:** Files with similar license detection (Jaccard similarity)
- **Confidence modifier:** 0.75
- **Best for:** Confirming origin when license signals match

## Key Architecture Decisions

1. **Self-Referential Model**: Used ForeignKey('self') for propagation_source to maintain chain
2. **Method-Based Confidence**: Different methods have different confidence modifiers
3. **Max Confidence Cap**: Propagated origins capped at 0.95 to distinguish from manual
4. **No Re-Propagation**: Propagated origins cannot be propagation sources (prevents cascading errors)
5. **Metadata Tracking**: Full provenance tracked in propagation_metadata

## Testing the Implementation

### 1. Check Model Changes

```python
from scanpipe.models import CodeOriginDetermination

# Check new fields exist
origin = CodeOriginDetermination.objects.first()
print(origin.is_propagated)
print(origin.propagation_source)
print(origin.can_be_propagation_source)
```

### 2. Test Propagation Functions

```python
from scanpipe import origin_utils
from scanpipe.models import Project

project = Project.objects.get(name='test')

# Run propagation
stats = origin_utils.propagate_origins_for_project(project)
print(stats)

# Check statistics
prop_stats = origin_utils.get_propagation_statistics(project)
print(f"Propagated: {prop_stats['propagated_origins']}")
```

### 3. Test Management Command

```bash
python manage.py propagate-origins --project test --report
```

### 4. Test API Endpoints

```bash
# Propagate via API
curl -X POST http://localhost/api/origin-determinations/propagate/ \
  -H "Content-Type: application/json" \
  -d '{
    "project": "test",
    "methods": ["package_membership"],
    "min_confidence": 0.8
  }'
```

### 5. Test UI

1. Navigate to: `/project/test/origin-determinations/`
2. Look for "Source" column
3. Check for propagation badges
4. Filter by `is_propagated`

## File Locations Summary

```
scanpipe/
├── models.py                              # CodeOriginDetermination model (extended)
├── origin_utils.py                        # Core propagation logic (NEW FUNCTIONS)
├── views.py                               # OriginDeterminationListView (updated)
├── filters.py                             # OriginDeterminationFilterSet (extended)
├── api/
│   ├── serializers.py                     # CodeOriginDeterminationSerializer (extended)
│   └── views.py                           # CodeOriginDeterminationViewSet (new actions)
├── pipelines/
│   └── origin_detection_with_propagation.py  # NEW PIPELINE FILE
├── management/
│   └── commands/
│       └── propagate-origins.py           # NEW MANAGEMENT COMMAND
├── migrations/
│   ├── 0001_add_origin_determination.py   # Initial model
│   └── 0002_add_origin_propagation.py     # NEW MIGRATION
└── templates/
    └── scanpipe/
        └── origin_determination_list.html # Updated template

docs/
└── ORIGIN_PROPAGATION_GUIDE.md            # NEW DOCUMENTATION
```

## Next Steps

1. **Run Migrations:**
   ```bash
   python manage.py migrate scanpipe
   ```

2. **Test on Sample Project:**
   ```bash
   # Create test project
   python manage.py create-project --name test
   python manage.py add-input --project test --input-file sample.zip
   
   # Run pipeline
   python manage.py add-pipeline --project test \
       --pipeline origin_detection_with_propagation.DetectAndPropagateOrigins
   python manage.py execute --project test
   ```

3. **Review Results:**
   - Check UI at `/project/test/origin-determinations/`
   - Look for propagated origins (badge icon)
   - Verify confidence scores are appropriate

4. **Iterate:**
   - Adjust confidence thresholds if needed
   - Modify propagation methods based on your use case
   - Add custom propagation logic as needed

## Customization Points

### Adjust Confidence Modifiers

Edit `calculate_propagation_confidence()` in `origin_utils.py`:

```python
method_modifiers = {
    "package_membership": 0.95,  # Adjust these
    "path_pattern_same_dir": 0.85,
    "path_pattern_similar": 0.70,
    "license_similarity": 0.75,
    "combined_signals": 0.80,
}
```

### Add Custom Propagation Method

```python
def propagate_origin_by_custom_signal(source_origin, max_targets=100):
    """Your custom propagation logic."""
    if not source_origin.can_be_propagation_source:
        return []
    
    # Find targets using your custom logic
    target_resources = find_custom_related_files(source_origin.codebase_resource)
    
    propagated_origins = []
    for target_resource in target_resources:
        confidence = calculate_propagation_confidence(
            source_origin, target_resource, "custom_signal"
        )
        
        propagated_origin = CodeOriginDetermination.objects.create(
            codebase_resource=target_resource,
            # ... other fields
            propagation_method="custom_signal",
        )
        propagated_origins.append(propagated_origin)
    
    return propagated_origins
```

Then update `propagate_origins_for_project()` to include your method.

## Conclusion

The origin propagation system is now fully integrated into ScanCode.io at multiple levels:
- **Model layer** - Database schema and properties
- **Business logic** - Core propagation algorithms
- **Pipeline** - Automated workflow integration
- **API** - REST endpoints for programmatic access
- **CLI** - Management command for manual execution
- **UI** - Visual display and filtering

All components follow ScanCode.io conventions and integrate seamlessly with existing features.
