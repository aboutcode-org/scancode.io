.. _origin_determination:

Origin Determination
====================

The :ref:`pipeline_find_origins` pipeline stores the candidate origin packages
reported by each origin detection tool as origin matches, see
:ref:`data_models_origin_match`. Its last step combines these matches into one
origin determination per matched file or directory, see
:ref:`data_models_origin_determination`.

Each determination has a status and the name of the rule that set it. Only an
agreement between two tools confirms an origin automatically. Any other case
needs a review, with a proposed origin when a rule can select one.

Candidates
----------

The origin matches of a file or directory are grouped by package into
candidates:

- The matches of the same package version are one candidate, even when the tools
  report different PURLs, such as ``pkg:github/benjaminp/six@1.17.0`` and
  ``pkg:pypi/six@1.17.0``, as SCANOSS reports the equivalent PURLs of a
  component.
- The snippet matches covering fewer than 20 lines of the file are ignored, such
  as a common license header found in many unrelated packages. They are still
  stored as origin matches.
- When nested directories are matched to the same package, the deepest
  directory is kept as the most precise match.
- A file matched only to the package of its closest matched directory has no
  determination of its own: its matches count for the directory.

Statuses
--------

``auto-confirmed``
    Set by the ``confirmed-by-two-tools`` rule.

``needs-review``
    Set by any other rule. The PURL is the proposed origin, or empty when no
    candidate is preferred.

``confirmed``
    Set by a user who confirms the origin.

``no-origin``
    Set by a user when the file or directory has no open source origin.

Rules
-----

The rules are evaluated in this order, and the first rule that applies sets the
determination.

.. list-table::
    :header-rows: 1
    :widths: 20 50 15 15

    * - Rule
      - Applies when
      - Status
      - Proposed origin
    * - ``containment``
      - Different packages: the copy in all the candidates but one is in a
        directory or file named after another candidate, such as
        ``pip/_vendor/six.py`` in pip.
      - ``needs-review``
      - The remaining candidate.
    * - ``highest-similarity``
      - Different packages: one candidate is more similar than all the others by
        at least 20 points, and all the similarities are known.
      - ``needs-review``
      - The most similar candidate.
    * - ``earliest-release``
      - Different packages: one candidate was released before all the others,
        and all the release dates are known.
      - ``needs-review``
      - The earliest released candidate.
    * - ``conflicting-candidates``
      - Different packages, not resolved by the previous rules.
      - ``needs-review``
      - None.
    * - ``preferred-version``
      - Versions of the same package: one is more similar than all the others by
        at least 20 points, or else only one is a release, as opposed to a commit
        hash or a missing version, or else one release is more similar than the
        other releases by at least 20 points.
      - ``needs-review``
      - The preferred version.
    * - ``conflicting-versions``
      - Versions of the same package, without a preferred version.
      - ``needs-review``
      - None.
    * - ``no-exact-match``
      - One candidate, with partial matches only: snippet, approximate, or
        directory matches.
      - ``needs-review``
      - The candidate.
    * - ``single-tool``
      - One candidate, with an exact file or package match, reported by a single
        tool.
      - ``needs-review``
      - The candidate.
    * - ``confirmed-by-two-tools``
      - One candidate, with at least one exact file or package match, reported by
        two tools.
      - ``auto-confirmed``
      - The candidate.

Similarity and release date
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- The similarity is the percentage of the file lines matched: the SCANOSS
  ``matched`` value, 100 for a MatchCode.io exact match, and the line coverage of
  the MatchCode.io snippet matches. It is unknown for the directory and
  approximate matches. The tools measure the same copy a few points apart, hence
  the 20 points margin.
- The release date is reported by SCANOSS, and by MatchCode.io when PurlDB
  knows it. A copy cannot be older than its origin.
- The similarity is checked before the release date, as it is measured on the
  copy itself, while a release date only tells that a package version could
  have been copied.

Re-running the pipeline
-----------------------

- The automatic determinations, ``auto-confirmed`` and ``needs-review``, are
  replaced.
- The user determinations, ``confirmed`` and ``no-origin``, are kept. A
  directory determined by a user covers its content: the origin matches under it
  are not used.

Origin packages
---------------

The files and directories of the ``auto-confirmed`` and ``confirmed``
determinations are assigned to the package of their PURL. The files of a
determined directory are assigned with it, unless they have a determination of
their own.

- A package detected by the codebase scan is reused, also when its PURL has
  other qualifiers, such as a Maven ``classifier``.
- Otherwise, the package is created from the tools data: download URL, homepage
  URL, release date, and declared license. It is identified with the
  ``origin_determination`` datasource ID, and created again on each run.

Limitations
-----------

- A single tool never confirms an origin automatically: MatchCode.io stops at
  the first package matched, and SCANOSS reports one component per file.
- MatchCode.io rarely reports a release date, so the ``earliest-release`` rule
  rarely applies to its candidates.
- The ``containment`` rule needs the path of the copy in each candidate.
  SCANOSS only reports the file name, and the path of a MatchCode.io match is
  fetched from PurlDB, when configured.
