# -*- coding: utf-8 -*-
"""
    pyrseas.conversion
    ~~~~~~~~~~~~~~~~~~

    This defines two classes, Conversion and ConversionDict, derived from
    DbSchemaObject and DbObjectDict, respectively.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject


class Conversion(DbSchemaObject):
    """A conversion definition"""

    keylist = ['schema', 'name']
    objtype = "CONVERSION"

    def create(self):
        """Return SQL statements to CREATE the conversion

        :return: SQL statements
        """
        stmts = []
        dflt = ''
        if hasattr(self, 'default') and self.default:
            dflt = 'DEFAULT '
        stmts.append("CREATE %sCONVERSION %s\n    FOR '%s' TO '%s' FROM %s" % (
                dflt, self.qualname(), self.source_encoding,
                self.dest_encoding, self.function))
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts


class ConversionDict(DbObjectDict):
    "The collection of conversions in a database."

    cls = Conversion
    query = \
        """SELECT nspname AS schema, conname AS name,
                  pg_encoding_to_char(c.conforencoding) AS source_encoding,
                  pg_encoding_to_char(c.contoencoding) AS dest_encoding,
                  conproc AS function, condefault AS default,
                  obj_description(c.oid, 'pg_conversion') AS description
           FROM pg_conversion c
                JOIN pg_namespace n ON (connamespace = n.oid)
           WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
           ORDER BY nspname, conname"""

    def from_map(self, schema, inmap):
        """Initialize the dictionary of conversions by examining the input map

        :param schema: the schema owing the conversions
        :param inmap: the input YAML map defining the conversions
        """
        for key in inmap.keys():
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

    def diff_map(self, inconvs):
        """Generate SQL to transform existing conversions

        :param inconvs: a YAML map defining the new conversions
        :return: list of SQL statements

        Compares the existing conversion definitions, as fetched from
        the catalogs, to the input map and generates SQL statements to
        create, drop or change the conversions accordingly.
        """
        stmts = []
        # check input conversions
        for cnv in inconvs.keys():
            inconv = inconvs[cnv]
            # does it exist in the database?
            if cnv in self:
                stmts.append(self[cnv].diff_map(inconv))
            else:
                # check for possible RENAME
                if hasattr(inconv, 'oldname'):
                    oldname = inconv.oldname
                    try:
                        stmts.append(self[oldname].rename(inconv.name))
                        del self[oldname]
                    except KeyError as exc:
                        exc.args = ("Previous name '%s' for conversion '%s' "
                                    "not found" % (oldname, inconv.name), )
                        raise
                else:
                    # create new conversion
                    stmts.append(inconv.create())
        # check database conversions
        for (sch, cnv) in self.keys():
            # if missing, drop it
            if (sch, cnv) not in inconvs:
                stmts.append(self[(sch, cnv)].drop())

        return stmts
