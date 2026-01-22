Changelog
=========

**v36 Breaking Change:** PostgreSQL 17 is now required (previously 13).

Docker Compose users with existing data: run `./migrate-pg13-to-17.sh` before starting
the stack.
Fresh installations require no action.

v36.1.0 (2026-01-22)
--------------------

- Bump to latest scancode-toolkit v32.5.0 with:
  * package and license detection performance improvement
  * python3.14 support with updated dependencies
  * improved copyright, license and package detection
  For more details see https://github.com/aboutcode-org/scancode-toolkit/releases/tag/v32.5.0
  https://github.com/aboutcode-org/scancode.io/pull/2000

- Support python3.14
  https://github.com/aboutcode-org/scancode.io/pull/2000

- Update to scancode-toolkit v32.4.1
  https://github.com/aboutcode-org/scancode.io/pull/1984
  For more details see https://github.com/aboutcode-org/scancode-toolkit/releases/tag/v32.4.1

- Store the whole vulnerability data from cdx to local models
  https://github.com/aboutcode-org/scancode.io/pull/2007

- Add project vulnerability list view
  https://github.com/aboutcode-org/scancode.io/pull/2018

- Update minecode-pipelines to latest v0.1.1
  https://github.com/aboutcode-org/scancode.io/pull/2013

- Refine d2d pipelines with misc improvements
  https://github.com/aboutcode-org/scancode.io/pull/1996
  https://github.com/aboutcode-org/scancode.io/pull/1995
  https://github.com/aboutcode-org/scancode.io/pull/1999
  https://github.com/aboutcode-org/scancode.io/pull/2021

- Sanitize ORT package IDs to handle colons in versions
  https://github.com/aboutcode-org/scancode.io/pull/2005

- Restructure docs and README
  https://github.com/aboutcode-org/scancode.io/pull/2032



v36.0.1 (2025-12-09)
--------------------

- Add support for authors in ORT package list generation.
  https://github.com/aboutcode-org/scancode.io/issues/1988

- Add authors field to the CycloneDX output.
  https://github.com/aboutcode-org/scancode.io/issues/1990

- Store non-supported fields in the comment SPDX field.
  https://github.com/aboutcode-org/scancode.io/issues/1989

- Add support for CycloneDX spec v1.7.
  https://github.com/aboutcode-org/scancode.io/issues/1975

v36.0.0 (2025-12-05)
--------------------

- Upgrade PostgreSQL from 13 to 17 in Docker compose file
  https://github.com/aboutcode-org/scancode.io/issues/1973

- Upgrade Django to latest 5.2.x version
  https://github.com/aboutcode-org/scancode.io/issues/1976

- Remove the dependency on scipy
  https://github.com/aboutcode-org/scancode.io/issues/1754

- Add "ort-package-list" to the formats list in run command
  https://github.com/aboutcode-org/scancode.io/issues/1982

v35.5.0 (2025-12-01)
--------------------

- Add arguments support for the reset action in REST API.
  https://github.com/aboutcode-org/scancode.io/issues/1948

- Add management command to analyze Kubernetes cluster.
  https://github.com/aboutcode-org/scancode.io/issues/1950

- Improve source mapping for .py and .pyi files.
  https://github.com/aboutcode-org/scancode.io/issues/1920

- Keep webhook subscription in project reset.
  https://github.com/aboutcode-org/scancode.io/issues/1963

- Add --vulnerabilities and --strict options in verify-project.
  https://github.com/aboutcode-org/scancode.io/issues/1964

- Add support for PyPI PURLs as Inputs.
  https://github.com/aboutcode-org/scancode.io/issues/1966

- Add JFrog Artifactory and Sonatype Nexus integrations documentation.
  https://github.com/aboutcode-org/scancode.io/issues/1970

v35.4.1 (2025-10-24)
--------------------

- Add ability to download all output results formats as a zipfile for a given project.
  https://github.com/aboutcode-org/scancode.io/issues/1880

- Add support for tagging inputs in the run management command
  Add ability to skip the SQLite auto db in combined_run
  Add documentation to leverage PostgreSQL service
  https://github.com/aboutcode-org/scancode.io/pull/1916

- Refine d2d pipeline for scala and kotlin.
  https://github.com/aboutcode-org/scancode.io/issues/1898

- Add utilities to create/init FederatedCode data repo.
  https://github.com/aboutcode-org/scancode.io/issues/1896

- Add a verify-project CLI management command.
  https://github.com/aboutcode-org/scancode.io/issues/1903

- Add support for multiple inputs in the run management command.
  https://github.com/aboutcode-org/scancode.io/issues/1916

- Add the django-htmx app to the stack.
  https://github.com/aboutcode-org/scancode.io/issues/1917

- Adjust the resource tree view table rendering.
  https://github.com/aboutcode-org/scancode.io/issues/1840

- Add ".." navigation option in table to navigate to parent resource.
  https://github.com/aboutcode-org/scancode.io/issues/1869

- Add ability to download all output results formats.
  https://github.com/aboutcode-org/scancode.io/issues/1880

- Update Java D2D Pipeline to Include Checksum Mapped Sources for Accurate Java Mapping.
  https://github.com/aboutcode-org/scancode.io/issues/1870

- Auto-detect pipeline from provided input.
  https://github.com/aboutcode-org/scancode.io/issues/1883

- Migrate SCA workflows verification to new verify-project management command.
  https://github.com/aboutcode-org/scancode.io/issues/1902

v35.4.0 (2025-09-30)
--------------------

- Use deterministic UID/GID in Dockerfile.
  A temporary ``chown`` service is now started in the ``docker-compose`` stack
  to fix the permissions. This process is only fully run once.
  You may manually run this process using the following:
  ``$ chown -R 1000:1000 /var/scancodeio/``
  https://github.com/aboutcode-org/scancode.io/issues/1555

- Resolve and load dependencies from SPDX SBOMs.
  https://github.com/aboutcode-org/scancode.io/issues/1145

- Display the optional steps in the Pipelines autodoc.
  https://github.com/aboutcode-org/scancode.io/issues/1822

- Add new ``benchmark_purls`` pipeline.
  https://github.com/aboutcode-org/scancode.io/issues/1804

- Add a Resources tree view.
  https://github.com/aboutcode-org/scancode.io/issues/1682

- Improve CycloneDX SBOM support.
  * Upgrade the cyclonedx-python-lib to 11.0.0
  * Fix the validate_document following library upgrade.
  * Add support when the "components" entry is missing.
  https://github.com/aboutcode-org/scancode.io/issues/1727

- Split the functionality of
  ``scanpipe.pipes.federatedcode.commit_and_push_changes`` into
  ``scanpipe.pipes.federatedcode.commit_changes`` and
  ``scanpipe.pipes.federatedcode.push_changes``. Add
  ``scanpipe.pipes.federatedcode.write_data_as_yaml``.

- Add ORT ``package-list.yml`` as new downloadable output format.
  https://github.com/aboutcode-org/scancode.io/pull/1852

- Add support for SPDX as YAML in ``load_sbom`` pipeline.

v35.3.0 (2025-08-20)
--------------------

- Enhanced scorecard compliance support with:
  * New ``scorecard_compliance_alert`` in project ``extra_data``.
  * ``/api/projects/{id}/scorecard_compliance/`` API endpoint.
  * Scorecard compliance integration in ``check-compliance`` management command.
  * UI template support for scorecard compliance alert.
  * ``evaluate_scorecard_compliance()`` pipe function for compliance evaluation.
  https://github.com/aboutcode-org/scancode.io/pull/1800

v35.2.0 (2025-08-01)
--------------------

- Refactor policies implementation to support more than licenses.
  The entire ``policies`` data is now stored on the ``ScanPipeConfig`` in place of the
  ``license_policy_index``.
  Also, a new method ``get_policies_dict`` methods is now available on the ``Project``
  model to easily retrieve all the policies data as a dictionary.
  Renamed for clarity:
  * ``policy_index`` to ``license_policy_index``
  * ``policies_enabled`` to ``license_policies_enabled``
  https://github.com/aboutcode-org/scancode.io/pull/1718

- Add support for SPDX license identifiers as ``license_key`` in license policies
  ``policies.yml`` file.
  https://github.com/aboutcode-org/scancode.io/issues/1348

- Enhance the dependency tree view in a more dynamic rendering.
  Vulnerabilities and compliance alert are displayed along the dependency entries.
  https://github.com/aboutcode-org/scancode.io/pull/1742

- Add new ``fetch_scores`` pipeline.
  This pipeline retrieves ScoreCode data for each discovered package in the project
  and stores it in the corresponding package instances.
  https://github.com/aboutcode-org/scancode.io/pull/1294

v35.1.0 (2025-07-02)
--------------------

- Replace the ``setup.py``/``setup.cfg`` by ``pyproject.toml`` file.
  https://github.com/aboutcode-org/scancode.io/issues/1608

- Update scancode-toolkit to v32.4.0. See CHANGELOG for updates:
  https://github.com/aboutcode-org/scancode-toolkit/releases/tag/v32.4.0
  Adds a new ``git_sha1`` attribute to the ``CodebaseResource`` model as this
  is now computed and returned from the ``scancode-toolkit`` ``--info`` plugin.
  https://github.com/aboutcode-org/scancode.io/pull/1708

- Add a ``--fail-on-vulnerabilities`` option in ``check-compliance`` management command.
  When this option is enabled, the command will exit with a non-zero status if known
  vulnerabilities are detected in discovered packages and dependencies.
  Requires the ``find_vulnerabilities`` pipeline to be executed beforehand.
  https://github.com/aboutcode-org/scancode.io/pull/1702

- Enable ``--license-references`` scan option in the ``scan_single_package`` pipeline.
  The ``license_references`` and ``license_rule_references`` attributes will now be
  available in the scan results, including the details about detected licenses and
  license rules used during the scan.
  https://github.com/aboutcode-org/scancode.io/issues/1657

- Add a new step to the ``DeployToDevelop`` pipeline, ``map_python``, to match
  Cython source files (.pyx) to their compiled binaries.
  https://github.com/aboutcode-org/scancode.io/pull/1703

v35.0.0 (2025-06-23)
--------------------

- Add support for Python 3.13.
  Upgrade the base image in Dockerfile to ``python:3.13-slim``.
  https://github.com/aboutcode-org/scancode.io/pull/1469/files

- Display matched snippets details in "Resource viewer", including the package,
  resource, and similarity values.
  https://github.com/aboutcode-org/scancode.io/issues/1688

- Add filtering by label and pipeline in the ``flush-projects`` management command.
  Also, a new ``--dry-run`` option is available to test the filters before applying
  the deletion.
  https://github.com/aboutcode-org/scancode.io/pull/1690

