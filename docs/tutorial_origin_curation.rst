.. _tutorial_origin_curation:

Origin Curation and Determination
==================================

This tutorial provides a comprehensive guide to understanding, reviewing, and
curating code origin determinations in ScanCode.io. Origin determination helps
identify where code comes from—whether it's copied from open source packages,
vendored dependencies, or internally developed—enabling better license compliance
and provenance tracking.

.. contents:: Table of Contents
    :local:
    :depth: 3

What is Origin Determination?
------------------------------

Origin determination is the process of identifying the source and provenance of
code in your codebase. When ScanCode.io scans a project, it detects:

- **Exact matches** to known open-source packages
- **Copied files** from other codebases
- **Vendored dependencies** included directly in your repository
- **Modified code** derived from other sources
- **Original code** developed internally

Understanding code origins is critical for:

- **License compliance**: Knowing which licenses apply to your code
- **Vulnerability management**: Tracking known security issues in dependencies
- **Supply chain security**: Understanding your software composition
- **Legal due diligence**: Providing evidence during audits or acquisitions

Origin Types
^^^^^^^^^^^^

ScanCode.io supports several origin types:

**package**
    Code that matches a known package from package repositories (npm, PyPI, Maven, etc.)

**copied_from**
    Code copied from another source without modification

**vendored**
    Third-party dependencies included directly in your repository

**modified_from**
    Code derived from another source with modifications

**internal**
    Originally developed code with no external source

**unknown**
    Code whose origin cannot be determined

When to Use Origin Curation
----------------------------

Origin curation is particularly valuable when:

1. **Initial Scan Results Need Refinement**
   
   Automated detection may miss context that humans can provide. For example,
   a file might be detected as "unknown" but you know it was copied from a
   specific package version.

2. **Vendored Dependencies Are Present**
   
   Many projects include third-party code directly. Curating these origins
   ensures proper attribution and license tracking.

3. **Modified Open Source Code**
   
   When you've modified code from an open source project, documenting the
   original source maintains compliance and provenance.

4. **Large Codebases with Repeated Patterns**
   
   Using propagation features, you can confirm origins for a subset of files
   and automatically apply them to similar files.

5. **Sharing Knowledge Across Teams**
   
   Export curations to share origin determinations with other projects or
   teams via FederatedCode integration.

Prerequisites
-------------

Before starting with origin curation, ensure:

- You have a ScanCode.io project with completed scan results
- The project includes detected packages and codebase resources
- You have appropriate permissions to modify origin determinations

.. tip::
    This tutorial assumes you've already created a project and run a pipeline.
    If not, see :ref:`tutorial_web_ui_analyze_docker_image` first.

Accessing Origin Determinations
--------------------------------

Navigate to Origin Review Interface
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. From the **ScanCode.io homepage**, click on your project name
2. In the project details page, locate the **"Origin Determinations"** section
3. Click **"View Origin Determinations"** or the count of determinations

Alternatively, access directly via URL:
``http://localhost/project/{project-name}/origins/``

.. image:: images/origin-determination-list.png

The origin determination list shows:

- **File Path**: The resource being analyzed
- **Detected Origin**: Automatically detected origin type and identifier
- **Effective Origin**: The confirmed or amended origin (may differ from detected)
- **Confidence Score**: How confident the detection algorithm is (0-100%)
- **Status**: Whether the origin has been verified, amended, or needs review

Understanding the Interface
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The origin list interface provides several features:

**Filtering Options**

- **By Origin Type**: Filter by package, copied_from, vendored, etc.
- **By Verification Status**: Show only verified, unverified, or amended origins
- **By Confidence Level**: Filter low, medium, or high confidence detections
- **By Detection Method**: Filter by the method used for detection

**Sorting**

Click column headers to sort by:

- File path (alphabetical)
- Confidence score (highest/lowest first)
- Origin type
- Verification status

**Bulk Actions**

Select multiple origins using checkboxes to:

- Verify multiple origins at once
- Export selected origins
- Propagate origins to similar files

Reviewing Individual Origins
-----------------------------

Click on any file path to open the detailed origin review page:

.. image:: images/origin-determination-detail.png

The detail page shows:

Detected Origin Section
^^^^^^^^^^^^^^^^^^^^^^^

- **Origin Type**: The automatically detected type (package, vendored, etc.)
- **Identifier**: Package name, URL, or other identifier
- **Confidence Score**: Detection confidence (0-100%)
- **Detection Method**: How the origin was detected (sha1, file_name, package_match, etc.)
- **Match Details**: Specific information about what matched

