# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.operfamily
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: OperatorFamily derived from
    DbSchemaObject and OperatorFamilyDict derived from DbObjectDict.
"""
from . import DbObjectDict, DbSchemaObject
from . import commentable, ownable, split_schema_obj


class OperatorFamily(DbSchemaObject):
    """An operator family"""

    keylist = ['schema', 'name', 'index_method']
    single_extern_file = True
    catalog = 'pg_opfamily'

    def __init__(self, name, schema, index_method, description, owner,
                 oid=None):
        """Initialize the operator family

        :param name: operator name (from opfname)
        :param schema: schema name (from opfnamespace)
        :param index_method: index access method (from amname via opfmethod)
        :param description: comment text (from obj_description())
        :param owner: owner name (from rolname via opfowner)
        """
        super(OperatorFamily, self).__init__(name, schema, description)
        self._init_own_privs(owner, [])
        self.index_method = index_method
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, opfname AS name, rolname AS owner,
                   amname AS index_method,
                   obj_description(o.oid, 'pg_opfamily') AS description, o.oid
            FROM pg_opfamily o JOIN pg_roles r ON (r.oid = opfowner)
                 JOIN pg_am a ON (opfmethod = a.oid)
                 JOIN pg_namespace n ON (opfnamespace = n.oid)
            WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
              AND o.oid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e'
                               AND classid = 'pg_opfamily'::regclass)
            ORDER BY opfnamespace, opfname, amname"""

    @staticmethod
    def from_map(name, schema, index_method, inobj):
        """Initialize an operator family instance from a YAML map

        :param name: operator family name
        :param name: schema name
        :param index_method: index method
        :param inobj: YAML map of the operator family
        :return: operator family instance
        """
        obj = OperatorFamily(
            name, schema.name, index_method, inobj.pop('description', None),
            inobj.pop('owner', None))
        obj.set_oldname(inobj)
        return obj

    @property
    def objtype(self):
        return "OPERATOR FAMILY"

    def extern_key(self):
        """Return the key to be used in external maps for the operator family

        :return: string
        """
        return '%s %s using %s' % (self.objtype.lower(), self.name,
                                   self.index_method)

    def identifier(self):
        """Return a full identifier for an operator family object

        :return: string
        """
        return "%s USING %s" % (self.qualname(), self.index_method)

    @commentable
    @ownable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the operator family

        :return: SQL statements
        """
        return ["CREATE OPERATOR FAMILY %s USING %s" % (
                self.qualname(), self.index_method)]


class OperatorFamilyDict(DbObjectDict):
    "The collection of operator families in a database"

    cls = OperatorFamily

    def from_map(self, schema, inopfams):
        """Initialize the dict of operator families by converting the input map

        :param schema: schema owning the operators
        :param inopfams: YAML map defining the operator families
        """
        for key in inopfams:
            if not key.startswith('operator family ') or ' using ' not in key:
                raise KeyError("Unrecognized object type: %s" % key)
            pos = key.rfind(' using ')
            opf = key[16:pos]  # 16 = len('operator family ')
            idx = key[pos + 7:]  # 7 = len(' using ')
            inobj = inopfams[key]
            self[(schema.name, opf, idx)] = OperatorFamily.from_map(
                opf, schema, idx, inobj)

    def find(self, sch, obj, meth):
        schema, name = split_schema_obj(obj, sch)
        return self.get((schema, name, meth))
