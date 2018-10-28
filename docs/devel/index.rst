.. _development:

Development
===========

The following details the tools needed to contribute to the
development of Pyrseas.  If you have any doubts or questions, please
open an issue on GitHub (https://github.com/perseas/Pyrseas/issues).
In addition, see *Version Control* below on how to set up a GitHub
account to participate in development.

Requirements
------------

- Git

- Python

- Postgres

- Psycopg2

- PyYAML

- PgDbConn

- Tox

Version Control
---------------

Pyrseas uses `Git <https://git-scm.com/>`_ to control changes to its
source code. As mentioned under :ref:`download`, the master Git
`repository <https://github.com/perseas/Pyrseas>`_ is located at GitHub.

To install Git, either `download and install
<https://git-scm.com/download>`_ the latest stable release for your
platform or follow the `Pro Git` `installation instructions
<https://git-scm.com/book/en/Getting-Started-Installing-Git>`_.  For
most Linux users, ``apt-get`` or ``yum`` (depending on Linux flavor)
will be the simplest means to install the ``git-core`` package.  For
Windows, downloading the installer and selecting ``Git Bash`` gives
you not only Git but a Bash shell, which is handy if you're coming
from a Linux/Unix background.

Once Git is installed, change to a suitable directory and clone the
master repository::

 git clone git://github.com/perseas/Pyrseas.git

or::

 git clone https://github.com/perseas/Pyrseas.git

To be able to create a fork on GitHub, open an issue or participate in
Pyrseas development, you'll first have to `create a GitHub account
<https://github.com/join>`_.

Programming Language
--------------------

To contribute to Pyrseas, you need at least one version of `Python
<https://www.python.org>`_.  You can develop using Python 3, but since
we will continue supporting Python 2 until its end-of-life, you'll
want to install Python 2.7 in addition to Python 3.6 or 3.5.

If Python is not already available on your machine, either `download
and install one or both <https://www.python.org/downloads/>`_ of the
production releases for your platform, follow the applicable
installation instructions given in `The Hitchhiker’s Guide to Python!
<http://docs.python-guide.org/en/latest/>`_ or install it from your
platform's package management system.

Database Installation
---------------------

To participate in Pyrseas development, you'll also need one or more
installations of `Postgres <https://www.postgresql.org>`_, versions
10, 9.6, 9.5, 9.4 or 9.3.  If you only have limited space, it is
preferable to install one of the latest two versions.

The versions can be obtained as binary packages or installers from the
`Postgres.org website <https://www.postgresql.org/download/>`_.  The
site also includes instructions for installing from package management
systems or building it from source.

To access Postgres from Python, you have to install the `Psycopg
<http://initd.org/psycopg/>`_ adapter. You can either follow the
instructions in `Psycopg's site
<http://initd.org/psycopg/docs/install.html>`_, or install it from
your package management system.  Note that if you install both Python
2 and 3, you will have to install two packages, e.g.,
``python-psycopg2`` and ``python3-psycopg2``.

Other Libraries and Tools
-------------------------

The ``dbtoyaml`` and ``yamltodb`` utilities use the `PyYAML
<http://pyyaml.org/wiki/PyYAML>`_ library.  You can install it from
the PyYAML site, or possibly from your package management system.  For
Windows 64-bit, please read the note under :ref:`installer`.

The utilities also rely on `PgDbConn
<https://github.com/perseas/pgdbconn>`_, an offshoot of the Perseas
project that provides a thin, object-oriented layer over Psycopg2.
You can install it from `PyPI <https://pypi.org/project/pgdbconn/>`_.

To easily run the Pyrseas tests against various Python/Postgres
version combinations, you will need `pytest
<https://docs.pytest.org/en/latest/>`_ and `Tox
<https://tox.readthedocs.io/en/latest/>`_.  Please refer to
:ref:`testing` for more information.


.. _api-ref:

API Reference
-------------

Currently, the only external APIs are the class
:class:`~pyrseas.database.Database` and the methods
:meth:`~pyrseas.database.Database.to_map` and
:meth:`~pyrseas.database.Database.diff_map` of the latter. Other
classes and methods are documented mainly for developer use.

.. toctree::
   :maxdepth: 2

   dbobject
   database
   schema

Non-schema Objects
~~~~~~~~~~~~~~~~~~
.. toctree::
   :maxdepth: 2

   cast
   eventtrig
   extension
   foreign
   language

Tables and Related Objects
~~~~~~~~~~~~~~~~~~~~~~~~~~
.. toctree::
   :maxdepth: 2

   table
   column
   constraint
   indexes
   rule

Functions, Operators and Triggers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. toctree::
   :maxdepth: 2

   function
   operator
   operfamily
   operclass
   trigger

Types and Other Schema Objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. toctree::
   :maxdepth: 2

   collation
   conversion
   textsearch
   type

Augmenter API Reference
-----------------------

.. toctree::
   :maxdepth: 2

   augmentdb
   cfgobjects
   augobjects

Other
-----

.. toctree::
   :maxdepth: 2

   testing

   