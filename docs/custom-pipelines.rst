.. _custom_pipelines:

Custom Pipelines
================

Pipelines are Python scripts; each contains a set of instructions that have to
be executed in an orderly manner—pipe-like nature—to perform a code analysis.

- A pipeline is a **Python class** that lives in a Python module as a ``.py``
  **file**.
- A pipeline class **always inherits** from the ``Pipeline`` base class
  :ref:`pipeline_base_class`, or from other existing pipeline classes, such as
  the :ref:`built_in_pipelines`.
- A pipeline **defines sequence of steps**—execution order of the steps—using
  the ``steps`` classmethod.

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

Modify Existing Pipelines
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
                cls.extract_archives,
                cls.collect_and_create_codebase_resources,
                cls.flag_empty_files,
                cls.flag_ignored_resources,
                cls.scan_for_application_packages,
                cls.scan_for_files,

                # My extra steps
                cls.extra_step1,
                cls.extra_step2,
            )

        def extra_step1(self):
            pass

        def extra_step2(self):
            pass

.. _custom_pipeline_example:

Custom Pipeline Example
-----------------------

The example below shows a custom pipeline that is based on the built-in
:ref:`pipeline_scan_codebase` pipeline with an extra reporting step.

Add the following code snippet to a Python file and register the path of
the file's directory in the :ref:`scancodeio_settings_pipelines_dirs`.

.. code-block:: python

    from collections import defaultdict

    from jinja2 import Template

    from scanpipe.pipelines.scan_codebase import ScanCodebase


    class ScanAndReport(ScanCodebase):
        """
        Runs the ScanCodebase built-in pipeline steps and generate a licenses report.
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
            Retrieves codebase resources and generates a licenses report file using
            a Jinja template.
            """
            resources = self.project.codebaseresources.has_license_detections()

            resources_by_matched_text = defaultdict(list)
            for resource in resources:
                for detection_data in resource.license_detections:
                    for match in detection_data.get("matches", []):
                        matched_text = match.get("matched_text")
                        resources_by_matched_text[matched_text].append(resource.path)

            template = Template(self.report_template, lstrip_blocks=True, trim_blocks=True)
            report_stream = template.stream(resources=resources_by_matched_text)
            report_file = self.project.get_output_file_path("license-report", "txt")
            report_stream.dump(str(report_file))

Pipeline Packaging
------------------

Once you created a custom pipeline, you’ll want to package it as a Python module
for easier distribution and reuse.
You can check `the Packaging Python Project tutorial at
PyPA <https://packaging.python.org/tutorials/packaging-projects/>`_, for
standard packaging instructions.

After you have packaged your own custom pipeline successfully, you need to
specify the entry point of the pipeline in the :guilabel:`setup.cfg` file.

.. code-block:: cfg

    [options.entry_points]
    scancodeio_pipelines =
        pipeline_name = pipeline_module:Pipeline_class

.. note ::
    Remember to replace ``pipeline_module`` with the name of the Python module
    containing your custom pipeline.

.. _pipeline_packaging_example:

Pipeline Packaging Example
--------------------------
The example below shows a standard pipeline packaging procedure for the custom
pipeline created in :ref:`custom_pipeline_example`.

A typical directory structure for the Python package would be:

::

    .
    ├── CHANGELOG.rst
    ├── LICENSE
    ├── MANIFEST.in
    ├── pyproject.toml
    ├── README.rst
    ├── setup.cfg
    ├── setup.py
    └── src
        └── scancodeio_scan_and_report_pipeline
            ├── __init__.py
            └── pipelines
                ├── __init__.py
                └── scan_and_report.py

Add the following code snippet to your :guilabel:`setup.cfg` file and specify
the entry point to the pipeline under the ``[options.entry_points]`` section.

.. code-block:: cfg

    [metadata]
    license_files =
        LICENSE
        CHANGELOG.rst

    name = scancodeio_scan_and_report_pipeline
    author = nexB. Inc. and others
    author_email = info@aboutcode.org
    license = Apache-2.0

    # description must be on ONE line https://github.com/pypa/setuptools/issues/1390
    description =  Generates a licenses report file from a template in ScanCode.io
    long_description = file:README.rst
    url = https://github.com/aboutcode-org/scancode.io
    classifiers =
        Development Status :: 4 - Beta
        Intended Audience :: Developers
        Programming Language :: Python :: 3
        Programming Language :: Python :: 3 :: Only
    keywords =
        scancodeio
        pipelines

    [options]
    package_dir=
        =src
    packages=find:
    include_package_data = true
    zip_safe = false
    python_requires = >=3.10
    setup_requires = setuptools_scm[toml] >= 4

    [options.packages.find]
    where=src

    [options.entry_points]
    scancodeio_pipelines =
        pipeline_name = scancodeio_scan_and_report_pipeline.pipelines.scan_and_report:ScanAndReport

.. tip::
    Take a look at `Google License Classifier pipeline for ScanCode.io
    <https://github.com/aboutcode-org/scancode.io-pipeline-glc_scan>`_
    for a complete example on packaging a custom tool as a pipeline.

Pipeline Publishing to PyPI
---------------------------
After successfully packaging a pipeline, you may consider distributing it—as a
plugin—via PyPI.
Ensure a directory structure similar to the :ref:`pipeline_packaging_example` with all
package files correctly configured.

.. tip::
    See the `Python packaging tutorial at PyPA
    <https://packaging.python.org/tutorials/packaging-projects/>`_
    for a detailed setup guide.

Next step involves generating the distribution archives for the package.
Make sure you have the latest version of ``build`` installed on your system.

.. code-block:: bash

    pip install --upgrade build

Now run the following command from within the same directory where the
``pyproject.toml`` is located:

.. code-block:: bash

    python -m build

Once completed, you should have two files inside the :guilabel:`dist/` directory with the
``.tar.gz`` and ``.whl`` extensions.

.. note::
    Remember to create an account on `PyPI <https://pypi.org/>`_ before uploading your
    distribution archive to PyPI.

You can use ``twine`` to upload the package to PyPI. To install twine, run the
following command:

.. code-block:: bash

    pip install twine

Finally, you can upload your package to PyPI with the next command:

.. code-block:: bash

    twine upload dist/*

Once successfully uploaded, your pipeline package should be viewable on PyPI under the
name specified in your manifest.

To make your pipeline available in your instance of ScanCode.io, you need to install
the package from PyPI. For example, to install the package described in the
:ref:`pipeline_packaging_example`, run:

.. code-block:: bash

    bin/pip install scancodeio_scan_and_report_pipeline
