.. _testing:

Testing
=======

The majority of Pyrseas' capabilities are exercised and verified via
unit tests written using Python's `unittest framework
<http://docs.python.org/library/unittest.html>`_.  The tests can be
run from the command line by most users, e.g.,

::

   cd tests/dbobject
   python test_table.py
   python test_constraint.py ForeignKeyToMapTestCase
   python test_trigger.py TriggerToSqlTestCase.test_create_trigger
   python __init__.py
   python -m unittest discover

The first ``python`` command above runs all tests related to tables,
mapping, creating, dropping, etc.  The next command runs the subset of
tests related to mapping tables with foreign keys and the following
one executes a single test to generate SQL to create a trigger.  The
fourth command runs through all the tests suites in the ``dbobject``
subdirectory.  The final command does the same but using the test
discovery feature available from Python 2.7.

Environment Variables
---------------------

By default, the tests use a PostgreSQL database named
``pyrseas_testdb`` which is created if it doesn't already exist. The
tests are run as the logged in user, using the ``USER`` Unix/Linux
environment variable (or ``USERNAME`` under Windows). They access
PostgreSQL on the local host using the default port number (5432).

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

Most tests do not require special privileges. However, tests that
define dynamically loaded functions (e.g.,
:func:`test_create_c_lang_function` in :mod:`test_function.py`)
require SUPERUSER privilege. Such tests will be skipped if the user
lacks the privilege.

Most tests do not require installation of supporting PostgreSQL
packages.  However, tests that define dynamically loaded functions
(see above) require that the `contrib/spi module
<http://www.postgresql.org/docs/current/static/contrib-spi.html>`_ be
installed.

On Windows, it is necessary to install Perl in order to run some of
the tests. A suitable choice is Strawberry Perl which can be
downloaded from http://strawberryperl.com/releases.html. However, the
default installation is placed in ``C:\strawberry`` and can hold a
single Perl version.  Furthermore, PostgreSQL 8.4 and 9.0 are linked
with Perl 5.10 whereas PostgreSQL 9.1 and 9.2 are linked with 5.14.
It is recommended that Perl 5.10 be installed as this gives the fewest
test failures.  See `this blog post
<http://pyrseas.wordpress.com/2012/10/17/testing-python-and-postgresql-on-windows-part-5/>`_
for more details.

The COLLATION tests, run under PostgreSQL 9.1 and 9.2, require the
``fr_FR.utf8`` locale (or ``French.France.1252`` language on Windows)
to be installed.

Testing Checklist
-----------------

The following is a summary list of steps needed to test Pyrseas on a
new machine.  Refer to :ref:`development` for details on how to
accomplish a given installation task.  "Package manager" refers to the
platform's package management system utility such as ``apt-get`` or
``yum``.  Installation from PyPI can be done with either ``pip`` or
``easy_install``.  Some operations require administrative or superuser
privileges, at either the operating system or PostgreSQL level.

 - Install Git using package manager or from
   http://git-scm.com/download (on Windows, prefer Git Bash)

 - ``git clone git://github.com/jmafc/Pyrseas.git``

 - Install Python 2.7 and 3.2, using package manager or from
   installers at http://www.python.org/download/.

 - Install PostgreSQL 9.2, 9.1, 9.0 and 8.4, using package manager or
   binary installers at http://www.postgresql.org/download/

   .. note:: On Linux, make sure you install the contrib and plperl
             packages, e.g., on Debian, postgresql-contrib-n.n and
             postgresql-plperl-n.n (where `n.n` is the PostgreSQL
             version number)

 - Install Psycopg2, using package manager, or from PyPI
   (http://pypi.python.org/pypi/psycopg2) or
   http://initd.org/psycopg/download/.

   .. note:: On Windows, it is best to first install the 2008
             Microsoft Visual Express Studio from `here`_.  An
             alternative that may work is to use `MinGW
             <http://mingw.org/>`_. See `these blog`_ `posts`_ for
             more details.

 .. _here: https://www.microsoft.com/en-us/download/details.aspx?displaylang=en&id=14597

 .. _these blog: http://pyrseas.wordpress.com/2012/09/25/testing-python-and-postgresql-on-windows-part-2/

 .. _posts: http://pyrseas.wordpress.com/2012/09/28/testing-python-and-postgresql-on-windows-part-3/

 - Install PyYAML, using package manager, or from PyPI
   (http://pypi.python.org/pypi/PyYAML/) or
   http://pyyaml.org/download/pyyaml/.

 - Install Tox, from PyPI (http://pypi.python.org/pypi/tox)

   .. note:: Psycopg2, PyYAML and Tox all have to be installed twice,
             i.e., once under Python 2.7 and another under 3.2.

 - On Windows, install Perl (see discussion above under
   "Restrictions"). On Linux, usually Perl is already available.

 - As **postgres** user, using psql or pgAdmin, create a test user,
   e.g., your name.  The user running tests must have at a minimum
   createdb privilege, in order to create the test database.  To run
   *all* the tests, the user also needs superuser privilege.

 - Create a PostgreSQL password file, e.g., on Linux: ``~/.pgpass``, on
   Windows: ``%APPDATA%\postgresql\pgpass.conf``.

 - Using psql or pgAdmin, create roles **user1** and **user2**.

 - Create directories to hold tablespaces, e.g., ``/extra/pg/9.1/ts1``
   on Linux, ``C:\\extra\\pg\\9.1\\ts1`` on Windows.  The directories
   need to be owned by the **postgres** user. This may be tricky on
   older Windows versions, but the command ``cacls <dir> /E /G
   postgres:F`` should suffice.  Using psql or pgAdmin, create
   tablespaces **ts1** and **ts2**, e.g., ``CREATE TABLESPACE ts1
   LOCATION '<directory>'`` (on Windows, you'll have to use, e.g.,
   ``E'C:\\dir\\ts1'``, to specify the directory).

   - On Windows, for PostgreSQL 9.2, the default installation is owned
     by the Network Service account, so the ``cacls`` command should
     be ``cacls <dir> /E /G networkservices:F``.

   .. note:: The creation of users/roles and tablespaces has to be
             repeated for each PostgreSQL version.

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

   - Define the environment variables ``PG84_PORT``, ``PG90_PORT``,
     ``PG91_PORT`` and ``PG92_PORT`` to point to the corresponding
     PostgreSQL ports.

 - Invoke ``tox``. This will create two virtualenvs in a ``.tox``
   subdirectory--one for Python 2.7 and another for 3.2, install
   Pyrseas and its prerequisites (Psycopg2 and PyYAML) into each
   virtualenv and run the unit tests for each combination of
   PostgreSQL and Python.
