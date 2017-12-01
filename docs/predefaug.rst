.. _predef-aug:

Predefined Database Augmentations
=================================

These augmentations are specified in the ``config.yaml`` configuration
file distributed with Pyrseas' :program:`dbaugment`.

Columns
-------

These are predefined column specifications that can be added to
tables, e.g., in various audit column combinations (see `Audit
Columns`_ below).

- created_by_ip_address: An INET column to record the IP address which
  originated the current row.

- created_by_user: A VARCHAR(63) column to record the user, e.g.,
  CURRENT_USER, who created the current row.

- created_date: A DATE column that defaults to CURRENT_DATE.

- created_timestamp: A TIMESTAMP WITH TIME ZONE column to record the
  date and time when the current row was created.

- modified_by_ip_address: An INET column to record the IP address
  which originated the last modification to the current row.

- modified_by_user: A VARCHAR(63) column to record the user, e.g.,
  CURRENT_USER, who last modified the current row.

- modified_timestamp: A TIMESTAMP WITH TIME ZONE column to record the
  date and time when the current row was last modified.

Functions
---------

The following are predefined trigger functions which are used to
implement various augmentations.  The source for each function,
written in PL/pgSQL, is specified in a function template, named with a
``functempl_`` prefixed to the function name.

- Audit when modified (``audit_modified``): This function provides the
  CURRENT_TIMESTAMP value for audit columns.

- Default audit (``audit_default``): This function provides the
  CURRENT_USER and CURRENT_TIMESTAMP for audit columns.

- Full audit (``audit_full``): For SQL INSERTs, this function provides
  values for the user who created the row, the CURRENT_TIMESTAMP and
  the IP address for both the ``created_`` and ``modified_`` audit
  columns.  For UPDATEs, it retains the existing values in the
  ``created_`` columns and supplies current values for the
  ``modified_`` columns.

In addition, the following helper functions are defined in schema
``pyrseas``:

- get_session_variable
- set_session_variable

A variant of ``get_session_variable`` is invoked by the ``audit_full``
function to retrieve the actual (logged-on) user and IP address.  In
web applications, the user that connects to the database is typically
the system user running the web server, rather than the application
(logged on) user.  The application can invoke the
``pyrseas.set_session_variable`` function to supply the application
user and IP address so that the audit trail will reflect the
application context corrrectly.

Audit Columns
-------------

These are predefined combinations of columns to be added to tables to
record audit trail information. They may also include triggers to be
invoked to maintain the column values.

- created_date_only: This is the simplest audit trail that adds a
  ``created_date`` column which defaults to the CURRENT_DATE.

- modified_only: This is another simple audit trail.  It adds a
  ``modified_timestamp`` column which is supplied by a trigger named
  `table_name`\_20_audit_modified_only.

- default: This is the default for audit columns.  It adds the columns
  ``modified_by_user`` and ``modified_timestamp`` and a trigger named
  `table_name`\_20_audit_default to fill in the columns.

- full: This is the most extensive audit trail combination.  It adds
  ``created_`` and ``modified_`` columns for user, IP address and
  timestamp.  It also adds a trigger named
  `table_name`\_20_audit_full.
