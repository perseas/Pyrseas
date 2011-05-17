# -*- coding: utf-8 -*-
"""
    pyrseas.language
    ~~~~~~~~~~~~~~~~

    This defines two classes, Language and LanguageDict, derived from
    DbObject and DbObjectDict, respectively.
"""
from pyrseas.dbobject import DbObjectDict, DbObject


class Language(DbObject):
    """A procedural language definition"""

    keylist = ['name']
    objtype = "LANGUAGE"

    def to_map(self):
        """Convert language to a YAML-suitable format

        :return: dictionary
        """
        dct = self.__dict__.copy()
        for k in self.keylist:
            del dct[k]
        key = self.extern_key()
        language = {key: dct}
        if hasattr(self, 'description'):
            language[key].update(description=self.description)
        return language

    def create(self):
        """Return SQL statements to CREATE the language

        :return: SQL statements
        """
        stmts = ["CREATE LANGUAGE %s" % self.name]
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts

    def diff_map(self, inlanguage):
        """Generate SQL to transform an existing language

        :param inlanguage: a YAML map defining the new language
        :return: list of SQL statements

        Compares the language to an input language and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if hasattr(self, 'description'):
            if hasattr(inlanguage, 'description'):
                if self.description != inlanguage.description:
                    self.description = inlanguage.description
                    stmts.append(self.comment())
            else:
                del self.description
                stmts.append(self.comment())
        else:
            if hasattr(inlanguage, 'description'):
                self.description = inlanguage.description
                stmts.append(self.comment())
        return stmts


class LanguageDict(DbObjectDict):
    "The collection of procedural languages in a database."

    cls = Language
    query = \
        """SELECT lanname AS name, lanpltrusted AS trusted, description
           FROM pg_language l
                LEFT JOIN pg_description d
                     ON (l.oid = d.objoid AND d.objsubid = 0)
           WHERE lanispl
           ORDER BY lanname"""

    def from_map(self, inmap):
        """Initialize the dictionary of languages by examining the input map

        :param inmap: the input YAML map defining the languages
        """
        for lng in inmap.keys():
            key = lng.split()[1]
            language = self[key] = Language(name=key)
            inlanguage = inmap[lng]
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
        for (sch, fnc) in dbfunctions.keys():
            func = dbfunctions[(sch, fnc)]
            language = ''  # TODO: get language for function
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
                    except KeyError, exc:
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