**Common Detection Methods:**

- ``sha1``: Exact file hash match
- ``file_name``: Filename pattern match
- ``package_match``: Matched to package metadata
- ``directory_structure``: Matched based on directory patterns
- ``combined_evidence``: Multiple signals combined

File Information
^^^^^^^^^^^^^^^^

- **File Path**: Full path within the scanned codebase
- **File Type**: Programming language or file format
- **Size**: File size in bytes
- **SHA1**: File content hash
- **License, Copyright**: Detected license and copyright information

Related Resources
^^^^^^^^^^^^^^^^^

Shows files that are:

- **In the same directory**: Helpful for understanding context
- **Similar by hash**: Files with matching or similar content
- **Part of the same package**: If detected as part of a package

Amending Origin Determinations
-------------------------------

When the detected origin is incorrect or incomplete, you can amend it:

Step 1: Access Amendment Form
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On the origin detail page, click the **"Amend Origin"** button to reveal the
amendment form:

.. image:: images/origin-amendment-form.png

Step 2: Select Correct Origin Type
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use the **Origin Type** dropdown to select the correct type:

.. code-block:: text

    ┌─────────────────────────────┐
    │ Original Type: unknown      │
    │                            │
    │ Amend to:                   │
    │ ┌───────────────────────┐  │
    │ │ ☐ package             │  │
    │ │ ☐ copied_from         │  │
    │ │ ☑ vendored            │  │
    │ │ ☐ modified_from       │  │
    │ │ ☐ internal            │  │
    │ └───────────────────────┘  │
    └─────────────────────────────┘

Step 3: Provide Identifier
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Depending on the origin type selected, provide an appropriate identifier:

**For package origins:**

.. code-block:: text

    pkg:npm/lodash@4.17.21
    pkg:pypi/requests@2.28.0
    pkg:maven/org.apache.commons/commons-lang3@3.12.0

Use Package URL (purl) format for precise identification.

**For copied_from or modified_from:**

.. code-block:: text

    https://github.com/owner/repo/blob/main/path/to/file.js
    https://example.com/project/file.py

Provide URLs or references to the original source.

**For vendored:**

.. code-block:: text

    vendor/github.com/pkg/errors@v0.9.1
    third_party/boost-1.76.0

Specify the vendor path or package information.

**For internal:**

.. code-block:: text

    internal
    developed-in-house
    proprietary

A simple marker indicating internal development.

Step 4: Set Confidence Level
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Adjust the confidence score (0-100%) based on how certain you are:

- **90-100%**: Absolutely certain (exact match confirmed)
- **70-89%**: Very confident (strong evidence)
- **50-69%**: Moderately confident (reasonable evidence)
- **Below 50%**: Low confidence (uncertain)

Step 5: Specify Detection Method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Select or enter the method used to determine the origin:

- ``manual_review``: You reviewed and determined manually
- ``sha1``: Hash comparison confirmed the match
- ``package_metadata``: Package manifest or lock file reference
- ``git_history``: Git commit history revealed the source
- ``documentation``: README or comments indicated the source
- ``developer_knowledge``: Team member confirmed the origin

Step 6: Add Notes
^^^^^^^^^^^^^^^^^

Use the **Notes** field to document:

- Why you made this amendment
- Evidence supporting your determination
- Links to supporting documentation
- Context for future reviewers

.. code-block:: text

    This file is vendored from lodash 4.17.21. Confirmed by checking
    package.json in the original repository and comparing file hashes.
    See: https://github.com/ourorg/ourproject/issues/123

Step 7: Save Amendment
^^^^^^^^^^^^^^^^^^^^^^^

Click **"Save Amendment"** to record your changes. The system will:

- Update the effective origin to your amended values
- Record the amendment in provenance history
- Update the confidence score
- Mark the origin as amended (not auto-detected)

Verifying Origins
-----------------

Once you've reviewed an origin and confirmed it's correct (whether detected
automatically or amended), you should verify it:

How to Verify
^^^^^^^^^^^^^

1. **Individual Verification**: On the origin detail page, click **"Verify Origin"**
2. **Bulk Verification**: Select multiple origins in the list, then click **"Verify Selected"**
3. **API Verification**: Use the REST API endpoint for programmatic verification

Why Verify?
^^^^^^^^^^^

Verification indicates:

