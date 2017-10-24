# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.collation
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    This defines two classes, Collation and CollationDict, derived from
    DbSchemaObject and DbObjectDict, respectively.
"""
from . import DbObjectDict, DbSchemaObject
from . import commentable, ownable


class Collation(DbSchemaObject):
    """A collation definition"""

    keylist = ['schema', 'name']
    single_extern_file = True
    catalog = 'pg_collation'

    def __init__(self, name, schema, description, owner, lc_collate, lc_ctype,
                 oid=None):
        """Initialize the collation

        :param name: collation name (from collname)
        :param description: comment text (from obj_description())
        :param schema: schema name (from colnamespace)
        :param owner: owner name (from rolname via collowner)
        :param lc_collate: LC_COLLATE (from collcollate)
        :param lc_ctype: LC_CTYPE (from collctype)
        """
        super(Collation, self).__init__(name, schema, description)
        self._init_own_privs(owner, [])
        self.lc_collate = lc_collate
        self.lc_ctype = lc_ctype
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, collname AS name, rolname AS owner,
                   collcollate AS lc_collate, collctype AS lc_ctype,
                   obj_description(c.oid, 'pg_collation') AS description, c.oid
            FROM pg_collation c
                 JOIN pg_roles r ON (r.oid = collowner)
                JOIN pg_namespace n ON (collnamespace = n.oid)
            WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
            ORDER BY nspname, collname"""

    @staticmethod
    def from_map(name, schema, inobj):
        """Initialize a Collation instance from a YAML map

        :param name: collation name
        :param name: schema map
        :param inobj: YAML map of the collation
        :return: Collation instance
        """
        obj = Collation(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('lc_collate', None),
            inobj.pop('lc_ctype', None))
        obj.set_oldname(inobj)
        return obj

    @commentable
    @ownable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the collation

        :return: SQL statements
        """
        return ["CREATE COLLATION %s (\n    LC_COLLATE = '%s',"
                "\n    LC_CTYPE = '%s')" % (
                    self.qualname(), self.lc_collate, self.lc_ctype)]


class CollationDict(DbObjectDict):
    "The collection of collations in a database."

    cls = Collation

    def from_map(self, schema, inmap):
        """Initialize the dictionary of collations by examining the input map

        :param schema: the schema owing the collations
        :param inmap: the input YAML map defining the collations
        """
        for key in inmap:
            if not key.startswith('collation '):
                raise KeyError("Unrecognized object type: %s" % key)
            name = key[10:]
            inobj = inmap[key]
            self[(schema.name, name)] = Collation.from_map(name, schema, inobj)
