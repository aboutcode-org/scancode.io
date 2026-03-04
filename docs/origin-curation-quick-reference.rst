.. _origin_curation_quick_reference:

Origin Curation Quick Reference
================================

This page provides a quick reference for common origin curation tasks.
For detailed explanations, see :ref:`tutorial_origin_curation`.

Common Tasks
------------

Verify an Origin
^^^^^^^^^^^^^^^^

**Web UI:**

1. Click on origin determination
2. Click **"Verify Origin"** button

**Command Line:**

.. code-block:: bash

    # Via API
    curl -X POST http://localhost/api/origin-determinations/{uuid}/verify/

**When to verify:**

- After reviewing and confirming an origin is correct
- Before propagating to other files
- When preparing curations for export

Amend an Origin
^^^^^^^^^^^^^^^

**Web UI:**

1. Click on origin determination
2. Click **"Amend Origin"** button
3. Select correct origin type
4. Enter identifier (e.g., ``pkg:npm/lodash@4.17.21``)
5. Set confidence (0-1)
6. Add notes explaining the amendment
7. Click **"Save Amendment"**

**Required fields:**

- Origin type: ``package``, ``copied_from``, ``vendored``, ``modified_from``, ``internal``, ``unknown``
- Identifier: Package URL, URL, or description
- Notes: Explanation with evidence

**Command Line:**

.. code-block:: bash

    curl -X PATCH http://localhost/api/origin-determinations/{uuid}/ \
         -H "Content-Type: application/json" \
         -d '{
               "amended_origin_type": "vendored",
               "amended_identifier": "pkg:npm/lodash@4.17.21",
               "amended_confidence": 0.95,
               "amended_method": "manual_review",
               "notes": "Confirmed by package.json"
             }'

Propagate Origins
^^^^^^^^^^^^^^^^^

**Web UI:**

1. Click on verified origin
2. Click **"Propagate Origin"** button
3. Choose match method:
   
   - ``sha1``: Exact file hash match (most accurate)
   - ``directory``: Files in same directory
   - ``package``: Files from same package

4. Set confidence threshold (0.5-1.0)
5. Review preview
6. Click **"Confirm Propagation"**

**Command Line:**

.. code-block:: bash

    # Propagate single origin
    curl -X POST http://localhost/api/origin-determinations/{uuid}/propagate/ \
         -H "Content-Type: application/json" \
         -d '{
               "match_method": "sha1",
               "confidence_threshold": 0.7,
               "overwrite_existing": false
             }'
    
    # Propagate all verified origins in project
    python manage.py run-pipeline my-project propagate_verified_origins

**Propagation strategies:**

- **Conservative**: SHA1 only, threshold 0.9+
- **Moderate**: SHA1 + directory, threshold 0.7-0.9
- **Aggressive**: All methods, threshold 0.5+

Export Curations
^^^^^^^^^^^^^^^^

**Command Line:**

.. code-block:: bash

    # Export to local file (JSON)
    python manage.py export-curations \
        --project my-project \
        --destination file \
        --format json \
        --output curations.json \
        --verified-only
    
    # Export to FederatedCode repository
    python manage.py export-curations \
        --project my-project \
        --destination federatedcode \
        --curator-name "Your Name" \
        --curator-email "you@example.com" \
        --verified-only

**Export options:**

- ``--format``: ``json`` or ``yaml``
- ``--verified-only``: Export only verified origins
- ``--include-propagated``: Include propagated origins
- ``--path-filter``: Export only matching paths (e.g., ``^vendor/``)

**Web UI:**

1. Navigate to origin determinations list
2. Click **"Export Curations"** button
3. Configure options
4. Click **"Export"**

Import Curations
^^^^^^^^^^^^^^^^

**Command Line:**

.. code-block:: bash

    # Import from URL
    python manage.py import-curations \
        --project my-project \
        --source https://example.com/curations.json \
        --conflict-strategy highest_confidence
    
    # Import from Git repository
    python manage.py import-curations \
        --project my-project \
        --source https://github.com/curations/pkg-npm-lodash.git \
        --conflict-strategy highest_confidence
    
    # Dry run (preview without applying)
    python manage.py import-curations \
        --project my-project \
        --source https://example.com/curations.json \
        --dry-run

**Conflict strategies:**

- ``manual_review``: Create conflict records (default)
- ``keep_existing``: Always keep current origin
- ``use_imported``: Always use imported origin
- ``highest_confidence``: Use origin with higher confidence
- ``highest_priority``: Use origin from higher-priority source

**Web UI:**

1. Navigate to origin determinations
2. Click **"Import Curations"** button
3. Choose source (upload file, URL, or Git)
4. Select conflict strategy
5. Click **"Import"**

