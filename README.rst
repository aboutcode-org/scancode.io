ScanCode.io
===========

ScanCode.io is a server to script and automate software composition analysis
with ScanPipe pipelines.

First application is for Docker container and VM composition analysis.

Getting started
---------------

The ScanCode.io documentation is available here: https://scancodeio.readthedocs.org/

If you have questions that are not covered by our
`Documentation <https://scancodeio.readthedocs.io/en/latest/faq.html>`_ or
`FAQs <https://scancodeio.readthedocs.io/en/latest/faq.html>`_,
please ask them in `Discussions <https://github.com/nexB/scancode.io/discussions>`_.

If you want to contribute to ScanCode.io, start with our
`Contributing <https://scancodeio.readthedocs.io/en/latest/contributing.html>`_ page.

A new GitHub action is now available at
`scancode-action <https://github.com/nexB/scancode-action>`_
to run ScanCode.io pipelines from your GitHub Workflows.
Visit https://scancodeio.readthedocs.io/en/latest/automation.html to learn more
about automation.

Build and tests status
----------------------

+------------+-------------------+
| **Tests**  | **Documentation** |
+============+===================+
| |ci-tests| |    |docs-rtd|     |
+------------+-------------------+

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


.. |ci-tests| image:: https://github.com/nexB/scancode.io/actions/workflows/ci.yml/badge.svg?branch=main
    :target: https://github.com/nexB/scancode.io/actions/workflows/ci.yml
    :alt: CI Tests Status

.. |docs-rtd| image:: https://readthedocs.org/projects/scancodeio/badge/?version=latest
    :target: https://scancodeio.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Build Status
