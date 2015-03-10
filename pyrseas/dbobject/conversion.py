# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.conversion
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This defines two classes, Conversion and ConversionDict, derived from
    DbSchemaObject and DbObjectDict, respectively.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject import commentable, ownable


class Conversion(DbSchemaObject):
    """A conversion definition"""

    keylist = ['schema', 'name']
    single_extern_file = True
    catalog_table = 'pg_conversion'

    @commentable
    @ownable
    def create(self):
        """Return SQL statements to CREATE the conversion

        :return: SQL statements
        """
        dflt = ''
        if hasattr(self, 'default') and self.default:
            dflt = 'DEFAULT '
        return ["CREATE %sCONVERSION %s\n    FOR '%s' TO '%s' FROM %s" % (
                dflt, self.qualname(), self.source_encoding,
                self.dest_encoding, self.function)]


class ConversionDict(DbObjectDict):
    "The collection of conversions in a database."

    cls = Conversion
    query = \
        """SELECT c.oid, nspname AS schema, conname AS name, rolname AS owner,
                  pg_encoding_to_char(c.conforencoding) AS source_encoding,
                  pg_encoding_to_char(c.contoencoding) AS dest_encoding,
                  conproc AS function, condefault AS default,
                  obj_description(c.oid, 'pg_conversion') AS description
           FROM pg_conversion c
                JOIN pg_roles r ON (r.oid = conowner)
                JOIN pg_namespace n ON (connamespace = n.oid)
           WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
           ORDER BY nspname, conname"""

    def from_map(self, schema, inmap):
        """Initialize the dictionary of conversions by examining the input map

        :param schema: the schema owing the conversions
        :param inmap: the input YAML map defining the conversions
        """
        for key in inmap:
            if not key.startswith('conversion '):
                raise KeyError("Unrecognized object type: %s" % key)
            cnv = key[11:]
            inconv = inmap[key]
            conv = Conversion(schema=schema.name, name=cnv, **inconv)
            if inconv:
                if 'oldname' in inconv:
                    conv.oldname = inconv['oldname']
                    del inconv['oldname']
                if 'description' in inconv:
                    conv.description = inconv['description']
            self[(schema.name, cnv)] = conv
