# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.extension
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: Extension derived from DbObject,
    and ExtensionDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbObject
from pyrseas.dbobject import quote_id, commentable


class Extension(DbObject):
    """An extension"""

    keylist = ['name']
    objtype = "EXTENSION"
    single_extern_file = True
    catalog_table = 'pg_extension'

    def __init__(self, name, description, owner, schema, privileges=None,
                 version=None, oid=None):
        super(Extension, self).__init__(name, description, owner, privileges)
        self.schema = schema
        self.version = version
        self.oid = oid

    def get_implied_deps(self, db):
        """Return the implied dependencies of the object

        :param db: the database where this object exists
        :return: set of `DbObject`
        """
        deps = super(Extension, self).get_implied_deps(db)
        if self.schema is not None:
            s = db.schemas.get(self.schema)
            if s:
                deps.add(s)

        return deps

    @commentable
    def create(self):
        """Return SQL statements to CREATE the extension

        :return: SQL statements
        """
        opt_clauses = []
        if self.schema is not None and self.schema not in (
                'pg_catalog', 'public'):
            opt_clauses.append("SCHEMA %s" % quote_id(self.schema))
        if self.version is not None:
            opt_clauses.append("VERSION '%s'" % self.version)
        return ["CREATE EXTENSION %s%s" % (
                quote_id(self.name), ('\n    ' + '\n    '.join(opt_clauses))
                if opt_clauses else '')]

    def alter_sql(self, inobj, no_owner=True):
        return super(Extension, self).alter_sql(inobj, no_owner=no_owner)

    def drop_sql(self):
        # TODO: this should not be special-cased -- see Language
        if self.name != 'plpgsql':
            return super(Extension, self).drop_sql()
        else:
            return []


class ExtensionDict(DbObjectDict):
    "The collection of extensions in a database"

    cls = Extension
    query = \
        """SELECT oid,
                  extname AS name, nspname AS schema, extversion AS version,
                  rolname AS owner,
                  obj_description(e.oid, 'pg_extension') AS description
           FROM pg_extension e
                JOIN pg_roles r ON (r.oid = extowner)
                JOIN pg_namespace n ON (extnamespace = n.oid)
           WHERE nspname != 'information_schema'
           ORDER BY extname"""

    def _from_catalog(self):
        """Initialize the dictionary of extensions by querying the catalogs"""
        if self.dbconn.version < 90100:
            return
        for ext in self.fetch():
            self.by_oid[ext.oid] = self[ext.key()] = ext

    def from_map(self, inexts, langtempls, newdb):
        """Initalize the dictionary of extensions by converting the input map

        :param inexts: YAML map defining the extensions
        :param langtempls: list of language templates
        :param newdb: dictionary of input database
        """
        for key in inexts:
            if not key.startswith('extension '):
                raise KeyError("Unrecognized object type: %s" % key)
            ext = key[10:]
            inexten = inexts[key]
            self[ext] = Extension(name=ext,
                                  description=inexten.get('description'),
                                  owner=inexten.get('owner'),
                                  schema=inexten['schema'],
                                  version=inexten.get('version'))
            if self[ext].name in langtempls:
                lang = {'language %s' % self[ext].name: {'_ext': 'e'}}
                newdb.languages.from_map(lang)
