.. _project_configuration:

Project configuration
=====================

You have two options for configuring your project: using the user interface settings
form or providing a ``scancode-config.yml`` configuration file as part of your project
inputs.

User Interface
--------------

To configure your project using the user interface, refer to the instructions in the
:ref:`user_interface_project_settings` section.

Configuration file
------------------

You can also store your project settings in a ``scancode-config.yml`` configuration
file. That file will have to be uploaded as one of the Project inputs:

- In the :ref:`user_interface`: Using the "Inputs" section of the "Create a Project"
  form or using the "Add inputs" button on an existing project view.
- In the :ref:`command_line_interface`: you can provide a ``scancode-config.yml``
  configuration file as part of the project inputs with the ``--input-file`` option.
- In the :ref:`rest_api`: Using the ``upload_file`` or ``input_urls`` fields.

Example
^^^^^^^

The following configuration example displays all the project settings currently
available.
It is not necessary to include the ones for which you do not need to provide a value.

Content of a ``scancode-config.yml`` file:

.. code-block:: yaml

    product_name: My Product Name
    product_version: '1.0'
    ignored_patterns:
      - '*.tmp'
      - tests/*

See the :ref:`project_configuration_settings` section for the details about each
setting.

.. tip::
    You can generate the project configuration file from the
    :ref:`user_interface_project_settings` UI.


.. _project_configuration_settings:

Settings
--------

product_name
^^^^^^^^^^^^

The product name of this project, as specified within the DejaCode application.

product_version
^^^^^^^^^^^^^^^

The product version of this project, as specified within the DejaCode application.

ignored_patterns
^^^^^^^^^^^^^^^^

Provide one or more path patterns to be ignored, **one per line**.

Each pattern should follow the syntax of Unix shell-style wildcards:
 - Use ``*`` to match multiple characters.
 - Use ``?`` to match a single character.

Here are some examples:
 - To ignore all files with a ".tmp" extension, use: ``*.tmp``
 - To ignore all files in a "tests" directory, use: ``tests/*``
 - To ignore specific files or directories, provide their exact names or paths, such as:
   ``example/file_to_ignore.txt`` or ``folder_to_ignore/*``

You can also **use regular expressions for more complex matching**.
Remember that these patterns will be applied recursively to all files and directories
within the project.

.. warning::
    Be cautious when specifying patterns to avoid unintended exclusions.
