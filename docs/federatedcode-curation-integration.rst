# FederatedCode Curation Integration

## Overview

The FederatedCode Curation Integration enables collaborative sharing of origin curations across multiple ScanCode.io instances and with the broader open-source community. This system allows organizations and communities to:

- **Export** their verified origin determinations as shareable curation packages
- **Import** curations from trusted external sources
- **Resolve conflicts** when multiple curations exist for the same files
- **Track provenance** of all curations (who, when, from where)
- **Build a digital commons** of shared code origin knowledge

## Architecture

### Components

The FederatedCode Curation Integration consists of several key components:

1. **Curation Models** (`models_curation.py`)
   - `CurationSource`: External sources of curations
   - `CurationProvenance`: Full audit trail of curation changes
   - `CurationConflict`: Tracks conflicts requiring resolution
   - `CurationExport`: Records of curation exports

2. **Curation Schema** (`curation_schema.py`)
   - Standardized format for sharing curations
   - Supports file-level and package-level curations
   - Includes provenance, verification, and metadata
   - JSON/YAML serialization

3. **Utilities** (`curation_utils.py`)
   - Export curations to FederatedCode or files
   - Import curations from external sources
   - Conflict detection and resolution
   - Provenance tracking

4. **Pipelines** (`pipelines/curation_federatedcode.py`)
   - `ExportCurationsToFederatedCode`: Publish to Git repositories
   - `ImportCurationsFromFederatedCode`: Import from external sources
   - `ExportCurationsToFile`: Export to local files

5. **Management Commands**
   - `export-curations`: Export from command line
   - `import-curations`: Import from command line
   - `resolve-curation-conflicts`: Automated conflict resolution

6. **REST API Endpoints**
   - `/api/origin-determinations/export_curations/`: Export curations
   - `/api/origin-determinations/import_curations/`: Import curations
   - `/api/curation-sources/`: Manage curation sources
   - `/api/curation-conflicts/`: View and resolve conflicts

## Curation Schema

### CurationPackage Structure

```json
{
  "schema_version": "1.0.0",
  "package": {
    "purl": "pkg:npm/example@1.0.0",
    "name": "example",
    "version": "1.0.0",
    "namespace": null
  },
  "curation_metadata": {
    "created_date": "2024-01-01T00:00:00Z",
    "updated_date": "2024-01-02T00:00:00Z",
    "total_files": 100,
    "verified_files": 85,
    "propagated_files": 15,
    "curation_license": "CC0-1.0"
  },
  "source": {
    "instance_name": "ACME ScanCode.io",
    "instance_url": "https://scancode.acme.com",
    "project_name": "example-scan",
    "project_uuid": "12345678-1234-5678-1234-567812345678"
  },
  "curator": {
    "name": "Jane Doe",
    "email": "jane@acme.com",
    "organization": "ACME Corp"
  },
  "package_origin": {
    "origin_type": "repository",
    "origin_identifier": "https://github.com/example/example",
    "confidence": 1.0,
    "detection_method": "manual_amendment"
  },
  "file_curations": [
    {
      "file_path": "src/main.js",
      "file_sha256": "abc123...",
      "file_size": 1024,
      "detected_origin": {
        "origin_type": "package",
        "origin_identifier": "pkg:npm/example@1.0.0",
        "confidence": 0.9,
        "detection_method": "scancode"
      },
      "amended_origin": {
        "origin_type": "repository",
        "origin_identifier": "https://github.com/example/example",
        "confidence": 1.0,
        "detection_method": "manual_amendment"
      },
      "is_verified": true,
      "is_propagated": false,
      "provenance": [
        {
          "action_type": "created",
          "actor_name": "ScanCode.io",
          "action_date": "2024-01-01T00:00:00Z",
          "tool_name": "scancode-toolkit",
          "tool_version": "32.0.0"
        },
        {
          "action_type": "amended",
          "actor_name": "Jane Doe",
          "actor_email": "jane@acme.com",
          "action_date": "2024-01-01T10:00:00Z",
          "notes": "Verified against official repository"
        },
        {
          "action_type": "verified",
          "actor_name": "John Smith",
          "actor_email": "john@acme.com",
          "action_date": "2024-01-02T00:00:00Z",
          "notes": "Second review confirms repository origin"
        }
      ]
    }
  ]
}
```

### Schema Validation

The schema is validated during import:
- Required fields: `schema_version`, `package.purl`, `package.name`, `file_curations[].file_path`
- Origin fields: `origin_type`, `origin_identifier`, `confidence` (0-1), `detection_method`
- Provenance fields: `action_type`, `actor_name`, `action_date`

## Usage

### Exporting Curations

#### Via Management Command

