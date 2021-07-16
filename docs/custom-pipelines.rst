.. _custom_pipelines:

Custom Pipelines
================

A pipeline always inherits from the ``Pipeline`` base class :ref:`pipeline_base_class`
It define steps using the ``steps`` class method.

Pipeline registration
---------------------

Built-in pipelines are located in scanpipe/pipelines/ and registered during the
ScanCode.io installation.

Custom pipelines can be added as python files in the TBD/ directory and will be
automatically registered at runtime.

Create a Pipeline
-----------------

Create a new Python file ``my_pipeline.py`` in the  TBD/ directory.

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
    Have a look in the scanpipe/pipelines/ directory for more pipeline examples.

Modify existing Pipelines
-------------------------

Any existing pipeline can be reused as a base and customized.
You may want to override existing steps, add new ones, and remove some.

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

                # Commented-out as I'm not interested in a csv output
                # cls.csv_output,

                # My extra steps
                cls.extra_step1,
                cls.extra_step2,
            )

        def extra_step1(self):
            pass

        def extra_step2(self):
            pass