- The origin has been human-reviewed
- The determination is trustworthy
- The origin can be used for propagation
- The origin is ready for export/sharing

Verified origins are given higher priority during:

- Propagation operations
- Conflict resolution when importing curations
- Quality metrics and reporting

Origin Propagation
------------------

Propagation automatically applies confirmed origin determinations to similar or
related files, saving significant manual review time for large codebases.

How Propagation Works
^^^^^^^^^^^^^^^^^^^^^

When you propagate an origin, ScanCode.io:

1. **Finds Related Files**
   
   - Files with matching SHA1 hashes (exact duplicates)
   - Files in the same directory with similar patterns
   - Files with matching package references
   - Files with similar paths or names

2. **Checks Eligibility**
   
   - Target files must lack verified origins
   - Source origin must be verified
   - Sufficient confidence in the match (configurable threshold)

3. **Creates New Determinations**
   
   - Copies origin type and identifier
   - Adjusts confidence based on match strength
   - Records propagation in provenance
   - Links to the source origin

4. **Maintains Provenance**
   
   - Records who initiated propagation
   - Links propagated origins to source origin
   - Tracks propagation date and method

When to Use Propagation
^^^^^^^^^^^^^^^^^^^^^^^^

**Scenario 1: Vendored Dependencies**

You've confirmed one file from a vendored library is from package "lodash@4.17.21".
Propagate to apply this origin to all other lodash files in the vendor directory.

**Scenario 2: Copied Headers**

A header file is copied from an open source project. Propagate to mark all
identical header files across your codebase.

**Scenario 3: Generated Code**

Files generated from the same generator tool can be propagated once you've
confirmed the first instance.

**Scenario 4: Template Files**

Configuration templates copied from documentation can be propagated to all
instances of that template.

Triggering Propagation
^^^^^^^^^^^^^^^^^^^^^^^

**Method 1: From Origin Detail Page**

1. Navigate to a verified origin determination
2. Click **"Propagate Origin"** button
3. Review the preview of files that will be affected
4. Configure options:

   - **Match by**: SHA1 hash, directory, package reference
   - **Confidence threshold**: Minimum confidence for propagation
   - **Overwrite existing**: Whether to replace unverified origins

5. Click **"Confirm Propagation"**

.. image:: images/origin-propagation-preview.png

**Method 2: Bulk Propagation**

1. Select multiple verified origins in the list view
2. Click **"Propagate Selected"**
3. Choose propagation strategy:

   - **Conservative**: Only propagate to exact matches (SHA1)
   - **Moderate**: Include directory and pattern matches  
   - **Aggressive**: Include all related files

4. Review and confirm

**Method 3: REST API**

.. code-block:: bash

    curl -X POST http://localhost/api/origin-determinations/{uuid}/propagate/ \
         -H "Content-Type: application/json" \
         -d '{
               "match_method": "sha1",
               "confidence_threshold": 0.8,
               "overwrite_existing": false
             }'

Propagation Results
^^^^^^^^^^^^^^^^^^^

After propagation completes, you'll see:

- **Number of origins created**: How many files received the propagated origin
- **Number skipped**: Files that didn't meet criteria
- **Confidence distribution**: Breakdown of confidence scores assigned
- **Affected paths**: List of files that were updated

.. tip::
    Start with conservative propagation and verify the results before using
    more aggressive strategies.

Reviewing Propagated Origins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Propagated origins are marked with:

- **Source Link**: Reference to the origin they were propagated from
- **Propagation Date**: When propagation occurred
- **Method**: How files were matched (sha1, directory, etc.)
- **Lower Confidence**: Often slightly lower than the source origin

You can:

- Verify propagated origins after reviewing them
- Amend if the propagation was incorrect
- Trace back to the original source origin

Exporting and Sharing Curations
--------------------------------

Share your curation work with other projects, teams, or the broader community
using FederatedCode integration.

Why Export Curations?
^^^^^^^^^^^^^^^^^^^^^^

- **Share Knowledge**: Help others benefit from your review work
- **Consistency**: Apply the same curations across multiple projects
- **Collaboration**: Contribute to community curation repositories
- **Backup**: Preserve your curation work externally
- **Compliance**: Maintain records of origin determinations

Export Formats
^^^^^^^^^^^^^^

**JSON Format**

Complete, machine-readable format with all metadata:

