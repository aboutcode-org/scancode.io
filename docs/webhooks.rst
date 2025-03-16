.. _webhooks:

Webhooks
========

Webhooks in ScanCode.io allow you to receive real-time notifications about project pipeline execution events. This enables seamless integration with external services, automation systems, or monitoring tools.

Once configured, a webhook sends an HTTP ``POST`` request to the specified target URL whenever the defined conditions are met. The webhook payload can include a summary of the scan results or full pipeline execution details, depending on your configuration.

ScanCode.io provides multiple ways to manage webhooks:

- **Web UI**: Add, modify, and delete webhooks using a graphical interface.
- **CLI command**: Configure webhooks from the command line for automation.
- **REST API**: Programmatically manage webhooks.
- **Global settings**: Apply a webhook automatically to every new project.

To test webhook delivery before integrating with production systems, you can use tools like **Beeceptor** (https://beeceptor.com/) or **PostBin** (https://www.postb.in/). These services allow you to inspect incoming webhook requests and debug payloads easily.

.. _webhooks_ui:

Managing Webhooks in the Web UI
-------------------------------

The ScanCode.io Web UI provides an interface to manage webhooks at the project level.

From the **Project Settings** page, you can:

- **Create a webhook** by specifying a target URL that will receive notifications.
- **Modify an existing webhook** to change its target URL, trigger settings, or payload details.
- **Remove a webhook** if it is no longer needed.

### Webhook Configuration Options

When creating a webhook, the following options are available:

+----------------------+---------------------------------------------------------------+
| **Option**          | **Description**                                               |
+======================+===============================================================+
| **Target URL**      | The destination URL where the webhook payload is sent.        |
+----------------------+---------------------------------------------------------------+
| **Trigger on Each   | Send notifications after every pipeline run or only on       |
| Run**              | completion.                                                    |
+----------------------+---------------------------------------------------------------+
| **Include Summary** | Attach a high-level summary of the pipeline execution.        |
+----------------------+---------------------------------------------------------------+
| **Include Results** | Optionally include full scan results in the payload.          |
+----------------------+---------------------------------------------------------------+
| **Active Status**   | Enable or disable the webhook without deleting it.            |
+----------------------+---------------------------------------------------------------+

For details on how to access the Web UI, see the :ref:`user_interface_manage_webhook`.

.. _webhooks_cli:

Managing Webhooks via the CLI
-----------------------------

You can manage webhooks from the command line using the ``scanpipe add-webhook`` command.

#### Basic Usage:

.. code-block:: bash

    $ scanpipe add-webhook --project PROJECT TARGET_URL

#### Available Options:

- ``--trigger-on-each-run``: Trigger the webhook after each pipeline run.
- ``--include-summary``: Include summary data in the webhook payload.
- ``--include-results``: Include detailed scan results.
- ``--inactive``: Create the webhook but leave it disabled.

To test the webhook delivery, you can use Beeceptor or PostBin before pointing it to your production system.

For more details, see the :ref:`cli_add_webhook` section.

.. _webhooks_api:

Managing Webhooks via the REST API
----------------------------------

The ScanCode.io REST API allows webhooks to be configured programmatically when creating or updating a project.

### Example JSON payload when creating a project:

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

To test the API configuration, you can use tools like **Beeceptor** or **PostBin** to inspect the incoming webhook requests.

For more details, refer to the :ref:`rest_api_webhooks` section.

.. _webhooks_global_setting:

Global Webhook Configuration
----------------------------

A **global webhook** can be automatically applied to every new project using the ``SCANCODEIO_GLOBAL_WEBHOOK`` setting.

#### Configuration in ``.env`` file:

.. code-block:: ini

    SCANCODEIO_GLOBAL_WEBHOOK=target_url=https://webhook.url,trigger_on_each_run=False,include_summary=True,include_results=False

#### Available Options:

- ``target_url`` (**required**): The webhook destination URL.
- ``trigger_on_each_run`` (**default**: ``False``): Whether to trigger on every pipeline run.
- ``include_summary`` (**default**: ``False``): Include scan summary data in the payload.
- ``include_results`` (**default**: ``False``): Include detailed scan results.

For more information, see the :ref:`scancodeio_settings_global_webhook` section.

.. _webhooks_slack_notifications:

Slack Notifications
-------------------

ScanCode.io supports sending notifications to Slack using Slack's "Incoming Webhooks" feature.

### Steps to Integrate Slack Notifications:

1. **Create a Slack Incoming Webhook:**
   - Visit the Slack API documentation at https://api.slack.com/messaging/webhooks.
   - Generate a webhook URL (e.g., ``https://hooks.slack.com/...``).

2. **Configure a Webhook in ScanCode.io:**
   - Add a webhook to your project using the Slack webhook URL as the target.
   - Alternatively, define a :ref:`Global Webhook <webhooks_global_setting>` to apply the webhook globally.

3. **Ensure the Site URL is set:**
   - Define the site URL in your ``.env`` file:

.. code-block:: ini

    SCANCODEIO_SITE_URL=https://scancode.example.com/

With these settings in place, ScanCode.io will send pipeline completion updates directly to your Slack channel.

## Testing Webhooks

Before integrating with production services, test webhook responses using **Beeceptor** or **PostBin**:

- **Beeceptor**: Create an endpoint at https://beeceptor.com/, configure it as your webhook URL, and inspect incoming requests.
- **PostBin**: Set up a test endpoint at https://www.postb.in/ to monitor webhook payloads.
