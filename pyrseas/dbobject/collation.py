# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.collation
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    This defines two classes, Collation and CollationDict, derived from
    DbSchemaObject and DbObjectDict, respectively.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject import commentable, ownable


class Collation(DbSchemaObject):
    """A collation definition"""

    keylist = ['schema', 'name']
    single_extern_file = True
    catalog = 'pg_collation'

    @commentable
    @ownable
    def create(self):
        """Return SQL statements to CREATE the collation

        :return: SQL statements
        """
        return ["CREATE COLLATION %s (\n    LC_COLLATE = '%s',"
                "\n    LC_CTYPE = '%s')" % (
                self.qualname(), self.lc_collate, self.lc_ctype)]


class CollationDict(DbObjectDict):
    "The collection of collations in a database."

    cls = Collation
    query = \
        """SELECT c.oid,
                  nspname AS schema, collname AS name, rolname AS owner,
                  collcollate AS lc_collate, collctype AS lc_ctype,
                  obj_description(c.oid, 'pg_collation') AS description
           FROM pg_collation c
                JOIN pg_roles r ON (r.oid = collowner)
                JOIN pg_namespace n ON (collnamespace = n.oid)
           WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
           ORDER BY nspname, collname"""

    def from_map(self, schema, inmap):
        """Initialize the dictionary of collations by examining the input map

        :param schema: the schema owing the collations
        :param inmap: the input YAML map defining the collations
        """
        for key in inmap:
            if not key.startswith('collation '):
                raise KeyError("Unrecognized object type: %s" % key)
            cll = key[10:]
            incoll = inmap[key]
            coll = Collation(schema=schema.name, name=cll, **incoll)
            if incoll:
                if 'oldname' in incoll:
                    coll.oldname = incoll['oldname']
                    del incoll['oldname']
                if 'description' in incoll:
                    coll.description = incoll['description']
            self[(schema.name, cll)] = coll

    def _from_catalog(self):
        """Initialize the dictionary of collations by querying the catalogs"""
        if self.dbconn.version < 90100:
            return
        for coll in self.fetch():
            self.by_oid[coll.oid] = self[coll.key()] = coll
