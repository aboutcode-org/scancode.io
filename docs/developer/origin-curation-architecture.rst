.. _origin_curation_architecture:

Origin Curation Architecture
============================

This document describes the internal architecture that powers the origin
review, curation, propagation, and deployment features. It targets developers
who need to extend the workflow, integrate custom propagation strategies, or
adjust how curations are exported to external services such as FederatedCode.

High-level overview
-------------------

The origin system is composed of four main layers:

#. **Data model** additions on :class:`~scanpipe.models.CodebaseRelation` plus
   the :class:`~scanpipe.models.OriginCuration` and
   :class:`~scanpipe.models.PropagationBatch` helper models.
#. **UI forms and views** that expose review, detail, creation, propagation,
   and deployment screens.
#. **REST API endpoints** that mirror the UI capabilities for automation.
#. **Background pipes** that implement propagation heuristics and deployment
   steps to FederatedCode.

The following sections drill into each layer and explain how the pieces fit
together.

Data model
----------

``CodebaseRelation`` gained the following fields to track manual decisions:

``curation_status``
    ``pending`` | ``approved`` | ``rejected`` (stored as ``CharField``)
``confidence_level``
    Optional qualitative indicator (``low`` → ``verified``).
``curation_notes``
    Free-form text field for rationale and references.
``curated_by`` / ``curated_at``
    Backreferences to the curator (``AUTH_USER_MODEL``) and timestamp.

Each update writes an ``OriginCuration`` entry that captures the previous
resource mapping, curator, status, confidence, and optional notes. This audit
trail enables accountability and rollback. ``OriginCuration`` inherits
``ProjectRelatedModel`` and is indexed by relation and curator timestamps for
fast lookups.

Propagation batches are tracked through ``PropagationBatch``. They aggregate
metadata about automatically generated relations (strategy used, curator,
count, extra data) and expose an ``undo`` helper that deletes all relations
created in the batch.

Forms and views
---------------

All UI flows live inside ``scanpipe/forms.py`` and ``scanpipe/views.py``:

``OriginCurationForm``
    A ``ModelForm`` bound to ``CodebaseRelation`` that edits curation fields.
``OriginCurateCreateForm``
    A form for manual relation creation with validation to prevent duplicates.
``BulkCurationForm``
    Radio-based form powering the modal that updates multiple relations.
``OriginPropagationForm``
    Collects strategy, preview-only flag, similarity threshold, and patterns.
``OriginDeployForm``
    Holds merge strategy, include-history flag, and preview-only toggle.

Corresponding views:

``OriginReviewView``
    ``PaginatedFilterView`` with bulk actions and export helpers.
``OriginCurateView`` and ``OriginCurateCreateView``
    Manage detail editing and manual creation. Both ensure the project context
    is loaded and leverage ``TabSetMixin`` for UI consistency.
``OriginPropagateView``
    ``FormView`` that orchestrates preview and execution of propagation logic.
``OriginDeployView``
    Handles FederatedCode export preview and pipeline launch.

Most views inherit :class:`~scanpipe.views.ProjectRelatedViewMixin`, which
provides ``get_project`` and ensures templates receive the project instance.

Propagation pipe
----------------

``scanpipe/pipes/origin_propagation.py`` implements four propagation
strategies. Each strategy returns a list of tuples ``(to_resource, from_resource,
map_type_suffix, confidence)`` which is fed to ``_apply_propagation``.

Key functions:

``propagate_origin_to_similar_resources``
    Combines checksum matches, directory similarity, and path heuristics.
``propagate_origin_by_directory_structure``
    Targets sibling resources that share parent directories.
``propagate_origin_by_package``
    Uses package membership to propagate relative paths within the same
    discovered package.
``propagate_origin_by_pattern``
    Applies glob-style patterns (``fnmatch``) to extend a relation.

``_apply_propagation`` records a ``PropagationBatch`` (when the user is
authenticated), writes new relations via ``make_relation``, stamps batch UUIDs
in ``extra_data``, and returns the count/relations/batch tuple.

Extending propagation
~~~~~~~~~~~~~~~~~~~~~

Developers can add new strategies by:

#. Implementing a helper that returns a candidate list similar to the existing
   functions.
#. Registering the new strategy in ``OriginPropagationForm`` choices and
   handling it inside ``OriginPropagateView.form_valid``.
#. Updating ``get_propagation_candidates`` so previews are aware of the
   strategy.

REST API
--------

``scanpipe/api/views.py`` extends :class:`ProjectViewSet` with three actions:

``relations``
    GET for listing relations with filters, POST for creating new relations.
``relation_detail``
    GET/PATCH/DELETE endpoints for individual relations.
``relations_bulk_curate``
    POST endpoint to approve/reject/update multiple relations.

Serializers in ``scanpipe/api/serializers.py`` expose read-only and write-only
fields:

* ``CodebaseRelationSerializer`` (read) adds computed ``status`` and ``score`` for
  existing exports and pipelines.
* ``CodebaseRelationCurationSerializer`` extends the base serializer with
  curation metadata for the REST API.
* ``CodebaseRelationWriteSerializer`` validates resource paths within the
  project context and automatically records ``OriginCuration`` history when
  curation fields change.

FederatedCode integration
-------------------------

``scanpipe/pipes/federatedcode.py`` adds:

``export_origin_curations(project, include_history=True)``
    Builds the YAML payload containing curated relations and optionally their
    history.
``add_origin_curations(project, repo, package_scan_file, include_history, merge_strategy)``
    Writes the export into the cloned repository and merges with existing
    curations using ``merge_curations``.
``merge_curations``
    Implements ``latest``, ``priority``, and ``manual`` strategies for
    combining datasets.

The ``PublishToFederatedCode`` pipeline pulls these helpers in ``add_origin_curations``.
Deployment options (merge strategy, include history) are stored in
``Project.extra_data["origin_deploy"]`` before the pipeline launches so the
background job runs with the requested configuration.

Audit trail and undo
--------------------

Every user-facing entry point (UI and API) that touches curation fields creates
an ``OriginCuration`` row. Propagation stores the batch UUID in relation
``extra_data`` and in ``PropagationBatch`` for traceability. The ``undo`` method
on ``PropagationBatch`` deletes all relations created in the batch and removes
the batch record.

When building additional tooling on top of this system, favour reusing the
existing history mechanisms to maintain consistent audit coverage.

Testing considerations
----------------------

* :ref:`tutorial_origin_curation` exercises the complete workflow through the UI.
* When adding new propagation strategies or serializers, extend test cases to
  validate:

  - candidate generation accuracy
  - history creation
  - FederatedCode export content

Future extensions
-----------------

Potential areas for extension include:

* New propagation heuristics (for example similarity scoring based on symbol
  analysis).
* Alternative deployment targets or export formats.
* Integration with external review workflows (e.g. webhooks when a relation
  changes status).

Follow core patterns—reuse ``OriginCuration`` for auditability, take advantage
of the mixins in ``scanpipe.views``, and keep serializers responsible for
validation/normalisation while delegating heavy logic to pipes or services.


