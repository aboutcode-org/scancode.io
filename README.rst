ScanCode.io
===========

Pre-requisite
-------------

 * Debian-like distro or macOS
 * Latest version of Python 3.6: https://www.python.org/downloads/
 * PostgreSQL 10: https://www.postgresql.org/ (or https://postgresapp.com/ on macOS)
 * Recent version of git: https://git-scm.com/

Development setup
-----------------

Clone the git ScanCode.io repo, install dependencies, and prepare the database::

   git clone git@github.com:nexB/scancode.io.git && cd scancode.io
   make dev
   make envfile
   make cleandb

Tests
-----

Run the tests suite with::

   make test

Documentation
------------

Start with `docs/introduction.rst`.

Workspace
---------

By default, the workspace is set to a `var/` directory at the root of this codebase.
This location is used to store the input and output files such as scan results and
pipeline outputs.

You can configure the workspace to your preferred location using the
`SCANCODEIO_WORKSPACE_LOCATION` environment variable::

   export SCANCODEIO_WORKSPACE_LOCATION=/path/to/scancodeio/workspace/

Webserver
---------

Start the ScanCode.io Webserver with::

   make run

.. note:: In local development mode, the task manager worker is not required
since the tasks are executed locally instead of being sent to the queue.

Code update
-----------

Update the code, install dependencies, and run the database migrations::

   cd scancode.io
   git pull
   make dev
   make migrate

User and Token
--------------

You need to create a user and generate a token to access the API::

    bin/python manage.py createsuperuser --username [USERNAME]
    bin/python manage.py drf_create_token [USERNAME]

Copy the token value from the command output. You need it to authenticate in the API.

.. warning:: An API token is like a password and should be treated with the same care.

Task manager
------------

In local development mode, you can emulate the server setup:
Webserver and task manager as their own processes.

Turn off the `CELERY_TASK_ALWAYS_EAGER` settings and manually start the
Celery workers::

    bin/celery multi start --app=scancodeio default low --loglevel=INFO -Ofair -c:default 1 -Q:default default -c:low 1 -Q:low priority.low --soft-time-limit:default=3600 --time-limit:default=3900 --soft-time-limit:low=14400 --time-limit:low=14700 --prefetch-multiplier=1

Stop the workers with::

    bin/celery multi stop default low

    
License
-------

SPDX-License-Identifier: Apache-2.0

The ScanCode.io software is licensed under the Apache License version 2.0.
Data generated with ScanCode.io is provided as-is without warranties.
ScanCode is a trademark of nexB Inc.

You may not use this software except in compliance with the License.
You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
OR CONDITIONS OF ANY KIND, either express or implied. No content created from
ScanCode.io should be considered or used as legal advice. Consult an Attorney
for any legal advice.