Resolve Conflicts
^^^^^^^^^^^^^^^^^

**Command Line:**

.. code-block:: bash

    # Resolve all conflicts with a strategy
    python manage.py resolve-curation-conflicts \
        --project my-project \
        --strategy highest_confidence
    
    # Resolve specific conflict type
    python manage.py resolve-curation-conflicts \
        --project my-project \
        --conflict-type identifier_mismatch \
        --strategy use_imported
    
    # Dry run
    python manage.py resolve-curation-conflicts \
        --project my-project \
        --strategy highest_confidence \
        --dry-run

**Web UI:**

1. Navigate to **"Curation Conflicts"**
2. Click on a conflict
3. Review existing vs. imported origin
4. Choose resolution:
   
   - **Keep Existing**
   - **Use Imported**
   - **Amend Both** (create custom resolution)

5. Click **"Resolve Conflict"**

**Bulk resolution:**

1. Select multiple conflicts
2. Click bulk action dropdown
3. Choose resolution strategy
4. Confirm

Filter and Search
^^^^^^^^^^^^^^^^^

**Web UI filters:**

- **Origin Type**: package, vendored, copied_from, etc.
- **Verification Status**: verified, unverified, amended
- **Confidence**: <50%, 50-70%, 70-90%, >90%
- **Path Pattern**: Regex or glob pattern
- **Package**: Filter by package identifier

**API queries:**

.. code-block:: bash

    # High confidence unverified origins
    curl 'http://localhost/api/origin-determinations/?confidence__gte=0.9&is_verified=false'
    
    # Vendor directory origins
    curl 'http://localhost/api/origin-determinations/?path__startswith=vendor/'
    
    # Specific origin type
    curl 'http://localhost/api/origin-determinations/?effective_origin_type=vendored'

Origin Type Reference
---------------------

Package
^^^^^^^

**Description**: Code from a known package repository

**Identifier format**: Package URL (purl)

**Examples**:

.. code-block:: text

    pkg:npm/lodash@4.17.21
    pkg:pypi/requests@2.28.0
    pkg:gem/rails@7.0.0
    pkg:maven/org.apache.commons/commons-lang3@3.12.0
    pkg:cargo/serde@1.0.0

**When to use**: 

- Files match packages from npm, PyPI, Maven, etc.
- Package metadata confirms the origin
- File hashes match package contents

Vendored
^^^^^^^^

**Description**: Third-party code bundled in repository

**Identifier format**: Package URL or vendor path

**Examples**:

.. code-block:: text

    pkg:npm/lodash@4.17.21
    vendor/github.com/pkg/errors@v0.9.1
    third_party/boost-1.76.0

**When to use**:

- Dependencies copied into the repository
- Libraries checked into version control
- Third-party code without package manager

Copied From
^^^^^^^^^^^

**Description**: Code copied from another source

**Identifier format**: URL or reference to source

**Examples**:

.. code-block:: text

    https://github.com/owner/repo/blob/main/path/file.js
    https://stackoverflow.com/questions/12345/...
    https://example.com/blog/code-sample.html

**When to use**:

- Code snippets from documentation
- Examples from tutorials or blogs
- Files copied from other projects

Modified From
^^^^^^^^^^^^^

**Description**: Code derived from another source with changes

**Identifier format**: URL or package URL of original

**Examples**:

.. code-block:: text

    pkg:npm/original-package@1.0.0 (modified)
    https://github.com/original/repo (modified)

**When to use**:

- Forked code with modifications
- Adapted open source code
- Customized vendor libraries

Internal
^^^^^^^^

**Description**: Originally developed code

**Identifier format**: Simple marker

**Examples**:

.. code-block:: text

    internal
    developed-in-house
    proprietary
    original

**When to use**:

- Code written by your team
- No external source
- Proprietary development

Unknown
^^^^^^^

**Description**: Origin cannot be determined

**Identifier format**: Empty or explanation

**Examples**:

.. code-block:: text

    unknown
    origin unclear
    needs investigation

**When to use**:

- Insufficient evidence for other types
- Conflicting signals
- Needs further research

Confidence Scoring Guide
------------------------

Score Ranges
^^^^^^^^^^^^

**90-100% (Very High)**

- Exact hash match to known source
- Verified by package manifest
- Multiple confirming signals
- No conflicting evidence

**70-89% (High)**

- Strong filename + content patterns
- Package metadata suggests match
- Directory structure confirms
- Minor uncertainty

**50-69% (Medium)**

- Filename patterns match
- Partial content similarity
- Contextual clues present
- Some uncertainty

**Below 50% (Low)**

