.. _origin_curation_api:

Origin Curation API
===================

The origin curation API extends the project endpoints with helpers to list,
create, update, and bulk-curate ``CodebaseRelation`` entries. Every endpoint
is nested under a project resource:

.. code-block:: text

    /api/projects/<project_uuid>/relations/

Authentication
--------------

All endpoints require the same authentication and permission settings as the
core API. When ``REQUIRE_AUTHENTICATION`` is enabled, include the API token in
the ``Authorization`` header::

    Authorization: Token <your-token>

Listing relations
-----------------

``GET /api/projects/<uuid>/relations/``

Returns a paginated list of relations for the project. Results can be filtered
using the parameters provided by :class:`RelationFilterSet`:

``search``
    Full text search on the ``to_resource.path``.
``map_type``
    Filter by relation map type (for example ``java_to_class``).
``status``
    Status of the ``to_resource`` (``requires-review``, ``ok``, etc.).
``curation_status``
    One of ``pending``, ``approved``, or ``rejected``.
``confidence_level``
    One of ``low``, ``medium``, ``high``, or ``verified``.
``curated_by``
    Username of the curator (partial match).
``requires_review``
    Boolean flag to return relations whose ``to_resource`` status is
    ``requires-review``.

Example:

.. code-block:: console

    curl -X GET \
      "http://localhost:8001/api/projects/4f3f.../relations/?curation_status=pending&requires_review=true" \
      -H "Authorization: Token abc123"

Sample response:

.. code-block:: json

    {
      "count": 2,
      "next": null,
      "previous": null,
      "results": [
        {
          "uuid": "f3d9cfcd-7627-478b-91cb-a2d553b79db9",
          "to_resource": "to/com/example/App.class",
          "status": "requires-review",
          "map_type": "java_to_class",
          "score": "0.87 diff_ratio: 0.12",
          "from_resource": "from/src/main/java/com/example/App.java",
          "curation_status": "pending",
          "confidence_level": "medium",
          "curation_notes": "Automated detection, needs review",
          "curated_by": "admin",
          "curated_at": "2025-11-11T06:12:48.912345Z"
        }
      ]
    }

Creating a relation
-------------------

``POST /api/projects/<uuid>/relations/``

Required fields:

``from_resource_path``
    Path of the source resource within the project.
``to_resource_path``
    Path of the target resource within the project.
``map_type``
    Relation category (for example ``java_to_class`` or ``checksum_match``).

Optional fields:

``curation_status`` ``confidence_level`` ``curation_notes``
    Set initial curation metadata. When provided, an ``OriginCuration`` record
    is automatically created.

.. code-block:: json

    {
      "from_resource_path": "from/src/main/java/com/example/Service.java",
      "to_resource_path": "to/com/example/Service.class",
      "map_type": "java_to_class",
      "curation_status": "approved",
      "confidence_level": "high",
      "curation_notes": "Reviewed manually"
    }

Updating or deleting a relation
-------------------------------

``GET /api/projects/<uuid>/relations/<relation_uuid>/``
``PATCH /api/projects/<uuid>/relations/<relation_uuid>/``
``DELETE /api/projects/<uuid>/relations/<relation_uuid>/``

PATCH accepts the same payload as the creation endpoint. When curation fields
change, a new ``OriginCuration`` history row is added.

.. code-block:: console

    curl -X PATCH \
      "http://localhost:8001/api/projects/4f3f.../relations/f3d9cfcd-7627-478b-91cb-a2d553b79db9/" \
      -H "Authorization: Token abc123" \
      -H "Content-Type: application/json" \
      -d '{"curation_status": "approved", "confidence_level": "verified"}'

Bulk curation
-------------

``POST /api/projects/<uuid>/relations/bulk-curate/``

Payload structure:

``relation_uuids`` *(list, required)*
    Array of relation UUIDs to update.
``action`` *(string, required)*
    One of ``approve``, ``reject``, ``mark_pending``, or ``set_confidence``.
``confidence_level`` *(string, required when action is ``set_confidence``)*
    Confidence level to apply.
``curation_notes`` *(string, optional)*
    Notes appended to each relation (preserved across updates).

Example:

.. code-block:: json

    {
      "relation_uuids": [
        "f3d9cfcd-7627-478b-91cb-a2d553b79db9",
        "a49036e2-f0c0-4104-9d9d-00ba578d72f6"
      ],
      "action": "approve",
      "curation_notes": "Reviewed with upstream team"
    }

Successful responses include the count of updated relations and per-relation
history entries are written automatically.

Field reference
---------------

Returned ``CodebaseRelation`` objects contain:

``uuid``
    Stable identifier for the relation.
``from_resource`` ``to_resource``
    Resource paths represented as strings.
``map_type``
    Relation mapping category.
``status``
    The ``to_resource.status`` value, exposed for convenience.
``score``
    Human-readable hint compiled from ``extra_data`` (for example similarity
    or diff metrics). Blank when no score is available.
``curation_status`` ``confidence_level`` ``curation_notes``
    Latest curation metadata.
``curated_by`` ``curated_at``
    Username and timestamp of the most recent curation update.

Error handling
--------------

Errors return a JSON object with a ``message`` key and the HTTP status code
appropriate to the failure (400 for validation issues, 404 when a relation
cannot be found, etc.). Examples:

.. code-block:: json

    {
      "message": "relation_uuids is required."
    }

    {
      "message": {
        "from_resource_path": ["Resource not found: from/src/missing.java"]
      }
    }




