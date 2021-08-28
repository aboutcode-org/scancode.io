.. _faq:

FAQs
====

You can't find what you're looking for? Below you'll find answers to a few of
our frequently asked questions.

How can I run a scan?
^^^^^^^^^^^^^^^^^^^^^

You simply start by creating a `new project <https://scancodeio.readthedocs.io/en/latest/user-interface.html#creating-a-new-project>`_
and run the appropriate pipeline. ScanCode.io offers several `built-in pipeline <https://scancodeio.readthedocs.io/en/latest/built-in-pipelines.html>`_
depending on your input—Docker image, Codebase drop, Package archive, etc.

I am unable to run ScanCode.io on Windows?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Unfortunatelly, we never tested nor support Windows. Please refer to our
:ref:`installation` section for more details on how to install Scancode.io
locally.

Is it possible to compare sxan results?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

At the moment, you can only download full reports in JSON, xlsx formats.

How can I trigger a pipeline scan from a CI/CD, such as Jenkins, TeamCity or Azure Devops?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can use `REST API <https://scancodeio.readthedocs.io/en/latest/scanpipe-api.html>`_
to automate your project or pipeline management.
