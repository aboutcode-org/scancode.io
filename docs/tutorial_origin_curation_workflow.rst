.. _tutorial_origin_curation:

Tutorial: Origin Review and Curation Workflow
=============================================

This tutorial walks through a complete origin review session using the ScanCode.io
web interface and supporting API calls. You will triage relations, curate them,
propagate trustworthy determinations, and finally deploy curations to FederatedCode.

Prerequisites
-------------

* ScanCode.io running locally (``make run``).
* A staff user account (``python manage.py createsuperuser``).
* Optional: install dependencies needed for FederatedCode integration (``git``
  access, configured credentials).

Step 1: Explore the origin review dashboard
-------------------------------------------

#. Sign in at ``http://127.0.0.1:8002/admin/`` if authentication is required.
#. Navigate to ``http://127.0.0.1:8002/project/origin-review-test/`` and click the
   **Origin Review** button in the header.
#. Use the filter menu to narrow the list (for example enable **Requires Review**).
#. Select a few relations and trigger **Bulk Actions → Approve selected** to clear
   obvious cases.
#. Download the filtered list with **Export JSON** or **Export XLSX** to verify
   curation metadata.

Step 2: Curate a single relation
--------------------------------

#. Click **Review** in the actions column.
#. Inspect the **Curation** tab: change status to ``approved``, set the confidence
   to ``verified``, and add a justification in the notes field.
#. Submit to save. Switch to the **History** tab to confirm the ``OriginCuration``
   record was created and that your username is recorded.

Step 3: Create a missing relation
---------------------------------

#. Return to the review page and click **Add Relation**.
#. Fill in the form with:

   * From resource path: ``from/src/main/java/com/example/NewService.java``
   * To resource path: ``to/com/example/NewService.class``
   * Map type: ``java_to_class``
   * Curation status: ``pending`` (optional)

#. Submit the form and confirm the relation appears in the table.

Step 4: Propagate the approval
------------------------------

#. Select an approved relation (for instance ``App.java``) and click **Propagate**.
#. Choose **Similar resources** strategy and check **Preview only**.
#. Submit to display the candidate list. Review the suggestions and, if they look
   reasonable, uncheck **Preview only** and submit again to apply the batch.
#. Back in the review list, filter for ``extra_data__propagation_batch`` to inspect
   the newly created relations. Use the batch UUID if you need to undo the changes
   in the Django shell with ``PropagationBatch.objects.get(uuid=...).undo()``.

Step 5: Deploy to FederatedCode
-------------------------------

#. Ensure the project has a Package URL. From the project detail page click
   **Settings** and populate the ``purl`` field (for example ``pkg:maven/com.example/app@1.0.0``).
#. Open ``/project/origin-review-test/origin-deploy/``.
#. Verify the summary: curated relation count, history entries, FederatedCode
   configuration status.
#. Keep **Preview only** enabled and submit to inspect the YAML payload.
#. When ready, choose a merge strategy (``latest`` is a good default), disable
   preview, and submit to launch the ``PublishToFederatedCode`` pipeline. Track
   progress via the **Pipelines** tab.

Optional: use the REST API
--------------------------

The same workflow can be automated. For example, approve a relation via API:

.. code-block:: console

    curl -X PATCH \
      "http://127.0.0.1:8002/api/projects/<project_uuid>/relations/<relation_uuid>/" \
      -H "Authorization: Token <api_key>" \
      -H "Content-Type: application/json" \
      -d '{"curation_status": "approved", "confidence_level": "high"}'

Use the bulk-curate endpoint to update multiple relations at once:

.. code-block:: json

    {
      "relation_uuids": ["uuid-1", "uuid-2"],
      "action": "set_confidence",
      "confidence_level": "verified",
      "curation_notes": "Validated via automation"
    }

Next steps
----------

* Explore additional propagation strategies (directory, package, pattern) and
  compare candidate previews.
* Combine UI and API actions in a script to triage large batches.
* Extend the deployment pipeline with project-specific metadata using
  ``merge_curations`` or additional export hooks.

Related references
------------------

* :ref:`origin_curation_guide`
* :ref:`origin_curation_api`
* :ref:`origin_curation_architecture`


