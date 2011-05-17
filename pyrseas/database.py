# -*- coding: utf-8 -*-
"""
    pyrseas.database
    ~~~~~~~~~~~~~~~~

    A `Database` is initialized with a DbConnection object.  It
    consists of one or two `Dicts` objects, each holding various
    dictionary objects.  The `db` Dicts object defines the database
    schemas, including their tables and other objects, by querying the
    system catalogs.  The `ndb` Dicts object defines the schemas based
    on the `input_map` supplied to the `from_map` method.
"""
from pyrseas.dbobject.language import LanguageDict
from pyrseas.dbobject.schema import SchemaDict
from pyrseas.dbobject.table import ClassDict
from pyrseas.dbobject.column import ColumnDict
from pyrseas.dbobject.constraint import ConstraintDict
from pyrseas.dbobject.index import IndexDict
from pyrseas.dbobject.function import FunctionDict


def flatten(lst):
    "Flatten a list possibly containing lists to a single list"
    for elem in lst:
        if isinstance(elem, list) and not isinstance(elem, basestring):
            for subelem in flatten(elem):
                yield subelem
        else:
            yield elem


class Database(object):
    """A database definition, from its catalogs and/or a YAML spec."""

    class Dicts(object):
        """A holder for dictionaries (maps) describing a database"""

        def __init__(self, dbconn=None):
            """Initialize the various DbObjectDict-derived dictionaries

            :param dbconn: a DbConnection object
            """
            self.languages = LanguageDict(dbconn)
            self.schemas = SchemaDict(dbconn)
            self.tables = ClassDict(dbconn)
            self.columns = ColumnDict(dbconn)
            self.constraints = ConstraintDict(dbconn)
            self.indexes = IndexDict(dbconn)
            self.functions = FunctionDict(dbconn)

    def __init__(self, dbconn):
        """Initialize the database

        :param dbconn: a DbConnection object
        """
        self.dbconn = dbconn
        self.db = None

    def _link_refs(self, db):
        """Link related objects"""
        db.tables.link_refs(db.columns, db.constraints, db.indexes)
        db.schemas.link_refs(db.tables, db.functions)

    def from_catalog(self):
        """Populate the database objects by querying the catalogs

        The `db` holder is populated by various DbObjectDict-derived
        classes by querying the catalogs. The objects in the
        dictionary are then linked to related objects, e.g., columns
        are linked to the tables they belong.
        """
        self.db = self.Dicts(self.dbconn)
        if self.dbconn.conn:
            self.dbconn.conn.close()
        self._link_refs(self.db)

    def from_map(self, input_map):
        """Populate the new database objects from the input map

        :param input_map: a YAML map defining the new database

        The `ndb` holder is populated by various DbObjectDict-derived
        classes by traversing the YAML input map. The objects in the
        dictionary are then linked to related objects, e.g., columns
        are linked to the tables they belong.
        """
        self.ndb = self.Dicts()
        input_schemas = {}
        input_langs = {}
        for key in input_map.keys():
            if key.startswith('schema '):
                input_schemas.update({key: input_map[key]})
            elif key.startswith('language '):
                input_langs.update({key: input_map[key]})
            else:
                raise KeyError("Expected typed object, found '%s'" % key)
        self.ndb.languages.from_map(input_langs)
        self.ndb.schemas.from_map(input_schemas, self.ndb)
        self._link_refs(self.ndb)

    def to_map(self):
        """Convert the db maps to a single hierarchy suitable for YAML

        :return: a YAML-suitable dictionary (without Python objects)
        """
        if not self.db:
            self.from_catalog()
        dbmap = self.db.languages.to_map()
        dbmap.update(self.db.schemas.to_map())
        return dbmap

    def diff_map(self, input_map):
        """Generate SQL to transform an existing database

        :param input_map: a YAML map defining the new database
        :return: list of SQL statements

        Compares the existing database definition, as fetched from the
        catalogs, to the input YAML map and generates SQL statements
        to transform the database into the one represented by the
        input.
        """
        if not self.db:
            self.from_catalog()
        self.from_map(input_map)
        stmts = self.db.languages.diff_map(self.ndb.languages,
                                           self.dbconn.version)
        stmts.append(self.db.schemas.diff_map(self.ndb.schemas))
        stmts.append(self.db.tables.diff_map(self.ndb.tables))
        stmts.append(self.db.constraints.diff_map(self.ndb.constraints))
        stmts.append(self.db.indexes.diff_map(self.ndb.indexes))
        stmts.append(self.db.columns.diff_map(self.ndb.columns))
        stmts.append(self.db.functions.diff_map(self.ndb.functions))
        stmts.append(self.db.schemas._drop())
        stmts.append(self.db.languages._drop())
        return [s for s in flatten(stmts)]
