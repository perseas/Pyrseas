Configuration Items
===================

The following lists the various sections allowed in a configuration
file and the items that are recognized by the Pyrseas utilities.

Augmenter
---------

This section is used by the :program:`dbaugment` utility (see
:doc:`dbaugment`).  Most of these are specified in the system
configuration file delivered with Pyrseas, but can also be included or
overriden in user or repository configuration files.

- audit_columns: This section defines combinations of columns and
  triggers to be added to tables.  Both columns and triggers are
  specified as YAML lists (to be consistent with :program:`dbtoyaml`
  YAML output), although normally a single trigger will be necessary
  per column combination.  The columns and triggers should reference
  previously defined items in the ``columns`` and ``triggers``
  sections (see below).  See :doc:`predefaug` for audit columns
  defined in the system ``config.yaml``.

- columns: This section defines prototype columns to be added to a
  table by Augmenter.  For each column, a valid `Postgres data type
  <https://www.postgresql.org/docs/current/static/datatype.html>`_
  should be included.

  You can also add a ``not_null`` constraint and a ``default``
  specification.  See :doc:`predefaug` for columns defined in the
  system ``config.yaml``.  In a repository or user configuration file,
  you can also specify an alternate name for a previously defined
  column.  For example, if you prefer that the ``modified_timestamp``
  columns be named ``last_update``, you can add the following to a
  configuration file::

   augmenter:
     columns:
       modified_timestamp:
         name: last_update

- function_templates: This section defines the source text for the
  trigger functions (see below) using a template language. Any text
  enclosed in double braces, e.g., ``{{modified_by_user}}``, will be
  replaced, typically by a previously defined column or its alternate
  name (see above).

- functions: This section defines prototype trigger functions to be
  invoked by audit columns or other augmentations.  The following
  items can be specified for each function:

  - description: Text for a `COMMENT
    <https://www.postgresql.org/docs/current/static/sql-comment.html>`_
    statement on the function.

  - language: Procedural language, e.g., ``plpgsql``, in which the
    function is written.

  - returns: Value should be ``trigger``.

  - security_definer: Indicates whether the function is to be executed
    with the privileges of the user that created it.  This is usually
    needed for audit column trigger functions.

  - source: This is usually a reference to a function template (see
    above) enclosed in double braces, e.g.,
    ``{{functempl_audit_default}}``.  However, in user or repository
    configurations, this can also be the actual text of the function.

  See :doc:`predefaug` for functions defined in the system
  configuration file.

- schema pyrseas: This section currently defines three functions that
  may be installed in the ``pyrseas`` schema if the ``full`` audit
  columns specifications is added for Augmenter processing.

- schemas and tables: Multiple ``schema schema-name`` sections can be
  present, typically in a repository configuration file.  Each such
  section can include ``table table-name`` items, and under each the
  ``audit_columns`` specifications to be added to the given table.
  For example::

   augmenter:
     schema public:
       table t1:
         audit_columns: default

- triggers: This section defines the prototype triggers to be used
  with audit columns and other augmentations.  The following items can
  be specified for each trigger:

  - events: This is a list that can include one or more of ``insert``,
    ``update`` or ``delete`` (the latter is not used for audit columns
    but may be used in future augmentations).

  - level: This can take the values ``row`` or ``statement`` (usually
    the former).

  - name: This specifies the name to be given to a trigger.  It can be
    a template using ``{{table_name}}`` which will then be replaced
    with the actual table name on which the trigger will act.

  - procedure: This is the invocation name, e.g., ``audit_default()``
    of the function to be called when the trigger fires.

  - timing: This can take the values ``before`` or ``after`` (usually
    the former).

Database
--------

This section is primarily for a user configuration file.  If you
frequently connect to a particular host, port or as a given user, that
are *not* the Postgres defaults, adding corresponding entries to your
user configuration file allows you to automatically override the
defaults.  If for a given invocation you need to connect to or as a
different host, port or user, you can still override the configuration
using the command line options (see :doc:`cmdargs`):

- host: Name of the host to connect. Please refer to the `Postgres
  connection host documentation
  <https://www.postgresql.org/docs/current/static/libpq-connect.html#LIBPQ-CONNECT-HOST>`_
  for details and defaults.

- port: Port number to connect to.  See the `Postgres connection port
  documentation
  <https://www.postgresql.org/docs/current/static/libpq-connect.html#LIBPQ-CONNECT-PORT>`_
  for more.

- username: Name of the user to connect as.  View the `Postgres
  connection user documentation
  <https://www.postgresql.org/docs/current/static/libpq-connect.html#LIBPQ-CONNECT-USER>`_
  for more.

Datacopy
--------

This section is normally in a user or repository configuration file.
It is used by :program:`dbtoyaml` and :program:`yamltodb` to determine
which tables should be exported from or imported to the database.  It
consists of schema names, using the format `schema schema_name`,
followed by lists of table names.  For example::

 datacopy:
   schema public:
   - t1
   - t2
   schema s1:
   - t3

Repository
----------

This section is used by all utilities (but :program:`dbaugment` does
not fully support it).  The "repository" is intended to be a version
control, e.g., Git, Mercurial, or Subversion, repository.

- data: Path, relative to the root of the repository, where
  :program:`dbtoyaml` and :program:`yamltodb` place or expect the
  files containing data exported from or imported to the database. The
  tables to be exported or imported are specified in the ``Datacopy``
  section.  The default value (defined in the system ``config.yaml``)
  is **metadata**.

- metadata: Path, relative to the root of the repository, where
  :program:`dbtoyaml` and :program:`yamltodb` place or expect the YAML
  specification files for the database objects when the
  `--multiple-files` option is used.  The default value (defined
  in the system ``config.yaml``) is **metadata**.

- path: Absolute path to the root of the repository.  This should
  normally be specified in a user configuration file, or in a file
  given with the :option:`--config` option.  If not specified, this
  defaults to the current working directory from which the utility is
  run.
