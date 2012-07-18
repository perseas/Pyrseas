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

    @commentable
    def create(self):
        """Return SQL statements to CREATE the extension

        :return: SQL statements
        """
        opt_clauses = []
        if hasattr(self, 'schema') and self.schema != 'public':
            opt_clauses.append("SCHEMA %s" % quote_id(self.schema))
        if hasattr(self, 'version'):
            opt_clauses.append("VERSION '%s'" % self.version)
        return ["CREATE EXTENSION %s%s" % (
                quote_id(self.name), ('\n    ' + '\n    '.join(opt_clauses))
                if opt_clauses else '')]


class ExtensionDict(DbObjectDict):
    "The collection of extensions in a database"

    cls = Extension
    query = \
        """SELECT extname AS name, nspname AS schema, extversion AS version,
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
            self[ext.key()] = ext

    def from_map(self, inexts, langtempls, newdb):
        """Initalize the dictionary of extensions by converting the input map

        :param inexts: YAML map defining the extensions
        :param langtempls: list of language templates
        :param newdb: dictionary of input database
        """
        for key in list(inexts.keys()):
            if not key.startswith('extension '):
                raise KeyError("Unrecognized object type: %s" % key)
            ext = key[10:]
            inexten = inexts[key]
            self[ext] = exten = Extension(name=ext)
            for attr, val in list(inexten.items()):
                setattr(exten, attr, val)
            if exten.name in langtempls:
                lang = {'language %s' % exten.name: {'_ext': 'e'}}
                newdb.languages.from_map(lang)

    def to_map(self, no_owner):
        """Convert the extension dictionary to a regular dictionary

        :param no_owner: exclude extension owner information
        :return: dictionary

        Invokes the `to_map` method of each extension to construct a
        dictionary of extensions.
        """
        extens = {}
        for ext in list(self.keys()):
            extens.update(self[ext].to_map(no_owner))
        return extens

    def diff_map(self, inexts):
        """Generate SQL to transform existing extensions

        :param inexts: a YAML map defining the new extensions
        :return: list of SQL statements

        Compares the existing extension definitions, as fetched from
        the catalogs, to the input map and generates SQL statements to
        transform the extensions accordingly.
        """
        stmts = []
        # check input extensions
        for ext in list(inexts.keys()):
            inexten = inexts[ext]
            # does it exist in the database?
            if ext not in self:
                if not hasattr(inexten, 'oldname'):
                    # create new extension
                    stmts.append(inexten.create())
                else:
                    stmts.append(self[ext].rename(inexten))
            else:
                # check extension objects
                stmts.append(self[ext].diff_map(inexten))

        # check existing extensions
        for ext in list(self.keys()):
            exten = self[ext]
            # if missing, drop them
            if ext not in inexts:
                    stmts.append(exten.drop())

        return stmts

    def _drop(self):
        """Actually drop the extension

        :return: SQL statements
        """
        stmts = []
        for ext in list(self.keys()):
            if hasattr(self[ext], 'dropped'):
                stmts.append(self[ext].drop())
        return stmts
