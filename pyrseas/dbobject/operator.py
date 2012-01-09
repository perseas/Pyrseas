# -*- coding: utf-8 -*-
"""
    pyrseas.operator
    ~~~~~~~~~~~~~~~~

    This module defines two classes: Operator derived from
    DbSchemaObject and OperatorDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject, quote_id


class Operator(DbSchemaObject):
    """An operator"""

    objtype = "OPERATOR"

    keylist = ['schema', 'name', 'leftarg', 'rightarg']

    def extern_key(self):
        """Return the key to be used in external maps for this operator

        :return: string
        """
        return '%s %s(%s, %s)' % (self.objtype.lower(), self.name,
                                  self.leftarg, self.rightarg)

    def qualname(self):
        """Return the schema-qualified name of the operator

        :return: string

        No qualification is used if the schema is 'public'.
        """
        return self.schema == 'public' and self.name \
            or "%s.%s" % (quote_id(self.schema), self.name)

    def identifier(self):
        """Return a full identifier for an operator object

        :return: string
        """
        return "%s(%s, %s)" % (self.qualname(), self.leftarg, self.rightarg)

    def create(self):
        """Return SQL statements to CREATE or REPLACE the operator

        :return: SQL statements
        """
        stmts = []
        opt_clauses = []
        if self.leftarg != 'NONE':
            opt_clauses.append("LEFTARG = %s" % self.leftarg)
        if self.rightarg != 'NONE':
            opt_clauses.append("RIGHTARG = %s" % self.rightarg)
        if hasattr(self, 'commutator'):
            opt_clauses.append("COMMUTATOR = OPERATOR(%s)" % self.commutator)
        if hasattr(self, 'negator'):
            opt_clauses.append("NEGATOR = OPERATOR(%s)" % self.negator)
        if hasattr(self, 'restrict'):
            opt_clauses.append("RESTRICT = %s" % self.restrict)
        if hasattr(self, 'join'):
            opt_clauses.append("JOIN = %s" % self.join)
        if hasattr(self, 'hashes') and self.hashes:
            opt_clauses.append("HASHES")
        if hasattr(self, 'merges') and self.merges:
            opt_clauses.append("MERGES")
        stmts.append("CREATE OPERATOR %s (\n    PROCEDURE = %s%s%s)" % (
                self.qualname(), self.procedure,
                ',\n    ' if opt_clauses else '', ',\n    '.join(opt_clauses)))
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts


class OperatorDict(DbObjectDict):
    "The collection of operators in a database"

    cls = Operator
    query = \
        """SELECT nspname AS schema, oprname AS name,
                  oprleft::regtype AS leftarg, oprright::regtype AS rightarg,
                  oprcode::regproc AS procedure, oprcom::regoper AS commutator,
                  oprnegate::regoper AS negator, oprrest::regproc AS restrict,
                  oprjoin::regproc AS join, oprcanhash AS hashes,
                  oprcanmerge AS merges,
                  obj_description(o.oid, 'pg_operator') AS description
           FROM pg_operator o
                JOIN pg_namespace n ON (oprnamespace = n.oid)
           WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
           ORDER BY nspname, oprname"""

    def _from_catalog(self):
        """Initialize the dictionary of operators by querying the catalogs"""
        for oper in self.fetch():
            sch, opr, lft, rgt = oper.key()
            if lft == '-':
                lft = oper.leftarg = 'NONE'
            if rgt == '-':
                rgt = oper.rightarg = 'NONE'
            if oper.commutator == '0':
                del oper.commutator
            if oper.negator == '0':
                del oper.negator
            if oper.restrict == '-':
                del oper.restrict
            if oper.join == '-':
                del oper.join
            self[(sch, opr, lft, rgt)] = Operator(**oper.__dict__)

    def from_map(self, schema, inopers):
        """Initalize the dictionary of operators by converting the input map

        :param schema: schema owning the operators
        :param inopers: YAML map defining the operators
        """
        for key in inopers.keys():
            (objtype, spc, opr) = key.partition(' ')
            if spc != ' ' or objtype != 'operator':
                raise KeyError("Unrecognized object type: %s" % key)
            paren = opr.find('(')
            if paren == -1 or opr[-1:] != ')':
                raise KeyError("Invalid operator signature: %s" % opr)
            (leftarg, rightarg) = opr[paren + 1:-1].split(',')
            rightarg = rightarg.lstrip()
            inoper = inopers[key]
            opr = opr[:paren]
            self[(schema.name, opr, leftarg, rightarg)] = oper = Operator(
                schema=schema.name, name=opr, leftarg=leftarg,
                rightarg=rightarg)
            if not inoper:
                raise ValueError("Operator '%s' has no specification" % opr)
            for attr, val in inoper.items():
                setattr(oper, attr, val)
            if 'oldname' in inoper:
                oper.oldname = inoper['oldname']
            if 'description' in inoper:
                oper.description = inoper['description']

    def diff_map(self, inopers):
        """Generate SQL to transform existing operators

        :param inopers: a YAML map defining the new operators
        :return: list of SQL statements

        Compares the existing operator definitions, as fetched from
        the catalogs, to the input map and generates SQL statements to
        transform the operators accordingly.
        """
        stmts = []
        # check input operators
        for (sch, opr, lft, rgt) in inopers.keys():
            inoper = inopers[(sch, opr, lft, rgt)]
            # does it exist in the database?
            if (sch, opr, lft, rgt) not in self:
                if not hasattr(inoper, 'oldname'):
                    # create new operator
                    stmts.append(inoper.create())
                else:
                    stmts.append(self[(sch, opr, lft, rgt)].rename(inoper))
            else:
                # check operator objects
                stmts.append(self[(sch, opr, lft, rgt)].diff_map(inoper))

        # check existing operators
        for (sch, opr, lft, rgt) in self.keys():
            oper = self[(sch, opr, lft, rgt)]
            # if missing, mark it for dropping
            if (sch, opr, lft, rgt) not in inopers:
                oper.dropped = False

        return stmts

    def _drop(self):
        """Actually drop the operators

        :return: SQL statements
        """
        stmts = []
        for (sch, opr, lft, rgt) in self.keys():
            oper = self[(sch, opr, lft, rgt)]
            if hasattr(oper, 'dropped'):
                stmts.append(oper.drop())
        return stmts