.. code-block:: json

    {
      "metadata": {
        "schema_version": "1.0.0",
        "generator": "ScanCode.io",
        "generated_at": "2026-03-04T10:30:00Z",
        "project_name": "my-project",
        "curator": {
          "name": "Jane Doe",
          "email": "jane@example.com"
        }
      },
      "file_curations": [
        {
          "path": "src/vendor/lodash/lodash.js",
          "detected_origin": {
            "origin_type": "unknown",
            "confidence": 0.0
          },
          "amended_origin": {
            "origin_type": "vendored",
            "identifier": "pkg:npm/lodash@4.17.21",
            "confidence": 0.95,
            "method": "manual_review"
          },
          "provenance": [
            {
              "action_type": "amended",
              "actor": "jane@example.com",
              "timestamp": "2026-03-04T10:15:00Z",
              "notes": "Confirmed by package.json"
            }
          ]
        }
      ]
    }

**YAML Format**

Human-readable format, ideal for version control:

.. code-block:: yaml

    metadata:
      schema_version: '1.0.0'
      generator: ScanCode.io
      project_name: my-project
      curator:
        name: Jane Doe
        email: jane@example.com
    
    file_curations:
      - path: src/vendor/lodash/lodash.js
        amended_origin:
          origin_type: vendored
          identifier: pkg:npm/lodash@4.17.21
          confidence: 0.95
          method: manual_review
        provenance:
          - action_type: amended
            actor: jane@example.com
            notes: Confirmed by package.json

Exporting via Web UI
^^^^^^^^^^^^^^^^^^^^^

**Export All Origins**

1. Navigate to the origin determinations list
2. Click **"Export Curations"** button
3. Configure export options:

   - **Format**: JSON or YAML
   - **Include**: Verified only, all, or verified + amended
   - **Destination**: Local file or FederatedCode repository

4. Click **"Export"**

.. image:: images/origin-export-dialog.png

**Export Selected Origins**

1. Use checkboxes to select specific origins
2. Click **"Export Selected"**
3. Configure and download

Exporting via Command Line
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Export to Local File**

.. code-block:: bash

    python manage.py export-curations \
        --project my-project \
        --destination file \
        --format json \
        --output /path/to/curations.json \
        --curator-name "Jane Doe" \
        --curator-email "jane@example.com" \
        --verified-only

**Export to FederatedCode**

.. code-block:: bash

    python manage.py export-curations \
        --project my-project \
        --destination federatedcode \
        --curator-name "Jane Doe" \
        --curator-email "jane@example.com" \
        --verified-only

This will:

- Clone or update the FederatedCode repository
- Generate curation files in the standard format
- Commit changes with attribution
- Push to the remote repository

Exporting via REST API
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    curl -X POST http://localhost/api/projects/{project-uuid}/origins/export/ \
         -H "Content-Type: application/json" \
         -d '{
               "destination": "file",
               "format": "json",
               "verified_only": true,
               "curator_name": "Jane Doe",
               "curator_email": "jane@example.com"
             }'

Importing Curations
-------------------

Import curations from exported files, FederatedCode repositories, or community
sources to leverage existing review work.

Sources for Curations
^^^^^^^^^^^^^^^^^^^^^^

- **FederatedCode Repositories**: Community-maintained curation repositories
- **Internal Repositories**: Your organization's shared curations
- **Project Exports**: Curations from other ScanCode.io projects
- **Manual Curations**: Hand-crafted curation files

Importing via Web UI
^^^^^^^^^^^^^^^^^^^^^

1. Navigate to project origin determinations
2. Click **"Import Curations"** button
3. Choose import source:

   - **Upload File**: Select a JSON/YAML file from your computer
   - **URL**: Provide a URL to a curation file
   - **Git Repository**: Enter a Git repository URL

4. Configure import options:

   - **Conflict Strategy**: How to handle conflicting origins
   - **Dry Run**: Preview changes without applying them
   - **Create Conflicts**: Record conflicts for manual review

5. Click **"Import"**

.. image:: images/origin-import-dialog.png

Importing via Command Line
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    python manage.py import-curations \
        --project my-project \
        --source https://github.com/curations/pkg-npm-lodash.git \
        --conflict-strategy highest_confidence \
        --dry-run

Conflict Strategies:

- ``manual_review``: Create conflict records for manual resolution (default)
- ``keep_existing``: Always keep the current origin
- ``use_imported``: Always use the imported origin
- ``highest_confidence``: Use the origin with higher confidence
- ``highest_priority``: Use origin from higher-priority source

