.. _predef-aug:

Predefined Database Augmentations
=================================

These augmentations are built-in to :program:`dbaugment`.

Columns
-------

These are predefined column specifications that can be added to
tables, e.g., in various audit column combinations.

- created_by_ip_addr: An INET column to record the IP address which
  originated the current row.

- created_by_user: A VARCHAR(63) column to record the user, e.g.,
  CURRENT_USER, who created the current row.

- created_date: A DATE column that defaults to CURRENT_DATE.

- created_timestamp: A TIMESTAMP WITH TIME ZONE column to record the
  date and time when the current row was created.

- modified_by_ip_addr: An INET column to record the IP address which
  originated the last modification to the current row.

- modified_by_user: A VARCHAR(63) column to record the user, e.g.,
  CURRENT_USER, who last modified the current row.

- modified_timestamp: A TIMESTAMP WITH TIME ZONE column to record the
  date and time when the current row was last modified.

Functions
---------

These are predefined functions which can be added to be used in
triggers to implement various augmentations.

- Audit default (``aud_dflt``): This trigger function provides values
  for the modified_by_user and modified_timestamp audit columns.

Audit Columns
-------------

These are predefined combinations of columns to be added to tables to
record audit trail information. They may also include triggers to be
invoked to maintain the column values.

- default: This is the default for audit columns.  It adds the columns
  ``modified_by_user`` and ``modified_timestamp`` and a trigger named
  `table_name`\_20_aud_dflt to fill in the columns.

- created_date_only: This is a simple audit trail that adds a
  ``created_date`` column which defaults to the CURRENT_DATE.
