.. _webhooks:

Webhooks
========

Webhooks in ScanCode.io allow you to receive real-time notifications about project
pipeline execution events. This enables integration with external services, automation
systems, or monitoring tools.

Once configured, a webhook sends an HTTP ``POST`` request to the specified target URL
whenever the defined conditions are met. The webhook payload can include a summary of
the scan results or full pipeline execution details.

ScanCode.io provides multiple ways to manage webhooks, including:

- A **Web UI** for adding, modifying, and deleting webhooks.
- A **CLI command** for adding webhooks to projects from the command line.
- A **REST API** to configure webhooks programmatically.
- A **global setting** to automatically apply a webhook to every new project.

.. _webhooks_ui:

Managing Webhooks in the Web UI
-------------------------------

The ScanCode.io Web UI provides an interface to manage webhooks at the project level.

From the **Project Settings** page, you can:

- **Create a webhook** by specifying a target URL that will receive notifications.
- **Modify an existing webhook** to change its target URL, trigger settings, or payload
  details.
- **Remove a webhook** if it is no longer needed.

When creating a webhook, the following options are available:

- **Target URL**: The destination URL where the webhook payload is sent.
- **Trigger on Each Run**: Choose whether to send notifications after every pipeline
  run or only when all runs are complete.
- **Include Summary**: Include a high-level summary of the pipeline execution in the
  webhook payload.
- **Include Results**: Optionally include the full scan results in the payload.
- **Active Status**: Enable or disable the webhook without deleting it.

For details on how to access the Web UI, see the :ref:`user_interface_manage_webhook`.

.. _webhooks_cli:

Managing Webhooks via the CLI
-----------------------------

Webhooks can also be managed from the command line using the ``scanpipe add-webhook``
command.

Basic usage::

    $ scanpipe add-webhook --project PROJECT TARGET_URL

Options include:

- ``--trigger-on-each-run``: Trigger the webhook after each pipeline run.
- ``--include-summary``: Include summary data in the webhook payload.
- ``--include-results``: Include detailed scan results.
- ``--inactive``: Create the webhook but leave it disabled.

For more details, see the :ref:`cli_add_webhook` section.

.. _webhooks_api:

Managing Webhooks via the REST API
----------------------------------

The ScanCode.io REST API allows webhooks to be configured programmatically when
creating or updating a project.

You can provide:

- A **single webhook URL** using the ``webhook_url`` field.
- A **list of webhook configurations** using the ``webhooks`` field.

Example JSON payload when creating a project:

.. code-block:: json

    {
      "name": "example_project",
      "webhook_url": "https://example.com/webhook",
      "webhooks": [
        {
          "target_url": "https://webhook.example.com",
          "trigger_on_each_run": true,
          "include_summary": true,
          "include_results": false,
          "is_active": true
        }
      ]
    }

For more details, refer to the :ref:`rest_api_webhooks` section.

.. _webhooks_global_setting:

Global Webhook Configuration
----------------------------

A **global webhook** can be automatically applied to every new project using the
``SCANCODEIO_GLOBAL_WEBHOOK`` setting.

To enable this, add the following configuration in your ``.env`` file::

    SCANCODEIO_GLOBAL_WEBHOOK=target_url=https://webhook.url,trigger_on_each_run=False,include_summary=True,include_results=False

Available options:

- ``target_url`` (**required**): The webhook destination URL.
- ``trigger_on_each_run`` (**default**: ``False``): Whether to trigger on every pipeline run.
- ``include_summary`` (**default**: ``False``): Include scan summary data in the payload.
- ``include_results`` (**default**: ``False``): Include detailed scan results.

For more information, see the :ref:`scancodeio_settings_global_webhook` section.

.. _webhooks_slack_notifications:

Slack Notifications
-------------------

The Webhook system in ScanCode.io provides built-in support for sending Slack
notifications using Slack's "Incoming Webhooks" feature.

If you want to receive notifications in Slack when your project's pipeline completes,
follow these steps:

1. **Create a Slack Incoming Webhook:**
   Visit the Slack API documentation at https://api.slack.com/messaging/webhooks
   to generate a webhook URL. The URL will be in the format:
   ``https://hooks.slack.com/...``.

2. **Configure a Webhook in ScanCode.io:**

   - Add a webhook to your project using the Slack webhook URL as the target.
   - Alternatively, define a :ref:`Global Webhook <webhooks_global_setting>` to
     apply the webhook globally across all projects.

3. **Ensure the Site URL is set:**
   Make sure the :ref:`scancodeio_settings_site_url` setting is correctly defined in
   your ``.env`` file::

       SCANCODEIO_SITE_URL=https://scancode.example.com/

With these settings in place, ScanCode.io will send pipeline completion updates directly
to your Slack channel.