```bash
# Export to FederatedCode Git repository
python manage.py export-curations \
  --project my-project \
  --destination federatedcode \
  --curator-name "Jane Doe" \
  --curator-email "jane@acme.com"

# Export to local file (JSON)
python manage.py export-curations \
  --project my-project \
  --destination file \
  --output-path /tmp/curations.json \
  --format json

# Export to local file (YAML)
python manage.py export-curations \
  --project my-project \
  --destination file \
  --format yaml

# Include all curations (not just verified)
python manage.py export-curations \
  --project my-project \
  --all-curations

# Include propagated origins
python manage.py export-curations \
  --project my-project \
  --include-propagated
```

#### Via Pipeline

```python
# Run export pipeline
from scanpipe.models import Project

project = Project.objects.get(name="my-project")
run = project.add_pipeline("ExportCurationsToFederatedCode")
run.execute()

# With custom parameters
run = project.add_pipeline(
    "ExportCurationsToFederatedCode",
    env={
        "curator_name": "Jane Doe",
        "curator_email": "jane@acme.com",
        "verified_only": True,
        "include_propagated": False,
    }
)
run.execute()
```

#### Via REST API

```bash
# Export to FederatedCode
curl -X POST http://localhost:8000/api/origin-determinations/export_curations/ \
  -H "Content-Type: application/json" \
  -d '{
    "project": "my-project",
    "destination": "federatedcode",
    "curator_name": "Jane Doe",
    "curator_email": "jane@acme.com",
    "verified_only": true,
    "include_propagated": false
  }'

# Export to file
curl -X POST http://localhost:8000/api/origin-determinations/export_curations/ \
  -H "Content-Type: application/json" \
  -d '{
    "project": "my-project",
    "destination": "file",
    "format": "json",
    "verified_only": true
  }'
```

### Importing Curations

#### Via Management Command

```bash
# Import from FederatedCode Git repository
python manage.py import-curations \
  --project my-project \
  --source-url https://github.com/curations/pkg-npm-example.git \
  --source-name "Community Curations"

# Import with conflict strategy
python manage.py import-curations \
  --project my-project \
  --source-url https://github.com/curations/pkg-npm-example.git \
  --conflict-strategy highest_confidence

# Dry run (preview without making changes)
python manage.py import-curations \
  --project my-project \
  --source-url https://example.com/curations.json \
  --dry-run

# Available conflict strategies:
# - manual_review: Create conflict records for manual resolution (default)
# - keep_existing: Keep existing curations, skip imports
# - use_imported: Replace existing with imported curations
# - highest_confidence: Use curation with higher confidence score
# - highest_priority: Use source with higher priority
```

#### Via Pipeline

```python
# Run import pipeline
from scanpipe.models import Project

project = Project.objects.get(name="my-project")
run = project.add_pipeline(
    "ImportCurationsFromFederatedCode",
    env={
        "source_url": "https://github.com/curations/pkg-npm-example.git",
        "source_name": "Community Curations",
        "conflict_strategy": "highest_confidence",
        "dry_run": False,
    }
)
run.execute()
```

#### Via REST API

```bash
curl -X POST http://localhost:8000/api/origin-determinations/import_curations/ \
  -H "Content-Type: application/json" \
  -d '{
    "project": "my-project",
    "source_url": "https://github.com/curations/pkg-npm-example.git",
    "source_name": "Community Curations",
    "conflict_strategy": "highest_confidence",
    "dry_run": false
  }'
```

### Managing Curation Sources

Curation sources represent external origins of curations and track their synchronization status.

#### Via Admin Interface

1. Navigate to `/admin/scanpipe/curationsource/`
2. Click "Add Curation Source"
3. Configure:
   - **Name**: Human-readable name
   - **Source Type**: federatedcode_git, scancodeio_api, community_service, etc.
   - **URL**: Git repository or API endpoint
   - **Priority**: Higher = preferred (0-100)
   - **Auto Sync**: Enable periodic synchronization
   - **Sync Frequency**: Hours between syncs

#### Via REST API

```bash
# List curation sources
curl http://localhost:8000/api/curation-sources/

# Create a curation source
curl -X POST http://localhost:8000/api/curation-sources/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Community Curations",
    "source_type": "federatedcode_git",
    "url": "https://github.com/curations/",
    "priority": 60,
    "is_active": true,
    "auto_sync": false
  }'

# Trigger manual sync
curl -X POST http://localhost:8000/api/curation-sources/{uuid}/sync/ \
  -H "Content-Type: application/json" \
  -d '{
    "project": "my-project",
    "conflict_strategy": "highest_confidence"
  }'
```

### Resolving Conflicts

