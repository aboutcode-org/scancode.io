.. _origin_curation_workflows:

Origin Curation Workflows
==========================

This page provides visual workflows for common origin curation scenarios.
Each workflow shows the recommended sequence of steps.

Quick Navigation
----------------

- :ref:`workflow_initial_review`
- :ref:`workflow_vendor_libraries`
- :ref:`workflow_copied_snippets`
- :ref:`workflow_large_codebase`
- :ref:`workflow_team_collaboration`
- :ref:`workflow_compliance_audit`

.. _workflow_initial_review:

Initial Review Workflow
-----------------------

For first-time review of scan results:

.. code-block:: text

    START
      │
      ├─> 1. Run Initial Scan
      │    └─> Execute pipeline (e.g., scan_codebase)
      │
      ├─> 2. Review Scan Results
      │    ├─> Check packages detected
      │    ├─> Review resources scanned
      │    └─> Note any errors
      │
      ├─> 3. Access Origin Determinations
      │    └─> Navigate to project → Origin Determinations
      │
      ├─> 4. Filter High-Confidence Detections
      │    ├─> Filter: Confidence > 90%
      │    └─> Sort: Confidence (highest first)
      │
      ├─> 5. Quick Verification Pass
      │    ├─> Review top 10 origins
      │    ├─> Verify if correct
      │    └─> Note any issues
      │
      ├─> 6. Bulk Verify High Confidence
      │    ├─> Select all >95% confidence
      │    └─> Bulk action: Verify selected
      │
      ├─> 7. Import Community Curations
      │    ├─> Click "Import Curations"
      │    ├─> Enter community repo URL
      │    └─> Use "highest_confidence" strategy
      │
      ├─> 8. Review Medium Confidence (70-90%)
      │    ├─> Filter: Confidence 70-90%
      │    ├─> Review individually
      │    ├─> Amend if incorrect
      │    └─> Verify if correct
      │
      └─> 9. Plan Next Steps
           ├─> Count unknowns remaining
           ├─> Identify patterns (vendor dirs, etc.)
           └─> Choose specialized workflow
    
    END → Continue to specialized workflows

**Time estimate**: 1-2 hours for typical small-medium project (500-1000 files)

**Success criteria**:
- >50% of files have verified origins
- High-confidence detections validated
- Patterns identified for next phase

.. _workflow_vendor_libraries:

Vendor Libraries Workflow
--------------------------

For projects with vendored third-party code:

.. code-block:: text

    START (After initial review)
      │
      ├─> 1. Identify Vendor Directories
      │    ├─> Common patterns:
      │    │    • vendor/
      │    │    • third_party/
      │    │    • external/
      │    │    • lib/
      │    └─> Note directory structure
      │
      ├─> 2. Filter to Vendor Path
      │    ├─> Path filter: ^vendor/
      │    └─> Review directory listing
      │
      ├─> 3. Identify Packages
      │    ├─> Look for package boundaries
      │    │    vendor/
      │    │    ├── package1/
      │    │    ├── package2/
      │    │    └── package3/
      │    └─> List all packages
      │
      ├─> 4. Research First Package
      │    ├─> Check for package metadata
      │    │    • package.json
      │    │    • setup.py
      │    │    • pom.xml
      │    │    • Gemfile
      │    ├─> Search online if needed
      │    └─> Determine exact version
      │
      ├─> 5. Verify One File Per Package
      │    ├─> Select representative file
      │    │    (e.g., main entry point)
      │    ├─> Verify or amend origin:
      │    │    Type: vendored
      │    │    ID: pkg:npm/package@1.0.0
      │    │    Confidence: 0.9+
      │    └─> Add notes with evidence
      │
      ├─> 6. Propagate Within Package
      │    ├─> Click "Propagate Origin"
      │    ├─> Match by: directory + package
      │    ├─> Confidence threshold: 0.7
      │    └─> Review preview → Confirm
      │
      ├─> 7. Spot-Check Propagation
      │    ├─> Review 5-10 propagated origins
      │    ├─> Verify they're correct
      │    └─> Note any issues
      │
      ├─> 8. Repeat for Each Package
      │    └─> Go to step 4 for next package
      │
      ├─> 9. Handle Edge Cases
      │    ├─> Modified vendor files
      │    │    → Use "modified_from" type
      │    ├─> Mixed-source directories
      │    │    → Tag individually
      │    └─> Unknown vendor code
      │         → Research or mark "unknown"
      │
      └─> 10. Export Vendor Curations
           ├─> Path filter: ^vendor/
           ├─> Export to file
           └─> Save for reuse
    
    END

