# -*- coding: utf-8 -*-
"""
    pyrseas.schema
    ~~~~~~~~~~~~~~

    This defines two classes, Schema and SchemaDict, derived from
    DbObject and DbObjectDict, respectively.
"""
from pyrseas.dbobject import DbObjectDict, DbObject
from table import Table, Sequence

KEY_PREFIX = 'schema '


class Schema(DbObject):
    """A database schema definition, i.e., a named collection of tables,
    views, triggers and other schema objects."""

    keylist = ['name']

    def extern_key(self):
        """Return the key to be used in external maps for this schema

        :return: string
        """
        return KEY_PREFIX + self.name

    def to_map(self, dbschemas):
        """Convert tables, etc., dictionaries to a YAML-suitable format

        :param dbschemas: dictionary of schemas
        :return: dictionary
        """
        key = self.extern_key()
        schema = {key: {}}
        if hasattr(self, 'sequences'):
            seqs = {}
            for seq in self.sequences.keys():
                seqs.update(self.sequences[seq].to_map())
            schema[key].update(seqs)
        if hasattr(self, 'tables'):
            tbls = {}
            for tbl in self.tables.keys():
                tbls.update(self.tables[tbl].to_map(dbschemas))
            schema[key].update(tbls)
        return schema

    def create(self):
        """Return SQL statement to CREATE the schema

        :return: SQL statement
        """
        return "CREATE SCHEMA %s" % self.name

    def drop(self):
        """Return SQL statement to DROP the schema

        :return: SQL statement
        """
        return "DROP SCHEMA %s CASCADE" % self.name

    def rename(self, newname):
        """Return SQL statement to RENAME the schema

        :param newname: the new name for the schema
        :return: SQL statement
        """
        return "ALTER SCHEMA %s RENAME TO %s" % (self.name, newname)


class SchemaDict(DbObjectDict):
    "The collection of schemas in a database.  Minimally, the 'public' schema."

    cls = Schema
    query = \
        """SELECT nspname AS name
           FROM pg_namespace JOIN pg_roles ON (nspowner = pg_roles.oid)
           WHERE nspname = 'public' OR rolname <> 'postgres'
           ORDER BY nspname"""

    def from_map(self, inmap, newdb):
        """Initialize the dictionary of schemas by converting the input map

        :param inmap: the input YAML map defining the schemas
        :param newdb: collection of dictionaries defining the database

        Starts the recursive analysis of the input map and
        construction of the internal collection of dictionaries
        describing the database objects.
        """
        for sch in inmap.keys():
            if not sch.startswith(KEY_PREFIX):
                raise KeyError("Expected named schema, found '%s'" % sch)
            key = sch.split()[1]
            schema = self[key] = Schema(name=key)
            inschema = inmap[sch]
            if inschema:
                if 'oldname' in inschema:
                    schema.oldname = inschema['oldname']
                    del inschema['oldname']
                newdb.tables.from_map(schema, inschema, newdb)

    def link_refs(self, dbtables):
        """Connect tables and sequences to their respective schemas

        :param dbtables: dictionary of tables and sequences

        Fills in the `tables` and `sequences` dictionaries for each
        schema by traversing the `dbtables` dictionary, which is keyed
        by schema and table name.
        """
        for (sch, tbl) in dbtables.keys():
            table = dbtables[(sch, tbl)]
            assert self[sch]
            schema = self[sch]
            if isinstance(table, Table):
                if not hasattr(schema, 'tables'):
                    schema.tables = {}
                schema.tables.update({tbl: table})
            elif isinstance(table, Sequence):
                if not hasattr(schema, 'sequences'):
                    schema.sequences = {}
                schema.sequences.update({tbl: table})

    def to_map(self):
        """Convert the schema dictionary to a regular dictionary

        :return: dictionary

        Invokes the `to_map` method of each schema to construct a
        dictionary of schemas.
        """
        schemas = {}
        for sch in self.keys():
            schemas.update(self[sch].to_map(self))
        return schemas

    def diff_map(self, inschemas):
        """Generate SQL to transform existing schemas

        :param input_map: a YAML map defining the new schemas
        :return: list of SQL statements

        Compares the existing schema definitions, as fetched from the
        catalogs, to the input map and generates SQL statements to
        transform the schemas accordingly.
        """
        stmts = []
        # check input schemas
        for sch in inschemas.keys():
            insch = inschemas[sch]
            # does it exist in the database?
            if sch not in self:
                # check for possible RENAME
                if hasattr(insch, 'oldname'):
                    oldname = insch.oldname
                    try:
                        stmts.append(self[oldname].rename(insch.name))
                        del self[oldname]
                    except KeyError, exc:
                        exc.args = ("Previous name '%s' for schema '%s' "
                                   "not found" % (oldname, insch.name), )
                        raise
                else:
                    # create new schema
                    stmts.append(insch.create())
        # check database schemas
        for sch in self.keys():
            # if missing and not 'public', drop it
            if sch != 'public' and sch not in inschemas:
                stmts.append(self[sch].drop())
        return stmts
