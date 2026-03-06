# Code Origin Determination Feature - Implementation Summary

## Overview
A complete Django/React UI component for reviewing combined scan results for code origin determination in ScanCode.io.

## Files Created/Modified

### 1. Database & Models
- **`scanpipe/migrations/0001_add_origin_determination.py`**
  - Migration file to create the CodeOriginDetermination table
  - Defines indexes and constraints

- **`scanpipe/models.py`** (modified)
  - Added `CodeOriginDetermination` model class
  - Added `origin_determination_count` property to Project model
  - Includes properties: `effective_origin_type`, `effective_origin_identifier`, `is_amended`, `get_confidence_display()`

### 2. API Layer
- **`scanpipe/api/serializers.py`** (modified)
  - Added `CodeOriginDeterminationSerializer`
  - Handles serialization of origin determinations for API responses

- **`scanpipe/api/views.py`** (modified)
  - Added `CodeOriginDeterminationViewSet`
  - Endpoints: list, retrieve, create, update
  - Custom actions: `bulk_update`, `bulk_verify`

- **`scancodeio/urls.py`** (modified)
  - Registered `origin-determinations` endpoint in API router

### 3. Views & Templates
- **`scanpipe/views.py`** (modified)
  - Added `OriginDeterminationListView`
  - Implements filtering, sorting, pagination
  - Follows existing ScanCode.io patterns

- **`scanpipe/urls.py`** (modified)
  - Added route: `/project/<slug>/origin-determinations/`

- **`scanpipe/templates/scanpipe/origin_determination_list.html`** (new)
  - Main template for origin determination list view
  - Features: table view, edit modal, bulk selection UI
  - Responsive design using Bulma CSS

### 4. Filtering
- **`scanpipe/filters.py`** (modified)
  - Added `OriginDeterminationFilterSet`
  - Filters: search, origin type, verification status, confidence range
  - Sortable by multiple fields

### 5. Frontend JavaScript
- **`scancodeio/static/origin-determination.js`** (new)
  - Handles interactive features:
    - Checkbox selection (individual and bulk)
    - Modal editing
    - AJAX API calls for updates
    - Bulk operations (verify, amend)
    - Toast notifications

### 6. Integration
- **`scanpipe/templates/scanpipe/includes/project_summary_level.html`** (modified)
  - Added "Origin Determinations" link in project summary navigation
  - Shows count of origin determinations

### 7. Utilities & Helpers
- **`scanpipe/origin_utils.py`** (new)
  - Utility functions for working with origins:
    - `create_origin_from_package_data()`
    - `create_origin_from_repository()`
    - `bulk_create_origins_from_scan_results()`
    - `update_origin_confidence()`
    - `get_origins_by_confidence()`
    - `verify_origins_by_type()`
    - `get_origin_statistics()`

### 8. Sample Pipeline
- **`scanpipe/pipelines/origin_detection.py`** (new)
  - Reference implementation showing how to integrate origin detection
  - Example pipeline with multiple detection methods:
    - Package-based detection
    - URL-based detection
    - Repository association
    - Confidence score calculation

### 9. Documentation
- **`docs/ORIGIN_DETERMINATION_FEATURE.md`** (new)
  - Comprehensive feature documentation
  - Usage examples (Python and REST API)
  - Data model details
  - UI feature descriptions
  - Integration guide

## Key Features Implemented

✅ **Display List of Scanned Files with Origins**
- Sortable, filterable table view
- Shows detected and amended origins
- Confidence score visualization

✅ **Drill-down into Individual File Results**
- Link to resource detail pages
- Shows all origin data including metadata

✅ **Inline Editing to Amend/Override Origins**
- Modal-based editing interface
- Can override detected origins with user amendments
- Notes field for documentation

✅ **Confidence Scores Display**
- Visual progress bars with color coding
- High/Medium/Low categorization
- Numeric display