When importing curations that differ from existing ones, conflicts are created for resolution.

#### Via Management Command

```bash
# Resolve all pending conflicts automatically
python manage.py resolve-curation-conflicts \
  --project my-project \
  --strategy highest_confidence

# Resolve specific conflict type
python manage.py resolve-curation-conflicts \
  --project my-project \
  --strategy keep_existing \
  --conflict-type origin_identifier_mismatch

# Dry run
python manage.py resolve-curation-conflicts \
  --project my-project \
  --strategy use_imported \
  --dry-run
```

#### Via Admin Interface

1. Navigate to `/admin/scanpipe/curationconflict/`
2. Filter by project and status
3. Select conflicts to resolve
4. Choose action:
   - **Resolve: Keep existing curations**
   - **Resolve: Use imported curations**
   - **Resolve: Highest confidence**
5. Or edit individual conflicts manually

#### Via REST API

```bash
# List conflicts
curl http://localhost:8000/api/curation-conflicts/?project=my-project&resolution_status=pending

# Resolve a specific conflict
curl -X POST http://localhost:8000/api/curation-conflicts/{uuid}/resolve/ \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "highest_confidence",
    "notes": "Automated resolution based on confidence scores"
  }'
```

## Conflict Resolution Strategies

### manual_review (Default)

Creates conflict records without automatic resolution. Requires human review via admin interface or API.

**Use when:**
- Quality control is critical
- Conflicts involve sensitive data
- You want to review all differences

### keep_existing

Keeps existing curations and skips imports.

**Use when:**
- Local curations are more trusted
- Preserving manual amendments is important
- Import source is lower priority

### use_imported

Replaces existing curations with imported ones.

**Use when:**
- Import source is more authoritative
- Updating from trusted upstream source
- Local curations are outdated

### highest_confidence

Compares confidence scores and uses the higher one.

**Use when:**
- Both sources are equally trusted
- Confidence scores are reliable
- Automated resolution is acceptable

### highest_priority

Uses the source with higher priority setting.

**Use when:**
- Source priority is well-established
- Multiple sources with clear hierarchy
- Organizational policy defines priorities

## Provenance Tracking

All curation changes are tracked with full provenance:

- **Action Type**: created, amended, verified, imported, merged, propagated, rejected
- **Actor**: Name and email of person/system
- **Date**: When the action occurred
- **Source**: Where the curation came from
- **Previous/New Values**: What changed
- **Notes**: Additional context
- **Metadata**: Tool versions, confidence, etc.

### Viewing Provenance

```python
from scanpipe.models import CodeOriginDetermination

origin = CodeOriginDetermination.objects.get(uuid="...")

# Get all provenance records
for prov in origin.provenance_records.all():
    print(f"{prov.action_type} by {prov.actor_name} at {prov.action_date}")
    print(f"  Source: {prov.curation_source.name if prov.curation_source else 'N/A'}")
    print(f"  Notes: {prov.notes}")
```

## Configuration

### FederatedCode Settings

Configure in `settings.py` or environment variables:

```python
# Git account URL (GitHub organization or user)
FEDERATEDCODE_GIT_ACCOUNT_URL = "https://github.com/my-org"

# Git service authentication
FEDERATEDCODE_GIT_SERVICE_TOKEN = "ghp_..."
FEDERATEDCODE_GIT_SERVICE_EMAIL = "curations@example.com"
FEDERATEDCODE_GIT_SERVICE_NAME = "Curation Bot"

# Instance identification (for provenance)
SCANCODEIO_INSTANCE_NAME = "ACME ScanCode.io"
SCANCODEIO_BASE_URL = "https://scancode.acme.com"
```

### Source Priority Guidelines

Recommended priority ranges:

- **100**: Local (this instance)
- **90-99**: Manual imports by trusted staff
- **70-89**: Community curations from verified sources
- **50-69**: Automated curations from known tools
- **30-49**: Third-party community contributions
- **0-29**: Experimental or unverified sources

## Integration with Existing Features

### Origin Determination Workflow

1. **Detect** origins using ScanCode and other tools
2. **Review** and amend in the UI
3. **Verify** curations
4. **Propagate** to similar files
5. **Export** to FederatedCode
6. **Share** with community

### Import into Workflow

1. **Import** curations from trusted sources
2. **Resolve conflicts** with existing curations
3. **Review** imported curations
4. **Verify** accuracy
5. **Use** in compliance reports

## Best Practices

### Exporting

- Export only verified curations to maintain quality
- Provide curator information for provenance
- Use descriptive project names
- Document curation methodology in metadata

### Importing

- Start with trusted sources only
- Use `dry_run` to preview changes
- Review conflicts manually for important projects
- Set appropriate conflict resolution strategies

