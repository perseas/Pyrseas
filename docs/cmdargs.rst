Common Command Line Options
===========================

The Pyrseas utilities support the following command line options:

-H `host`, ---host= `host`

    Specifies the host name of the machine on which the PostgreSQL
    server is running. The default host name is 'localhost'.

-h, ---help

    Show help about the program's command line arguments, and exit.

-o `file`, ---output= `file`

    Send output to the specified file. If this is omitted, the
    standard output is used.

-p `port`, ---port= `port`

    Specifies the TCP port on which the PostgreSQL server is listening
    for connections. The default port number is 5432.

-U `username`, ---user= `username`

    User name to connect as. The default user name is provided by the
    environment variable :envvar:`USER`.

---version

    Print the program version and exit.

-W, ---password

    Force the program to prompt for a password before connecting to a
    database.  If this option is not specified and password
    authentication is required, the program will resort to libpq
    defaults, i.e., `password file
    <http://www.postgresql.org/docs/current/static/libpq-pgpass.html>`_
    or `PGPASSWORD environment variable
    <http://www.postgresql.org/docs/current/static/libpq-envars.html>`_.

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