- Add support for using Package URL (purl) as project input.
  This implementation is based on ``purl2url.get_download_url``.
  https://github.com/aboutcode-org/scancode.io/issues/1383

- Raise a ``MatchCodeIOException`` when the response from the MatchCode.io service is
  not valid in ``send_project_json_to_matchcode``.
  This generally means an issue on the MatchCode.io server side.
  https://github.com/aboutcode-org/scancode.io/issues/1665

- Upgrade Bulma CSS and Ace JS libraries to latest versions.
  Refine the CSS for the Resource viewer.
  https://github.com/aboutcode-org/scancode.io/pull/1692

- Add "(No value detected)" for Copyright and Holder charts.
  https://github.com/aboutcode-org/scancode.io/issues/1697

- Add "Package Compliance Alert" chart in the Policies section.
  https://github.com/aboutcode-org/scancode.io/pull/1699

- Update univers to v31.0.0, catch ``NotImplementedError`` in
  ``get_unique_unresolved_purls``, and properly log error in project.
  https://github.com/aboutcode-org/scancode.io/pull/1700
  https://github.com/aboutcode-org/scancode.io/pull/1701

v34.11.0 (2025-05-02)
---------------------

- Add a ``UUID`` field on the DiscoveredDependency model.
  Use the UUID for the DiscoveredDependency spdx_id for better SPDX compatibility.
  https://github.com/aboutcode-org/scancode.io/issues/1651

- Add MatchCode-specific functions to compute fingerprints from stemmed code
  files. Update CodebaseResource file content view to display snippet matches,
  if available, when the codebase has been sent for matching to MatchCode.
  https://github.com/aboutcode-org/scancode.io/pull/1656

- Add the ability to export filtered QuerySet of a FilterView into the JSON format.
  https://github.com/aboutcode-org/scancode.io/pull/1572

- Include ``ProjectMessage`` records in the JSON output ``headers`` section.
  https://github.com/aboutcode-org/scancode.io/issues/1659

v34.10.1 (2025-03-26)
---------------------

- Convert the ``declared_license`` field value return by ``python-inspector`` in
  ``resolve_pypi_packages``.
  Resolving requirements.txt files will now return proper license data.
  https://github.com/aboutcode-org/scancode.io/issues/1598

- Add support for installing on Apple Silicon (macOS ARM64) in dev mode.
  https://github.com/aboutcode-org/scancode.io/pull/1646

v34.10.0 (2025-03-21)
---------------------

- Rename the ``docker``, ``docker_windows``, and ``root_filesystem`` modules to
  ``analyze_docker``, ``analyze_docker_windows``, and ``analyze_root_filesystem``
  for consistency.

- Refine and document the Webhook system
  https://github.com/aboutcode-org/scancode.io/issues/1587
  * Add UI to add/delete Webhooks from the project settings
  * Add a new ``add-webhook`` management command
  * Add a ``add_webhook`` REST API action
  * Add a new ``SCANCODEIO_GLOBAL_WEBHOOK`` setting
  * Add a new chapter dedicated to Webhooks management in the documentation
  * Add support for custom payload dedicated to Slack webhooks

- Upgrade Bulma CSS library to version 1.0.2
  https://github.com/aboutcode-org/scancode.io/pull/1268

- Disable the creation of the global webhook in the ``batch-create`` command by default.
  The global webhook can be created by providing the ``--create-global-webhook`` option.
  A ``--no-global-webhook`` option was also added to the ``create-project`` command to
  provide the ability to skip the global webhook creation.
  https://github.com/aboutcode-org/scancode.io/pull/1629

- Add support for "Permission denied" file access in make_codebase_resource.
  https://github.com/aboutcode-org/scancode.io/issues/1630

- Refine the ``scan_single_package`` pipeline to work on git fetched inputs.
  https://github.com/aboutcode-org/scancode.io/issues/1376

v34.9.5 (2025-02-19)
--------------------

- Add support for the XLSX report in REST API.
  https://github.com/aboutcode-org/scancode.io/issues/1524

- Add options to the Project reset action.
  Also, the Project labels are kept during reset.
  https://github.com/aboutcode-org/scancode.io/issues/1568

- Add aboutcode.pipeline as an install_requires external dependency to prevent conflicts
  with other aboutcode submodules.
  https://github.com/aboutcode-org/scancode.io/issues/1423

- Add a ``add-webhook`` management command that allows to add webhook subscription on
  a project.
  https://github.com/aboutcode-org/scancode.io/issues/1587

- Add proper progress logging for the ``assemble`` section of the
  ``scan_for_application_packages``.
  https://github.com/aboutcode-org/scancode.io/issues/1601

v34.9.4 (2025-01-21)
--------------------

- Improve Project list page navigation.
  A top previous/next page navigation was added in the header for consistency with other
  list views.
  Any paginated view can now be navigated using the left/right keyboard keys.
  https://github.com/aboutcode-org/scancode.io/issues/1200

- Add support for importing the ``extra_data`` value from the JSON input with the
  ``load_inventory`` pipeline.
  When multiple JSON files are provided as inputs, the ``extra`` is prefixed with
  the input filename.
  https://github.com/aboutcode-org/scancode.io/issues/926

- Disable CycloneDX document strict validation, which halts the entire loading process,
  and let the data loading process handle the data issues.
  https://github.com/aboutcode-org/scancode.io/issues/1515

- Add a report action on project list to export XLSX containing packages from selected
  projects.
  https://github.com/aboutcode-org/scancode.io/issues/1437

- Add a download action on project list to enable bulk download of Project output files.
  https://github.com/aboutcode-org/scancode.io/issues/1518

- Add labels to Project level search.
  The labels are now always presented in alphabetical order for consistency.
  https://github.com/aboutcode-org/scancode.io/issues/1520

- Add a ``batch-create`` management command that allows to create multiple projects
  at once from a directory containing input files.
  https://github.com/aboutcode-org/scancode.io/issues/1437

- Do not download input_urls in management commands. The fetch/download is delegated to
  the pipeline execution.
  https://github.com/aboutcode-org/scancode.io/issues/1437

- Add a "TODOS" sheet containing on REQUIRES_REVIEW resources in XLSX.
  https://github.com/aboutcode-org/scancode.io/issues/1524

- Improve XLSX output for Vulnerabilities.
  Replace the ``affected_by_vulnerabilities`` field in the PACKAGES and DEPENDENCIES
  sheets with a dedicated VULNERABILITIES sheet.
  https://github.com/aboutcode-org/scancode.io/issues/1519

- Keep the InputSource objects when using ``reset`` on Projects.
  https://github.com/aboutcode-org/scancode.io/issues/1536

- Add a ``report`` management command that allows to generate XLSX reports for
  multiple projects at once using labels and searching by project name.
  https://github.com/aboutcode-org/scancode.io/issues/1524

- Add the ability to "select across" in Projects list when using the "select all"
  checkbox on paginated list.
  https://github.com/aboutcode-org/scancode.io/issues/1524

- Update scancode-toolkit to v32.3.2. See CHANGELOG for updates:
  https://github.com/aboutcode-org/scancode-toolkit/releases/tag/v32.3.2
  https://github.com/aboutcode-org/scancode-toolkit/releases/tag/v32.3.1

- Adds  a project settings ``scan_max_file_size`` and a scancode.io settings field
  ``SCANCODEIO_SCAN_MAX_FILE_SIZE`` to skip scanning files above a certain
  file size (in bytes) as a temporary fix for large memory spikes while
  scanning for licenses in certain large files.
  https://github.com/aboutcode-org/scancode-toolkit/issues/3711

v34.9.3 (2024-12-31)
--------------------

- Refine the available settings for RQ_QUEUES:
  * Rename the RQ_QUEUES sub-settings to SCANCODEIO_RQ_REDIS_*
  * Add SCANCODEIO_RQ_REDIS_SSL setting to enable SSL.
  https://github.com/aboutcode-org/scancode.io/issues/1465

- Add support to map binaries to source files using symbols
  for rust binaries and source files. This adds also using
  ``rust-inspector`` to extract symbols from rust binaries.
  This is a new optional ``Rust`` step in the
  ``map_deploy_to_develop`` pipeline.
  https://github.com/aboutcode-org/scancode.io/issues/1435

v34.9.2 (2024-12-10)
--------------------

- Fix an issue with the ``scan_rootfs_for_system_packages`` pipe when a namespace is
  missing for the discovered packages.
  https://github.com/aboutcode-org/scancode.io/issues/1462

v34.9.1 (2024-12-09)
--------------------

- Add the ability to filter on Project endpoint API actions.
  The list of ``resources``, ``packages``, ``dependencies``, ``relations``, and
  ``messages`` can be filtered providing the ``?field_name=value`` in the URL
  parameters.
  https://github.com/aboutcode-org/scancode.io/issues/1449

- Fix the ability to provide multiple optional step when defining pipelines in the
  REST API.
  The support for providing pipeline names as a comma-separated single string was
  remove as the comma is used as the optional step separator.
  Use a list of pipeline names instead.
  https://github.com/aboutcode-org/scancode.io/issues/1454

- Make the header row of tables sticky to the top of the screen so it is always
  visible.
  https://github.com/aboutcode-org/scancode.io/issues/1457

v34.9.0 (2024-11-14)
--------------------

- Add ability to declared pipeline selected groups in create project REST API endpoint.
  https://github.com/aboutcode-org/scancode.io/issues/1426

- Add a new ``list-pipelines`` management command.
  https://github.com/aboutcode-org/scancode.io/issues/1397

- Refactor the policies related code to its own module.
  https://github.com/aboutcode-org/scancode.io/issues/386

- Add support for project-specific license policies and compliance alerts.
  Enhance Project model to handle policies from local settings, project input
  "policies.yml" files, or global app settings.
  https://github.com/aboutcode-org/scancode.io/issues/386

- Refactor the ``group`` decorator for pipeline steps as ``optional_step``.
  The steps decorated as optional are not included by default anymore.
  https://github.com/aboutcode-org/scancode.io/issues/386

- Add a new ``PublishToFederatedCode`` pipeline (addon) to push scan result
  to FederatedCode.
  https://github.com/nexB/scancode.io/pull/1400

- Add new ``purl`` field to project model. https://github.com/nexB/scancode.io/pull/1400

v34.8.3 (2024-10-30)
--------------------

- Include the ``aboutcode`` module in the wheel and source distribution.
  https://github.com/aboutcode-org/scancode.io/issues/1423

- Update ScanCode-toolkit to v32.3.0
  https://github.com/aboutcode-org/scancode.io/issues/1418

