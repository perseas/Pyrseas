# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.extension
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: Extension derived from DbObject,
    and ExtensionDict derived from DbObjectDict.
"""
from . import DbObjectDict, DbObject
from . import quote_id, commentable


class Extension(DbObject):
    """An extension"""

    keylist = ['name']
    single_extern_file = True
    catalog = 'pg_extension'

    def __init__(self, name, description, owner, schema, version=None,
                 oid=None):
        """Initialize the extension

        :param name: extension name (from extlname)
        :param description: comment text (from obj_description())
        :param schema: schema name (from extnamespace)
        :param owner: owner name (from rolname via extowner)
        :param version: version name (from extversion)
        """
        super(Extension, self).__init__(name, description)
        self._init_own_privs(owner, [])
        self.schema = schema
        self.version = version
        self.oid = oid

    @staticmethod
    def query():
        return """
            SELECT extname AS name, nspname AS schema, extversion AS version,
                   rolname AS owner,
                   obj_description(e.oid, 'pg_extension') AS description, oid
            FROM pg_extension e
                 JOIN pg_roles r ON (r.oid = extowner)
                 JOIN pg_namespace n ON (extnamespace = n.oid)
            WHERE nspname != 'information_schema'
            ORDER BY extname"""

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

    def alter(self, inobj, no_owner=True):
        """Generate SQL to transform an existing extension

        :param inobj: a YAML map defining the new extension
        :return: list of SQL statements

        This exists because ALTER EXTENSION does not permit altering
        the owner.
        """
        return super(Extension, self).alter(inobj, no_owner=no_owner)

    def drop(self):
        # TODO: this should not be special-cased -- see Language
        if self.name != 'plpgsql':
            return super(Extension, self).drop()
        else:
            return []


class ExtensionDict(DbObjectDict):
    "The collection of extensions in a database"

    cls = Extension

    def _from_catalog(self):
        """Initialize the dictionary of extensions by querying the catalogs"""
        for obj in self.fetch():
            self[obj.key()] = obj
            self.by_oid[obj.oid] = obj

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
            inobj = inexts[key]
            self[ext] = Extension(ext, inobj.pop('description', None),
                                  inobj.pop('owner', None),
                                  inobj.get('schema'),
                                  inobj.pop('version', None))
            if self[ext].name in langtempls:
                lang = {'language %s' % self[ext].name: {'_ext': 'e'}}
                newdb.languages.from_map(lang)
