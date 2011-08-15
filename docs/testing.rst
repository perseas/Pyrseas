Testing
=======

The majority of Pyrseas' capabilites are exercised and verified via
unit tests written using Python's `unittest framework
<http://docs.python.org/library/unittest.html>`_.  The tests can be
run from the command line by most users, e.g.,

::

   cd tests/dbobject
   python test_table.py
   python test_constraint.py ForeignKeyToMapTestCase
   python test_trigger.py TriggerToSqlTestCase.test_create_trigger
   python __init__.py

The first ``python`` command above runs all tests related to tables,
mapping, creating, dropping, etc.  The next command runs the subset of
tests related to mapping tables with foreign keys and the following
one executes a single test to generate SQL to create a trigger.  The
final command runs through all the tests suites in the ``dbobject``
subdirectory.

Environment Variables
---------------------

By default, the tests use a PostgreSQL database named
``pyrseas_testdb`` which is created if it doesn't already exist. The
tests are run as the logged in user, using the "USER" Unix/Linux
environment variable if defined. They access PostgreSQL on the local
host using the default port number (5432).

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
require SUPERUSER privilege.

Most tests do not require installation of supporting packages.
However, tests that define dynamically loaded functions (see above)
require that the `contrib/spi module
<http://www.postgresql.org/docs/current/static/contrib-spi.html>`_ be
installed.
