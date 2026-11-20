.. _tutorial_custom_attribution:

Customize the Attribution Output
================================

ScanCode.io generates an HTML attribution document from the packages discovered in a
project. In this tutorial, you will customize that document with a template stored in
the input codebase.

Requirements
------------

You need:

- A ScanCode.io instance and access to its Web UI.
- A codebase that can be processed by a pipeline that discovers packages.
- The ability to add files to the codebase before uploading it.

Create the custom template
--------------------------

Create the template directory at the root of the codebase:

.. code-block:: bash

    $ mkdir -p .scancode/templates

Download the current default template as a starting point:

.. code-block:: bash

    $ curl --location \
        https://raw.githubusercontent.com/aboutcode-org/scancode.io/main/scanpipe/templates/scanpipe/attribution.html \
        --output .scancode/templates/attribution.html

The template uses the Django template language. Edit
``.scancode/templates/attribution.html`` to match your requirements. For example,
change the existing ``title`` element to include your company name:

.. code-block:: html+django

    <title>Example Corp open source attribution</title>

Then customize the existing ``title`` block:

.. code-block:: html+django

    {% block title %}
      <h1>{{ project.name }} open source attribution</h1>
      <p>Prepared for Example Corp.</p>
    {% endblock %}

The template context provides these variables:

- ``project``: the project name, notes, and creation date.
- ``packages``: the discovered package data, including Package URLs, license
  expressions, copyrights, and notice text when available.
- ``licenses``: the unique licenses referenced by the discovered packages.

Keep the package and license loops from the default template unless you intend to
remove those sections from the output. See :ref:`data_model` for details about the
available package fields.

Add the template to the input
-----------------------------

The ``.scancode`` directory must be at the root of the codebase after ScanCode.io
extracts the input. Your codebase should have this structure:

.. code-block:: text

    .scancode/
      templates/
        attribution.html
    src/
    ...

When creating an archive for upload, archive the contents of the codebase so that
``.scancode`` remains at the archive root. For example, run this command from the
codebase directory:

.. code-block:: bash

    $ zip -r ../my-codebase.zip .

Upload the archive to a new ScanCode.io project and run the appropriate analysis
pipeline for your input. See :ref:`built_in_pipelines` for available pipelines.

.. note::
    You can also paste a complete template into the **Attribution template** field in
    the project's **Settings** page. A template saved in that field takes precedence
    over ``.scancode/templates/attribution.html``. Leave the field empty when testing
    the template from the codebase.

Generate the attribution document
---------------------------------

After the pipeline run completes:

1. Open the project details page.
2. Open the **Download** menu.
3. Select **Attribution**.
4. Open the downloaded ``attribution.html`` file in a browser and verify the changes.

If the default output is still used, verify that the template is located at
``codebase/.scancode/templates/attribution.html`` in the project workspace and that
the **Attribution template** field in the project settings is empty.
