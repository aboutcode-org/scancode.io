Transitive Dependencies
=============================

Why
-----
In order to understand the codebase better, it is necessary to have an SBOM that gives not a list
but a graph of the bill of materials. A developer working on a project might not be aware of a
dependency introduced by a package that they are using as a library. It becomes even more crucial in
case of of the dependencies being used is vulnerable or outdated.
Consider the following dependency graph::

.. code::
    My Project
    ├── B
    ├── C
    └── D
        └── E
            └── F

In case a vulnerability is identified in ``F``, and there is no graph relationship between the
packages, the developer would have no idea what to update in order to mitigate this vulnerability.
On the other hand, if they get to know about the graph, they are aware of the fact that ``F`` is
introduced by a direct dependency of ``My Project`` named ``D``.
A similar argument could be presented in case ``F`` has incompatible or unpreferred license.


What
-----
This document aims to achieve a dependency graph in SCIO. The current implementation of Package ->
Dependency relationship does not support such a feature.

How
-----
A packages will have many-to-many relationship to itself. This cannot be one-to-one because of the
following dependency graph::

.. code::
    My Second Project
    ├── B
    ├── C
    ├── D
    │   └── E
    └───────└── F

Here ``F`` is a direct dependency of ``My Second Project`` as well as a transitive dependency via
the path ``D -> E -> F``. If there is any requirement of removing ``F`` from the project, both paths
need to be taken into consideration.
