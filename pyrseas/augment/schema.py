# -*- coding: utf-8 -*-
"""
    pyrseas.augment.schema
    ~~~~~~~~~~~~~~~~~~~~~~

    This defines two classes, AugSchema and AugSchemaDict, derived from
    DbAugment and DbAugmentDict, respectively.
"""
from pyrseas.augment import DbAugmentDict, DbAugment
from pyrseas.augment.table import AugTable


class AugSchema(DbAugment):
    """A database schema definition, i.e., a named collection of tables,
    views, triggers and other schema objects."""

    keylist = ['name']

    def apply(self, augdb):
        """Augment objects in a schema.

        :param augdb: the augmenter dictionaries
        """
        for tbl in self.tables:
            self.tables[tbl].apply(augdb)

    def add_func(self, func):
        """Add a function to the schema if not already present

        :param func: the possibly new function
        """
        sch = self.current
        if not hasattr(sch, 'functions'):
            sch.functions = {}
        if func.name not in sch.functions:
            sch.functions.update({func.name: func})


class AugSchemaDict(DbAugmentDict):
    "The collection of schemas in a database"

    cls = AugSchema

    def from_map(self, augmap, augdb):
        """Initialize the dictionary of schemas by converting the augmenter map

        :param augmap: the input YAML map defining the augmentations
        :param augdb: collection of dictionaries defining the augmentations

        Starts the recursive analysis of the input map and
        construction of the internal collection of dictionaries
        describing the database objects.
        """
        for key in augmap:
            (objtype, spc, sch) = key.partition(' ')
            if spc != ' ' or objtype != 'schema':
                raise KeyError("Unrecognized object type: %s" % key)
            schema = self[sch] = AugSchema(name=sch)
            inschema = augmap[key]
            augtables = {}
            augfuncs = {}
            for key in inschema:
                if key.startswith('table '):
                    augtables.update({key: inschema[key]})
                elif key.startswith('function '):
                    augfuncs.update({key: inschema[key]})
                else:
                    raise KeyError("Expected typed object, found '%s'" % key)
            augdb.tables.from_map(schema, augtables, augdb)

    def link_current(self, schemas):
        """Connect schemas to be augmented to actual database schemas

        :param schemas: schemas in current database
        """
        for sch in self:
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
        for (sch, tbl) in dbtables:
            table = dbtables[(sch, tbl)]
            assert self[sch]
            schema = self[sch]
            if isinstance(table, AugTable):
                if not hasattr(schema, 'tables'):
                    schema.tables = {}
                schema.tables.update({tbl: table})
