# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.language
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    This defines two classes, Language and LanguageDict, derived from
    DbObject and DbObjectDict, respectively.

    See note at
    https://www.postgresql.org/docs/current/static/sql-createlanguage.html
    regarding status of procedural languages since Postgres 9.1.
"""
from . import DbObjectDict, DbObject, quote_id
from .function import Function


class Language(DbObject):
    """A procedural language definition"""

    keylist = ['name']
    single_extern_file = True
    catalog = 'pg_language'

    def __init__(self, name, description=None, owner=None, privileges=[],
                 trusted=False,
                 oid=None):
        """Initialize the language

        :param name: language name (from lanname)
        :param description: comment text (from obj_description())
        :param owner: owner name (from rolname via lanowner)
        :param privileges: access privileges (from lanacl)
        :param trusted: is this a trusted language? (from lanpltrusted)
        """
        super(Language, self).__init__(name, description)
        self._init_own_privs(owner, privileges)
        self.trusted = trusted
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT lanname AS name, lanpltrusted AS trusted, rolname AS owner,
                   array_to_string(lanacl, ',') AS privileges,
                   obj_description(l.oid, 'pg_language') AS description, l.oid
            FROM pg_language l JOIN pg_roles r ON (r.oid = lanowner)
            WHERE lanispl
              AND l.oid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e'
                               AND classid = 'pg_language'::regclass)
            ORDER BY lanname"""

    @staticmethod
    def from_map(name, inobj):
        """Initialize a Language instance from a YAML map

        :param name: Language name
        :param inobj: YAML map of the Language
        :return: Language instance
        """
        obj = Language(
            name, inobj.pop('description', None), inobj.pop('owner', None),
            inobj.pop('privileges', []), inobj.pop('trusted', False))
        obj.fix_privileges()
        if '_ext' in inobj:
            obj._ext = inobj['_ext']
        obj.set_oldname(inobj)
        return obj

    def to_map(self, db, no_owner, no_privs):
        """Convert language to a YAML-suitable format

        :param no_owner: exclude language owner information
        :return: dictionary
        """
        if hasattr(self, '_ext'):
            return None
        dct = super(Language, self).to_map(db, no_owner, no_privs)
        if 'functions' in dct:
            del dct['functions']
        return dct

    def create(self, dbversion=None):
        """Return SQL statements to CREATE the language

        :return: SQL statements
        """
        stmts = []
        if not hasattr(self, '_ext'):
            stmts.append("CREATE LANGUAGE %s" % quote_id(self.name))
            if self.owner is not None:
                stmts.append(self.alter_owner())
            if self.description is not None:
                stmts.append(self.comment())
        return stmts

    def drop(self):
        # TODO: this should not be special-cased
        # remove it after merging with the master, where plpgsql should be
        # treated normally
        if self.name != 'plpgsql':
            return super(Language, self).drop()
        else:
            return []


class LanguageDict(DbObjectDict):
    "The collection of procedural languages in a database."

    cls = Language

    def from_map(self, inmap):
        """Initialize the dictionary of languages by examining the input map

        :param inmap: the input YAML map defining the languages
        """
        for key in inmap:
            (objtype, spc, lng) = key.partition(' ')
            if spc != ' ' or objtype != 'language':
                raise KeyError("Unrecognized object type: %s" % key)
            inobj = inmap[key]
            self[lng] = Language.from_map(lng, inobj)

    def link_refs(self, dbfunctions, langs):
        """Connect functions to their respective languages

        :param dbfunctions: dictionary of functions

        Fills in the `functions` dictionary for each language by
        traversing the `dbfunctions` dictionary, which is keyed by
        schema and function name.
        """
        for (sch, fnc, arg) in dbfunctions:
            func = dbfunctions[(sch, fnc, arg)]
            if not isinstance(func, Function) or (
                    func.language in ['sql', 'c', 'internal']):
                continue
            try:
                language = self[(func.language)]
            except KeyError as exc:
                if func.language in langs:
                    continue
                raise exc
            if not hasattr(language, 'functions'):
                language.functions = {}
            language.functions.update({fnc: func})
