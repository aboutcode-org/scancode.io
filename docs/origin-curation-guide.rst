.. _origin_curation_guide:

Origin Curation Guide
=====================

This guide walks through the complete workflow for reviewing automated origin
determinations, curating relations manually, propagating trustworthy signals,
and publishing curated results to FederatedCode.

The origin workflow builds on the ``CodebaseRelation`` model and introduces
curation status, confidence levels, audit history, and deployment tooling. It
is accessible from the project detail page through the **Origin Review** button
and the dedicated navigation links in relation list views.

Prerequisites
-------------

Before starting an origin review session:

* Ensure a project scan has been completed so that ``CodebaseRelation`` entries
  are available.
* Assign yourself a staff account so curated actions are attributed to an
  authenticated user.

Origin Review Interface
-----------------------

Open ``/project/<slug>/origin-review/`` to access the origin review dashboard.
The page is built on ``PaginatedFilterView`` and provides:

* **Filters** for curation status, confidence level, curator, map type, and
  resource tags.
* **Bulk selection** checkboxes with actions to approve, reject, set pending,
  or update the confidence level for several relations at once.
* **Inline context** showing the from/to resource paths, current curation
  metadata, and a link to open the relation detail view.
* **Export controls** for JSON and XLSX snapshots of the filtered relations.

Use the filters to focus on relations that need attention (for example
``status:requires-review`` or ``curation_status:pending``) and apply bulk
actions to clear low-risk queues quickly.

Manual Curation
---------------

Select a relation from the review table to open the
``/project/<slug>/origin-curate/<uuid>/`` page. The detail view provides:

* A tab-based layout exposing essential relation fields, editable curation
  metadata, and the historical audit trail (``OriginCuration`` records).
* A form for setting the curation status (pending, approved, rejected),
  confidence level, curator notes, and for attaching supplemental comments.
* Automatically recorded metadata capturing the authenticated curator and the
  timestamp of each change.

Submit the form to update the relation. Each change creates a corresponding
``OriginCuration`` entry that captures the previous values, the curator, and
optional notes. Use the **History** tab to trace who approved or rejected a
relation over time.

Creating Relations Manually
---------------------------

Use ``/project/<slug>/origin-curate/add/`` when a relation is missing. The
``OriginCurateCreateForm`` accepts the from/to resource paths, map type,
optional curation metadata, and validates that the relation is unique inside
the project. When the curator is authenticated the initial entry is stamped
with the curator name and timestamp.

Propagation Strategies
----------------------

Propagation helps extend trustworthy origin decisions to related files. Access
``/project/<slug>/origin-propagate/?relation_uuid=<uuid>`` and choose among the
available strategies:

``Similar resources``
    Matches sibling files based on checksums, path similarity, and directory
    structure. Useful for mirrored class files or generated artifacts.

``Directory structure``
    Applies the origin determination to peers within the same directory on both
    sides, favouring mirrored project layouts.

``Package``
    Scans resources that belong to the same discovered package, respecting
    relative paths within the package contents.

``Pattern``
    Uses an explicit ``fnmatch``-style pattern (for example ``**/*.class``) to
    locate additional candidates relative to the source relation.

Each strategy exposes a preview mode. Submit with **Preview only** checked to
see the candidate list, confidence hints, and to confirm the batch before
writing. Finalising the propagation creates a ``PropagationBatch`` record,
stamps new relations with the batch UUID in ``extra_data``, and records the
curator (when authenticated) for traceability.

FederatedCode Deployment
------------------------

Once a curated set of relations is available, open
``/project/<slug>/origin-deploy/`` to prepare an export:

* Verify that FederatedCode integration is configured and that the project has
  a Package URL (``purl``).
* Choose a merge strategy: ``latest`` (newest wins), ``priority`` (project
  always overwrites), or ``manual`` (flag conflicts for later review).
* Decide whether to include the full ``OriginCuration`` history or export only
  the current relation states.
* Use preview mode to inspect the generated YAML payload before running the
  pipeline.

Starting the deployment launches the ``PublishToFederatedCode`` pipeline which
clones the target repository, writes ``origin-curations.yaml`` alongside the
scan output, optionally merges with existing data, and commits/pushes the
changes.

Best Practices
--------------

* **Triage first**: sort by map type or confidence level to clear obvious
  approvals/rejections before diving into edge cases.
* **Use notes**: capture reasoning and external references so future curators
  understand the decision path.
* **Review propagation batches**: after propagation, use the batch UUID filter
  (``extra_data__propagation_batch``) to sample the new relations and revert if
  needed.
* **Keep history**: when deploying, favour including curation history unless a
  consumer explicitly requires a trimmed dataset.

Troubleshooting
---------------

No relations listed
    Run a scan pipeline or load sample data. The review UI only displays
    existing ``CodebaseRelation`` entries.

Bulk actions disabled
    Ensure at least one checkbox is selected and that you have the necessary
    staff permissions to curate relations.

Propagation fails with anonymous user
    Log in through the admin panel or provide valid session credentials. Batch
    tracking requires an authenticated curator.

Deployment blocked by configuration
    Confirm the FederatedCode settings in ``scanpipe/settings.py`` (or the
    environment variables) and assign a ``purl`` to the project under Project
    Settings.

Related Resources
-----------------

* :ref:`origin_curation_api` for REST endpoint details.
* :ref:`origin_curation_architecture` for implementation notes.
* :ref:`tutorial_origin_curation` for a hands-on walkthrough.