v34.8.2 (2024-10-28)
--------------------

- Add ``android_analysis`` to ``extra_requires``. This installs the package
  ``android_inspector``, which provides a pipeline for Android APK
  deploy-to-development analysis.

- Remove the sleep time in the context of testing ``matchcode.poll_run_url_status``
  to speed up the test.
  https://github.com/aboutcode-org/scancode.io/issues/1411

- Add ability to specify the CycloneDX output spec version using the ``output``
  management command and providing the ``cyclonedx:VERSION`` syntax as format value.
  https://github.com/aboutcode-org/scancode-action/issues/8

- Add new ``compliance`` REST API action that list all compliance alert for a given
  project. The severity level can be provided using the
  ``?fail_level={ERROR,WARNING,MISSING}`` parameter.
  https://github.com/aboutcode-org/scancode.io/issues/1346

- Add new ``Compliance alerts`` panel in the project detail view.
  https://github.com/aboutcode-org/scancode.io/issues/1346

v34.8.1 (2024-09-06)
--------------------

- Upgrade Django to security release 5.1.1 and related dependencies.

v34.8.0 (2024-08-15)
--------------------

- Add a new ``enrich_with_purldb`` add-on pipeline to enrich the discovered packages
  with data available in the PurlDB.
  https://github.com/nexB/scancode.io/issues/1182

- Add the ability to define a results_url on the Pipeline class.
  When available, that link is displayed in the UI to easily reach the results view
  related to the Pipeline run.
  https://github.com/nexB/scancode.io/pull/1330

- Expands on the existing WebhookSubscription model by adding a few fields to
  configure the behavior of the Webhooks, and moves some of the fields to a new
  WebhookDelivery model, which captures the results of a WebhookSubscription
  "delivery".
  https://github.com/nexB/scancode.io/issues/1325

- Add support for creating dependencies using the ``load_sboms`` pipeline on CycloneDX
  SBOM inputs.
  https://github.com/nexB/scancode.io/issues/1145

- Add a new Dependency view that renders the project dependencies as a tree.
  https://github.com/nexB/scancode.io/issues/1145

- The ``purldb-scan-worker`` command has been updated to send project results
  back using the Project webhook subscriptions. This allows us to not have the
  main task loop to monitor a single project run for completion in order to
  return data, and allows us to have multiple scan projects active at once while
  we use ``purldb-scan-worker``. A new option ``--max-concurrent-projects`` has
  been added to set the number of purldb packages that can be requested and
  processed at once.
  https://github.com/nexB/scancode.io/issues/1287

- Add notes field on the DiscoveredPackage model.
  https://github.com/nexB/scancode.io/issues/1342

- Fix an issue with conflicting groups checkbox id in the Add pipeline modal.
  https://github.com/nexB/scancode.io/issues/1353

- Move the BasePipeline class to a new `aboutcode.pipeline` module.
  https://github.com/nexB/scancode.io/issues/1351

- Update link references of ownership from nexB to aboutcode-org
  https://github.com/aboutcode-org/scancode.io/issues/1350

- Add a new ``check-compliance`` management command to check for compliance issues in
  a project.
  https://github.com/nexB/scancode.io/issues/1182

- Fix issues in ``match_to_matchcode`` where the incorrect polling function was
  used and match results were not properly collected.

v34.7.1 (2024-07-15)
--------------------

- Add pipeline step selection for a run execution.
  This allows to run a pipeline in an advanced mode allowing to skip some steps,
  or restart from a step, like the last failed step.
  The steps can be edited from the Run "status" modal using the "Select steps" button.
  This is an advanced feature and should we used with caution.
  https://github.com/nexB/scancode.io/issues/1303

- Display the resolved_to_package as link in the dependencies tab.
  https://github.com/nexB/scancode.io/pull/1314

- Add support for multiple instances of a PackageURL in the CycloneDX outputs.
  The `package_uid` is now included in each BOM Component as a property.
  https://github.com/nexB/scancode.io/issues/1316

- Add administration interface. Can be enabled with the SCANCODEIO_ENABLE_ADMIN_SITE
  setting.
  Add ``--admin`` and ``--super`` options to the ``create-user`` management command.
  https://github.com/nexB/scancode.io/pull/1323

- Add ``results_url`` and ``summary_url`` on the API ProjectSerializer.
  https://github.com/nexB/scancode.io/issues/1325

v34.7.0 (2024-07-02)
--------------------

- Add all "classify" plugin fields from scancode-toolkit on the CodebaseResource model.
  https://github.com/nexB/scancode.io/issues/1275

- Refine the extraction errors reporting to include the resource path for rendering
  link to the related resources in the UI.
  https://github.com/nexB/scancode.io/issues/1273

- Add a ``flush-projects`` management command, to Delete all project data and their
  related work directories created more than a specified number of days ago.
  https://github.com/nexB/scancode.io/issues/1289

- Update the ``inspect_packages`` pipeline to have an optional ``StaticResolver``
  group to create resolved packages and dependency relationships from lockfiles
  and manifests having pre-resolved dependencies. Also update this pipeline to
  perform package assembly from multiple manifests and files to create
  discovered packages. Also update the ``resolve_dependencies`` pipeline to have
  the same ``StaticResolver`` group and mode the dynamic resolution part to a new
  optional ``DynamicResolver`` group.
  See https://github.com/nexB/scancode.io/pull/1244

- Add a new attribute ``is_direct`` to the DiscoveredDependency model and two new
  attributes ``is_private`` and ``is_virtual`` to the DiscoveredPackage model.
  Also update the UIs to show these attributes and show the ``package_data`` field
  contents for CodebaseResources in the ``extra_data`` tab.
  See https://github.com/nexB/scancode.io/pull/1244

- Update scancode-toolkit to version ``32.2.1``. For the complete list of updates
  and improvements see https://github.com/nexB/scancode-toolkit/releases/tag/v32.2.0
  and https://github.com/nexB/scancode-toolkit/releases/tag/v32.2.1

- Add support for providing pipeline "selected_groups" in the ``run`` entry point.
  https://github.com/nexB/scancode.io/issues/1306

v34.6.3 (2024-06-21)
--------------------

- Use the ``--option=value`` syntax for args entries in place of ``--option value``
  for fetching Docker images using skopeo through ``run_command_safely`` calls.
  https://github.com/nexB/scancode.io/issues/1257

- Fix an issue in the d2d JavaScript mapper.
  https://github.com/nexB/scancode.io/pull/1274

- Add support for a ``ignored_vulnerabilities`` field on the Project configuration.
  https://github.com/nexB/scancode.io/issues/1271

v34.6.2 (2024-06-18)
--------------------

- Store SBOMs headers in the `Project.extra_data` field during the load_sboms
  pipeline.
  https://github.com/nexB/scancode.io/issues/1253

- Add support for fetching Git repository as Project input.
  https://github.com/nexB/scancode.io/issues/921

- Enhance the logging and reporting of input fetch exceptions.
  https://github.com/nexB/scancode.io/issues/1257

v34.6.1 (2024-06-07)
--------------------

- Remove print statements from migration files.
- Display full traceback on error in the ``execute`` management command.
- Log the Project message creation.
- Refactor the ``get_env_from_config_file`` to support empty config file.

v34.6.0 (2024-06-07)
--------------------

- Add a new ``scan_for_virus`` add-on pipeline based on ClamAV scan.
  Found viruses are stored as "error" Project messages and on their related codebase
  resource instance using the ``extra_data`` field.
  https://github.com/nexB/scancode.io/issues/1182

- Add ability to filter by tag on the resource list view.
  https://github.com/nexB/scancode.io/issues/1217

- Use "unknown" as the Package URL default type when no values are provided for that
  field. This allows to create a discovered package instance instead of raising a
  Project error message.
  https://github.com/nexB/scancode.io/issues/1249

- Rename DiscoveredDependency ``resolved_to`` to ``resolved_to_package``, and
  ``resolved_dependencies`` to ``resolved_from_dependencies`` for clarity and
  consistency.
  Add ``children_packages`` and ``parent_packages`` ManyToMany field on the
  DiscoveredPackage model.
  Add full dependency tree in the CycloneDX output.
  https://github.com/nexB/scancode.io/issues/1066

- Add a new ``run`` entry point for executing pipeline as a single command.
  https://github.com/nexB/scancode.io/pull/1256

- Generate a DiscoveredPackage.package_uid in create_from_data when not provided.
  https://github.com/nexB/scancode.io/issues/1256

v34.5.0 (2024-05-22)
--------------------

- Display the current path location in the "Codebase" panel as a navigation breadcrumbs.
  https://github.com/nexB/scancode.io/issues/1158

- Fix a rendering issue in the dependency details view when for_package or
  datafile_resource fields do not have a value.
  https://github.com/nexB/scancode.io/issues/1177

- Add a new `CollectPygmentsSymbolsAndStrings` pipeline (addon) for collecting source
  symbol, string and comments using Pygments.
  https://github.com/nexB/scancode.io/pull/1179

- Workaround an issue with the cyclonedx-python-lib that does not allow to load
  SBOMs that contains properties with no values.
  Also, a few fixes pre-validation are applied before deserializing thr SBOM for
  maximum compatibility.
  https://github.com/nexB/scancode.io/issues/1185
  https://github.com/nexB/scancode.io/issues/1230

- Add a new `CollectTreeSitterSymbolsAndStrings` pipeline (addon) for collecting source
  symbol and string using tree-sitter.
  https://github.com/nexB/scancode.io/pull/1181

- Fix `inspect_packages` pipeline to properly link discovered packages and dependencies to
  codebase resources of package manifests where they were found. Also correctly assign
  the datasource_ids attribute for packages and dependencies.
  https://github.com/nexB/scancode.io/pull/1180

- Add "Product name" and "Product version" as new project settings.
  https://github.com/nexB/scancode.io/issues/1197

- Add "Product name" and "Product version" as new project settings.
  https://github.com/nexB/scancode.io/issues/1197

- Raise the minimum RAM required per CPU code in the docs.
  A good rule of thumb is to allow **2 GB of memory per CPU**.
  For example, if Docker is configured for 8 CPUs, a minimum of 16 GB of memory is
  required.
  https://github.com/nexB/scancode.io/issues/1191

- Add value validation for the search complex query syntax.
  https://github.com/nexB/scancode.io/issues/1183

- Bump matchcode-toolkit version to v5.0.0.

- Fix the content of the ``package_url`` field in CycloneDX outputs.
  https://github.com/nexB/scancode.io/issues/1224

- Enhance support for encoded ``package_url`` during the conversion to model fields.
  https://github.com/nexB/scancode.io/issues/1171

