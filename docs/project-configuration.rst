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

Template
^^^^^^^^

To simplify the configuration process, we provide a template for the
``scancode-config.yml`` file. You can download it from the following link:
`download scancode-config.yml template <https://raw.githubusercontent.com/nexB/scancode.io/main/docs/scancode-config.yml>`_

Once downloaded, follow these steps:

1. **Open** the downloaded ``scancode-config.yml`` file in a text editor.
2. **Uncomment and set the values** for the settings that are relevant to your project.
3. **Save** the changes to the file.

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
     - 'tests/*'
    scan_max_file_size: 5242880
    ignored_dependency_scopes:
     - package_type: npm
       scope: devDependencies
     - package_type: pypi
       scope: tests
    ignored_vulnerabilities:
     - VCID-q4q6-yfng-aaag
     - CVE-2024-27351
     - GHSA-vm8q-m57g-pff3

See the following :ref:`project_configuration_settings` section for the details about
each setting.

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

scan_max_file_size
^^^^^^^^^^^^^^^^^^

Maximum file size allowed for a file to be scanned when scanning a codebase.

The value unit is bytes and is defined as an integer, see the following
example of setting this at 5 MB::

    scan_max_file_size=5242880

Default is ``None``, in which case all files will be scanned.

.. note::
    This is the same as the scancodeio setting ``SCANCODEIO_SCAN_MAX_FILE_SIZE``
    set using the .env file, and the project setting ``scan_max_file_size`` takes
    precedence over the scancodeio setting ``SCANCODEIO_SCAN_MAX_FILE_SIZE``.

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

ignored_dependency_scopes
^^^^^^^^^^^^^^^^^^^^^^^^^

Specify certain dependency scopes to be ignored for a given package type.
This allows you to exclude dependencies from being created or resolved based on their
scope.

**Guidelines:**

- **Exact Matches Only:** The scope names must be specified exactly as they appear.
  Wildcards and partial matches are not supported.
- **Scope Specification:** List each scope name you wish to ignore.

**Examples:**

To exclude all ``devDependencies`` for ``npm`` packages and ``tests`` for ``pypi``
packages, define the following in your ``scancode-config.yml`` configuration file:

.. code-block:: yaml

    ignored_dependency_scopes:
     - package_type: npm
       scope: devDependencies
     - package_type: pypi
       scope: tests

If you prefer to use the :ref:`user_interface_project_settings` form, list each
ignored scope using the `package_type:scope` syntax, **one per line**, such as:

.. code-block:: text

    npm:devDependencies
    pypi:tests

.. warning::
    Be precise when listing scope names to avoid unintended exclusions.
    Ensure the scope names are correct and reflect your project requirements.

ignored_vulnerabilities
^^^^^^^^^^^^^^^^^^^^^^^

Provide one or more vulnerability id to be ignored, **one per line**.

You can provide ``VCID`` from VulnerableCode or any aliases such as ``CVE`` or
``GHSA``.

.. code-block:: yaml

    ignored_vulnerabilities:
     - VCID-q4q6-yfng-aaag
     - CVE-2024-27351
     - GHSA-vm8q-m57g-pff3
     - OSV-2020-871
     - BIT-django-2024-24680
     - PYSEC-2024-28

.. _project_configuration_settings_policies:

policies
^^^^^^^^

For detailed information about the policies system, refer to :ref:`policies`.

Instead of providing a separate ``policies.yml`` file, policies can be directly
defined within the project configuration.
This can be done through the web UI, see :ref:`user_interface_project_settings`,
or by using a ``scancode-config.yml`` file.
