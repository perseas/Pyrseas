# -*- coding: utf-8 -*-
"""
    pyrseas.table
    ~~~~~~~~~~~~~

    This module defines three classes: DbType derived from
    DbSchemaObject, Domain derived from DbType, and DbTypeDict derived
    from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject.constraint import CheckConstraint


class DbType(DbSchemaObject):
    """A domain or enum type"""

    keylist = ['schema', 'name']


class Domain(DbType):
    "A domain definition"

    objtype = "DOMAIN"

    def to_map(self):
        """Convert a domain to a YAML-suitable format

        :return: dictionary
        """
        dct = self.__dict__.copy()
        for k in self.keylist:
            del dct[k]
        if hasattr(self, 'check_constraints'):
            if not 'check_constraints' in dct:
                dct.update(check_constraints={})
            for cns in self.check_constraints.values():
                dct['check_constraints'].update(
                    self.check_constraints[cns.name].to_map(None))

        return {self.extern_key(): dct}

    def create(self):
        """Return SQL statements to CREATE the domain

        :return: SQL statements
        """
        stmts = []
        create = "CREATE DOMAIN %s AS %s" % (self.qualname(), self.type)
        if hasattr(self, 'not_null'):
            create += ' NOT NULL'
        if hasattr(self, 'default'):
            create += ' DEFAULT ' + str(self.default)
        if hasattr(self, 'check_constraints'):
            cnslist = []
            for cns in self.check_constraints.values():
                cnslist.append(" CONSTRAINT %s CHECK (%s)" % (
                    cns.name, cns.expression))
            create += ", ".join(cnslist)
        stmts.append(create)
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts

    def diff_map(self, indomain):
        """Generate SQL to transform an existing domain

        :param indomain: a YAML map defining the new domain
        :return: list of SQL statements

        Compares the domain to an input domain and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        stmts.append(self.diff_description(indomain))
        return stmts


class TypeDict(DbObjectDict):
    "The collection of domains and enums in a database"

    cls = DbType
    query = \
        """SELECT nspname AS schema, typname AS name, typtype AS kind,
                  format_type(typbasetype, typtypmod) AS type,
                  typnotnull AS not_null, typdefault AS default, description
           FROM pg_type t
                JOIN pg_namespace n ON (typnamespace = n.oid)
                LEFT JOIN pg_description d
                     ON (t.oid = d.objoid AND d.objsubid = 0)
           WHERE typtype in ('d', 'e')
             AND (nspname != 'pg_catalog' AND nspname != 'information_schema')
           ORDER BY nspname, typname"""

    def _from_catalog(self):
        """Initialize the dictionary of types by querying the catalogs"""
        for dbtype in self.fetch():
            sch, typ = dbtype.key()
            kind = dbtype.kind
            del dbtype.kind
            if kind == 'd':
                self[(sch, typ)] = Domain(**dbtype.__dict__)

    def from_map(self, schema, inobjs, newdb):
        """Initalize the dictionary of types by converting the input map

        :param schema: schema owning the types
        :param inobjs: YAML map defining the schema objects
        :param newdb: collection of dictionaries defining the database
        """
        for k in inobjs.keys():
            spc = k.find(' ')
            if spc == -1:
                raise KeyError("Unrecognized object type: %s" % k)
            objtype = k[:spc]
            key = k[spc + 1:]
            if objtype == 'domain':
                self[(schema.name, key)] = domain = Domain(
                    schema=schema.name, name=key)
                indomain = inobjs[k]
                if not indomain:
                    raise ValueError("Domain '%s' has no specification" % k)
                for attr, val in indomain.items():
                    setattr(domain, attr, val)
                if 'oldname' in indomain:
                    domain.oldname = indomain['oldname']
                newdb.constraints.from_map(domain, indomain, 'd')
                if 'description' in indomain:
                    domain.description = indomain['description']
            else:
                raise KeyError("Unrecognized object type: %s" % k)

    def link_refs(self, dbconstrs):
        """Connect constraints to their respective domains

        :param dbconstrs: dictionary of constraints

        Fills the `check_constraints` dictionaries for each domain by
        traversing the `dbconstrs` dictionary.
        """
        for (sch, typ, cns) in dbconstrs.keys():
            constr = dbconstrs[(sch, typ, cns)]
            if not hasattr(constr, 'target') or constr.target != 'd':
                continue
            assert self[(sch, typ)]
            dbtype = self[(sch, typ)]
            if isinstance(constr, CheckConstraint):
                if not hasattr(dbtype, 'check_constraints'):
                    dbtype.check_constraints = {}
                dbtype.check_constraints.update({cns: constr})

    def diff_map(self, intypes):
        """Generate SQL to transform existing domains and types

        :param intypes: a YAML map defining the new domains/types
        :return: list of SQL statements

        Compares the existing domain/type definitions, as fetched from
        the catalogs, to the input map and generates SQL statements to
        transform the domains/types accordingly.
        """
        stmts = []
        # check input types
        for (sch, typ) in intypes.keys():
            intype = intypes[(sch, typ)]
            if not isinstance(intype, Domain):
                continue
            # does it exist in the database?
            if (sch, typ) not in self:
                if not hasattr(intype, 'oldname'):
                    # create new type
                    stmts.append(intype.create())
                else:
                    stmts.append(self[(sch, intype.oldname)].rename(typ))
                    del self[(sch, intype.oldname)]

        # check existing types
        for (sch, typ) in self.keys():
            dbtype = self[(sch, typ)]
            # if missing, mark it for dropping
            if (sch, typ) not in intypes:
                dbtype.dropped = False
            else:
                # check type/sequence/view objects
                stmts.append(dbtype.diff_map(intypes[(sch, typ)]))

        # now drop the marked types
        for (sch, typ) in self.keys():
            dbtype = self[(sch, typ)]
            if hasattr(dbtype, 'dropped') and not dbtype.dropped:
                # next, drop other subordinate objects
                if hasattr(dbtype, 'check_constraints'):
                    for chk in dbtype.check_constraints:
                        stmts.append(dbtype.check_constraints[chk].drop())
                # finally, drop the type itself
                stmts.append(dbtype.drop())

        return stmts
