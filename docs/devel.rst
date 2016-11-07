.. _development:

Development
===========

The following details the tools needed to contribute to the
development of Pyrseas.  If you have any doubts or questions, please
subscribe to the `Pyrseas-general mailing list
<http://pgfoundry.org/mailman/listinfo/pyrseas-general>`_ and post a
message to the list.  In addition, see *Version Control* below on how
to set up a GitHub account to participate in development.

Requirements
------------

- Git

- Python

- PostgreSQL

- Psycopg2

- PyYAML

- Tox

Version Control
---------------

Pyrseas uses `Git <http://git-scm.com/>`_ to control changes to its
source code. As mentioned under :ref:`download`, the master Git
`repository <https://github.com/perseas/Pyrseas>`_ is located at GitHub.

To install Git, either `download and install
<http://git-scm.com/download>`_ the latest stable release for your
platform or follow the `Pro Git` `installation instructions
<http://git-scm.com/book/en/Getting-Started-Installing-Git>`_.  For
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
<https://github.com/signup/free>`_.

Programming Language
--------------------

To contribute to Pyrseas, you need at least one version of `Python
<http://www.python.org>`_.  You can develop using Python 3, but since
we want to continue supporting Python 2, you'll want to install Python
2.7 in addition to Python 3.4 or 3.5.

If Python is not already available on your machine, either `download
and install one or both <http://www.python.org/download/>`_ of the
production releases for your platform, follow the applicable
installation instructions given in `The Hitchhiker’s Guide to Python!
<http://docs.python-guide.org/en/latest/>`_ or install it from your
platform's package management system.

Database Installation
---------------------

To participate in Pyrseas development, you'll also need one or more
installations of `PostgreSQL <http://www.postgresql.org>`_, versions
9.5, 9.4, 9.3 or 9.2.  If you only have limited space, it is
preferable to install one of the latest two versions.

The versions can be obtained as binary packages or installers from the
`PostgreSQL.org website <http://www.postgresql.org/download/>`_.  The
site also includes instructions for installing from package management
systems or building it from source.

To access PostgreSQL from Python, you'll have to install the `Psycopg
<http://initd.org/psycopg/>`_ adapter. You can either follow the
instructions in `Psycopg's site <http://initd.org/psycopg/install/>`_,
or install it from your package management system.  Note that if you
install both Python 2 and 3, you will have to install two packages,
e.g., ``python-psycopg2`` and ``python3-psycopg2``.

Other Libraries and Tools
-------------------------

The ``dbtoyaml`` and ``yamltodb`` utilities use the `PyYAML
<http://pyyaml.org/wiki/PyYAML>`_ library.  You can install it from
the PyYAML site, or possibly from your package management system.  For
Windows 64-bit, please read the note under :ref:`installers`.

To easily run the Pyrseas tests against various Python/PostgreSQL
version combinations, install `Tox
<http://tox.testrun.org/latest/install.html>`_.  Please refer to
:ref:`testing` for more information.
