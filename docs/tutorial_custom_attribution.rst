Generate Attribution with a Custom Template
===========================================

This tutorial explains how to create and use a custom attribution template in
ScanCode.io to override the default attribution output.

Overview
--------

ScanCode.io generates attribution documents based on an internal HTML template.
You can override this template at the *project level* using the web UI.

This is useful when you want:

- A custom layout
- Additional metadata fields
- Company branding
- Different formatting for license or copyright data

Default Attribution Template
----------------------------

The built-in attribution template is stored at:

``scanpipe/templates/scanpipe/attribution.html``

Use this file as a reference when creating your custom template.  
Template variables follow the Jinja2 syntax, such as:

- ``{{ resource.path }}``
- ``{{ resource.license_expression }}``
- ``{{ resource.copyright }}``
- ``{{ resource.package_name }}``

Create Your Custom Template
---------------------------

Start by copying the default template and modifying it to fit your needs.

Example simple template:

.. code-block:: html

    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Attribution</title>
        <style>
          body { font-family: sans-serif; margin: 20px; }
          .item { margin-bottom: 1.5em; border-bottom: 1px solid #ddd; padding-bottom: .5em; }
        </style>
      </head>

      <body>
        <h1>Project Attributions</h1>

        {% for resource in resources %}
          <div class="item">
            <h2>{{ resource.package_name or resource.path }}</h2>
            <p><strong>License:</strong> {{ resource.license_expression or "Unknown" }}</p>
            <p><strong>Copyright:</strong> {{ resource.copyright or "Unknown" }}</p>
          </div>
        {% endfor %}
      </body>
    </html>

Add Template to Project Settings
--------------------------------

1. Open your project in the ScanCode.io web UI.
2. Go to **Settings**.
3. Find the **Attribution Template** field.
4. Paste your custom HTML template directly into the field.
5. Save.

Your template will now override the default attribution generation for that project.

Generate and Download Attribution
---------------------------------

1. Open the project details page.
2. Use the **Download** dropdown.
3. Select **Attribution**.
4. The downloaded file will use your custom template.

Troubleshooting
---------------

- **Missing data?**  
  Check variable names against the default template.

- **HTML not rendering correctly?**  
  Test the HTML in a browser and simplify CSS if needed.

- **Template not applied?**  
  Ensure you pasted it into the correct project settings page.

Summary
-------

You can generate custom attribution documents by:

1. Reviewing the default template.
2. Creating your custom HTML file.
3. Adding it to project settings.
4. Downloading attributions using the web UI.

This enables complete control over attribution formatting and presentation.
