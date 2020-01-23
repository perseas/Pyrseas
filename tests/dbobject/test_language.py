# -*- coding: utf-8 -*-
"""Test languages"""

import pytest
import psycopg2

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase

CREATE_STMT = "CREATE LANGUAGE plperl"
DROP_STMT = "DROP LANGUAGE IF EXISTS plperl CASCADE"
COMMENT_STMT = "COMMENT ON LANGUAGE plperl IS 'Test language PL/Perl'"


class LanguageToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing languages"""

    def test_map_language(self):
        "Map an existing language"
        if self.db.version >= 90100:
            self.skipTest('Only available before PG 9.1')
        dbmap = self.to_map([DROP_STMT, CREATE_STMT])
        assert dbmap['language plperl'] == {'trusted': True}

    def test_map_language_comment(self):
        "Map a language with a comment"
        if self.db.version >= 90100:
            self.skipTest('Only available before PG 9.1')
        dbmap = self.to_map([DROP_STMT, CREATE_STMT, COMMENT_STMT],
                            superuser=True)
        assert dbmap['language plperl']['description'] == \
            'Test language PL/Perl'

    def test_map_language_bug_103(self):
        "Test a function created with language other than plpgsql/plperl"
        try:
            self.to_map(["CREATE OR REPLACE LANGUAGE plpython3u"])
        except psycopg2.OperationalError as e:
            self.skipTest("plpython3 installation failed: %s" % e)
        m = self.to_map(["CREATE FUNCTION test103() RETURNS int AS "
                         "'return 1' LANGUAGE plpython3u"])
        self.to_map(["DROP LANGUAGE plpython3u CASCADE"])
        assert 'language plpython3u' in m


class LanguageToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation for input languages"""

    def tearDown(self):
        self.db.execute_commit(DROP_STMT)
        self.db.close()

    def test_create_language(self):
        "Create a language that didn't exist"
        if self.db.version >= 90100:
            self.skipTest('Only available before PG 9.1')
        sql = self.to_sql({'language plperl': {}})
        assert sql == [CREATE_STMT]

    def test_bad_language_map(self):
        "Error creating a language with a bad map"
        with pytest.raises(KeyError):
            self.to_sql({'plperl': {}})

    def test_drop_language(self):
        "Drop an existing language"
        if self.db.version >= 90100:
            self.skipTest('Only available before PG 9.1')
        sql = self.to_sql({}, [CREATE_STMT])
        assert sql == ["DROP LANGUAGE plperl"]

    def test_drop_language_function(self):
        "Drop an existing function and the language it uses"
        if self.db.version >= 90100:
            self.skipTest('Only available before PG 9.1')
        stmts = [CREATE_STMT, "CREATE FUNCTION f1() RETURNS text "
                 "LANGUAGE plperl AS $_$return \"dummy\";$_$"]
        sql = self.to_sql({}, stmts)
        assert sql == ["DROP FUNCTION f1()", "DROP LANGUAGE plperl"]

    def test_comment_on_language(self):
        "Create a comment for an existing language"
        if self.db.version >= 90100:
            self.skipTest('Only available before PG 9.1')
        inmap = self.std_map()
        inmap.update({'language plperl': {
            'description': "Test language PL/Perl"}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        assert sql == [COMMENT_STMT]