- Weak signals
- Conflicting evidence
- Multiple possibilities
- Significant uncertainty

Setting Confidence
^^^^^^^^^^^^^^^^^^

Consider:

1. **Evidence strength**:
   
   - Hash match = highest
   - Filename only = lower
   - Multiple signals = higher

2. **Verification method**:
   
   - Automated detection = as reported
   - Manual review = based on evidence quality
   - Expert knowledge = can be higher

3. **Certainty level**:
   
   - Absolutely certain = 95-100%
   - Very confident = 80-94%
   - Reasonably sure = 60-79%
   - Uncertain = <60%

**Example scenarios:**

.. code-block:: text

    # SHA1 match to npm package
    Confidence: 0.98
    Method: sha1
    
    # Filename + directory structure + comments mention source
    Confidence: 0.85
    Method: manual_review
    
    # Similar filename, no other evidence
    Confidence: 0.45
    Method: file_name

Bulk Operations
---------------

Bulk Verify
^^^^^^^^^^^

.. code-block:: bash

    # Select origins matching criteria
    curl 'http://localhost/api/origin-determinations/?confidence__gte=0.9&is_verified=false' \
         | jq -r '.results[].uuid' \
         | xargs -I {} curl -X POST http://localhost/api/origin-determinations/{}/verify/

Bulk Export by Path
^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Export only vendor directory
    python manage.py export-curations \
        --project my-project \
        --path-filter "^vendor/" \
        --output vendor-curations.json

Bulk Propagate
^^^^^^^^^^^^^^

.. code-block:: bash

    # Create a pipeline that propagates all verified origins
    python manage.py add-pipeline my-project propagate_all_verified_origins
    python manage.py execute my-project

Automation Examples
-------------------

Auto-Verify High Confidence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # In a custom pipeline or script
    from scanpipe.models import CodeOriginDetermination
    
    high_confidence = CodeOriginDetermination.objects.filter(
        project=project,
        confidence__gte=0.95,
        is_verified=False
    )
    
    count = high_confidence.update(is_verified=True)
    print(f"Auto-verified {count} origins")

Auto-Mark Internal Code
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from scanpipe.models import CodeOriginDetermination, CodebaseResource
    
    # Mark files with company copyright as internal
    company_resources = CodebaseResource.objects.filter(
        project=project,
        copyrights__icontains="MyCorp Inc."
    )
    
    for resource in company_resources:
        origin, created = CodeOriginDetermination.objects.get_or_create(
            project=project,
            codebase_resource=resource,
            defaults={
                'detected_origin_type': 'internal',
                'amended_origin_type': 'internal',
                'amended_identifier': 'internal',
                'confidence': 0.9,
                'detection_method': 'copyright_holder'
            }
        )

Daily Export Job
^^^^^^^^^^^^^^^^

.. code-block:: bash

    #!/bin/bash
    # Add to crontab: 0 2 * * * /path/to/export-daily.sh
    
    PROJECT="my-project"
    OUTPUT_DIR="/backups/curations"
    DATE=$(date +%Y%m%d)
    
    python manage.py export-curations \
        --project "$PROJECT" \
        --destination file \
        --format json \
        --output "$OUTPUT_DIR/curations-$DATE.json" \
        --verified-only \
        --curator-email "system@example.com"
    
    # Keep only last 30 days
    find "$OUTPUT_DIR" -name "curations-*.json" -mtime +30 -delete

Best Practice Checklist
------------------------

Before Propagation
^^^^^^^^^^^^^^^^^^

☐ Source origin is verified  
☐ Confidence is reasonable (>0.7)  
☐ Origin type and identifier are correct  
☐ Notes explain the determination  
☐ Preview shows expected files  

Before Export
^^^^^^^^^^^^^

☐ All exported origins are verified  
☐ Notes are complete and clear  
☐ Confidence scores are accurate  
☐ Sensitive information removed  
☐ Curator information is correct  

Before Import
^^^^^^^^^^^^^

☐ Source is trusted  
☐ Dry run reviewed  
☐ Conflict strategy chosen  
☐ Backup of current origins (export)  
☐ Team is notified  

Quality Standards
^^^^^^^^^^^^^^^^^

☐ >80% of files have origin determinations  
☐ >90% of determinations are verified  
☐ Average confidence >0.75  
☐ All vendor code identified  
☐ No unknown high-risk files  

Keyboard Shortcuts
------------------

*Web UI (if implemented):*

- ``n``: Next origin
- ``p``: Previous origin
- ``v``: Verify current origin
- ``e``: Edit/amend current origin
- ``/``: Focus search box
- ``Esc``: Close modal