Importing via REST API
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    curl -X POST http://localhost/api/projects/{project-uuid}/origins/import/ \
         -H "Content-Type: application/json" \
         -d '{
               "source_url": "https://github.com/curations/pkg.git",
               "conflict_strategy": "highest_confidence",
               "dry_run": false
             }'

Handling Import Conflicts
^^^^^^^^^^^^^^^^^^^^^^^^^^

When imported curations conflict with existing ones:

**Automatic Resolution**

If you specified a conflict strategy, conflicts are resolved automatically:

.. code-block:: text

    Import Summary:
    ✓ 45 origins imported successfully
    ⚠ 5 conflicts resolved automatically (highest_confidence)
    → 2 existing origins kept (higher confidence)
    → 3 imported origins applied (higher confidence)

**Manual Resolution**

If using ``manual_review`` strategy, conflicts are recorded for review:

1. Navigate to **"Curation Conflicts"** in your project
2. Review each conflict:

   - **Existing Origin**: Current determination in your project
   - **Imported Origin**: Origin from the import source
   - **Conflict Type**: Why they conflict (type mismatch, identifier mismatch, etc.)

3. Choose resolution for each:

   - **Keep Existing**: Retain your current origin
   - **Use Imported**: Accept the imported origin
   - **Amend Both**: Create a new determination combining both

4. Click **"Resolve Conflict"**

.. image:: images/origin-conflict-resolution.png

Best Practices
--------------

For Large Codebases
^^^^^^^^^^^^^^^^^^^

**1. Start with High-Confidence Detections**

Review and verify high-confidence (>80%) origins first. These are likely correct
and can be quickly verified.

.. code-block:: bash

    # Filter to high-confidence origins
    Filter: Confidence > 80%
    Sort: Confidence (highest first)

**2. Use Sampling for Manual Review**

For codebases with thousands of files:

- Review a representative sample (10-20 files per package/directory)
- Verify these samples thoroughly
- Use propagation to apply to remaining files
- Spot-check propagated results

**3. Leverage Directory-Based Workflows**

Process files by directory structure:

- Start with ``vendor/`` or ``third_party/`` directories
- Move to ``src/`` or main code directories
- Handle test files separately (often have different origins)

**4. Prioritize by Impact**

Focus curation efforts on:

- Files with incompatible licenses
- Files in production (vs. test) code
- Files with security vulnerabilities
- Public-facing or distributed code

**5. Use Progressive Refinement**

- **First pass**: Verify obvious detections
- **Second pass**: Amend unclear origins with research
- **Third pass**: Propagate and verify propagated origins
- **Final pass**: Review low-confidence and unknown origins

For Collaborative Teams
^^^^^^^^^^^^^^^^^^^^^^^

**1. Establish Curation Guidelines**

Document your team's standards:

- When to mark something as "internal" vs. "unknown"
- Required confidence levels for verification
- Note formatting conventions
- Evidence standards for amendments

**2. Use Provenance Notes Consistently**

Always include in notes:

- Source of information (link, issue number, commit)
- Reasoning for the determination
- Any uncertainties or assumptions

**3. Regular Export and Import**

- Export curations weekly to FederatedCode
- Import community curations before starting new reviews
- Share curations across similar projects

**4. Assign Ownership**

For large projects:

- Assign directories or components to team members
- Track who verified which origins
- Review each other's work periodically

**5. Use API for Automation**

Integrate curation into your CI/CD:

.. code-block:: bash

    # Auto-verify origins that match internal patterns
    curl -X POST http://localhost/api/origin-determinations/bulk-verify/ \
         -d '{"filters": {"path_pattern": "^src/internal/.*"}}'

For Compliance and Auditing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**1. Maintain Complete Provenance**

- Never skip the notes field
- Document evidence thoroughly
- Keep links to supporting materials
- Export regularly for backup

**2. Verify Before Export**

Only export verified origins for compliance purposes:

.. code-block:: bash

    python manage.py export-curations \
        --project my-project \
        --verified-only \
        --format json \
        --output compliance-curations-$(date +%Y%m%d).json

**3. Track Quality Metrics**

Monitor:

- Percentage of files with verified origins
- Average confidence scores
- Number of unknown origins remaining
- Coverage by file type or directory

**4. Regular Review Cycles**

- Review curations quarterly
- Update when dependencies are updated
- Re-verify when code changes significantly
- Document review cycles in metadata

**5. Export for Records**

