# Changelog

## Release 0.2.1 (February 24, 2025)

* Include the ``optional_step`` steps in the ``get_graph()`` list.
  [Issue #1599](https://github.com/aboutcode-org/scancode.io/issues/1599)

## Release 0.2.0 (November 21, 2024)

* Refactor the ``group`` decorator for pipeline optional steps as ``optional_step``.
  The steps decorated as optional are not included by default anymore. 
  Migration: Use the ``optional_step`` decorator in place of the deprecated ``group``.
  [Issue #1442](https://github.com/nexB/scancode.io/issues/1442)

## Release 0.1.0 (August 9, 2024)

* Initial release of the `aboutcode.pipeline` library. 
  [Issue #1351](https://github.com/nexB/scancode.io/issues/1351)
