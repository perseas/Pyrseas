# -*- coding: utf-8 -*-
"""
    pyrseas.function
    ~~~~~~~~~~~~~~~~

    This module defines four classes: Proc derived from
    DbSchemaObject, Function and Aggregate derived from Proc, and
    FunctionDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject


VOLATILITY_TYPES = {'i': 'immutable', 's': 'stable', 'v': 'volatile'}


class Proc(DbSchemaObject):
    """A procedure such as a FUNCTION or an AGGREGATE"""

    keylist = ['schema', 'name', 'arguments']

    def extern_key(self):
        """Return the key to be used in external maps for this function

        :return: string
        """
        return '%s %s(%s)' % (self.objtype.lower(), self.name, self.arguments)

    def identifier(self):
        """Return a full identifier for a function object

        :return: string
        """
        return "%s(%s)" % (self.qualname(), self.arguments)


class Function(Proc):
    """A procedural language function"""

    objtype = "FUNCTION"

    def to_map(self):
        """Convert a function to a YAML-suitable format

        :return: dictionary
        """
        dct = self.__dict__.copy()
        for k in self.keylist:
            del dct[k]
        if self.volatility == 'v':
            del dct['volatility']
        else:
            dct['volatility'] = VOLATILITY_TYPES[self.volatility]
        return {self.extern_key(): dct}

    def create(self, newsrc=None):
        """Return SQL statements to CREATE or REPLACE the function

        :param newsrc: new source for a changed function
        :return: SQL statements
        """
        stmts = []
        src = newsrc or self.source
        volat = strict = ''
        if hasattr(self, 'volatility'):
            volat = ' ' + VOLATILITY_TYPES[self.volatility].upper()
        if hasattr(self, 'strict') and self.strict:
            strict = ' STRICT'
        stmts.append("CREATE%s FUNCTION %s(%s) RETURNS %s\n    LANGUAGE %s"
                     "\n    AS $_$%s$_$%s%s" % (
                newsrc and " OR REPLACE" or '', self.qualname(),
                self.arguments, self.returns, self.language, src,
                volat, strict))
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


class Aggregate(Proc):
    """An aggregate function"""

    objtype = "AGGREGATE"

    def to_map(self):
        """Convert an agggregate to a YAML-suitable format

        :return: dictionary
        """
        dct = self.__dict__.copy()
        for k in self.keylist:
            del dct[k]
        del dct['language']
        return {self.extern_key(): dct}

    def create(self):
        """Return SQL statements to CREATE the aggregate

        :return: SQL statements
        """
        stmts = []
        ffunc = cond = ''
        if hasattr(self, 'finalfunc'):
            ffname = self.finalfunc[:self.finalfunc.index('(')]
            ffunc = ",\n    FINALFUNC = %s" % (ffname)
        if hasattr(self, 'initcond'):
            cond = ",\n    INITCOND = '%s'" % (self.initcond)
        stmts.append("CREATE AGGREGATE %s(%s) (\n    SFUNC = %s,"
                     "\n    STYPE = %s%s%s)" % (
                self.qualname(),
                self.arguments, self.sfunc, self.stype, ffunc, cond))
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts


class ProcDict(DbObjectDict):
    "The collection of regular and aggregate functions in a database"

    cls = Proc
    query = \
        """SELECT nspname AS schema, proname AS name,
                  pg_get_function_arguments(p.oid) AS arguments,
                  pg_get_function_result(p.oid) AS returns,
                  l.lanname AS language, provolatile AS volatility,
                  proisstrict AS strict, proisagg, prosrc AS source,
                  aggtransfn::regprocedure AS sfunc,
                  aggtranstype::regtype AS stype,
                  aggfinalfn::regprocedure AS finalfunc,
                  agginitval AS initcond,
                  description
           FROM pg_proc p
                JOIN pg_namespace n ON (pronamespace = n.oid)
                JOIN pg_language l ON (prolang = l.oid)
                LEFT JOIN pg_aggregate a ON (p.oid = aggfnoid)
                LEFT JOIN pg_description d
                     ON (p.oid = d.objoid AND d.objsubid = 0)
           WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
           ORDER BY nspname, proname"""

    def _from_catalog(self):
        """Initialize the dictionary of procedures by querying the catalogs"""
        for proc in self.fetch():
            sch, prc, arg = proc.key()
            if hasattr(proc, 'proisagg'):
                del proc.proisagg
                del proc.source
                del proc.volatility
                del proc.returns
                if proc.finalfunc == '-':
                    del proc.finalfunc
                self[(sch, prc, arg)] = Aggregate(**proc.__dict__)
            else:
                self[(sch, prc, arg)] = Function(**proc.__dict__)

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
            if objtype not in ['function', 'aggregate']:
                raise KeyError("Unrecognized object type: %s" % key)
            fnc = key[spc + 1:]
            paren = fnc.find('(')
            if paren == -1 or fnc[-1:] != ')':
                raise KeyError("Invalid function signature: %s" % fnc)
            arguments = fnc[paren + 1:-1]
            infunc = infuncs[key]
            fnc = fnc[:paren]
            if objtype == 'function':
                self[(schema.name, fnc, arguments)] = func = Function(
                    schema=schema.name, name=fnc, arguments=arguments)
            else:
                self[(schema.name, fnc, arguments)] = func = Aggregate(
                    schema=schema.name, name=fnc, arguments=arguments)
                func.language = 'internal'
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
        created = False
        # check input functions
        for (sch, fnc, arg) in infuncs.keys():
            infunc = infuncs[(sch, fnc, arg)]
            if isinstance(infunc, Aggregate):
                continue
            # does it exist in the database?
            if (sch, fnc, arg) not in self:
                if not hasattr(infunc, 'oldname'):
                    # create new function
                    stmts.append(infunc.create())
                    created = True
                else:
                    stmts.append(self[(sch, fnc, arg)].rename(infunc))
            else:
                # check function objects
                diff_stmts = self[(sch, fnc, arg)].diff_map(infunc)
                for stmt in diff_stmts:
                    if isinstance(stmt, list) and stmt:
                        stmt = stmt[0]
                    if isinstance(stmt, basestring) and \
                            stmt.startswith("CREATE "):
                        created = True
                        break
                stmts.append(diff_stmts)

        # check input aggregates
        for (sch, fnc, arg) in infuncs.keys():
            infunc = infuncs[(sch, fnc, arg)]
            if not isinstance(infunc, Aggregate):
                continue
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
            func = self[(sch, fnc, arg)]
            # if missing, drop them
            if (sch, fnc, arg) not in infuncs:
                    stmts.append(func.drop())

        if created:
            stmts.insert(0, "SET check_function_bodies = false")
        return stmts
