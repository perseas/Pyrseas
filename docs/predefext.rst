.. _predef-ext:

Predefined Database Extensions
==============================

These extensions are built-in to :program:`dbextend`.

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
triggers to implement various extensions.

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

Copy Denormalizations
---------------------

These are one or more columns to be added to a table by copying values
from a related table.  Given a "child" table, a column from a "parent"
table can be added to the child and triggers and functions added to
both, by using a foreign key from the child and the corresponding
parent primary key, so that the child's values are automatically kept
in sync with those of the parent.

Aggregate Denormalizations
--------------------------

These are one or more columns to be added to a table by aggregating
values from a related table.  Given a "parent" table, a column can be
added to it to summarize values from a "child" table.  Triggers and
functions are added to the tables by using the parent's primary key
and a suitable child foreign key.

Calculated Columns
------------------

These are columns that can be added to a table that result from
calculations on other columns of the same table and that are stored
redundantly rather than re-calculated upon retrieval.  For example, an
extended_price column can be added to an order item table to be
derived by multiplying the quantity_ordered by the unit_price value.
