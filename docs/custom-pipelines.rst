.. _custom_pipelines:

Custom Pipelines
================

A Pipeline is a Python script that performs code analysis by executing a
sequence of steps.

- A pipeline is a **Python class** that lives in a Python module as a ``.py``
  **file**.
- A pipeline class **always inherits** from the ``Pipeline`` base class
  :ref:`pipeline_base_class`, or from other existing pipeline classes, such as
  the :ref:`built_in_pipelines`.
- It **defines steps** - execution order of the steps - using the ``steps``
  classmethod.

See :ref:`pipelines_concept` for more details.

Pipeline registration
---------------------

Built-in pipelines are located in :guilabel:`scanpipe/pipelines/` directory and
are registered during the ScanCode.io installation.

Whereas custom pipelines are added as Python files ``.py`` in the directories
defined in the :ref:`scancodeio_settings_pipelines_dirs` setting. Custom
pipelines are registered at runtime.

Create a Pipeline
-----------------

Create a new Python file ``my_pipeline.py``, and make sure to include the full
path of the new pipeline directory in the :ref:`scancodeio_settings_pipelines_dirs`
setting.

.. code-block:: python

    from scanpipe.pipelines import Pipeline

    class MyPipeline(Pipeline):

        @classmethod
        def steps(cls):
            return (
                cls.step1,
                cls.step2,
            )

        def step1(self):
            pass

        def step2(self):
            pass


.. tip::
    You can view the :guilabel:`scanpipe/pipelines/` directory for more pipeline
    examples.

Modify existing Pipelines
-------------------------

Existing pipelines are flexible and can be reused as a base for custom pipelines
, i.e. be customized. For instance, you can override existing steps, add new
ones, or remove any of them.

.. code-block:: python

    from scanpipe.pipelines.scan_codebase import ScanCodebase

    class MyCustomScan(ScanCodebase):

        @classmethod
        def steps(cls):
            return (
                # Original steps from the ScanCodebase pipeline
                cls.copy_inputs_to_codebase_directory,
                cls.run_extractcode,
                cls.run_scancode,
                cls.build_inventory_from_scan,

                # Commented-out as not interested in a csv output
                # cls.csv_output,

                # My extra steps
                cls.extra_step1,
                cls.extra_step2,
            )

        def extra_step1(self):
            pass

        def extra_step2(self):
            pass


Custom Pipeline example
-----------------------

The example below shows a custom pipeline that is based on the built-in :ref:`pipeline_scan_codebase`
pipeline with an extra reporting step.

Add the following code snippet to a Python file and register the path of
the file's directory in the :ref:`scancodeio_settings_pipelines_dirs`.

.. code-block:: python

    from collections import defaultdict

    from jinja2 import Template

    from scanpipe.pipelines.scan_codebase import ScanCodebase


    class ScanAndReport(ScanCodebase):
        """
        Run the ScanCodebase built-in pipeline steps and generate a licenses report.
        """

        @classmethod
        def steps(cls):
            return ScanCodebase.steps() + (
                cls.report_licenses_with_resources,
            )

        # See https://jinja.palletsprojects.com/en/3.0.x/templates/ for documentation
        report_template = """
        {% for matched_text, paths in resources.items() -%}
            {{ matched_text }}

            {% for path in paths -%}
                {{ path }}
            {% endfor %}

        {% endfor %}
        """

        def report_licenses_with_resources(self):
            """
            Retrieve codebase resources filtered by license categories,
            Generate a licenses report file from a template.
            """
            categories = ["Commercial", "Copyleft"]
            resources = self.project.codebaseresources.licenses_categories(categories)

            resources_by_licenses = defaultdict(list)
            for resource in resources:
                for license_data in resource.licenses:
                    matched_text = license_data.get("matched_text")
                    resources_by_licenses[matched_text].append(resource.path)

            template = Template(self.report_template, lstrip_blocks=True, trim_blocks=True)
            report_stream = template.stream(resources=resources_by_licenses)
            report_file = self.project.get_output_file_path("license-report", "txt")
            report_stream.dump(str(report_file))