- Remove the ``scancode_license_score`` option from the Project configuration.
  https://github.com/nexB/scancode.io/issues/1231

- Remove the ``extract_recursively`` option from the Project configuration.
  https://github.com/nexB/scancode.io/issues/1236

- Add support for a ``ignored_dependency_scopes`` field on the Project configuration.
  https://github.com/nexB/scancode.io/issues/1197

- Add support for storing the scancode-config.yml file in codebase.
  The scancode-config.yml file can be provided as a project input, or can be located
  in the codebase/ immediate subdirectories. This allows to provide the configuration
  file as part of an input archive or a git clone for example.
  https://github.com/nexB/scancode.io/issues/1236

- Provide a downloadable YAML scancode-config.yml template in the documentation.
  https://github.com/nexB/scancode.io/issues/1197

- Add support for CycloneDX SBOM component properties as generated by external tools.
  For example, the ``ResolvedUrl`` generated by cdxgen is now imported as the package
  ``download_url``.

v34.4.0 (2024-04-22)
--------------------

- Upgrade Gunicorn to v22.0.0 security release.

- Display the list of fields available for the advanced search syntax in the modal UI.
  https://github.com/nexB/scancode.io/issues/1164

- Add support for CycloneDX 1.6 outputs and inputs.
  Also, the CycloneDX outputs can be downloaded as 1.6, 1.5, and 1.4 spec versions.
  https://github.com/nexB/scancode.io/pull/1165

- Update matchcode-toolkit to v4.1.0

- Add a new function
  `scanpipe.pipes.matchcode.fingerprint_codebase_resources()`, which computes
  approximate file matching fingerprints for text files using the new
  `get_file_fingerprint_hashes` function from matchcode-toolkit.

- Rename the `purldb-scan-queue-worker` management command to `purldb-scan-worker`.

- Add `docker-compose.purldb-scan-worker.yml` to run ScanCode.io as a PurlDB
  scan worker service.

v34.3.0 (2024-04-10)
--------------------

- Associate resolved packages with their source codebase resource.
  https://github.com/nexB/scancode.io/issues/1140

- Add a new `CollectSourceStrings` pipeline (addon) for collecting source string using
  xgettext.
  https://github.com/nexB/scancode.io/pull/1160

v34.2.0 (2024-03-28)
--------------------

- Add support for Python 3.12 and upgrade to Python 3.12 in the Dockerfile.
  https://github.com/nexB/scancode.io/pull/1138

- Add support for CycloneDX XML inputs.
  https://github.com/nexB/scancode.io/issues/1136

- Upgrade the SPDX schema to v2.3.1
  https://github.com/nexB/scancode.io/issues/1130

v34.1.0 (2024-03-27)
--------------------

- Add support for importing CycloneDX SBOM 1.2, 1.3, 1.4 and 1.5 spec formats.
  https://github.com/nexB/scancode.io/issues/1045

- The pipeline help modal is now available from all project views: form, list, details.
  The docstring are converted from markdown to html for proper rendering.
  https://github.com/nexB/scancode.io/pull/1105

- Add a new `CollectSymbols` pipeline (addon) for collecting codebase symbols using
  Universal Ctags.
  https://github.com/nexB/scancode.io/pull/1116

- Capture errors during the `inspect_elf_binaries` pipeline execution.
  Errors on resource inspection are stored as project error message instead of global
  pipeline failure.
  The problematic resource path is stored in the message details and displayed in the
  message list UI as a link to the resource details view.
  https://github.com/nexB/scancode.io/issues/1121
  https://github.com/nexB/scancode.io/issues/1122

- Use the `package_only` option in scancode `get_package_data` API in
  `inspect_packages` pipeline, to skip license and copyright detection in
  extracted license and copyright statements found in package metadata.
  https://github.com/nexB/scancode-toolkit/pull/3689

- Rename the ``match_to_purldb`` pipeline to ``match_to_matchcode``, and add
  MatchCode.io API settings to ScanCode.io settings.

- In the DiscoveredPackage model, rename the "datasource_id" attribute to
  "datasource_ids" and add a new attribute "datafile_paths". This is aligned
  with the scancode-toolkit Package model, and package detection information
  is now stored correctly. Also update the UI for discovered packages to
  show the corresponding package datafiles and their datasource IDs.
  A data migration is included to facilitate the migration of existing data.
  https://github.com/nexB/scancode.io/issues/1099

- Add PurlDB tab, displayed when the PURLDB_URL settings is configured.
  When loading the package details view, a request is made on the PurlDB to fetch and
  and display any available data.
  https://github.com/nexB/scancode.io/issues/1125

- Create a new management command `purldb-scan-queue-worker`, that runs
  scancode.io as a Package scan queue worker for PurlDB.
  `purldb-scan-queue-worker` gets the next available Package to be scanned and
  the list of pipeline names to be run on the Package from PurlDB, creates a
  Project, fetches the Package, runs the specified pipelines, and returns the
  results to PurlDB.
  https://github.com/nexB/scancode.io/pull/1078
  https://github.com/nexB/purldb/issues/236

- Update matchcode-toolkit to v4.0.0

v34.0.0 (2024-03-04)
--------------------

- Add ability to "group" pipeline steps to control their inclusion in a pipeline run.
  The groups can be selected in the UI, or provided using the
  "pipeline_name:group1,group2" syntax in CLI and REST API.
  https://github.com/nexB/scancode.io/issues/1045

- Refine pipeline choices in the "Add pipeline" modal based on the project context.
   * When there is at least one existing pipeline in the project, the modal now includes
     all addon pipelines along with the existing pipeline for selection.
   * In cases where no pipelines are assigned to the project, the modal displays all
     base (non-addon) pipelines for user selection.

   https://github.com/nexB/scancode.io/issues/1071

- Rename pipeline for consistency and precision:
  * scan_codebase_packages: inspect_packages

  Restructure the inspect_manifest pipeline into:
  * load_sbom: for loading SPDX/CycloneDX SBOMs and ABOUT files
  * resolve_dependencies: for resolving package dependencies
  * inspect_packages: gets package data from package manifests/lockfiles

  A data migration is included to facilitate the migration of existing data.
  Only the new names are available in the web UI but the REST API and CLI are backward
  compatible with the old names.
  https://github.com/nexB/scancode.io/issues/1034
  https://github.com/nexB/scancode.io/discussions/1035

- Remove "packageFileName" entry from SPDX output.
  https://github.com/nexB/scancode.io/issues/1076

- Add an add-on pipeline for collecting DWARF debug symbol compilation
  unit paths when available from elfs.
  https://github.com/nexB/purldb/issues/260

- Extract all archives recursively in the `scan_single_package` pipeline.
  https://github.com/nexB/scancode.io/issues/1081

- Add URL scheme validation with explicit error messages for input URLs.
  https://github.com/nexB/scancode.io/issues/1047

- All supported `output_format` can now be downloaded using the results_download API
  action providing a value for the new `output_format` parameter.
  https://github.com/nexB/scancode.io/issues/1091

- Add settings related to fetching private files. Those settings allow to
  define credentials for various authentication types.
  https://github.com/nexB/scancode.io/issues/620
  https://github.com/nexB/scancode.io/issues/203

- Update matchcode-toolkit to v3.0.0

v33.1.0 (2024-02-02)
--------------------

- Rename multiple pipelines for consistency and precision:
   * docker: analyze_docker_image
   * root_filesystems: analyze_root_filesystem_or_vm_image
   * docker_windows: analyze_windows_docker_image
   * inspect_manifest: inspect_packages
   * deploy_to_develop: map_deploy_to_develop
   * scan_package: scan_single_package

  A data migration is included to facilitate the migration of existing data.
  Only the new names are available in the web UI but the REST API and CLI are backward
  compatible with the old names.
  https://github.com/nexB/scancode.io/issues/1044

- Generate CycloneDX SBOM in 1.5 spec format, migrated from 1.4 previously.
  The Package vulnerabilities are now included in the CycloneDX SBOM when available.
  https://github.com/nexB/scancode.io/issues/807

- Improve the inspect_manifest pipeline to accept archives as inputs.
  https://github.com/nexB/scancode.io/issues/1034

- Add support for "tagging" download URL inputs using the "#<fragment>" section of URLs.
  This feature is particularly useful in the map_develop_to_deploy pipeline when
  download URLs are utilized as inputs. Tags such as "from" and "to" can be specified
  by adding "#from" or "#to" fragments at the end of the download URLs.
  Using the CLI, the uploaded files can be tagged using the "filename:tag" syntax
  while using the `--input-file` arguments.
  In the UI, tags can be edited from the Project details view "Inputs" panel.
  On the REST API, a new `upload_file_tag` field is available to use along the
  `upload_file`.
  https://github.com/nexB/scancode.io/issues/708

v33.0.0 (2024-01-16)
--------------------

- Upgrade Django to version 5.0 and drop support for Python 3.8 and 3.9
  https://github.com/nexB/scancode.io/issues/1020

- Fetching "Download URL" inputs is now delegated to an initial pipeline step that is
  always run as the start of a pipeline.
  This allows to run pipelines on workers running from a remote location, external to
  the main ScanCode.io app server.
  https://github.com/nexB/scancode.io/issues/410

- Migrate the Project.input_sources field into a InputSource model.
  https://github.com/nexB/scancode.io/issues/410

- Refactor run_scancode to not fail on scan errors happening at the resource level,
  such as a timeout. Project error message are created instead.
  https://github.com/nexB/scancode.io/issues/1018

- Add support for the SCANCODEIO_SCAN_FILE_TIMEOUT setting in the scan_package pipeline.
  https://github.com/nexB/scancode.io/issues/1018

- Add support for non-archive single file in the scan_package pipeline.
  https://github.com/nexB/scancode.io/issues/1009

- Do not include "add-on" pipelines in the "New project" form choices.
  https://github.com/nexB/scancode.io/issues/1041

- Display a "Run pipelines" button in the "Pipelines" panel.
  Remove the ability to run a single pipeline in favor of running all "not started"
  project pipeline.
  https://github.com/nexB/scancode.io/issues/997

- In "map_deploy_to_develop" pipeline, add support for path patterns
  in About file attributes documenting resource paths.
  https://github.com/nexB/scancode.io/issues/1004

- Fix an issue where the pipeline details cannot be fetched when using URLs that
  include credentials such as "user:pass@domain".
  https://github.com/nexB/scancode.io/issues/998

- Add a new pipeline, ``match_to_purldb``, that check CodebaseResources of a
  Project against PurlDB for Package matches.

v32.7.0 (2023-10-25)
--------------------

