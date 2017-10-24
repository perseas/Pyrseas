# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.conversion
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This defines two classes, Conversion and ConversionDict, derived from
    DbSchemaObject and DbObjectDict, respectively.
"""
from . import DbObjectDict, DbSchemaObject
from . import commentable, ownable


class Conversion(DbSchemaObject):
    """A conversion definition"""

    keylist = ['schema', 'name']
    single_extern_file = True
    catalog = 'pg_conversion'

    def __init__(self, name, schema, description, owner, source_encoding,
                 dest_encoding, function, default=False,
                 oid=None):
        """Initialize the conversion

        :param name: conversion name (from conname)
        :param schema: schema name (from connamespace)
        :param description: comment text (from obj_description())
        :param owner: owner name (from rolname via conowner)
        :param source_encoding: source encoding (from conforencoding)
        :param source_encoding: destination encoding (from contoencoding)
        :param function: conversion function (from conproc)
        :param default: indicates this is default conversion (from condefault)
        """
        super(Conversion, self).__init__(name, schema, description)
        self._init_own_privs(owner, [])
        self.source_encoding = source_encoding
        self.dest_encoding = dest_encoding
        self.function = function
        self.default = default
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, conname AS name, rolname AS owner,
                   pg_encoding_to_char(c.conforencoding) AS source_encoding,
                   pg_encoding_to_char(c.contoencoding) AS dest_encoding,
                   conproc AS function, condefault AS default, c.oid,
                   obj_description(c.oid, 'pg_conversion') AS description
            FROM pg_conversion c
                 JOIN pg_roles r ON (r.oid = conowner)
                 JOIN pg_namespace n ON (connamespace = n.oid)
            WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
            ORDER BY nspname, conname"""

    @staticmethod
    def from_map(name, schema, inobj):
        """Initialize a Conversion instance from a YAML map

        :param name: conversion name
        :param table: schema map
        :param inobj: YAML map of the conversion
        :return: Conversion instance
        """
        obj = Conversion(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('source_encoding'),
            inobj.pop('dest_encoding'), inobj.pop('function'),
            inobj.pop('default', False))
        obj.set_oldname(inobj)
        return obj

    def to_map(self, db, no_owner=False, no_privs=False):
        """Convert a conversion to a YAML-suitable format

        :return: dictionary
        """
        dct = super(Conversion, self).to_map(db, no_owner)
        if not self.default:
            del dct['default']
        return dct

    @commentable
    @ownable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the conversion

        :return: SQL statements
        """
        dflt = ''
        if self.default:
            dflt = 'DEFAULT '
        return ["CREATE %sCONVERSION %s\n    FOR '%s' TO '%s' FROM %s" % (
                dflt, self.qualname(), self.source_encoding,
                self.dest_encoding, self.function)]


class ConversionDict(DbObjectDict):
    "The collection of conversions in a database."

    cls = Conversion

    def from_map(self, schema, inmap):
        """Initialize the dictionary of conversions by examining the input map

        :param schema: the schema owing the conversions
        :param inmap: the input YAML map defining the conversions
        """
        for key in inmap:
            if not key.startswith('conversion '):
                raise KeyError("Unrecognized object type: %s" % key)
            cnv = key[11:]
            inobj = inmap[key]
            self[(schema.name, cnv)] = Conversion.from_map(cnv, schema, inobj)