Keep exports as part of compliance records:

.. code-block:: bash

    # Create dated export for records
    python manage.py export-curations \
        --project product-v2.1.0 \
        --verified-only \
        --curator-name "Compliance Team" \
        --output exports/compliance-$(date +%Y%m%d).json

Example Workflows
-----------------

Scenario 1: Reviewing Vendored Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Context**: Your project includes vendored third-party libraries in ``vendor/``

**Workflow**:

1. **Filter to vendor directory**

   .. code-block:: text

       Path filter: ^vendor/
       Status: Unverified

2. **Identify packages**

   Look at directory structure::

       vendor/
       ├── lodash/          # npm package
       ├── requests/        # Python package
       └── commons-lang3/   # Java package

3. **Verify one file per package**

   For ``vendor/lodash/lodash.js``:
   
   - Check if detected correctly (if origin_type = "vendored" ✓)
   - If not, amend to:
     - Origin Type: ``vendored``
     - Identifier: ``pkg:npm/lodash@4.17.21``
     - Method: ``manual_review``
     - Notes: "Vendored from npm, version confirmed by package.json"
   - Click **"Verify Origin"**

4. **Propagate to package files**

   - Click **"Propagate Origin"**
   - Match by: Package reference + directory
   - Confidence threshold: 0.7
   - Review preview, confirm

5. **Spot-check results**

   - Review 3-5 propagated origins
   - Verify they're correct
   - If issues found, adjust and re-propagate

6. **Repeat for other packages**

7. **Export for reuse**

   .. code-block:: bash

       python manage.py export-curations \
           --project my-project \
           --path-filter "^vendor/" \
           --verified-only \
           --output vendor-curations.json

Scenario 2: Handling Copied Code Snippets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Context**: Developers copied utility functions from StackOverflow/blogs

**Workflow**:

1. **Identify suspected copied code**

   .. code-block:: text

       Filter: Origin Type = unknown
       Filter: File Type = (python, javascript, java)
       Sort: Confidence (lowest first)

2. **Research each file**

   For ``src/utils/string_helpers.py``:
   
   - Search for distinctive function names online
   - Check code comments for attribution
   - Ask the developer if possible

3. **Amend with source information**

   - Origin Type: ``copied_from``
   - Identifier: ``https://stackoverflow.com/questions/12345/...``
   - Confidence: 0.85
   - Method: ``manual_review``
   - Notes: "Copied from StackOverflow answer by user XYZ, CC BY-SA 4.0 license"

4. **Verify and document**

   - Click **"Verify Origin"**
   - Screenshot or save the source page
   - Update any license/copyright fields

5. **Check for duplicates**

   - Look for other files with similar code
   - Use propagation if identical copies exist

6. **Update documentation**

   Create ``ATTRIBUTIONS.md`` if needed:

   .. code-block:: markdown

       ## Third-Party Code Attributions
       
       ### src/utils/string_helpers.py
       Source: StackOverflow Question #123456
       Author: John Doe
       License: CC BY-SA 4.0
       URL: https://stackoverflow.com/questions/12345/...

Scenario 3: Processing a Large Monorepo
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Context**: 10,000+ files across multiple components and languages

**Workflow**:

**Week 1: High-Confidence Quick Wins**

1. Verify all origins with confidence > 90% (estimated 40%)

   .. code-block:: text

       Filter: Confidence > 90%
       Bulk action: Verify selected
       - Review 10 samples for accuracy
       - If >95% accurate, verify all

2. Export early results

   .. code-block:: bash

       python manage.py export-curations \
           --project monorepo \
           --verified-only \
           --output curations-week1.json

**Week 2: Vendor and Third-Party Code**

3. Process vendor directories (estimated 25%)

   - Filter: ``^vendor/``, ``^third_party/``, ``^external/``
   - Verify package-level representatives
   - Propagate within each package
   - Spot-check propagations

4. Handle node_modules (if vendored)

   - Create one verification per package
   - Use aggressive propagation
   - Verify sample from each package

**Week 3: Internal Code Patterns**

5. Mark obvious internal code (estimated 20%)

   .. code-block:: text

       Filter: Path matches ^src/company_name/
       Filter: Copyright holder = "YourCompany Inc."
       
   - Create one "internal" origin
   - Propagate to matching files
   - Verify samples

**Week 4: Research and Manual Review**