**Time estimate**: 2-4 hours for 10-20 vendor packages

**Success criteria**:
- All vendor directories identified
- Each package has verified origin
- Propagation covers >90% of vendor files
- Export saved for future reuse

**Checklist per package**:

☐ Package name identified  
☐ Version determined  
☐ License confirmed  
☐ Representative file verified  
☐ Propagation completed  
☐ Spot-check passed  

.. _workflow_copied_snippets:

Copied Code Snippets Workflow
------------------------------

For handling code copied from online sources:

.. code-block:: text

    START (After initial review)
      │
      ├─> 1. Identify Suspected Copies
      │    ├─> Filter: Origin type = unknown
      │    ├─> Filter: File type = source code
      │    ├─> Sort: Size (smaller files)
      │    └─> Look for:
      │         • Utility functions
      │         • Helper scripts
      │         • Configuration templates
      │
      ├─> 2. Check File Comments
      │    ├─> Look for attribution comments
      │    │    // Copied from: URL
      │    │    # Source: StackOverflow
      │    │    /* Based on: ... */
      │    └─> Note any URLs or references
      │
      ├─> 3. Search for Distinctive Code
      │    ├─> Copy unique function name
      │    ├─> Search on:
      │    │    • Google
      │    │    • GitHub
      │    │    • StackOverflow
      │    └─> Find original source
      │
      ├─> 4. Verify License Compatibility
      │    ├─> Check source license
      │    ├─> Compare with project license
      │    └─> Flag incompatibilities
      │
      ├─> 5. Amend Origin
      │    ├─> Origin type: copied_from
      │    ├─> Identifier: [Source URL]
      │    ├─> Confidence: 0.85
      │    ├─> Notes: Include:
      │    │    • Source URL
      │    │    • Author/License
      │    │    • Date copied
      │    │    • Modifications made
      │    └─> Save amendment
      │
      ├─> 6. Check for Duplicates
      │    ├─> Search for identical files
      │    │    (same SHA1)
      │    └─> If found → Propagate
      │
      ├─> 7. Document Attribution
      │    ├─> Create/update ATTRIBUTIONS.md
      │    ├─> Add entry:
      │    │    File: path/to/file.js
      │    │    Source: URL
      │    │    Author: Name
      │    │    License: Type
      │    └─> Commit to repository
      │
      ├─> 8. Verify Origin
      │    └─> Mark verified
      │
      ├─> 9. Repeat for Other Files
      │    └─> Go to step 2 for next file
      │
      └─> 10. Report License Issues
           ├─> List incompatible licenses
           ├─> Notify development team
           └─> Plan remediation
    
    END

**Time estimate**: 15-30 minutes per file

**Common sources**:
- StackOverflow (CC BY-SA license)
- GitHub snippets (various licenses)
- Tutorial/blog posts (check license)
- Official documentation examples

**Red flags**:
- No attribution comments
- Complex code with no clear origin
- License incompatibilities
- Multiple potential sources

.. _workflow_large_codebase:

Large Codebase Workflow
------------------------

For codebases with 10,000+ files:

.. code-block:: text

    START
      │
      ├─> WEEK 1: Foundation
      │    │
      │    ├─> Day 1-2: Setup & Planning
      │    │    ├─> Run comprehensive scan
      │    │    ├─> Review overall metrics
      │    │    ├─> Import community curations
      │    │    ├─> Divide by directory/team
      │    │    └─> Set goals (% coverage/week)
      │    │
      │    ├─> Day 3-4: High-Confidence Wins
      │    │    ├─> Filter: Confidence > 95%
      │    │    ├─> Sample verify (10% of set)
      │    │    ├─> If >95% accurate:
      │    │    │    └─> Bulk verify all
      │    │    └─> Export progress
      │    │
      │    └─> Day 5: Infrastructure
      │         ├─> Setup automation scripts
      │         ├─> Create curation guidelines
      │         └─> Brief team on process
      │
      ├─> WEEK 2: Vendor Code (25% estimated)
      │    │
      │    ├─> Day 1: Identify & Catalog
      │    │    ├─> List all vendor dirs
      │    │    ├─> Count files per package
      │    │    └─> Prioritize by size
      │    │
      │    ├─> Day 2-3: Large Packages
      │    │    ├─> Handle biggest packages first
      │    │    ├─> Verify + propagate each
      │    │    └─> Spot-check results
      │    │
      │    ├─> Day 4: Medium Packages
      │    │    └─> Continue verification
      │    │
      │    └─> Day 5: Small Packages & Cleanup
      │         ├─> Quick verify remaining
      │         ├─> Handle edge cases
      │         └─> Export vendor curations
      │
      ├─> WEEK 3: Internal Code (20% estimated)
      │    │
      │    ├─> Day 1: Identify Internal Patterns
      │    │    ├─> Filter by copyright holder
      │    │    ├─> Filter by path patterns
      │    │    └─> Confirm with team
      │    │
      │    ├─> Day 2-3: Mark & Propagate
      │    │    ├─> Create "internal" origins
      │    │    ├─> Propagate by directory
      │    │    └─> Verify samples
      │    │
      │    └─> Day 4-5: Edge Cases
      │         ├─> Mixed copyright files
      │         ├─> Unclear ownership
      │         └─> Consult developers
      │
      ├─> WEEK 4: Research & Manual Review
      │    │
      │    ├─> Assign by Component
      │    │    Team Member 1: Component A
      │    │    Team Member 2: Component B
      │    │    Team Member 3: Component C
      │    │
      │    ├─> Daily Goal: 50-75 files/person
      │    │    ├─> Research unknowns
      │    │    ├─> Amend & verify
      │    │    └─> Document findings
      │    │
      │    └─> Daily Sync
      │         ├─> Share discoveries
      │         ├─> Resolve questions
      │         └─> Adjust approach
      │
      └─> WEEK 5: Quality Assurance
           │
           ├─> Day 1: Audit Propagations
           │    ├─> Sample 5% of propagated
           │    ├─> Verify accuracy
           │    └─> Fix issues
           │
           ├─> Day 2: Low Confidence Review
           │    ├─> Filter: Confidence < 50%
           │    ├─> Research or mark unknown
           │    └─> Set realistic confidence
           │
           ├─> Day 3: License Analysis
           │    ├─> Review all licenses
           │    ├─> Flag incompatibilities
           │    └─> Generate report
           │
           ├─> Day 4: Documentation
           │    ├─> Create ATTRIBUTIONS.md
           │    ├─> Document process
           │    └─> Archive exports
           │
           └─> Day 5: Final Export & Metrics
                ├─> Export all verified
                ├─> Generate coverage report
                ├─> Share with stakeholders
                └─> Plan maintenance
    
    END

**Metrics to track daily**:

.. code-block:: text

    Day | Files Reviewed | Verified | Coverage % | Team Notes
    ----|---------------|----------|------------|------------
    1   | 150           | 120      | 8%         | High conf done
    2   | 200           | 180      | 20%        | Vendor started
    3   | 300           | 250      | 35%        | Props working well
    ...

**Success criteria**:
- >80% coverage (files with verified origins)
- >90% of verified origins have confidence >0.7
- All vendor code identified
- License issues documented
- Curations exported

.. _workflow_team_collaboration:

Team Collaboration Workflow
----------------------------

For distributed curation across multiple team members:

.. code-block:: text

    SETUP PHASE
      │
      ├─> 1. Establish Guidelines
      │    ├─> Create CURATION_GUIDE.md
      │    ├─> Define confidence levels
      │    ├─> Set note format standards
      │    └─> Document verification criteria
      │
      ├─> 2. Divide Responsibilities
      │    ├─> By directory structure
      │    │    Member A: src/backend/
      │    │    Member B: src/frontend/
      │    │    Member C: vendor/
      │    │
      │    ├─> By expertise
      │    │    JS expert: *.js, *.ts files
      │    │    Python expert: *.py files
      │    │    Java expert: *.java files
      │    │
      │    └─> By time
      │         Weekly rotation of unclaimed files
      │
      └─> 3. Setup Communication
           ├─> Daily standup (15 min)
           ├─> Shared documentation
           └─> Questions channel
    
    DAILY WORKFLOW (Per Team Member)
      │
      ├─> Morning (30 min)
      │    ├─> Import latest curations
      │    │    └─> Sync with team exports
      │    ├─> Review assigned section
      │    │    └─> Note challenging files
      │    └─> Plan daily work
      │         └─> Set goals (files to review)
      │
      ├─> Work Session 1 (2 hours)
      │    ├─> Review & verify obvious origins
      │    ├─> Amend incorrect detections
      │    ├─> Document in notes field:
      │    │    "Reviewed by [Name] - [Evidence]"
      │    └─> Track progress
      │
      ├─> Midday Sync (15 min)
      │    ├─> Quick standup:
      │    │    • What I completed
      │    │    • Blockers/questions
      │    │    • Plans for afternoon
      │    └─> Share discoveries
      │
      ├─> Work Session 2 (2 hours)
      │    ├─> Continue curation work
      │    ├─> Ask team for help if stuck
      │    └─> Use propagation where appropriate
      │
      └─> End of Day (30 min)
           ├─> Export your curations
           │    └─> Tag with date and name
           ├─> Update team documentation
           │    └─> Add to FINDINGS.md
           ├─> Share with team
           │    └─> Push to shared repository
           └─> Update status tracker
    
    WEEKLY WORKFLOW (Team-Wide)
      │
      ├─> Monday: Planning
      │    ├─> Review overall progress
      │    ├─> Adjust assignments if needed
      │    └─> Set week goals
      │
      ├─> Tuesday-Thursday: Curation Work
      │    └─> Follow daily workflow
      │
      └─> Friday: Review & Consolidation
           ├─> Peer review sample of curations
           ├─> Resolve conflicts
           ├─> Consolidate exports
           ├─> Update metrics dashboard
           └─> Plan next week
    
    COLLABORATION TOOLS
      │
      ├─> Shared Repository
      │    └─> Store daily exports
      │         exports/
      │         ├── 2026-03-04-alice.json
      │         ├── 2026-03-04-bob.json
      │         └── 2026-03-04-carol.json
      │
      ├─> Documentation
      │    ├─> CURATION_GUIDE.md
      │    │    • Standards
      │    │    • Examples
      │    │    • FAQs
      │    │
      │    ├─> FINDINGS.md
      │    │    • Interesting discoveries
      │    │    • Pattern notes
      │    │    • Questions resolved
      │    │
      │    └─> STATUS.md
      │         • Progress metrics
      │         • Assignments
      │         • Blockers
      │
      └─> Communication
           ├─> Daily standup
           ├─> Slack/Teams channel
           └─> Weekly retrospective
    
    END

**Team best practices**:

☐ Use consistent note formats  
☐ Document evidence for amendments  
☐ Ask questions early  
☐ Peer review each other's work  
☐ Share discoveries in team docs  
☐ Export and share daily  
☐ Track metrics together  

.. _workflow_compliance_audit:

Compliance Audit Workflow
--------------------------

For preparing origin determinations for compliance review:

