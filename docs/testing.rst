.. _testing:

Testing
=======

The majority of Pyrseas' capabilities are exercised and verified via
unit tests written using `pytest
<https://docs.pytest.org/en/latest/>`_.  The tests can be run from the
command line by most users, e.g.,

::

   py.test tests/dbobject/test_table.py
   py.test tests/dbobject/test_trigger.py -k test_create_trigger
   py.test tests/functional

The first ``python`` command above runs all tests related to tables,
mapping, creating, dropping, etc.  The second one executes a single
test to generate SQL to create a trigger.  The third runs all the
functional tests.  Please review the `pytest documentation
<https://docs.pytest.org/en/latest/usage.html>`_ for further options.

Environment Variables
---------------------

By default, the tests use a Postgres database named ``pyrseas_testdb``
which is created if it doesn't already exist. The tests are run as the
logged in user, using the ``USER`` Unix/Linux environment variable (or
``USERNAME`` under Windows). They access Postgres on the local host
using the default port number (5432).

The following four environment variables can be used to change the
defaults described above:

 - PYRSEAS_TEST_DB
 - PYRSEAS_TEST_USER
 - PYRSEAS_TEST_HOST
 - PYRSEAS_TEST_USER

Restrictions
------------

Unless the test database exists and the user running the tests has
access to it, the user role will need CREATEDB privilege.

Most tests do not require special privileges. However, certain tests
may require Postgres SUPERUSER privilege. Such tests will normally be
skipped if the user lacks the privilege.

Most tests do not require installation of supporting Postgres
packages.  However, a few tests rely on the availability of Postgres
``contrib`` modules such as the `spi module
<https://www.postgresql.org/docs/current/static/contrib-spi.html>`_ or
procedural languages such as ``plperl`` or ``plpython3u``.

On Windows, it is necessary to install Perl in order to run some of
the tests (most Linux or Unix variants already include it as part of
their normal distribution).  The last time we checked, a suitable
choice appeared to be Strawberry Perl which can be downloaded from
http://strawberryperl.com/releases.html. However, the default
installation is placed in ``C:\strawberry`` and can hold a single Perl
version.  Furthermore, some Postgres versions may be linked with
non-current Perl versions.  It is recommended that the latest Perl
version be installed as this will usually give the fewest test
failures.  See `this blog post
<https://pyrseas.wordpress.com/2012/10/17/testing-python-and-postgresql-on-windows-part-5/>`_
for more details.

The COLLATION tests require the
``fr_FR.utf8`` locale (or ``French.France.1252`` language on Windows)
to be installed.

Testing Checklist
-----------------

The following is a summary list of steps needed to test Pyrseas on a
new machine.  Refer to :ref:`development` for details on how to
accomplish a given installation task.  "Package manager" refers to the
platform's package management system utility such as ``apt-get`` or
``yum``.  Installation from PyPI can be done with ``pip``.  Some
operations require administrative or superuser privileges, at either
the operating system or Postgres level.

 - Install Git using package manager or from
   https://git-scm.com/download (on Windows, prefer Git Bash)

 - ``git clone git://github.com/perseas/Pyrseas.git``

 - Install Python 3.7 (or 3.6) and 2.7, using package manager or from
   installers at https://www.python.org/downloads/.

 - Install Postgres 11, 10, 9.6, 9.5 and 9.4, using package manager or
   binary installers at https://www.postgresql.org/download/

   .. note:: On Linux, make sure you install the contrib and plperl
             packages, e.g., on Debian, postgresql-contrib-n.n and
             postgresql-plperl-n.n (where `n.n` is the Postgres
             version number--or simply `n` from Postgres 10 onward)

 - Install Psycopg2, using package manager, or from PyPI
   (https://pypi.org/project/psycopg2/) or
   http://initd.org/psycopg/download/.

   .. note:: On Windows, you may first want to install a version of
             Microsoft Visual Studio from `here`_.  An alternative
             that may work is `MinGW <http://mingw.org/>`_. See
             `these blog`_ `posts`_ for more details.

 .. _here: https://www.microsoft.com/en-us/download/developer-tools.aspx

 .. _these blog: https://pyrseas.wordpress.com/2012/09/25/testing-python-and-postgresql-on-windows-part-2/

 .. _posts: https://pyrseas.wordpress.com/2012/09/28/testing-python-and-postgresql-on-windows-part-3/

 - Install PyYAML, using package manager, or from PyPI
   (https://pypi.org/project/PyYAML/) or
   http://pyyaml.org/download/pyyaml/.

 - Install PgDbConn from PyPI (https://pypi.org/project/pgdbconn/).

 - Install pytest, using package manager, or from PyPI
   (https://pypi.org/project/pytest/).

 - Install Tox, using package manager, or from PyPI
   (https://pypi.org/project/tox/)

   .. note:: Psycopg2, PyYAML, pytest and Tox all have to be installed
             twice, i.e., once under Python 3.7 (or 3.6) and another
             under 2.7.

 - On Windows, install Perl (see discussion above under
   "Restrictions"). On Linux, usually Perl is already available.

 - As **postgres** user, using psql or pgAdmin, create a test user,
   e.g., your name.  The user running tests must have at a minimum
   createdb privilege, in order to create the test database.  To run
   *all* the tests, the user also needs superuser privilege.

 - Create a Postgres password file, e.g., on Linux: ``~/.pgpass``, on
   Windows: ``%APPDATA%\postgresql\pgpass.conf``.

 - Create directories to hold tablespaces, e.g., ``/extra/pg/11.0/ts1``
   on Linux, ``C:\\extra\\pg\\11.0\\ts1`` on Windows.  The directories
   need to be owned by the **postgres** user. This may be tricky on
   older Windows versions, but the command ``cacls <dir> /E /G
   postgres:F`` should suffice.  Using ``psql``, create tablespaces
   **ts1** and **ts2**, e.g., ``CREATE TABLESPACE ts1 LOCATION
   '<directory>'`` (on Windows, you'll have to use, e.g.,
   ``E'C:\\dir\\ts1'``, to specify the directory).

 - Install the locale ``fr_FR.utf8`` on Linux/Unix or the language
   ``French.France.1252`` on Windows.

   - On Debian and derivatives, this can be done with the command::

      sudo dpkg-reconfigure locales

   - On Windows, open the Control Panel, select Date, Time, Language,
     and Regional Options, then Regional and Language Options (or Add
     other languages), click on the Advanced tab in the dialog and
     then choose “French (France)” from the dropdown. Finally, click
     OK and respond to any subsequent prompts to install the locale,
     including rebooting the machine.

 - Change to the Pyrseas source directory (created by the second step above).

   - Define the ``PYTHONPATH`` environment variable to the Pyrseas source
     directory, e.g., on Linux, ``export PYTHONPATH=$PWD``, on
     Windows, ``set PYTHONPATH=%USERPROFILE%\somedir\Pyrseas``.

   - Define the environment variables ``PG94_PORT``, ``PG95_PORT``,
     ``PG96_PORT``, ``PG100_PORT`` and ``PG110_PORT`` to point to the
     corresponding Postgres connection ports.

 - Invoke ``tox``. This will create two virtualenvs in a ``.tox``
   subdirectory--one for Python 3.7 or 3.6 and another for 2.7,
   install Pyrseas and its prerequisites (Psycopg2 and PyYAML) into
   each virtualenv and run the unit tests for each combination of
   Postgres and Python.

If you find any problems with the instructions above, please open an
issue on `GitHub <https://github.com/perseas/Pyrseas/issues>`_.
