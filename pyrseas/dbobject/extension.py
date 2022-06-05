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
    def query(dbversion=None):
        return """
            SELECT e.extname AS name, n.nspname AS schema, e.extversion AS version,
                   r.rolname AS owner,
                   obj_description(e.oid, 'pg_extension') AS description, e.oid
            FROM pg_extension e
                 JOIN pg_roles r ON (r.oid = e.extowner)
                 JOIN pg_namespace n ON (e.extnamespace = n.oid)
            WHERE n.nspname != 'information_schema'
            ORDER BY e.extname"""

    @staticmethod
    def from_map(name, inobj):
        """Initialize an Extension instance from a YAML map

        :param name: extension name
        :param inobj: YAML map of the extension
        :return: extension instance
        """
        return Extension(
            name, inobj.pop('description', None), inobj.pop('owner', None),
            inobj.get('schema'), inobj.pop('version', None))

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
    def create(self, dbversion=None):
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

KNOWN_LANGS = [
    "plpgsql",
    "pltcl",
    "pltclu",
    "plperl",
    "plperlu",
    "plpythonu",
    "plpython2u",
    "plpython3u"]

class ExtensionDict(DbObjectDict):
    "The collection of extensions in a database"

    cls = Extension

    def _from_catalog(self):
        """Initialize the dictionary of extensions by querying the catalogs"""
        for obj in self.fetch():
            self[obj.key()] = obj
            self.by_oid[obj.oid] = obj

    def from_map(self, inexts, newdb):
        """Initialize the dictionary of extensions by converting the input map

        :param inexts: YAML map defining the extensions
        :param newdb: dictionary of input database
        """
        for key in inexts:
            if not key.startswith('extension '):
                raise KeyError("Unrecognized object type: %s" % key)
            name = key[10:]
            inobj = inexts[key]
            self[name] = Extension.from_map(name, inobj)
            if self[name].name in KNOWN_LANGS:
                lang = {'language %s' % self[name].name: {
                    '_ext': 'e', 'owner': self[name].owner}}
                newdb.languages.from_map(lang)
