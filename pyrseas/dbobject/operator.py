# -*- coding: utf-8 -*-
"""
    pyrseas.operator
    ~~~~~~~~~~~~~~~~

    This module defines two classes: Operator derived from
    DbSchemaObject and OperatorDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject


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

    def identifier(self):
        """Return a full identifier for an operator object

        :return: string
        """
        return "%s(%s, %s)" % (self.qualname(), self.leftarg, self.rightarg)

    def to_map(self):
        """Convert a operator to a YAML-suitable format

        :return: dictionary
        """
        dct = self.__dict__.copy()
        for k in self.keylist:
            del dct[k]
        return {self.extern_key(): dct}

    def create(self):
        """Return SQL statements to CREATE or REPLACE the operator

        :return: SQL statements
        """
        stmts = []
        leftarg = rightarg = com_op = neg_op = ''
        if self.leftarg != 'NONE':
            leftarg = ",\n    LEFTARG = %s" % self.leftarg
        if self.rightarg != 'NONE':
            rightarg = ",\n    RIGHTARG = %s" % self.rightarg
        if hasattr(self, 'commutator'):
            com_op = ",\n    COMMUTATOR = OPERATOR(%s)" % self.commutator
        if hasattr(self, 'negator'):
            com_op = ",\n    NEGATOR = OPERATOR(%s)" % self.negator
        stmts.append("CREATE OPERATOR %s (\n    PROCEDURE = %s%s%s%s%s)" % (
                self.qualname(), self.procedure, leftarg, rightarg, com_op,
                neg_op))
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts

    def diff_map(self, inoperator):
        """Generate SQL to transform an existing operator

        :param inoperator: a YAML map defining the new operator
        :return: list of SQL statements

        Compares the operator to an input operator and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        stmts.append(self.diff_description(inoperator))
        return stmts


class OperatorDict(DbObjectDict):
    "The collection of operators in a database"

    cls = Operator
    query = \
        """SELECT nspname AS schema, oprname AS name,
                  oprleft::regtype AS leftarg, oprright::regtype AS rightarg,
                  oprcode::regproc AS procedure, oprcom::regoper AS commutator,
                  oprnegate::regoper AS negator, description
           FROM pg_operator o
                JOIN pg_namespace n ON (oprnamespace = n.oid)
                LEFT JOIN pg_description d
                     ON (o.oid = d.objoid AND d.objsubid = 0)
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
            self[(sch, opr, lft, rgt)] = Operator(**oper.__dict__)

    def from_map(self, schema, inopers):
        """Initalize the dictionary of operators by converting the input map

        :param schema: schema owning the operators
        :param inopers: YAML map defining the operators
        """
        for key in inopers.keys():
            spc = key.find(' ')
            if spc == -1:
                raise KeyError("Unrecognized object type: %s" % key)
            opr = key[spc + 1:]
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
