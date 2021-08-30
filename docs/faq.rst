.. _faq:

FAQs
====

You can't find what you're looking for? Below you'll find answers to a few of
our frequently asked questions.

How can I run a scan?
---------------------

You simply start by creating a :ref:`new project <user_interface_create_new_project>`
and run the appropriate pipeline.

ScanCode.io offers several :ref:`built_in_pipelines` depending on your input:

- Docker image
- Codebase drop
- Package archive
- Root filesystem
- ScanCode-toolkit results

I am unable to run ScanCode.io on Windows?
------------------------------------------

Unfortunately, we never tested nor support Windows. Please refer to our
:ref:`installation` section for more details on how to install ScanCode.io
locally.

Is it possible to compare scan results?
---------------------------------------

At the moment, you can only download full reports in JSON and XLSX formats.
Please refer to our :ref:`output_files` section for more details on the output formats.

How can I trigger a pipeline scan from a CI/CD, such as Jenkins, TeamCity or Azure Devops?
------------------------------------------------------------------------------------------

You can use the :ref:`rest_api` to automate your project or pipeline management.
