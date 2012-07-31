# -*- coding: utf-8 -*-
"""
    pyrseas.language
    ~~~~~~~~~~~~~~~~

    This defines two classes, Language and LanguageDict, derived from
    DbObject and DbObjectDict, respectively.
"""
from pyrseas.dbobject import DbObjectDict, DbObject, quote_id
from pyrseas.dbobject.function import Function


class Language(DbObject):
    """A procedural language definition"""

    keylist = ['name']
    objtype = "LANGUAGE"

    def to_map(self, no_owner, no_privs):
        """Convert language to a YAML-suitable format

        :param no_owner: exclude language owner information
        :return: dictionary
        """
        if hasattr(self, '_ext'):
            return {}
        dct = self._base_map(no_owner, no_privs)
        if 'functions' in dct:
            del dct['functions']
        return {self.extern_key(): dct}

    def create(self):
        """Return SQL statements to CREATE the language

        :return: SQL statements
        """
        stmts = []
        if not hasattr(self, '_ext'):
            stmts.append("CREATE LANGUAGE %s" % quote_id(self.name))
            if hasattr(self, 'owner'):
                stmts.append(self.alter_owner())
            if hasattr(self, 'description'):
                stmts.append(self.comment())
        return stmts


class LanguageDict(DbObjectDict):
    "The collection of procedural languages in a database."

    cls = Language
    query = \
        """SELECT lanname AS name, lanpltrusted AS trusted, deptype AS _ext,
                  rolname AS owner, array_to_string(lanacl, ',') AS privileges,
                  obj_description(l.oid, 'pg_language') AS description
           FROM pg_language l
                JOIN pg_roles r ON (r.oid = lanowner)
                LEFT JOIN pg_depend d ON (l.oid = d.objid
                     AND classid = 'pg_language'::regclass
                     AND refclassid != 'pg_proc'::regclass)
           WHERE lanispl
           ORDER BY lanname"""

    def from_map(self, inmap):
        """Initialize the dictionary of languages by examining the input map

        :param inmap: the input YAML map defining the languages
        """
        for key in list(inmap.keys()):
            (objtype, spc, lng) = key.partition(' ')
            if spc != ' ' or objtype != 'language':
                raise KeyError("Unrecognized object type: %s" % key)
            language = self[lng] = Language(name=lng)
            inlanguage = inmap[key]
            if inlanguage:
                for attr, val in list(inlanguage.items()):
                    setattr(language, attr, val)
                if 'oldname' in inlanguage:
                    del inlanguage['oldname']

    def link_refs(self, dbfunctions):
        """Connect functions to their respective languages

        :param dbfunctions: dictionary of functions

        Fills in the `functions` dictionary for each language by
        traversing the `dbfunctions` dictionary, which is keyed by
        schema and function name.
        """
        for (sch, fnc, arg) in list(dbfunctions.keys()):
            func = dbfunctions[(sch, fnc, arg)]
            if func.language in ['sql', 'c', 'internal']:
                continue
            try:
                language = self[(func.language)]
            except KeyError as exc:
                if func.language == 'plpgsql':
                    continue
                raise exc
            if isinstance(func, Function):
                if not hasattr(language, 'functions'):
                    language.functions = {}
                language.functions.update({fnc: func})

    def to_map(self, no_owner, no_privs):
        """Convert the language dictionary to a regular dictionary

        :param no_owner: exclude language owner information
        :param no_privs: exclude privilege information
        :return: dictionary

        Invokes the `to_map` method of each language to construct a
        dictionary of languages.
        """
        languages = {}
        for lng in list(self.keys()):
            languages.update(self[lng].to_map(no_owner, no_privs))
        return languages

    def diff_map(self, inlanguages):
        """Generate SQL to transform existing languages

        :param input_map: a YAML map defining the new languages
        :return: list of SQL statements

        Compares the existing language definitions, as fetched from the
        catalogs, to the input map and generates SQL statements to
        transform the languages accordingly.
        """
        stmts = []
        # check input languages
        for lng in list(inlanguages.keys()):
            inlng = inlanguages[lng]
            # does it exist in the database?
            if lng in self:
                if not hasattr(inlng, '_ext'):
                    stmts.append(self[lng].diff_map(inlng))
            else:
                # check for possible RENAME
                if hasattr(inlng, 'oldname'):
                    oldname = inlng.oldname
                    try:
                        stmts.append(self[oldname].rename(inlng.name))
                        del self[oldname]
                    except KeyError as exc:
                        exc.args = ("Previous name '%s' for language '%s' "
                                   "not found" % (oldname, inlng.name), )
                        raise
                else:
                    # create new language
                    stmts.append(inlng.create())
        # check database languages
        for lng in list(self.keys()):
            # if missing, drop it
            if lng not in inlanguages:
                # special case: plpgsql is installed in 9.0
                if self.dbconn.version >= 90000 \
                        and self[lng].name == 'plpgsql':
                    continue
                self[lng].dropped = True
        return stmts

    def _drop(self):
        """Actually drop the languages

        :return: SQL statements
        """
        stmts = []
        for lng in list(self.keys()):
            if hasattr(self[lng], 'dropped'):
                stmts.append(self[lng].drop())
        return stmts
