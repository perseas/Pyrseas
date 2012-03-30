# -*- coding: utf-8 -*-
"""
    pyrseas.extend.schema
    ~~~~~~~~~~~~~~~~~~~~~

    This defines two classes, ExtSchema and ExtSchemaDict, derived from
    DbExtension and DbExtensionDict, respectively.
"""
from pyrseas.extend import DbExtensionDict, DbExtension
from pyrseas.extend.table import ExtTable


class ExtSchema(DbExtension):
    """A database schema definition, i.e., a named collection of tables,
    views, triggers and other schema objects."""

    keylist = ['name']

    def apply(self, db, cfgdb):
        """Apply extensions to objects in a schema.

        :param db: the database to be extended
        :param cfgdb: the configuration objects
        """
        for tbl in self.tables:
            self.tables[tbl].apply(db, cfgdb)


class ExtSchemaDict(DbExtensionDict):
    "The collection of schemas in a database"

    cls = ExtSchema

    def from_map(self, extmap, extdb):
        """Initialize the dictionary of schemas by converting the extension map

        :param extmap: the input YAML map defining the extensions
        :param extdb: collection of dictionaries defining the extensions

        Starts the recursive analysis of the input map and
        construction of the internal collection of dictionaries
        describing the database objects.
        """
        for key in list(extmap.keys()):
            (objtype, spc, sch) = key.partition(' ')
            if spc != ' ' or objtype != 'schema':
                raise KeyError("Unrecognized object type: %s" % key)
            schema = self[sch] = ExtSchema(name=sch)
            inschema = extmap[key]
            exttables = {}
            extfuncs = {}
            for key in list(inschema.keys()):
                if key.startswith('table '):
                    exttables.update({key: inschema[key]})
                elif key.startswith('function '):
                    extfuncs.update({key: inschema[key]})
                else:
                    raise KeyError("Expected typed object, found '%s'" % key)
            extdb.tables.from_map(schema, exttables, extdb)

    def link_current(self, schemas):
        """Connect schemas to be extended to actual database schemas

        :param schemas: schemas in current database
        """
        for sch in list(self.keys()):
            if not sch in schemas:
                raise KeyError("Schema %s not in current database" % sch)
            if not hasattr(self[sch], 'current'):
                self[sch].current = schemas[sch]

    def link_refs(self, dbtables):
        """Connect tables and functions to their respective schemas

        :param dbtables: dictionary of tables

        Fills in the `tables` dictionary for each schema by
        traversing the `dbtables` dictionary.
        """
        for (sch, tbl) in list(dbtables.keys()):
            table = dbtables[(sch, tbl)]
            assert self[sch]
            schema = self[sch]
            if isinstance(table, ExtTable):
                if not hasattr(schema, 'tables'):
                    schema.tables = {}
                schema.tables.update({tbl: table})
