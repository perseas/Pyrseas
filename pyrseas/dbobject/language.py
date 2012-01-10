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

    def to_map(self):
        """Convert language to a YAML-suitable format

        :return: dictionary
        """
        dct = self._base_map()
        if 'functions' in dct:
            del dct['functions']
        return {self.extern_key(): dct}

    def create(self):
        """Return SQL statements to CREATE the language

        :return: SQL statements
        """
        stmts = ["CREATE LANGUAGE %s" % quote_id(self.name)]
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts


class LanguageDict(DbObjectDict):
    "The collection of procedural languages in a database."

    cls = Language
    query = \
        """SELECT lanname AS name, lanpltrusted AS trusted,
                  obj_description(l.oid, 'pg_language') AS description
           FROM pg_language l
           WHERE lanispl
           ORDER BY lanname"""

    def from_map(self, inmap):
        """Initialize the dictionary of languages by examining the input map

        :param inmap: the input YAML map defining the languages
        """
        for key in inmap.keys():
            (objtype, spc, lng) = key.partition(' ')
            if spc != ' ' or objtype != 'language':
                raise KeyError("Unrecognized object type: %s" % key)
            language = self[lng] = Language(name=lng)
            inlanguage = inmap[key]
            if inlanguage:
                if 'oldname' in inlanguage:
                    language.oldname = inlanguage['oldname']
                    del inlanguage['oldname']
                if 'description' in inlanguage:
                    language.description = inlanguage['description']

    def link_refs(self, dbfunctions):
        """Connect functions to their respective languages

        :param dbfunctions: dictionary of functions

        Fills in the `functions` dictionary for each language by
        traversing the `dbfunctions` dictionary, which is keyed by
        schema and function name.
        """
        for (sch, fnc, arg) in dbfunctions.keys():
            func = dbfunctions[(sch, fnc, arg)]
            if func.language in ['sql', 'c', 'internal']:
                continue
            assert self[(func.language)]
            language = self[(func.language)]
            if isinstance(func, Function):
                if not hasattr(language, 'functions'):
                    language.functions = {}
                language.functions.update({fnc: func})

    def to_map(self):
        """Convert the language dictionary to a regular dictionary

        :return: dictionary

        Invokes the `to_map` method of each language to construct a
        dictionary of languages.
        """
        languages = {}
        for lng in self.keys():
            languages.update(self[lng].to_map())
        return languages

    def diff_map(self, inlanguages, dbversion):
        """Generate SQL to transform existing languages

        :param input_map: a YAML map defining the new languages
        :param dbversion: DBMS version number
        :return: list of SQL statements

        Compares the existing language definitions, as fetched from the
        catalogs, to the input map and generates SQL statements to
        transform the languages accordingly.
        """
        stmts = []
        # check input languages
        for lng in inlanguages.keys():
            inlng = inlanguages[lng]
            # does it exist in the database?
            if lng in self:
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
        for lng in self.keys():
            # if missing, drop it
            if lng not in inlanguages:
                # special case: plpgsql is installed in 9.0
                if dbversion >= 90000 and self[lng].name == 'plpgsql':
                    continue
                self[lng].dropped = True
        return stmts

    def _drop(self):
        """Actually drop the languages

        :return: SQL statements
        """
        stmts = []
        for lng in self.keys():
            if hasattr(self[lng], 'dropped'):
                stmts.append(self[lng].drop())
        return stmts
