# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.extension
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: Extension derived from
    DbSchemaObject, and ExtensionDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject, quote_id


class Extension(DbSchemaObject):
    """An extension"""

    keylist = ['schema', 'name']
    objtype = "EXTENSION"

    def create(self):
        """Return SQL statements to CREATE the extension

        :return: SQL statements
        """
        stmts = []
        opt_clauses = []
        if self.schema != 'public':
            opt_clauses.append("SCHEMA %s" % quote_id(self.schema))
        if hasattr(self, 'version'):
            opt_clauses.append("VERSION '%s'" % self.version)
        stmts.append("CREATE EXTENSION %s%s" % (
                quote_id(self.name), ('\n    ' + '\n    '.join(opt_clauses))
                if opt_clauses else ''))
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts


class ExtensionDict(DbObjectDict):
    "The collection of extensions in a database"

    cls = Extension
    query = \
        """SELECT nspname AS schema, extname AS name, extversion AS version,
                  obj_description(e.oid, 'pg_extension') AS description
           FROM pg_extension e
                JOIN pg_namespace n ON (extnamespace = n.oid)
           WHERE nspname != 'information_schema'
           ORDER BY 1, 2"""

    def _from_catalog(self):
        """Initialize the dictionary of extensions by querying the catalogs"""
        if self.dbconn.version < 90100:
            return
        for ext in self.fetch():
            self[ext.key()] = ext

    def from_map(self, schema, inexts):
        """Initalize the dictionary of extensions by converting the input map

        :param schema: schema owning the extensions
        :param inexts: YAML map defining the extensions
        """
        for key in list(inexts.keys()):
            if not key.startswith('extension '):
                raise KeyError("Unrecognized object type: %s" % key)
            ext = key[10:]
            inexten = inexts[key]
            self[(schema.name, ext)] = exten = Extension(
                schema=schema.name, name=ext)
            for attr, val in list(inexten.items()):
                setattr(exten, attr, val)
            if 'oldname' in inexten:
                exten.oldname = inexten['oldname']
            if 'description' in inexten:
                exten.description = inexten['description']

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
        for (sch, ext) in list(inexts.keys()):
            inexten = inexts[(sch, ext)]
            # does it exist in the database?
            if (sch, ext) not in self:
                if not hasattr(inexten, 'oldname'):
                    # create new extension
                    stmts.append(inexten.create())
                else:
                    stmts.append(self[(sch, ext)].rename(inexten))
            else:
                # check extension objects
                stmts.append(self[(sch, ext)].diff_map(inexten))

        # check existing extensions
        for (sch, ext) in list(self.keys()):
            exten = self[(sch, ext)]
            # if missing, drop them
            if (sch, ext) not in inexts:
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