✅ **Bulk Selection and Batch Amendment**
- Select all / individual selection
- Bulk verify operation
- Bulk amend operation
- Clear selection

✅ **REST API Endpoints**
- Full CRUD operations
- Bulk operations support
- Project filtering

## Database Schema

```sql
CodeOriginDetermination:
  - uuid (PrimaryKey, UUID)
  - codebase_resource_id (ForeignKey, OneToOne)
  - created_date (DateTime)
  - updated_date (DateTime)
  - detected_origin_type (CharField, indexed)
  - detected_origin_identifier (CharField)
  - detected_origin_confidence (FloatField, indexed)
  - detected_origin_method (CharField)
  - detected_origin_metadata (JSONField)
  - amended_origin_type (CharField, indexed)
  - amended_origin_identifier (CharField)
  - amended_origin_notes (TextField)
  - amended_by (CharField)
  - is_verified (BooleanField, indexed)
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/origin-determinations/` | List all origins (filterable by project) |
| GET | `/api/origin-determinations/{uuid}/` | Get specific origin |
| POST | `/api/origin-determinations/` | Create new origin |
| PATCH | `/api/origin-determinations/{uuid}/` | Update origin |
| POST | `/api/origin-determinations/bulk_update/` | Bulk update multiple origins |
| POST | `/api/origin-determinations/bulk_verify/` | Bulk verify multiple origins |

## Usage Flow

1. **Data Population**:
   - Run a scanning pipeline that detects code origins
   - Use `origin_utils` functions to create origin determinations
   - Or populate via API

2. **Review in UI**:
   - Navigate to project's "Origin Determinations" page
   - Filter/sort to focus on specific items
   - Review confidence scores and detected origins

3. **Amendment**:
   - Click "Edit" on individual items or select multiple
   - Update origin type and identifier
   - Add notes explaining the amendment
   - Mark as verified

4. **Bulk Operations**:
   - Select multiple items using checkboxes
   - Verify all selected items at once
   - Or bulk amend with common values

## Integration Steps

To integrate this feature into your ScanCode.io installation:

1. **Apply Migration**:
   ```bash
   python manage.py migrate
   ```

2. **Static Files**:
   ```bash
   python manage.py collectstatic
   ```

3. **Restart Server**:
   ```bash
   python manage.py runserver
   ```

4. **Populate Data**:
   - Use the sample pipeline or utility functions
   - Or create via API/admin interface

5. **Access UI**:
   - Navigate to any project
   - Click "Origin Determinations" in the summary level
   - Or go to `/project/{slug}/origin-determinations/`

## Next Steps / Future Enhancements

- [ ] Export origin determinations to CSV/XLSX
- [ ] Import bulk amendments from file
- [ ] History/audit log for amendments
- [ ] Automated confidence calibration
- [ ] Integration with package registries for validation
- [ ] Statistics dashboard
- [ ] Diff view for comparing origins
- [ ] Integration with DejaCode or other systems

## Testing Checklist

- [ ] Create project and add resources
- [ ] Create origin determinations via API
- [ ] View origin list in UI
- [ ] Test filtering (type, confidence, verified, amended)
- [ ] Test sorting by columns
- [ ] Edit individual origin
- [ ] Verify individual origin
- [ ] Select multiple items
- [ ] Bulk verify selected
- [ ] Bulk amend selected
- [ ] Clear selection
- [ ] Check pagination
- [ ] Test API endpoints directly
- [ ] Verify database indexes are created

## Notes

- The feature follows existing ScanCode.io patterns for consistency
- Uses Bulma CSS framework (already in ScanCode.io)
- JavaScript uses vanilla JS (no additional frameworks required)
- API uses Django REST Framework standard patterns
- All code includes proper licensing headers (Apache 2.0)
- Confidence scores range from 0.0 to 1.0
- Origin types: package, repository, url, unknown
- Amendments preserve original detected values

## Support

For questions or issues, refer to the main documentation or create an issue in the GitHub repository.