### Source Management

- Document source trustworthiness
- Set priorities based on reliability
- Regularly review sync statistics
- Deactivate unreliable sources

### Conflict Resolution

- Use `manual_review` for critical projects
- Document resolution rationale in notes
- Track resolution patterns
- Adjust priorities based on results

## Troubleshooting

### Export Fails

**Issue**: "FederatedCode is not configured"
**Solution**: Set `FEDERATEDCODE_GIT_ACCOUNT_URL` and authentication settings

**Issue**: "No verified curations to export"
**Solution**: Verify some origin determinations first or use `--all-curations`

**Issue**: "Repository creation failed"
**Solution**: Check Git service token permissions (needs repo creation rights)

### Import Fails

**Issue**: "No curations file found in repository"
**Solution**: Ensure repository contains `curations/origins.json` or similar

**Issue**: "Validation failed"
**Solution**: Check curation schema matches expected format

**Issue**: "Resource not found"
**Solution**: Ensure project contains matching files before importing

### Conflicts Not Resolving

**Issue**: Conflicts remain after resolution
**Solution**: Check resolution strategy matches conflict type

**Issue**: "Cannot resolve without existing origin"
**Solution**: Some conflicts require manual review in admin

## API Reference

### Export Curations

`POST /api/origin-determinations/export_curations/`

**Request:**
```json
{
  "project": "string (required)",
  "destination": "federatedcode|file (default: federatedcode)",
  "format": "json|yaml (default: json)",
  "verified_only": "boolean (default: true)",
  "include_propagated": "boolean (default: false)",
  "curator_name": "string",
  "curator_email": "string"
}
```

**Response (Success):**
```json
{
  "status": "success",
  "message": "Successfully exported N curations..."
}
```

### Import Curations

`POST /api/origin-determinations/import_curations/`

**Request:**
```json
{
  "project": "string (required)",
  "source_url": "string (required)",
  "source_name": "string",
  "conflict_strategy": "manual_review|keep_existing|use_imported|highest_confidence|highest_priority (default: manual_review)",
  "dry_run": "boolean (default: false)"
}
```

**Response (Success):**
```json
{
  "status": "success",
  "dry_run": false,
  "statistics": {
    "total": 100,
    "imported": 75,
    "updated": 10,
    "skipped": 10,
    "conflicts": 5,
    "errors": 0
  }
}
```

### Resolve Conflict

`POST /api/curation-conflicts/{uuid}/resolve/`

**Request:**
```json
{
  "strategy": "keep_existing|use_imported|highest_confidence|manual_decision (required)",
  "notes": "string"
}
```

**Response:**
```json
{
  "uuid": "...",
  "resolution_status": "manual_resolved",
  "resolution_strategy": "highest_confidence",
  "resolved_date": "2024-01-01T00:00:00Z",
  ...
}
```

## Examples

### Complete Workflow Example

```bash
# 1. Scan a project
python manage.py create-project --name example-scan --input-url https://github.com/example/repo
python manage.py add-pipeline --project example-scan scan_single_package
python manage.py run --project example-scan

# 2. Review and verify origins in UI
# (Visit http://localhost:8000/project/example-scan/origin-review/)

# 3. Export verified curations
python manage.py export-curations \
  --project example-scan \
  --destination federatedcode \
  --curator-name "Jane Doe" \
  --curator-email "jane@acme.com"

# 4. Later, import curations from community
python manage.py import-curations \
  --project another-project \
  --source-url https://github.com/curations/pkg-npm-example.git \
  --conflict-strategy highest_confidence

# 5. Review any conflicts
python manage.py resolve-curation-conflicts \
  --project another-project \
  --strategy manual_review
```

## Schema Version History

### Version 1.0.0 (Current)

- Initial schema design
- File-level curations
- Provenance tracking
- Origin types: package, repository, url, file, unknown
- Confidence scores (0-1)
- Verification status
- Propagation information

## Contributing Curations

Organizations and individuals can contribute curations to the community:

1. **Create high-quality curations** with proper verification
2. **Export to FederatedCode** with full provenance
3. **Submit to community repositories** (e.g., GitHub)
4. **Document methodology** in curation metadata
5. **Maintain updates** as packages evolve

## Security Considerations

- **Authentication**: API requires authentication for import/export
- **Authorization**: Check project permissions before operations
- **Input Validation**: All imported data is validated against schema
- **Provenance**: Full audit trail of all curation sources
- **Trust Model**: Source priority system enables trust management

## License

Curations are released under CC0-1.0 (Public Domain) by default to maximize sharing and reuse. Organizations can specify different licenses in the curation metadata.