6. Handle remaining unknowns (estimated 15%)

   - Prioritize by:
     - Production vs. test code
     - License-critical files
     - Public-facing components
   
   - Assign to team members by component
   - Set daily review goals (50-75 files/person)
   - Use notes to document uncertainties

**Week 5: Quality Assurance**

7. Review propagated origins

   - Sample 5% of propagated origins
   - Check for incorrect propagations
   - Re-propagate with corrections if needed

8. Address low-confidence origins

   - Filter: Confidence < 50%, Verified = False
   - Research or mark as unknown if truly uncertain

9. Final export

   .. code-block:: bash

       python manage.py export-curations \
           --project monorepo \
           --verified-only \
           --curator-name "Compliance Team" \
           --output curations-final-$(date +%Y%m%d).json

**Metrics to Track**:

- Coverage: % of files with verified origins
- Quality: Average confidence of verified origins
- Efficiency: Files reviewed per day
- Accuracy: Sample verification success rate

Scenario 4: Contributing to Community Curations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Context**: You've curated a popular open-source package and want to share

**Workflow**:

1. **Ensure high quality**

   - All origins verified
   - Confidence scores accurate
   - Complete provenance notes
   - Tested propagation results

2. **Export for FederatedCode**

   .. code-block:: bash

       python manage.py export-curations \
           --project my-lodash-scan \
           --destination federatedcode \
           --curator-name "Your Name" \
           --curator-email "you@example.com" \
           --verified-only

3. **Review generated curation**

   Check the FederatedCode repository::

       curations/
       └── pkg-npm-lodash/
           └── 4.17.21/
               └── curations.yaml

4. **Add documentation**

   Create README in the curation folder:

   .. code-block:: markdown

       # Lodash 4.17.21 Origin Curations
       
       ## Overview
       Complete origin curations for lodash@4.17.21
       
       ## Coverage
       - 287 source files
       - 100% verified
       - All files marked as vendored or internal
       
       ## Curation Process
       Curated using ScanCode.io v36.1.0
       Compared against official npm package
       All file hashes verified
       
       ## Contact
       Questions: you@example.com

5. **Submit for review**

   - Create pull request to community repository
   - Provide context in PR description
   - Respond to review comments
   - Update based on feedback

6. **Import into new projects**

   Others can now use your curations:

   .. code-block:: bash

       python manage.py import-curations \
           --project their-project \
           --source https://github.com/curations/pkg-npm-lodash.git \
           --conflict-strategy highest_confidence

Troubleshooting
---------------

Common Issues and Solutions
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Issue: Propagation creates incorrect origins**

*Symptoms*: Files receive wrong origin type or identifier after propagation

*Solution*:

- Review the source origin carefully before propagating
- Use conservative match methods (SHA1 only)
- Increase confidence threshold
- Check related files manually before bulk propagation

**Issue: Import creates many conflicts**

*Symptoms*: Large number of conflicts when importing curations

*Solution*:

- Use ``--dry-run`` first to preview
- Try different conflict strategies
- Review conflict patterns to understand differences
- Consider if import source is compatible with your project

**Issue: Low confidence in detections**

*Symptoms*: Many origins have confidence < 50%

*Solution*:

- These often require manual review
- Research the files to understand their true origin
- Use external sources (git history, documentation)
- Consider marking as "unknown" if truly uncertain

**Issue: Cannot verify origin**

*Symptoms*: Verify button doesn't work or verification doesn't save

*Solution*:

- Check for validation errors (hover over fields)
- Ensure origin type and identifier are properly formatted
- Verify you have proper permissions
- Check browser console for errors

**Issue: Export fails**

*Symptoms*: Export times out or produces errors

*Solution*:

- Try exporting smaller subsets using path filters
- Use ``--verified-only`` to reduce size
- Check disk space for local exports
- For FederatedCode, verify Git credentials

**Issue: Propagation takes very long**

*Symptoms*: Propagation seems to hang or run indefinitely

*Solution*:

- Use more specific match criteria
- Reduce the scope (filter by directory)
- Check system resources
- Use pipeline for large propagations instead of UI

Getting Help
^^^^^^^^^^^^

- **Documentation**: Refer to :ref:`rest_api` for API details
- **GitHub Issues**: Report bugs at https://github.com/aboutcode-org/scancode.io
- **Gitter Chat**: Ask questions in the community chat
- **Mailing List**: Post to the ScanCode mailing list

Advanced Topics
---------------

Using the REST API for Automation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Automate curation workflows with the REST API:

**List Origins**