API Endpoints Reference
-----------------------

List Origins
^^^^^^^^^^^^

.. code-block:: text

    GET /api/origin-determinations/
    
    Query Parameters:
    - project: Project name or UUID
    - is_verified: true/false
    - confidence__gte: Minimum confidence
    - confidence__lte: Maximum confidence
    - effective_origin_type: Origin type
    - path__startswith: Path prefix
    - path__contains: Path substring

Get Origin Detail
^^^^^^^^^^^^^^^^^

.. code-block:: text

    GET /api/origin-determinations/{uuid}/

Update Origin
^^^^^^^^^^^^^

.. code-block:: text

    PATCH /api/origin-determinations/{uuid}/
    
    Body: {
      "amended_origin_type": "vendored",
      "amended_identifier": "pkg:npm/lodash@4.17.21",
      "amended_confidence": 0.95,
      "notes": "Explanation"
    }

Verify Origin
^^^^^^^^^^^^^

.. code-block:: text

    POST /api/origin-determinations/{uuid}/verify/

Propagate Origin
^^^^^^^^^^^^^^^^

.. code-block:: text

    POST /api/origin-determinations/{uuid}/propagate/
    
    Body: {
      "match_method": "sha1",
      "confidence_threshold": 0.7,
      "overwrite_existing": false
    }

Export Curations
^^^^^^^^^^^^^^^^

.. code-block:: text

    POST /api/projects/{project-uuid}/origins/export/
    
    Body: {
      "destination": "file",
      "format": "json",
      "verified_only": true,
      "curator_name": "Your Name",
      "curator_email": "you@example.com"
    }

Import Curations
^^^^^^^^^^^^^^^^

.. code-block:: text

    POST /api/projects/{project-uuid}/origins/import/
    
    Body: {
      "source_url": "https://example.com/curations.json",
      "conflict_strategy": "highest_confidence",
      "dry_run": false
    }

Troubleshooting Quick Fixes
----------------------------

"Propagation created incorrect origins"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Delete propagated origins from last hour
    python manage.py shell
    >>> from scanpipe.models import CodeOriginDetermination, CurationProvenance
    >>> from datetime import datetime, timedelta
    >>> recent = datetime.now() - timedelta(hours=1)
    >>> provenance = CurationProvenance.objects.filter(
    ...     action_type='propagated',
    ...     action_date__gte=recent
    ... )
    >>> origin_ids = provenance.values_list('origin_determination_id', flat=True)
    >>> CodeOriginDetermination.objects.filter(id__in=origin_ids).delete()

"Too many import conflicts"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Review conflicts, then resolve en masse
    python manage.py resolve-curation-conflicts \
        --project my-project \
        --strategy keep_existing  # or use_imported

"Export takes too long"
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Export in chunks by directory
    python manage.py export-curations \
        --project my-project \
        --path-filter "^vendor/" \
        --output vendor.json
    
    python manage.py export-curations \
        --project my-project \
        --path-filter "^src/" \
        --output src.json

"Low confidence everywhere"
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Focus on verifying what you can confirm
    # Set realistic confidence based on evidence
    # Mark truly unknown files as "unknown"
    # Use notes to document uncertainty

Common CLI Patterns
-------------------

Daily Workflow
^^^^^^^^^^^^^^

.. code-block:: bash

    # 1. Import community curations
    python manage.py import-curations \
        --project my-project \
        --source https://github.com/curations/common-packages.git
    
    # 2. Auto-verify high confidence
    curl 'http://localhost/api/origin-determinations/?confidence__gte=0.95' \
         | jq -r '.results[].uuid' \
         | xargs -I {} curl -X POST http://localhost/api/origin-determinations/{}/verify/
    
    # 3. Review and verify manually (via UI)
    
    # 4. Propagate verified origins
    python manage.py run-pipeline my-project propagate_verified_origins
    
    # 5. Export at end of day
    python manage.py export-curations \
        --project my-project \
        --verified-only \
        --output curations-$(date +%Y%m%d).json

Large Codebase Strategy
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Week 1: High confidence + vendor
    python manage.py export-curations --path-filter "^vendor/" --output week1-vendor.json
    
    # Week 2: Internal code
    python manage.py export-curations --path-filter "^src/company/" --output week2-internal.json
    
    # Week 3: Remaining
    python manage.py export-curations --output week3-complete.json

For More Information
--------------------

- Full tutorial: :ref:`tutorial_origin_curation`
- FederatedCode integration: :ref:`federatedcode_curation_integration`
- REST API documentation: :ref:`rest_api`
- Command line  interface: :ref:`command_line_interface`

.. tip::
    Bookmark this page for quick reference during curation work!
