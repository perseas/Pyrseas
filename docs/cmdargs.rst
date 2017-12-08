Common Command Line Options
===========================

The Pyrseas utilities support the following command line options:

.. cmdoption:: -c <config-file>
               --config <config-file>

    Specifies an additional `configuration file` to be read and merged
    with configuration information from other sources.  See
    :doc:`config` for more details.

.. cmdoption:: -H <host>
               --host <host>

    Specifies the `host name` of the machine on which the Postgres
    server is running.  The default host name is determined by
    Postgres (normally, a Unix-domain socket or ``localhost``).

.. cmdoption:: -h, --help

    Show help about the program's command line arguments, and exit.

.. cmdoption:: -o <file>
               --output <file>

    Send output to the specified `file`.  If this is omitted, the
    standard output is used.

.. cmdoption:: -p <port>
               --port <port>

    Specifies the `port` on which the Postgres server is listening
    for connections.  The default port number is determined by
    Postgres (normally, 5432).

.. cmdoption:: -r <path>
               --repository <path>

    Specifies the `path` to a directory where metadata and static data
    files will be written to or read from, or where an additional
    configuration file can be found.  Normally, this will be the root
    of a version control repository.  If this is not specified on the
    command line or in a configuration file, it defaults to the
    current working directory.

.. cmdoption:: -U <username>
               --user <username>

    Postgres `user name` to connect as.  The default user name is
    determined by Postgres (normally, the name of the operating system
    user running the program).

.. cmdoption:: --version

    Print the program name and version identifier and exit.

.. cmdoption:: -W, --password

    Force the program to prompt for a password before connecting to a
    database.  If this option is not specified and password
    authentication is required, the program will resort to libpq
    defaults, i.e., `password file
    <https://www.postgresql.org/docs/current/static/libpq-pgpass.html>`_
    or `PGPASSWORD environment variable
    <https://www.postgresql.org/docs/current/static/libpq-envars.html>`_.

Short options (those only one character long) can be concatenated with
their value arguments, e.g.::

  dbtoyaml -p5433 dbname

Several short options can be joined together, using only a single -
prefix, as long as only the last option (or none of them) requires a
value.

Long options (those with names longer than a single-character) can be
separated from their arguments by a '=' or passed as two separate
arguments.  For example::

  dbtoyaml --port=5433 dbname

or::

  dbtoyaml --port 5433 dbname

Long options can be abbreviated as long as the abbreviation is
unambiguous::

  dbtoyaml --pass dbname

