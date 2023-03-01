.. _vulnerablecode_integration:

VulnerableCode Integration
==========================

Here are the instructions to integrate VulnerableCode with Scancode.io:

- First, you need a VulnerableCode installation. We assume that you use the public
  instance at ``https://public.vulnerablecode.io/``

- Create an API user in this instance at https://public.vulnerablecode.io/account/request_api_key/
  and make note of the API key.

Run SCIO with these settings:

- In Scancode.io, you will need to add the environment variables in the ``docker.env``
  file if your run with docker or in the ``.env`` for a local development deployment:

  - Set the environment variable ``VULNERABLECODE_URL`` pointing to your
    VulnerableCode URL, for example ``https://public.vulnerablecode.io/``

  - Set the environment variable ``VULNERABLECODE_API_KEY`` with your API key.

The resulting ``docker.env`` file should look like this::

    VULNERABLECODE_URL = "https://public.vulnerablecode.io/"
    VULNERABLECODE_API_KEY = "paste your vulnerablecode API key here"

.. note::
    Optionally contact nexB support at support@nexb.com with your API user email if
    you are doing a larger scale evaluation and need to ease API throttling limitations.
