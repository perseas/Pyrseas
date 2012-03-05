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
        dct = self._base_map()
        if self.volatility == 'v':
            del dct['volatility']
        else:
            dct['volatility'] = VOLATILITY_TYPES[self.volatility]
        if hasattr(self, 'dependent_table'):
            del dct['dependent_table']
        if hasattr(self, 'obj_file'):
            dct['link_symbol'] = self.source
            del dct['source']
        if hasattr(self, '_dep_type'):
            del dct['_dep_type']
        if hasattr(self, 'cost') and self.cost != 0:
            if self.language in ['c', 'internal']:
                if self.cost == 1:
                    del dct['cost']
            else:
                if self.cost == 100:
                    del dct['cost']
        if hasattr(self, 'rows') and self.rows != 0:
            if self.rows == 1000:
                del dct['rows']
        return {self.extern_key(): dct}

    def create(self, newsrc=None, basetype=False):
        """Return SQL statements to CREATE or REPLACE the function

        :param newsrc: new source for a changed function
        :return: SQL statements
        """
        stmts = []
        if hasattr(self, '_dep_type') and not basetype:
            return stmts
        if hasattr(self, 'dependent_table'):
            stmts.append(self.dependent_table.create())
        if hasattr(self, 'obj_file'):
            src = "'%s', '%s'" % (self.obj_file,
                                  hasattr(self, 'link_symbol')
                                  and self.link_symbol or self.name)
        elif self.language == 'internal':
            src = "$$%s$$" % (newsrc or self.source)
        else:
            src = "$_$%s$_$" % (newsrc or self.source)
        volat = strict = secdef = cost = rows = ''
        if hasattr(self, 'volatility'):
            volat = ' ' + VOLATILITY_TYPES[self.volatility].upper()
        if hasattr(self, 'strict') and self.strict:
            strict = ' STRICT'
        if hasattr(self, 'security_definer') and self.security_definer:
            secdef = ' SECURITY DEFINER'
        if hasattr(self, 'cost') and self.cost != 0:
            if self.language in ['c', 'internal']:
                if self.cost != 1:
                    cost = " COST %s" % self.cost
            else:
                if self.cost != 100:
                    cost = " COST %s" % self.cost
        if hasattr(self, 'rows') and self.rows != 0:
            if self.rows != 1000:
                rows = " ROWS %s" % self.rows

        stmts.append("CREATE%s FUNCTION %s(%s) RETURNS %s\n    LANGUAGE %s"
                     "%s%s%s%s%s\n    AS %s" % (
                newsrc and " OR REPLACE" or '', self.qualname(),
                self.arguments, self.returns, self.language, volat, strict,
                secdef, cost, rows, src))
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
        if hasattr(self, 'source') and hasattr(infunction, 'source'):
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
        dct = self._base_map()
        del dct['language']
        return {self.extern_key(): dct}

    def create(self):
        """Return SQL statements to CREATE the aggregate

        :return: SQL statements
        """
        stmts = []
        opt_clauses = []
        if hasattr(self, 'finalfunc'):
            ffname = self.finalfunc[:self.finalfunc.index('(')]
            opt_clauses.append("FINALFUNC = %s" % ffname)
        if hasattr(self, 'initcond'):
            opt_clauses.append("INITCOND = '%s'" % self.initcond)
        if hasattr(self, 'sortop'):
            opt_clauses.append("SORTOP = %s" % self.sortop)
        stmts.append("CREATE AGGREGATE %s(%s) (\n    SFUNC = %s,"
                     "\n    STYPE = %s%s%s)" % (
                self.qualname(),
                self.arguments, self.sfunc, self.stype,
                opt_clauses and ',\n    ' or '', ',\n    '.join(opt_clauses)))
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
                  probin::text AS obj_file,
                  prosecdef AS security_definer, procost AS cost,
                  aggtransfn::regprocedure AS sfunc,
                  aggtranstype::regtype AS stype,
                  aggfinalfn::regprocedure AS finalfunc,
                  agginitval AS initcond, aggsortop::regoper AS sortop,
                  obj_description(p.oid, 'pg_proc') AS description,
                  prorows::integer AS rows
           FROM pg_proc p
                JOIN pg_namespace n ON (pronamespace = n.oid)
                JOIN pg_language l ON (prolang = l.oid)
                LEFT JOIN pg_aggregate a ON (p.oid = aggfnoid)
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
                del proc.cost
                if proc.finalfunc == '-':
                    del proc.finalfunc
                if proc.sortop == '0':
                    del proc.sortop
                self[(sch, prc, arg)] = Aggregate(**proc.__dict__)
            else:
                self[(sch, prc, arg)] = Function(**proc.__dict__)

    def from_map(self, schema, infuncs):
        """Initalize the dictionary of functions by converting the input map

        :param schema: schema owning the functions
        :param infuncs: YAML map defining the functions
        """
        for key in infuncs.keys():
            (objtype, spc, fnc) = key.partition(' ')
            if spc != ' ' or objtype not in ['function', 'aggregate']:
                raise KeyError("Unrecognized object type: %s" % key)
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
            if isinstance(func, Function):
                src = hasattr(func, 'source')
                obj = hasattr(func, 'obj_file')
                if (src and obj) or not (src or obj):
                    raise ValueError("Function '%s': either source or "
                                     "obj_file must be specified" % fnc)
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
                    if isinstance(stmt, str) and stmt.startswith("CREATE "):
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
            # if missing, mark it for dropping
            if (sch, fnc, arg) not in infuncs:
                func.dropped = False

        if created:
            stmts.insert(0, "SET check_function_bodies = false")
        return stmts

    def _drop(self):
        """Actually drop the functions

        :return: SQL statements
        """
        stmts = []
        for (sch, fnc, arg) in self.keys():
            func = self[(sch, fnc, arg)]
            if isinstance(func, Aggregate) and hasattr(func, 'dropped'):
                stmts.append(func.drop())

        for (sch, fnc, arg) in self.keys():
            func = self[(sch, fnc, arg)]
            if hasattr(func, 'dropped') and not hasattr(func, '_dep_type'):
                stmts.append(func.drop())

        return stmts