- Display the ``Run.scancodeio_version`` in the Pipeline run modal.
  When possible this value is displayed as a link to the diff view between the current
  ScanCode.io version and the version used when the Pipeline was run.
  https://github.com/nexB/scancode.io/issues/956

- Improve presentation of the "Resources detected license expressions" project section.
  https://github.com/nexB/scancode.io/issues/937

- Add ability to sort by Package URL in package list
  https://github.com/nexB/scancode.io/issues/938

- Fix an issue where the empty project settings were overriding the settings loaded
  from a config file.
  https://github.com/nexB/scancode.io/issues/961

- Control the execution order of Pipelines within a Project. Pipelines are not allowed
  to start anymore unless all the previous ones within a Project have completed.
  https://github.com/nexB/scancode.io/issues/901

- Add support for webhook subscriptions in project clone.
  https://github.com/nexB/scancode.io/pull/910

- Add resources license expression summary panel in the project details view.
  This panel displays the list of licenses detected in the project and include links
  to the resources list.
  https://github.com/nexB/scancode.io/pull/355

- Add the ``tag`` field on the DiscoveredPackage model. This new field is used to store
  the layer id where the package was found in the Docker context.
  https://github.com/nexB/scancode.io/issues/919

- Add to apply actions, such as archive, delete, and reset to a selection of project
  from the main list.
  https://github.com/nexB/scancode.io/issues/488

- Add new "Outputs" panel in the Project details view.
  Output files are listed and can be downloaded from the panel.
  https://github.com/nexB/scancode.io/issues/678

- Add a step in the ``deploy_to_develop`` pipelines to create "local-files" packages
  with from-side resource files that have one or more relations with to-side resources
  that are not part of a package.
  This allows to include those files in the SBOMs and attribution outputs.
  https://github.com/nexB/scancode.io/issues/914

- Enable sorting the packages list by resources count.
  https://github.com/nexB/scancode.io/issues/978

v32.6.0 (2023-08-29)
--------------------

- Improve the performance of the codebase relations list view to support large number
  of entries.
  https://github.com/nexB/scancode.io/issues/858

- Improve DiscoveredPackageListView query performances refining the prefetch_related.
  https://github.com/nexB/scancode.io/issues/856

- Fix the ``map_java_to_class`` d2d pipe to skip if no ``.java`` file is found.
  https://github.com/nexB/scancode.io/issues/853

- Enhance Package search to handle full ``pkg:`` purls and segment of purls.
  https://github.com/nexB/scancode.io/issues/859

- Add a new step in the ``deploy_to_develop`` pipeline where we tag archives as
  processed, if all the resources in their extracted directory is mapped/processed.
  https://github.com/nexB/scancode.io/issues/827

- Add the ability to clone a project.
  https://github.com/nexB/scancode.io/issues/874

- Improve perceived display performance of projects charts and stats on home page.
  The charts are displayed when the number of resources or packages are less than
  5000 records. Else, a button to load the charts is displayed.
  https://github.com/nexB/scancode.io/issues/844

- Add advanced search query system to all list views.
  Refer to the documentation for details about the search syntax.
  https://github.com/nexB/scancode.io/issues/871

- Migrate the ProjectError model to a global ProjectMessage.
  3 level of severity available: INFO, WARNING, and ERROR.
  https://github.com/nexB/scancode.io/issues/338

- Add label/tag system that can be used to group and filters projects.
  https://github.com/nexB/scancode.io/issues/769

v32.5.2 (2023-08-14)
--------------------

Security release: This release addresses the security issue detailed below.
We encourage all users of ScanCode.io to upgrade as soon as possible.

- GHSA-6xcx-gx7r-rccj: Reflected Cross-Site Scripting (XSS) in license endpoint
  The ``license_details_view`` function was subject to cross-site scripting (XSS)
  attack due to inadequate validation and sanitization of the key parameter.
  The license views were migrated class-based views are the inputs are now properly
  sanitized.
  Credit to @0xmpij for reporting the vulnerability.
  https://github.com/nexB/scancode.io/security/advisories/GHSA-6xcx-gx7r-rccj
  https://github.com/nexB/scancode.io/issues/847

- Add bandit analyzer and Django "check --deploy"  to the check/validation stack.
  This helps to ensure that we do not introduce know code vulnerabilities and
  deployment issues to the codebase.
  https://github.com/nexB/scancode.io/issues/850

- Migrate the run_command function into a safer usage of the subprocess module.
  Also fix various warnings returned by the bandit analyzer.
  https://github.com/nexB/scancode.io/issues/850

- Replace the ``scancode.run_scancode`` function by a new ``run_scan`` that interact
  with scancode-toolkit scanners without using subprocess. This new function is used
  in the ``scan_package`` pipeline.
  The ``SCANCODE_TOOLKIT_CLI_OPTIONS`` settings was renamed
  ``SCANCODE_TOOLKIT_RUN_SCAN_ARGS``. Refer to the documentation for the next "dict"
  syntax.
  https://github.com/nexB/scancode.io/issues/798

v32.5.1 (2023-08-07)
--------------------

Security release: This release addresses the security issue detailed below.
We encourage all users of ScanCode.io to upgrade as soon as possible.

- GHSA-2ggp-cmvm-f62f: Command injection in docker image fetch process
  The ``fetch_docker_image`` function was subject to potential injection attack.
  The user inputs are now sanitized before calling the subprocess function.
  Credit to @0xmpij for reporting the vulnerability.
  https://github.com/nexB/scancode.io/security/advisories/GHSA-2ggp-cmvm-f62f

---

- Add support for multiple input URLs, and adding multiple pipelines in the project
  creation REST API.
  https://github.com/nexB/scancode.io/issues/828

- Update the ``fetch_vulnerabilities`` pipe to make the API requests by batch of purls.
  https://github.com/nexB/scancode.io/issues/835

- Add vulnerability support for discovered dependencies.
  The dependency data is loaded using the ``find_vulnerabilities`` pipeline backed by
  a VulnerableCode database.
  https://github.com/nexB/scancode.io/issues/835

- Fix root filesystem scanning for installed packages and archived Linux distributions.
  Allows the scan to discover system packages from `rpmdb.sqlite` and other sources.
  https://github.com/nexB/scancode.io/pull/840

v32.5.0 (2023-08-02)
--------------------

WARNING: After upgrading the ScanCode.io codebase to this version,
and following the ``docker compose build``,
the permissions of the ``/var/scancodeio/`` directory of the Docker volumes require
to be updated for the new ``app`` user, using:
``docker compose run -u 0:0 web chown -R app:app /var/scancodeio/``

- Run Docker as non-root user using virtualenv.
  WARNING: The permissions of the ``/var/scancodeio/`` directory in the Docker volumes
  require to be updated for the new ``app`` user.
  https://github.com/nexB/scancode.io/issues/399

- Add column sort and filters in dependency list view.
  https://github.com/nexB/scancode.io/issues/823

- Add a new ``ScanCodebasePackage`` pipeline to scan a codebase for packages only.
  https://github.com/nexB/scancode.io/issues/815

- Add new ``outputs`` REST API action that list projects output files including an URL
  to download the file.
  https://github.com/nexB/scancode.io/issues/678

- Add support for multiple to/from input files in the ``deploy_to_develop`` pipeline.
  https://github.com/nexB/scancode.io/issues/813

- Add the ability to delete and download project inputs.
  Note that the inputs cannot be modified (added or deleted) once a pipeline run as
  started on the project.
  https://github.com/nexB/scancode.io/issues/813

- Fix root_filesystem data structure stored on the Project ``extra_data`` field.
  This was causing a conflict with the expected docker images data structure
  when generating an XLSX output.
  https://github.com/nexB/scancode.io/issues/824

- Fix the SPDX output to include missing detailed license texts for LicenseRef.
  Add ``licensedb_url`` and ``scancode_url`` to the SPDX ``ExtractedLicensingInfo``
  ``seeAlsos``.
  Include the ``Package.notice_text`` as the SPDX ``attribution_texts``.
  https://github.com/nexB/scancode.io/issues/841

v32.4.0 (2023-07-13)
--------------------

- Add support for license policies and complaince alert for Discovered Packages.
  https://github.com/nexB/scancode.io/issues/151

- Refine the details views and tabs:
  - Add a "Relations" tab in the Resource details view
  - Disable empty tabs by default
  - Display the count of items in the tab label
  - Improve query performances for details views
  https://github.com/nexB/scancode.io/issues/799

- Upgrade vulnerablecode integration:
  - Add ``affected_by_vulnerabilities`` field on ``DiscoveredPackage`` model.
  - Add UI for showing package vulnerabilities in details view.
  - Add packages filtering by ``is_vulnerable``.
  - Include vulnerability data in the JSON results.
  https://github.com/nexB/scancode.io/issues/600

- Add multiple new filtering option to list views table headers.
  Refactored the way to define filters using the table_columns view attribute.
  https://github.com/nexB/scancode.io/issues/216
  https://github.com/nexB/scancode.io/issues/580
  https://github.com/nexB/scancode.io/issues/506

- Update the CycloneDX BOM download file extension from ``.bom.json`` to ``.cdx.json``.
  https://github.com/nexB/scancode.io/issues/785

- SPDX download BOM do not include codebase resource files by default anymore.
  https://github.com/nexB/scancode.io/issues/785

- Add archive_location to the LAYERS worksheet of XLSX output.
  https://github.com/nexB/scancode.io/issues/773

- Add "New Project" button to Project details view.
  https://github.com/nexB/scancode.io/issues/763

- Display image type files in the codebase resource details view in a new "Image" tab.

- Add ``slug`` field on the Project model. That field is used in URLs instead of the
  ``uuid``.
  https://github.com/nexB/scancode.io/issues/745

- Fix the ordering of the Codebase panel in the Project details view.
  https://github.com/nexB/scancode.io/issues/795

- Do not rely on the internal ``id`` PK for package and dependency details URLs.
  Package details URL is now based on ``uuid`` and the dependency details URL is based
  on ``dependency_uid``.
  https://github.com/nexB/scancode.io/issues/331

- Add a "License score" project setting that can be used to limit the returned license
  matches with a score above the provided one.
  This is leveraging the ScanCode-toolkit ``--license-score`` option, see:
  https://scancode-toolkit.readthedocs.io/en/stable/cli-reference/basic-options.html#license-score-option
  https://github.com/nexB/scancode.io/issues/335

v32.3.0 (2023-06-12)
--------------------