.. code-block:: text

    START (4-6 weeks before audit)
      │
      ├─> PHASE 1: Assessment (Week 1)
      │    │
      │    ├─> Audit Current State
      │    │    ├─> Count total files
      │    │    ├─> % with verified origins
      │    │    ├─> % high confidence
      │    │    ├─> Unknown origins count
      │    │    └─> License conflicts
      │    │
      │    ├─> Identify Gaps
      │    │    ├─> Critical paths uncurated
      │    │    ├─> High-risk files unmarked
      │    │    ├─> Vendor attribution missing
      │    │    └─> Missing documentation
      │    │
      │    ├─> Create Action Plan
      │    │    ├─> Prioritize by risk:
      │    │    │    1. Production code
      │    │    │    2. Distributed binaries
      │    │    │    3. Public repositories
      │    │    │    4. Test/build code
      │    │    └─> Assign resources
      │    │
      │    └─> Set Standards
      │         ├─> Minimum confidence: 0.8
      │         ├─> Required evidence level
      │         ├─> Documentation format
      │         └─> Review requirements
      │
      ├─> PHASE 2: High-Priority Curation (Week 2-3)
      │    │
      │    ├─> Production Code First
      │    │    ├─> Identify production paths
      │    │    ├─> Research all unknowns
      │    │    ├─> Verify all origins
      │    │    └─> Confidence >0.9 required
      │    │
      │    ├─> Vendor Attribution
      │    │    ├─> Complete vendor inventory
      │    │    ├─> Verify all vendors
      │    │    ├─> Document versions
      │    │    └─> Check licenses
      │    │
      │    └─> License Review
      │         ├─> Map all licenses
      │         ├─> Check compatibility
      │         ├─> Document exceptions
      │         └─> Plan remediation
      │
      ├─> PHASE 3: Quality Assurance (Week 4)
      │    │
      │    ├─> Peer Review
      │    │    ├─> Sample 10% of curations
      │    │    ├─> Verify evidence quality
      │    │    ├─> Check note completeness
      │    │    └─> Validate confidence scores
      │    │
      │    ├─> Address Unknowns
      │    │    ├─> Research remaining unknowns
      │    │    ├─> Mark truly unknown as such
      │    │    ├─> Document why unknown
      │    │    └─> Flag for attention
      │    │
      │    └─> License Remediation
      │         ├─> Resolve conflicts
      │         ├─> Replace incompatible code
      │         ├─> Get legal approval
      │         └─> Document decisions
      │
      ├─> PHASE 4: Documentation (Week 5)
      │    │
      │    ├─> Generate Reports
      │    │    ├─> Coverage report
      │    │    ├─> License summary
      │    │    ├─> Vendor inventory
      │    │    └─> Risk assessment
      │    │
      │    ├─> Create Audit Package
      │    │    ├─> Export all verified curations
      │    │    │    └─> curations-audit-2026-03-04.json
      │    │    │
      │    │    ├─> ATTRIBUTIONS.md
      │    │    │    └─> Third-party attribution
      │    │    │
      │    │    ├─> LICENSE-COMPLIANCE.md
      │    │    │    ├─> License summary
      │    │    │    ├─> Compatibility analysis
      │    │    │    └─> Open issues
      │    │    │
      │    │    ├─> VENDOR-INVENTORY.md
      │    │    │    └─> Complete vendor list
      │    │    │
      │    │    └─> CURATION-PROCESS.md
      │    │         ├─> Methodology
      │    │         ├─> Standards used
      │    │         └─> Quality metrics
      │    │
      │    └─> Evidence Archive
      │         ├─> Screenshots
      │         ├─> Source links
      │         ├─> Research notes
      │         └─> Email confirmations
      │
      ├─> PHASE 5: Pre-Audit Review (Week 6)
      │    │
      │    ├─> Internal Review
      │    │    ├─> Legal review
      │    │    ├─> Engineering sign-off
      │    │    └─> Management approval
      │    │
      │    ├─> Mock Audit
      │    │    ├─> Simulate auditor questions
      │    │    ├─> Test documentation
      │    │    └─> Identify weak points
      │    │
      │    └─> Final Prep
      │         ├─> Address mock audit findings
      │         ├─> Update documentation
      │         └─> Prepare presentations
      │
      └─> AUDIT PHASE
           │
           ├─> Provide Documentation
           │    └─> Submit audit package
           │
           ├─> Answer Questions
           │    └─> Have evidence ready
           │
           └─> Post-Audit
                ├─> Address findings
                ├─> Update curations
                └─> Export final version
    
    END

**Audit Package Checklist**:

☐ All production code curated (>95%)  
☐ All vendor code identified  
☐ License summary complete  
☐ Attribution file created  
☐ Evidence documented  
☐ Confidence scores appropriate  
☐ Unknown files explained  
☐ Legal review completed  
☐ Process documentation written  
☐ Exports dated and archived  

**Quality Metrics for Audit**:

.. code-block:: text

    Metric                          | Target | Achieved
    --------------------------------|--------|----------
    Production code coverage        | >95%   | ____%
    Overall coverage                | >80%   | ____%
    Avg confidence (verified)       | >0.8   | ____
    Vendor identification           | 100%   | ____%
    License conflicts               | 0      | ____
    Unknown production files        | 0      | ____
    Documentation completeness      | 100%   | ____%

**Risk Levels**:

.. code-block:: text

    HIGH RISK (Must resolve before audit):
    • Unknown origins in production code
    • License conflicts in distributed binaries
    • Missing vendor attribution
    • Unverified GPL/AGPL code
    
    MEDIUM RISK (Should resolve):
    • Low confidence in production code
    • Incomplete vendor inventory
    • Missing documentation
    
    LOW RISK (Nice to have):
    • Unknown origins in test code
    • Incomplete build tool origins
    • Propagated origins not spot-checked

Summary
-------

Choose the workflow that matches your scenario:

- **Initial Review**: First-time curation setup
- **Vendor Libraries**: Projects with vendored code
- **Copied Snippets**: Handling online code samples
- **Large Codebase**: 10,000+ file projects
- **Team Collaboration**: Multi-person curation
- **Compliance Audit**: Preparing for legal review

All workflows can be combined and adapted. Start with Initial Review, then
add specialized workflows as needed.

For detailed instructions on each step, see:

- :ref:`tutorial_origin_curation` - Complete tutorial
- :ref:`origin_curation_quick_reference` - Quick reference guide
- :ref:`federatedcode_curation_integration` - FederatedCode details

.. tip::
    Print the relevant workflow and check off steps as you complete them!
