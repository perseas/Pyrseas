# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.operfamily
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: OperatorFamily derived from
    DbSchemaObject and OperatorFamilyDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject import commentable, ownable


class OperatorFamily(DbSchemaObject):
    """An operator family"""

    objtype = "OPERATOR FAMILY"

    keylist = ['schema', 'name', 'index_method']

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
    def create(self):
        """Return SQL statements to CREATE the operator family

        :return: SQL statements
        """
        return ["CREATE OPERATOR FAMILY %s USING %s" % (
                self.qualname(), self.index_method)]


class OperatorFamilyDict(DbObjectDict):
    "The collection of operator families in a database"

    cls = OperatorFamily
    query = \
        """SELECT nspname AS schema, opfname AS name, rolname AS owner,
                  amname AS index_method,
                  obj_description(o.oid, 'pg_opfamily') AS description
           FROM pg_opfamily o
                JOIN pg_roles r ON (r.oid = opfowner)
                JOIN pg_am a ON (opfmethod = a.oid)
                JOIN pg_namespace n ON (opfnamespace = n.oid)
           WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
             AND o.oid NOT IN (
                 SELECT objid FROM pg_depend WHERE deptype = 'e'
                              AND classid = 'pg_opfamily'::regclass)
           ORDER BY opfnamespace, opfname, amname"""

    def from_map(self, schema, inopfams):
        """Initalize the dict of operator families by converting the input map

        :param schema: schema owning the operators
        :param inopfams: YAML map defining the operator families
        """
        for key in list(inopfams.keys()):
            if not key.startswith('operator family ') or not ' using ' in key:
                raise KeyError("Unrecognized object type: %s" % key)
            pos = key.rfind(' using ')
            opf = key[16:pos]  # 16 = len('operator family ')
            idx = key[pos + 7:]  # 7 = len(' using ')
            inopfam = inopfams[key]
            self[(schema.name, opf, idx)] = opfam = OperatorFamily(
                schema=schema.name, name=opf, index_method=idx)
            for attr, val in list(inopfam.items()):
                setattr(opfam, attr, val)
            if 'oldname' in inopfam:
                opfam.oldname = inopfam['oldname']
            if 'description' in inopfam:
                opfam.description = inopfam['description']

    def diff_map(self, inopfams):
        """Generate SQL to transform existing operator families

        :param inopfams: a YAML map defining the new operator families
        :return: list of SQL statements

        Compares the existing operator family definitions, as fetched
        from the catalogs, to the input map and generates SQL
        statements to transform the operator families accordingly.
        """
        stmts = []
        # check input operator families
        for (sch, opf, idx) in list(inopfams.keys()):
            inopfam = inopfams[(sch, opf, idx)]
            # does it exist in the database?
            if (sch, opf, idx) not in self:
                if not hasattr(inopfam, 'oldname'):
                    # create new operator family
                    stmts.append(inopfam.create())
                else:
                    stmts.append(self[(sch, opf, idx)].rename(inopfam))
            else:
                # check operator family objects
                stmts.append(self[(sch, opf, idx)].diff_map(inopfam))

        # check existing operator families
        for (sch, opf, idx) in list(self.keys()):
            oper = self[(sch, opf, idx)]
            # if missing, mark it for dropping
            if (sch, opf, idx) not in inopfams:
                oper.dropped = False

        return stmts

    def _drop(self):
        """Actually drop the operator families

        :return: SQL statements
        """
        stmts = []
        for (sch, opf, idx) in list(self.keys()):
            oper = self[(sch, opf, idx)]
            if hasattr(oper, 'dropped'):
                stmts.append(oper.drop())
        return stmts