- Upgrade ScanCode-toolkit to latest v32.0.x
  Warning: This upgrade requires schema and data migrations (both included).
  It is recommended to reset and re-run the pipelines to benefit from the latest
  ScanCode detection improvements.
  Refer to https://github.com/nexB/scancode-toolkit/blob/develop/CHANGELOG.rst#v3200-next-roadmap
  for the full list of changes.
  https://github.com/nexB/scancode.io/issues/569

- Add a new ``deploy_to_develop`` pipeline specialized in creating relations between
  the development source code and binaries or deployed code.
  This pipeline is expecting 2 archive files with "from-" and "to-" filename prefixes
  as inputs:
  1. "from-[FILENAME]" archive containing the development source code
  2. "to-[FILENAME]" archive containing the deployment compiled code
  https://github.com/nexB/scancode.io/issues/659

- Add ability to configure a Project through a new "Settings" form in the UI or by
  providing a ".scancode-config.yml" configuration file as one of the Project inputs.
  The "Settings" form allows to rename a Project, add and edit the notes, as well
  as providing a list of patterns to be ignored during pipeline runs, the choice of
  extracting archives recursively, and the ability to provide a custom template for
  attribution.
  https://github.com/nexB/scancode.io/issues/685
  https://github.com/nexB/scancode.io/issues/764

- Add ``notes`` field on the Project model. Notes can be updated from the Project
  settings form. Also, notes can be provided while creating a project through the CLI
  using the a new ``--notes`` option.
  https://github.com/nexB/scancode.io/issues/709

- Add a mapper function to relate .ABOUT files during the d2d pipeline.
  https://github.com/nexB/scancode.io/issues/740

- Enhance the file viewer UI of the resource details view.
  A new search for the file content was added.
  Also, it is now possible to expand the file viewer in full screen mode.
  https://github.com/nexB/scancode.io/issues/724

- Refine the breadcrumb UI for details view.
  https://github.com/nexB/scancode.io/issues/717

- Move the "Resources status" panel from the run modal to the project details view.
  https://github.com/nexB/scancode.io/issues/370

- Improve the speed of Project ``reset`` and ``delete`` using the _raw_delete model API.
  https://github.com/nexB/scancode.io/issues/729

- Specify ``update_fields`` during each ``save()`` related to Run tasks,
  to force a SQL UPDATE in order to avoid any data loss when the model fields are
  updated during the task execution.
  https://github.com/nexB/scancode.io/issues/726

- Add support for XLSX input in the ``load_inventory`` pipeline.
  https://github.com/nexB/scancode.io/issues/735

- Add support for unknown licenses in attribution output.
  https://github.com/nexB/scancode.io/issues/749

- Add ``License`` objects to each of the package for attribution generation.
  https://github.com/nexB/scancode.io/issues/775

- The "Codebase" panel can now be used to browse the Project's codebase/ directory
  and open related resources details view.
  https://github.com/nexB/scancode.io/issues/744

v32.2.0 (2023-04-25)
--------------------

- Enhance the ``update_or_create_package`` pipe and add the ability to assign multiple
  codebase resources at once.
  https://github.com/nexB/scancode.io/issues/681

- Add new command line option to create-project and add-input management commands to
  copy the content of a local source directory to the project codebase work directory.
  https://github.com/nexB/scancode.io/pull/672

- Include the ScanCode-toolkit version in the output headers.
  https://github.com/nexB/scancode.io/pull/670

- Enhance the ``output`` management command to support providing multiple formats at
  once.
  https://github.com/nexB/scancode.io/issues/646

- Improve the resolution of CycloneDX BOM and SPDX document when the file extension is
  simply ``.json``.
  https://github.com/nexB/scancode.io/pull/688

- Add support for manifest types using ScanCode-toolkit handlers.
  https://github.com/nexB/scancode.io/issues/658

- Enhance the Resource details view to use the tabset system and display all
  available data including the content viewer.
  https://github.com/nexB/scancode.io/issues/215

- Add a "layers" data sheet in the xlsx output for docker pipeline run.
  https://github.com/nexB/scancode.io/issues/578

- Move the ``cyclonedx`` and ``spdx`` root modules into the ``pipes`` module.
  https://github.com/nexB/scancode.io/issues/657

- Remove the admin app and views.
  https://github.com/nexB/scancode.io/issues/645

- Enhance the ``resolve_about_packages`` pipe to handle filename and checksum values.

- Split the pipes unit tests into their own related submodule.

- Upgrade ScanCode Toolkit to v31.2.6
  https://github.com/nexB/scancode.io/issues/693

v32.1.0 (2023-03-23)
--------------------

- Add support for ScanCode.io results in the "load_inventory" pipeline.
  https://github.com/nexB/scancode.io/issues/609

- Add support for CycloneDX 1.4 to the "inspect-manifest" pipeline to import SBOM into
  a Project.
  https://github.com/nexB/scancode.io/issues/583

- Add fields in CycloneDX BOM output using the component properties.
  See registered properties at https://github.com/nexB/aboutcode-cyclonedx-taxonomy
  https://github.com/nexB/scancode.io/issues/637

- Upgrade to Python 3.11 in the Dockerfile.
  https://github.com/nexB/scancode.io/pull/611

- Refine the "Command Line Interface" documentation about the ``scanpipe`` command
  usages in the Docker context.
  Add the /app workdir in the "PYTHONPATH" env of the Docker file to make the
  ``scanpipe`` entry point available while running ``docker compose`` commands.
  https://github.com/nexB/scancode.io/issues/616

- Add new tutorial about the "find vulnerabilities" pipeline and the vulnerablecode
  integration in the documentation.
  https://github.com/nexB/scancode.io/issues/600

- Rewrite the CLI tutorials for a Docker-based installation.
  https://github.com/nexB/scancode.io/issues/440

- Use CodebaseResource ``path`` instead of ``id`` as slug_field in URL navigation.
  https://github.com/nexB/scancode.io/issues/242

- Remove dead code related to the project_tree view
  https://github.com/nexB/scancode.io/issues/623

- Update ``scanpipe.pipes.ProjectCodebase`` and related code to work properly
  with current Project/CodebaseResource path scheme.
  https://github.com/nexB/scancode.io/pull/624

- Add ``SCANCODEIO_PAGINATE_BY`` setting to customize the number of items displayed per
  page for each object type.
  https://github.com/nexB/scancode.io/issues/563

- Add setting for per-file timeout. The maximum time allowed for a file to be
  analyzed when scanning a codebase is configurable with SCANCODEIO_SCAN_FILE_TIMEOUT
  while the maximum time allowed for a pipeline to complete can be defined using
  SCANCODEIO_TASK_TIMEOUT.
  https://github.com/nexB/scancode.io/issues/593

v32.0.1 (2023-02-20)
--------------------

- Upgrade ScanCode-toolkit and related dependencies to solve installation issues.
  https://github.com/nexB/scancode.io/pull/586

- Add support for Python 3.11
  https://github.com/nexB/scancode.io/pull/611

- Populate ``documentDescribes`` field with Package and Dependency SPDX IDs in
  SPDX BOM output.
  https://github.com/nexB/scancode.io/issues/564

v32.0.0 (2022-11-29)
--------------------

- Add a new "find vulnerabilities" pipeline to lookup vulnerabilities in the
  VulnerableCode database for all project discovered packages.
  Vulnerability data is stored in the extra_data field of each package.
  More details about VulnerableCode at https://github.com/nexB/vulnerablecode/
  https://github.com/nexB/scancode.io/issues/101

- Add a new "inspect manifest" pipeline to resolve packages from manifest, lockfile,
  and SBOM. The resolved packages are created as discovered packages.
  Support PyPI "requirements.txt" files, SPDX document as JSON ".spdx.json",
  and AboutCode ".ABOUT" files.
  https://github.com/nexB/scancode.io/issues/284

- Generate SBOM (Software Bill of Materials) compliant with the SPDX 2.3 specification
  as a new downloadable output.
  https://github.com/nexB/scancode.io/issues/389

- Generate CycloneDX SBOM (Software Bill of Materials) as a new downloadable output.
  https://github.com/nexB/scancode.io/issues/389

- Display Webhook status in the Run modal.
  The WebhookSubscription model was refined to capture delivery data.
  https://github.com/nexB/scancode.io/issues/389

- Display the current active step of a running pipeline in the "Pipeline" section of
  the project details view, inside the run status tag.
  https://github.com/nexB/scancode.io/issues/300

- Add proper pagination for API actions: resources, packages, dependencies, and errors.

- Refine the fields ordering in API Serializers based on the toolkit order.
  https://github.com/nexB/scancode.io/issues/546

- Keep the current filters state when submitting a search in list views.
  https://github.com/nexB/scancode.io/issues/541

- Improve the performances of the project details view to load faster by deferring the
  the charts rendering. This is especially noticeable on projects with a large amount
  of codebase resources and discovered packages.
  https://github.com/nexB/scancode.io/issues/193

- Add support for filtering by "Other" values when filtering from the charts in the
  Project details view.
  https://github.com/nexB/scancode.io/issues/526

- ``CodebaseResource.for_packages`` now returns a list of
  ``DiscoveredPackage.package_uid`` or ``DiscoveredPackage.package_url`` if
  ``DiscoveredPackage.package_uid`` is not present. This is done to reflect the
  how scancode-toolkit's JSON output returns ``package_uid``s in the
  ``for_packages`` field for Resources.

- Add the model DiscoveredDependency. This represents Package dependencies
  discovered in a Project. The ``scan_codebase`` and ``scan_packages`` pipelines
  have been updated to create DiscoveredDepdendency objects. The Project API has
  been updated with new fields:

  - ``dependency_count``
    - The number of DiscoveredDependencies associated with the project.

  - ``discovered_dependencies_summary``
    - A mapping that contains following fields:

      - ``total``
        - The number of DiscoveredDependencies associated with the project.
      - ``is_runtime``
        - The number of runtime dependencies.
      - ``is_optional``
        - The number of optional dependencies.
      - ``is_resolved``
        - The number of resolved dependencies.

  These values are also available on the Project view.
  https://github.com/nexB/scancode.io/issues/447

- The ``dependencies`` field has been removed from the DiscoveredPackage model.

- Create directory CodebaseResources in the rootfs pipeline.
  https://github.com/nexB/scancode.io/issues/515

- Add ProjectErrors when the DiscoveredPackage could not be fetched using the
  provided `package_uid` during the `assemble_package` step instead of failing the whole
  pipeline.
  https://github.com/nexB/scancode.io/issues/525

- Escape paths before using them in regular expressions in ``CodebaseResource.walk()``.
  https://github.com/nexB/scancode.io/issues/525

- Disable multiprocessing and threading by default on macOS ("spawn" start method).
  https://github.com/nexB/scancode.io/issues/522

v31.0.0 (2022-08-25)
--------------------