.. code-block:: python

    import requests
    
    response = requests.get(
        'http://localhost/api/origin-determinations/',
        params={
            'project': 'my-project',
            'is_verified': False,
            'confidence__gte': 0.8
        }
    )
    
    origins = response.json()['results']

**Bulk Verify**

.. code-block:: python

    origin_uuids = [o['uuid'] for o in origins]
    
    response = requests.post(
        'http://localhost/api/origin-determinations/bulk-verify/',
        json={'uuids': origin_uuids}
    )

**Propagate Programmatically**

.. code-block:: python

    for origin in high_confidence_origins:
        response = requests.post(
            f'http://localhost/api/origin-determinations/{origin["uuid"]}/propagate/',
            json={
                'match_method': 'sha1',
                'confidence_threshold': 0.7,
                'overwrite_existing': False
            }
        )
        
        results = response.json()
        print(f"Propagated to {results['origins_created']} files")

Creating Custom Pipelines
^^^^^^^^^^^^^^^^^^^^^^^^^^

Build pipelines that include origin curation steps:

.. code-block:: python

    from scanpipe.pipelines import Pipeline
    from scanpipe.pipes import origin_utils
    
    class CustomOriginPipeline(Pipeline):
        """Custom pipeline with curation automation."""
        
        @classmethod
        def steps(cls):
            return (
                cls.step1_scan_codebase,
                cls.step2_detect_origins,
                cls.step3_auto_verify_high_confidence,
                cls.step4_propagate_vendored_origins,
                cls.step5_export_curations,
            )
        
        def step3_auto_verify_high_confidence(self):
            """Auto-verify origins above 95% confidence."""
            from scanpipe.models import CodeOriginDetermination
            
            high_conf = CodeOriginDetermination.objects.filter(
                project=self.project,
                confidence__gte=0.95,
                is_verified=False
            )
            
            count = high_conf.update(is_verified=True)
            self.log(f"Auto-verified {count} high-confidence origins")
        
        def step4_propagate_vendored_origins(self):
            """Propagate verified vendored origins."""
            results = origin_utils.propagate_origins_for_project(
                project=self.project,
                match_method='sha1',
                origin_types=['vendored'],
                only_verified=True
            )
            
            self.log(f"Propagated {results['origins_created']} origins")

Integrating with CI/CD
^^^^^^^^^^^^^^^^^^^^^^^

Add origin curation to your continuous integration:

.. code-block:: yaml

    # .github/workflows/scan-and-curate.yml
    name: Scan and Curate Origins
    
    on:
      push:
        branches: [main]
    
    jobs:
      scan:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v3
          
          - name: Run ScanCode.io scan
            run: |
              scancode-io create-project my-project --input .
              scancode-io add-pipeline my-project analyze_codebase
              scancode-io execute my-project
          
          - name: Import community curations
            run: |
              scancode-io import-curations my-project \
                --source ${{ secrets.CURATIONS_REPO_URL }} \
                --conflict-strategy highest_confidence
          
          - name: Auto-propagate verified origins
            run: |
              scancode-io run-pipeline my-project auto_propagate_origins
          
          - name: Check coverage
            run: |
              coverage=$(scancode-io status my-project --json | \
                jq '.origin_coverage_percent')
              
              if (( $(echo "$coverage < 80" | bc -l) )); then
                echo "Origin coverage below 80%: $coverage%"
                exit 1
              fi
          
          - name: Export curations
            if: success()
            run: |
              scancode-io export-curations my-project \
                --verified-only \
                --destination federatedcode

Summary
-------

This tutorial covered:

✓ Understanding origin determination and its importance
✓ Accessing and navigating the origin review interface
✓ Reviewing individual origin determinations in detail
✓ Amending incorrect or incomplete origins
✓ Verifying origins after review
✓ Using propagation to apply origins to similar files
✓ Exporting curations for sharing and backup
✓ Importing community curations to leverage existing work
✓ Best practices for large codebases and collaborative workflows
✓ Example workflows for common curation scenarios

Next Steps
----------

- Apply these techniques to your own projects
- Contribute curations to community repositories
- Explore the :ref:`rest_api` for automation opportunities
- Join the community to share your curation workflows

.. tip::
    Start small with one component or directory, perfect your workflow,
    then scale to the entire codebase. Origin curation is an iterative
    process that improves with practice.

For more detailed information on the FederatedCode integration, see
:ref:`federatedcode_curation_integration`.
