// Release notes
// -------------

### v1.0.2 (unreleased)

- **ScanPipe** -- Add documentation and tutorial.
  For https://github.com/nexB/scancode.io/issues/8

- **ScanPipe** -- Add a create-project, add-input, add-pipeline, run, output
  management commands to expose ScanPipe features through the command line.
  Fix for https://github.com/nexB/scancode.io/issues/13

- **ScanPipe** -- Always return the Pipeline subclass/implementation
  from the module inspection.
  Fix for https://github.com/nexB/scancode.io/issues/11

### v1.0.1 (2020-09-12)

- **ScanPipe** -- Do not fail when collecting system packages in
  Ubuntu docker images for layers that do not install packages by updating to a
  newer version of ScanCode Toolkit.
  Fix for https://github.com/nexB/scancode.io/issues/1

### v1.0.0 (2020-09-09)

- Initial release