- WARNING: Drop support for Python 3.6 and 3.7. Add support for Python 3.10.
  Upgrade Django to version 4.1 series.

- Upgrade ScanCode-toolkit to version 31.0.x.
  See https://github.com/nexB/scancode-toolkit/blob/develop/CHANGELOG.rst for an
  overview of the changes in the v31 compared to v30.

- Implement run status auto-refresh using the htmx JavaScript library.
  The statuses of queued and running pipeline are now automatically refreshed
  in the project list and project details views every 10 seconds.
  A new "toast" type of notification is displayed along the status update.
  https://github.com/nexB/scancode.io/issues/390

- Ensure the worker service waits for migrations completion before starting.
  To solve this issue we install the wait-for-it script available in
  Debian by @vishnubob and as suggested in the Docker documentation.
  In the docker-compose.yml, we let the worker wait for the web processing
  to be complete when gunicorn exposes port 8000 and web container is available.
  Reference: https://docs.docker.com/compose/startup-order/
  Reference: https://github.com/vishnubob/wait-for-it
  Reference: https://tracker.debian.org/pkg/wait-for-it
  https://github.com/nexB/scancode.io/issues/387

- Add a "create-user" management command to create new user with its API key.
  https://github.com/nexB/scancode.io/issues/458

- Add a "tag" field on the CodebaseResource model.
  The layer details are stored in this field in the "docker" pipeline.
  https://github.com/nexB/scancode.io/issues/443

- Add support for multiple inputs in the LoadInventory pipeline.
  https://github.com/nexB/scancode.io/issues/451

- Add new SCANCODEIO_REDIS_PASSWORD environment variable and setting
  to optionally set Redis instance password.

- Ensure a project cannot be deleted through the API while a pipeline is running.
  https://github.com/nexB/scancode.io/issues/402

- Display "License clarity" and "Scan summary" values as new panel in the project
  details view. The summary is generated during the `scan_package` pipeline.
  https://github.com/nexB/scancode.io/issues/411

- Enhance Project list view page:

  - 20 projects are now displayed per page
  - Creation date displayed under the project name
  - Add ability to sort by date and name
  - Add ability to filter by pipeline type
  - Add ability to filter by run status

  https://github.com/nexB/scancode.io/issues/413

- Correctly extract symlinks in docker images. We now use the latest
  container-inspector to fix symlinks extraction in docker image tarballs.
  In particular broken symlinks are not treated as an error anymore
  and symlinks are extracted correctly.
  https://github.com/nexB/scancode.io/issues/471
  https://github.com/nexB/scancode.io/issues/407

- Add a Package details view including all model fields and resources.
  Display only 5 resources per package in the list view.
  https://github.com/nexB/scancode.io/issues/164
  https://github.com/nexB/scancode.io/issues/464

- Add the ability to filter by empty and none values providing the
  "EMPTY" magic value to any filters.
  https://github.com/nexB/scancode.io/issues/296

- CodebaseResource.name now contains both the bare file name with extension, as
  opposed to just the bare file name without extension.
  Using a name stripped from its extension was something that was not used in
  other AboutCode project or tools.
  https://github.com/nexB/scancode.io/issues/467

- Export current results as XLSX for resource, packages, and errors list views.
  https://github.com/nexB/scancode.io/issues/48

- Add support for .tgz extension for input files in Docker pipeline
  https://github.com/nexB/scancode.io/issues/499

- Add support for resource missing file content in details view.
  Refine the annotation using the new className instead of type.
  https://github.com/nexB/scancode.io/issues/495

- Change the worksheet names in XLSX output, using the
  "PACKAGES", "RESOURCES", "DEPENDENCIES", and "ERRORS" names.
  https://github.com/nexB/scancode.io/issues/511

- Update application Package scanning step to reflect the updates in
  scancode-toolkit package scanning.

  - Package data detected from a file are now stored on the
    CodebaseResource.package_data field.
  - A second processing step is now done after scanning for Package data, where
    Package Resources are determined and DiscoveredPackages and
    DiscoveredDependencies are created.

  https://github.com/nexB/scancode.io/issues/444

v30.2.0 (2021-12-17)
--------------------

- Add authentication for the Web UI views and REST API endpoint.
  The autentication is disabled by default and can be enabled using the
  SCANCODEIO_REQUIRE_AUTHENTICATION settings.
  When enabled, users have to authenticate through a login form in the Web UI, or using
  their API Key in the REST API.
  The API Key can be viewed in the Web UI "Profile settings" view ince logged-in.
  Users can be created using the Django "createsuperuser" management command.
  https://github.com/nexB/scancode.io/issues/359

- Include project errors in XLSX results output.
  https://github.com/nexB/scancode.io/issues/364

- Add input_sources used to fetch inputs to JSON results output.
  https://github.com/nexB/scancode.io/issues/351

- Refactor the update_or_create_package pipe to support the ProjectError system
  and fix a database transaction error.
  https://github.com/nexB/scancode.io/issues/381

- Add webhook subscription available when creating project from REST API.
  https://github.com/nexB/scancode.io/issues/98

- Add the project "reset" feature in the UI, CLI, and REST API.
  https://github.com/nexB/scancode.io/issues/375

- Add a new GitHub action that build the docker-compose images and run the test suite.
  This ensure that the app is properly working and tested when running with Docker.
  https://github.com/nexB/scancode.io/issues/367

- Add --no-install-recommends in the Dockerfile apt-get install and add the
  `linux-image-amd64` package. This packages makes available the kernels
  required by extractcode and libguestfs for proper VM images extraction.
  https://github.com/nexB/scancode.io/issues/367

- Add a new `list-project` CLI command to list projects.
  https://github.com/nexB/scancode.io/issues/365

v30.1.1 (2021-11-23)
--------------------

- Remove the --no-install-recommends in the Dockerfile apt-get install to include
  required dependencies for proper VM extraction.
  https://github.com/nexB/scancode.io/issues/367

v30.1.0 (2021-11-22)
--------------------

- Synchronize QUEUED and RUNNING pipeline runs with their related worker jobs during
  worker maintenance tasks scheduled every 10 minutes.
  If a container was taken down while a pipeline was running, or if pipeline process
  was killed unexpectedly, that pipeline run status will be updated to a FAILED state
  during the next maintenance tasks.
  QUEUED pipeline will be restored in the queue as the worker redis cache backend data
  is now persistent and reloaded on starting the image.
  Note that internaly, a running job emits a "heartbeat" every 60 seconds to let all the
  workers know that it is properly running.
  After 90 seconds without any heartbeats, a worker will determine that the job is not
  active anymore and that job will be moved to the failed registry during the worker
  maintenance tasks. The pipeline run will be updated as well to reflect this failure
  in the Web UI, the REST API, and the command line interface.
  https://github.com/nexB/scancode.io/issues/130

- Enable redis data persistence using the "Append Only File" with the default policy of
  fsync every second in the docker-compose.
  https://github.com/nexB/scancode.io/issues/130

- Add a new tutorial chapter about license policies and compliance alerts.
  https://github.com/nexB/scancode.io/issues/337

- Include layers in docker image data.
  https://github.com/nexB/scancode.io/issues/175

- Fix a server error on resource details view when the compliance alert is "missing".
  https://github.com/nexB/scancode.io/issues/344

- Migrate the ScanCodebase pipeline from `scancode.run_scancode` subprocess to
  `scancode.scan_for_application_packages` and `scancode.scan_for_files`.
  https://github.com/nexB/scancode.io/issues/340

v30.0.1 (2021-10-11)
--------------------

- Fix a build failure related to dependency conflict.
  https://github.com/nexB/scancode.io/issues/342

v30.0.0 (2021-10-8)
-------------------

- Upgrade ScanCode-toolkit to version 30.1.0

- Replace the task queue system, from Celery to RQ.
  https://github.com/nexB/scancode.io/issues/176

- Add ability to delete "not started" and "queued" pipeline tasks.
  https://github.com/nexB/scancode.io/issues/176

- Add ability to stop "running" pipeline tasks.
  https://github.com/nexB/scancode.io/issues/176

- Refactor the "execute" management command and add support for --async mode.
  https://github.com/nexB/scancode.io/issues/130

- Include codebase resource data in the details of package creation project errors.
  https://github.com/nexB/scancode.io/issues/208

- Add a SCANCODEIO_REST_API_PAGE_SIZE setting to control the number of objects
  returned per page in the REST API.
  https://github.com/nexB/scancode.io/issues/328

- Provide an "add input" action on the Project endpoint of the REST API.
  https://github.com/nexB/scancode.io/issues/318

v21.9.6
-------

- Add ability to "archive" projects, from the Web UI, API and command line interface.
  Data cleanup of the project's input, codebase, and output directories is available
  during the archive operation.
  Archived projects cannot be modified anymore and are hidden by default from the
  project list.
  A project cannot be archived if one of its related run is queued or already running.
  https://github.com/nexB/scancode.io/issues/312

- Remove the run_extractcode pipe in favor of extractcode API.
  https://github.com/nexB/scancode.io/issues/312

- The `scancode.run_scancode` pipe now uses an optimal number of available CPUs for
  multiprocessing by default.
  The exact number of parallel processes available to ScanCode.io can be defined
  using the SCANCODEIO_PROCESSES setting.
  https://github.com/nexB/scancode.io/issues/302

- Renamed the SCANCODE_DEFAULT_OPTIONS setting to SCANCODE_TOOLKIT_CLI_OPTIONS.
  https://github.com/nexB/scancode.io/issues/302

- Log the outputs of run_scancode as progress indication.
  https://github.com/nexB/scancode.io/issues/300

v21.8.2
-------

- Upgrade ScanCode-toolkit to version 21.7.30

- Add new documentation chapters and tutorials on the usage of the Web User Interface.
  https://github.com/nexB/scancode.io/issues/241

- Add ability to register custom pipelines through a new SCANCODEIO_PIPELINES_DIRS
  setting.
  https://github.com/nexB/scancode.io/issues/237

- Add a pipeline `scan_package.ScanPackage` to scan a single package archive with
  ScanCode-toolkit.
  https://github.com/nexB/scancode.io/issues/25

- Detected Package dependencies are not created as Package instance anymore but stored
  on the Package model itself in a new `dependencies` field.
  https://github.com/nexB/scancode.io/issues/228

- Add the extra_data field on the DiscoveredPackage model.
  https://github.com/nexB/scancode.io/issues/191

- Improve XLSX creation. We now check that the content is correctly added before
  calling XlsxWriter and report and error if the truncated can be truncated.
  https://github.com/nexB/scancode.io/issues/206

