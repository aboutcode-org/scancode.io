# Code Origin Determination Feature

This feature provides a comprehensive UI for reviewing and managing code origin determinations in ScanCode.io. It allows users to view detected origins for scanned files, review confidence scores, and amend/override automatic determinations.

## Features

### 1. **Origin Determination Model**
- **Location**: `scanpipe/models.py`
- Stores both automatically detected and user-amended origin information
- Includes confidence scoring (0.0 to 1.0)
- Supports origin types: Package, Repository, URL, Unknown
- Tracks amendment history with notes and user attribution

### 2. **REST API Endpoints**
- **Base URL**: `/api/origin-determinations/`
- **Endpoints**:
  - `GET /api/origin-determinations/` - List all origin determinations (filterable by project)
  - `GET /api/origin-determinations/{uuid}/` - Retrieve specific origin
  - `POST /api/origin-determinations/` - Create new origin determination
  - `PATCH /api/origin-determinations/{uuid}/` - Update origin determination
  - `POST /api/origin-determinations/bulk_update/` - Bulk update multiple origins
  - `POST /api/origin-determinations/bulk_verify/` - Bulk verify multiple origins

### 3. **Web UI**
- **URL**: `/project/{project-slug}/origin-determinations/`
- **Features**:
  - List view with sortable columns
  - Confidence score visualization with color coding
  - Inline editing of origin determinations
  - Bulk selection and operations
  - Verification status tracking
  - Amendment tracking with notes

### 4. **Filtering Capabilities**
- Search by resource path or origin identifier
- Filter by origin type (detected or amended)
- Filter by verification status
- Filter by amendment status
- Filter by confidence range (min/max)
- Sortable columns

## Data Model

### CodeOriginDetermination

```python
class CodeOriginDetermination(UUIDPKModel):
    codebase_resource = OneToOneField(CodebaseResource)
    
    # Detected origin (automatic)
    detected_origin_type = CharField(choices=ORIGIN_TYPE_CHOICES)
    detected_origin_identifier = CharField(max_length=2048)
    detected_origin_confidence = FloatField()  # 0.0 to 1.0
    detected_origin_method = CharField()  # e.g., "scancode", "matchcode"
    detected_origin_metadata = JSONField()
    
    # Amended origin (user override)
    amended_origin_type = CharField(choices=ORIGIN_TYPE_CHOICES)
    amended_origin_identifier = CharField(max_length=2048)
    amended_origin_notes = TextField()
    amended_by = CharField()  # Username
    
    # Status
    is_verified = BooleanField(default=False)
```

## Usage Examples

### Creating Origin Determinations Programmatically

```python
from scanpipe.models import CodebaseResource, CodeOriginDetermination

# Get a resource
resource = CodebaseResource.objects.get(path="path/to/file.js")

# Create origin determination
origin = CodeOriginDetermination.objects.create(
    codebase_resource=resource,
    detected_origin_type="package",
    detected_origin_identifier="pkg:npm/lodash@4.17.21",
    detected_origin_confidence=0.95,
    detected_origin_method="scancode",
    detected_origin_metadata={
        "match_type": "exact",
        "source": "package.json"
    }
)
```

### Amending an Origin Determination

```python
# Update with user amendment
origin.amended_origin_type = "repository"
origin.amended_origin_identifier = "https://github.com/lodash/lodash"
origin.amended_origin_notes = "Verified source repository"
origin.amended_by = "john.doe"
origin.is_verified = True
origin.save()
```

### Using the REST API

#### List Origin Determinations

```bash
curl -X GET "http://localhost:8000/api/origin-determinations/?project=my-project-slug" \
  -H "Authorization: Token YOUR_TOKEN"
```

#### Update Origin Determination

```bash
curl -X PATCH "http://localhost:8000/api/origin-determinations/{uuid}/" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amended_origin_type": "package",
    "amended_origin_identifier": "pkg:npm/lodash@4.17.21",
    "amended_origin_notes": "Correct origin verified",
    "is_verified": true
  }'
```

#### Bulk Verify Origins

```bash
curl -X POST "http://localhost:8000/api/origin-determinations/bulk_verify/" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "uuids": ["uuid1", "uuid2", "uuid3"]
  }'
```

## UI Features

### List View
1. **Checkbox Selection**: Select individual or all items for bulk operations
2. **Confidence Visualization**: Progress bars with color coding:
   - Green (≥90%): High confidence
   - Yellow (70-89%): Medium confidence
   - Red (<70%): Low confidence
3. **Status Indicators**:
   - Verified badge (green checkmark)
   - Amended badge (yellow pencil)
4. **Quick Actions**: Edit and verify buttons for each item

### Bulk Operations
1. **Verify Selected**: Mark multiple origins as verified
2. **Amend Selected**: Update multiple origins with same values
3. **Clear Selection**: Deselect all items

### Edit Modal
- Origin Type selection dropdown
- Origin Identifier text input (supports PURLs, URLs, etc.)
- Notes text area for documentation
- Verification checkbox

## Integration with Scanning Pipelines

To populate origin determinations from a scanning pipeline:

```python
from scanpipe.models import CodeOriginDetermination

def detect_origins_step(self):
    """Pipeline step to detect and store code origins."""
    for resource in self.project.codebaseresources.files():
        # Your origin detection logic here
        origin_data = detect_origin(resource)
        
        if origin_data:
            CodeOriginDetermination.objects.create(
                codebase_resource=resource,
                detected_origin_type=origin_data['type'],
                detected_origin_identifier=origin_data['identifier'],
                detected_origin_confidence=origin_data['confidence'],
                detected_origin_method='custom_detector',
                detected_origin_metadata=origin_data.get('metadata', {})
            )
```

## Database Migration

To apply the database changes:

```bash
python manage.py migrate
```

This will create the `CodeOriginDetermination` table with appropriate indexes.

## Frontend Assets

- **Template**: `scanpipe/templates/scanpipe/origin_determination_list.html`
- **JavaScript**: `scancodeio/static/origin-determination.js`
- **Styling**: Uses Bulma CSS framework (consistent with ScanCode.io design)

## Permissions and Authentication

The origin determination views follow ScanCode.io's existing authentication patterns using `ConditionalLoginRequired` mixin. API endpoints use Django REST Framework's standard authentication.

## Future Enhancements

Potential improvements for this feature:
1. Export origin determinations to CSV/JSON
2. Import bulk amendments from file
3. Origin determination history/audit log
4. Automated origin detection from multiple sources
5. Confidence score calibration settings
6. Integration with package registries for validation
7. Diff view for comparing detected vs amended origins
8. Statistics dashboard for origin coverage

## Testing

To test the feature:

1. Run the development server: `python manage.py runserver`
2. Create a project and run a scan
3. Manually create some origin determinations or via API
4. Navigate to `/project/{slug}/origin-determinations/`
5. Test filtering, sorting, editing, and bulk operations

## Support

For issues or questions about this feature, refer to:
- ScanCode.io documentation: https://scancodeio.readthedocs.io/
- GitHub repository: https://github.com/aboutcode-org/scancode.io
