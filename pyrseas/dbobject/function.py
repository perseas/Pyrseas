# -*- coding: utf-8 -*-
"""
    pyrseas.function
    ~~~~~~~~~~~~~~~~

    This module defines two classes: Function derived from
    DbSchemaObject, and FunctionDict derived from DbObjectDict.
"""
import sys

from pyrseas.dbobject import DbObjectDict, DbSchemaObject


VOLATILITY_TYPES = {'i': 'immutable', 's': 'stable', 'v': 'volatile'}


class Function(DbSchemaObject):
    """A procedural language function"""

    keylist = ['schema', 'name', 'arguments']
    objtype = "FUNCTION"

    def extern_key(self):
        """Return the key to be used in external maps for this function

        :return: string
        """
        return 'function %s(%s)' % (self.name, self.arguments)

    def identifier(self):
        """Return a full identifier for a function object

        :return: string
        """
        return "%s(%s)" % (self.qualname(), self.arguments)

    def to_map(self):
        """Convert a function to a YAML-suitable format

        :return: dictionary
        """
        dct = self.__dict__.copy()
        for k in self.keylist[:-1]:
            del dct[k]
        if not self.arguments:
            del dct['arguments']
        if self.volatility == 'v':
            del dct['volatility']
        else:
            dct['volatility'] = VOLATILITY_TYPES[self.volatility]
        return {self.extern_key(): dct}

    def create(self, newsrc=None):
        """Return SQL statements to CREATE the function

        :return: SQL statements
        """
        stmts = []
        src = newsrc or self.source
        volat = ''
        if hasattr(self, 'volatility'):
            volat = ' ' + VOLATILITY_TYPES[self.volatility].upper()
        stmts.append("CREATE%s FUNCTION %s(%s) RETURNS %s\n    LANGUAGE %s"
                     "\n    AS $_$%s$_$%s" % (
                newsrc and " OR REPLACE" or '', self.qualname(),
                self.arguments, self.returns, self.language, src,
                volat))
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts

    def diff_map(self, infunction):
        """Generate SQL to transform an existing function

        :param infunction: a YAML map defining the new function
        :return: list of SQL statements

        Compares the function to an input function and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if self.source != infunction.source:
            stmts.append(self.create(infunction.source))
        stmts.append(self.diff_description(infunction))
        return stmts


class FunctionDict(DbObjectDict):
    "The collection of procedural language functions in a database"

    cls = Function
    query = \
        """SELECT nspname AS schema, proname AS name,
                  pg_get_function_arguments(p.oid) AS arguments,
                  pg_get_function_result(p.oid) AS returns,
                  l.lanname AS language, provolatile AS volatility,
                  prosrc AS source, description
           FROM pg_proc p
                JOIN pg_namespace n ON (pronamespace = n.oid)
                JOIN pg_language l ON (prolang = l.oid)
                LEFT JOIN pg_description d
                     ON (p.oid = d.objoid AND d.objsubid = 0)
           WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
           ORDER BY nspname, proname"""

    def from_map(self, schema, infuncs):
        """Initalize the dictionary of functions by converting the input map

        :param schema: schema owning the functions
        :param infuncs: YAML map defining the functions
        """
        for key in infuncs.keys():
            spc = key.find(' ')
            if spc == -1:
                raise KeyError("Unrecognized object type: %s" % key)
            objtype = key[:spc]
            if objtype != 'function':
                raise KeyError("Unrecognized object type: %s" % key)
            fnc = key[spc + 1:]
            paren = fnc.find('(')
            if paren == -1 or fnc[-1:] != ')':
                raise KeyError("Invalid function signature: %s" % fnc)
            arguments = fnc[paren + 1:-1]
            infunc = infuncs[key]
            fnc = fnc[:paren]
            self[(schema.name, fnc, arguments)] = func = Function(
                schema=schema.name, name=fnc, arguments=arguments)
            if not infunc:
                raise ValueError("Function '%s' has no specification" % fnc)
            for attr, val in infunc.items():
                setattr(func, attr, val)
            if hasattr(func, 'volatility'):
                func.volatility = func.volatility[:1].lower()
            if 'oldname' in infunc:
                func.oldname = infunc['oldname']
            if 'description' in infunc:
                func.description = infunc['description']

    def diff_map(self, infuncs):
        """Generate SQL to transform existing functions

        :param infuncs: a YAML map defining the new functions
        :return: list of SQL statements

        Compares the existing function definitions, as fetched from
        the catalogs, to the input map and generates SQL statements to
        transform the functions accordingly.
        """
        stmts = []
        # check input functions
        for (sch, fnc, arg) in infuncs.keys():
            infunc = infuncs[(sch, fnc, arg)]
            # does it exist in the database?
            if (sch, fnc, arg) not in self:
                if not hasattr(infunc, 'oldname'):
                    # create new function
                    stmts.append(infunc.create())
                else:
                    stmts.append(self[(sch, fnc, arg)].rename(infunc))
            else:
                # check function objects
                stmts.append(self[(sch, fnc, arg)].diff_map(infunc))

        # check existing functions
        for (sch, fnc, arg) in self.keys():
            table = self[(sch, fnc, arg)]
            # if missing, drop them
            if (sch, fnc, arg) not in infuncs:
                    stmts.append(table.drop())

        return stmts