- Add support for VMWare Photon-based Docker images and rootfs. This is an RPM-based
  Linux distribution

v21.6.10
--------

- Add support for VM image formats extraction such as VMDK, VDI and QCOW.
  See https://github.com/nexB/extractcode#archive-format-kind-file_system for the full
  list of supported extensions.
  The new extraction feature requires the installation of `libguestfs-tools`,
  see https://github.com/nexB/extractcode#adding-support-for-vm-images-extraction for
  installation details.
  https://github.com/nexB/scancode.io/issues/132

- Add the ability to disable multiprocessing and threading entirely through the
  SCANCODEIO_PROCESSES setting. Use 0 to disable multiprocessing and use -1 to also
  disable threading.
  https://github.com/nexB/scancode.io/issues/185

- Missing project workspace are restored on reports (xlsx, json) creation. This allow
  to download reports even if the project workspace (input, codebase) was deleted.
  https://github.com/nexB/scancode.io/issues/154

- Add ability to search on all list views.
  https://github.com/nexB/scancode.io/issues/184

- Add the is_binary, is_text, and is_archive fields to the CodebaseResource model.
  https://github.com/nexB/scancode.io/issues/75

v21.5.12
--------

- Adds a new way to fetch docker images using skopeo provided as a
  plugin using docker:// reference URL-like pointers to a docker image.
  The syntax is docker://<docker image> where <docker image> is the string
  that would be used in a "docker pull <docker image>" command.
  Also rename scanpipe.pipes.fetch.download() to fetch_http()
  https://github.com/nexB/scancode.io/issues/174

- Pipeline status modals are now loaded asynchronously and available from the
  project list view.

- Fix an issue accessing codebase resource content using the scan_codebase and
  load_inventory pipelines.
  https://github.com/nexB/scancode.io/issues/147

v21.4.28
--------

- The installation local timezone can be configured using the TIME_ZONE setting.
  The current timezone in now included in the dates representation in the web UI.
  https://github.com/nexB/scancode.io/issues/142

- Fix pipeline failure issue related to the assignment of un-saved (not valid) packages.
  https://github.com/nexB/scancode.io/issues/162

- Add a new QUEUED status to differentiate a pipeline that is in the queue for execution
  from a pipeline execution not requested yet.
  https://github.com/nexB/scancode.io/issues/130

- Refactor the multiprocessing code for file and package scanning.
  All database related operation are now executed in the main process as forking the
  existing database connection in sub-processes is a source of issues.
  Add progress logging for scan_for_files and scan_for_application_packages pipes.
  https://github.com/nexB/scancode.io/issues/145

- Links from the charts to the resources list are now also filtered by
  in_package/not_in_package if enabled on the project details view.
  https://github.com/nexB/scancode.io/issues/124

- Add ability to filter on codebase resource detected values such as licenses,
  copyrights, holders, authors, emails, and urls.
  https://github.com/nexB/scancode.io/issues/153

- Filtered list views from a click on chart sections can now be opened in a new tab
  using ctrl/meta + click.
  https://github.com/nexB/scancode.io/issues/125

- Add links to codebase resource and to discovered packages in list views.

v21.4.14
--------

- Implement timeout on the scan functions, default to 120 seconds per resources.
  https://github.com/nexB/scancode.io/issues/135

- Fix issue with closing modal buttons in the web UI.
  https://github.com/nexB/scancode.io/issues/116
  https://github.com/nexB/scancode.io/issues/141

v21.4.5
-------

- Add support for Docker and VM images using RPMs such as Fedora, CentOS, RHEL,
  and openSUSE linux distributions.
  https://github.com/nexB/scancode.io/issues/6

- Add a compliance alert system based on license policies provided through a
  policies.yml file. The compliance alerts are computed from the license_expression and
  stored on the codebase resource. When the policy feature is enabled, the compliance
  alert values are displayed in the UI and returned in all the downloadable results.
  The enable and setup the policy feature, refer to
  https://scancodeio.readthedocs.io/en/latest/scancodeio-settings.html#scancode-io-settings
  https://github.com/nexB/scancode.io/issues/90

- Add a new codebase resource detail view including the file content.
  Detected value can be displayed as annotation in the file source.
  https://github.com/nexB/scancode.io/issues/102

- Download URLs can be provided as inputs on the project form.
  Each URL is fetched and added to the project input directory.
  https://github.com/nexB/scancode.io/issues/100

- Run celery worker with the "threads" pool implementation.
  Implement parallelization with ProcessPoolExecutor for file and package scans.
  Add a SCANCODEIO_PROCESSES settings to control the multiprocessing CPUs count.
  https://github.com/nexB/scancode.io/issues/70

- Optimize "tag" type pipes using the update() API in place of save() on the QuerySet
  iteration.
  https://github.com/nexB/scancode.io/issues/70

- Use the extractcode API for the Docker pipeline.
  This change helps with performance and results consistency between pipelines.
  https://github.com/nexB/scancode.io/issues/70

- Implement cache to prevent scanning multiple times a duplicated codebase resource.
  https://github.com/nexB/scancode.io/issues/70

- Create the virtualenv using the virtualenv.pyz app in place of the bundled "venv".
  https://github.com/nexB/scancode.io/issues/104

- Consistent ordering for the pipelines, now sorted alphabetically.

v1.1.0 (2021-02-16)
-------------------

- Display project extra data in the project details view.
  https://github.com/nexB/scancode.io/issues/88

- Add a @profile decorator for profiling pipeline step execution.
  https://github.com/nexB/scancode.io/issues/73

- Support inputs as tarballs in root_filesystem pipelines.
  The input archives are now extracted with extractcode to the codebase/ directory.
  https://github.com/nexB/scancode.io/issues/96

- Improve support for unknown distros in docker and root_filesystem pipelines.
  The pipeline logs the distro errors on the project instead of failing.
  https://github.com/nexB/scancode.io/issues/97

- Implement Pipeline registration through distribution entry points.
  Pipeline can now be installed as part of external libraries.
  With this change pipelines are no longer referenced by the
  Python script path, but by their registered name.
  This is a breaking command line API change.
  https://github.com/nexB/scancode.io/issues/91

- Add a "Run Pipeline" button in the Pipeline modal of the Project details view.
  Pipelines can now be added from the Project details view.
  https://github.com/nexB/scancode.io/issues/84

- Upgrade scancode-toolkit to version 21.2.9

- Allow to start the pipeline run immediately on addition in the `add_pipeline` action
  of the Project API endpoint.
  https://github.com/nexB/scancode.io/issues/92

- Rename the pipes.outputs module to pipes.output for consistency.

- Remove the dependency on Metaflow.
  WARNING: The new Pipelines syntax is not backward compatible with v1.0.x
  https://github.com/nexB/scancode.io/issues/82

v1.0.7 (2021-02-01)
-------------------

- Add user interface to manage Projects from a web browser
  All the command-line features are available
  https://github.com/nexB/scancode.io/issues/24

- Log messages from Pipeline execution on a new Run instance `log` field
  https://github.com/nexB/scancode.io/issues/66

- Add support for scancode pipes and Project name with whitespaces

- Add a profile() method on the Run model for profiling pipeline execution
  https://github.com/nexB/scancode.io/issues/73

v1.0.6 (2020-12-23)
-------------------

- Add a management command to delete a Project and its related work directories
  https://github.com/nexB/scancode.io/issues/65

- Add CSV and XLSX support for the `output` management command
  https://github.com/nexB/scancode.io/issues/46

- Add a to_xlsx output pipe returning XLSX compatible content
  https://github.com/nexB/scancode.io/issues/46

- Add a "status" management command to display Project status information
  https://github.com/nexB/scancode.io/issues/66

- Fix the env_file location to run commands from outside the root dir
  https://github.com/nexB/scancode.io/issues/64

- Add utilities to save project error in the database during Pipeline execution
  https://github.com/nexB/scancode.io/issues/64

- Install psycopg2-binary instead of psycopg2 on non-Linux platforms
  https://github.com/nexB/scancode.io/issues/64

v1.0.5 (2020-12-07)
-------------------

- Add minimal license list and text views
  https://github.com/nexB/scancode.io/issues/32

- Add admin actions to export selected objects to CSV and JSON
  The output content, such as included fields, can be configured for CSV format
  https://github.com/nexB/scancode.io/issues/48
  https://github.com/nexB/scancode.io/issues/49

- Add --list option to the graph management command.
  Multiple graphs can now be generated at once.

- Add ProjectCodebase to help walk and navigate Project CodebaseResource
  loaded from the Database
  Add also a get_tree function compatible with scanpipe.CodebaseResource and
  commoncode.Resource
  https://github.com/nexB/scancode.io/issues/52

- Add support for running ScanCode.io as a Docker image
  https://github.com/nexB/scancode.io/issues/9

- Add support for Python 3.7, 3.8, and 3.9
  https://github.com/nexB/scancode.io/issues/54

v1.0.4 (2020-11-17)
-------------------

- Add a to_json output pipe returning ScanCode compatible content
  https://github.com/nexB/scancode.io/issues/45

- Improve Admin UI for efficient review:
  display, navigation, filters, and ability to view file content
  https://github.com/nexB/scancode.io/issues/36

- Add Pipelines and Pipes documentation using Sphinx autodoc
  Fix for https://github.com/nexB/scancode.io/issues/38

- Add new ScanCodebase pipeline for codebase scan
  Fix for https://github.com/nexB/scancode.io/issues/37

- Upgrade Django, Metaflow, and ScanCode-toolkit to latest versions

v1.0.3 (2020-09-24)
-------------------

- Add ability to resume a failed pipeline from the run management command
  Fix for https://github.com/nexB/scancode.io/issues/22

- Use project name as argument to run a pipeline
  Fix for https://github.com/nexB/scancode.io/issues/18

- Add support for "failed" task_output in Run.get_run_id method
  Fix for https://github.com/nexB/scancode.io/issues/17

v1.0.2 (2020-09-18)
-------------------

- Add documentation and tutorial
  For https://github.com/nexB/scancode.io/issues/8

- Add a create-project, add-input, add-pipeline, run, output
  management commands to expose ScanPipe features through the command line
  Fix for https://github.com/nexB/scancode.io/issues/13

- Always return the Pipeline subclass/implementation from the module inspection
  Fix for https://github.com/nexB/scancode.io/issues/11

v1.0.1 (2020-09-12)
-------------------

- Do not fail when collecting system packages in Ubuntu docker images for
  layers that do not install packages by updating to a newer version of
  ScanCode Toolkit
  Fix for https://github.com/nexB/scancode.io/issues/1

v1.0.0 (2020-09-09)
-------------------

- Initial release
