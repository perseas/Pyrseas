=======
Pyrseas
=======

.. image:: https://circleci.com/gh/DevotedHealth/Pyrseas/tree/master.svg?style=svg
    :target: https://circleci.com/gh/DevotedHealth/Pyrseas/tree/master
    
Pyrseas provides utilities to describe a PostgreSQL database schema as
YAML, to verify the schema against the same or a different database
and to generate SQL that will modify the schema to match the YAML
description.

Features
--------

- Outputs a YAML description of a Postgres database's tables
  and other objects (metadata), suitable for storing in a version
  control repository

- Generates SQL statements to modify a database so that it will match
  an input YAML/JSON specification

- Generates an augmented YAML description of a Postgres database
  from its catalogs and an augmentation specification.

Requirements
------------

- PostgreSQL 9.4 or higher

- Python 2.7, 3.4 or higher

License
-------

Pyrseas is free (libre) software and is distributed under the BSD
license.  Please see the LICENSE file for details.

Documentation
-------------

Please visit `Read the Docs <https://pyrseas.readthedocs.io/en/latest/>`_
for the latest documentation.

Devoted Notes
-------------

We forked Pyrseas a while ago because we needed to calculate the diffs at CI time, not just against a db. After a brief discussion with the maintainer (https://github.com/perseas/Pyrseas/issues/204), they pointed us at the right entry point and suggested that we fork.

It's best to use a virtualenv as installing this will impact other users on the dev server

```bash
> virtualenv venv
> source venv/bin/activate
> pip install . && ./venv/bin/yamltodb --db-spec <file> <file>
```

Most of their tests fail locally since it requires a db in order to run. We've created a new folder, in tests/unit that just takes two yaml dicts and runs the diff to make sure that our bug fixes remain fixed. You can test that those still run by cd'ing into that folder an running `pytest` (you might need to `pip install pytest` and be with in a virtualenv).
