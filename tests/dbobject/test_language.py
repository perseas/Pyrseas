# -*- coding: utf-8 -*-
"""Test languages"""

import unittest

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
        self.assertEqual(dbmap['language plperl'], {'trusted': True})

    def test_map_language_comment(self):
        "Map a language with a comment"
        if self.db.version >= 90100:
            self.skipTest('Only available before PG 9.1')
        dbmap = self.to_map([DROP_STMT, CREATE_STMT, COMMENT_STMT],
                            superuser=True)
        self.assertEqual(dbmap['language plperl']['description'],
                         'Test language PL/Perl')


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
        self.assertEqual(sql, [CREATE_STMT])

    def test_bad_language_map(self):
        "Error creating a language with a bad map"
        self.assertRaises(KeyError, self.to_sql, {'plperl': {}})

    def test_drop_language(self):
        "Drop an existing language"
        if self.db.version >= 90100:
            self.skipTest('Only available before PG 9.1')
        sql = self.to_sql({}, [CREATE_STMT])
        self.assertEqual(sql, ["DROP LANGUAGE plperl"])

    def test_drop_language_function(self):
        "Drop an existing function and the language it uses"
        if self.db.version >= 90100:
            self.skipTest('Only available before PG 9.1')
        stmts = [CREATE_STMT, "CREATE FUNCTION f1() RETURNS text "
                 "LANGUAGE plperl AS $_$return \"dummy\";$_$"]
        sql = self.to_sql({}, stmts)
        self.assertEqual(sql, ["DROP FUNCTION f1()", "DROP LANGUAGE plperl"])

    def test_comment_on_language(self):
        "Create a comment for an existing language"
        if self.db.version >= 90100:
            self.skipTest('Only available before PG 9.1')
        inmap = self.std_map()
        inmap.update({'language plperl': {
                    'description': "Test language PL/Perl"}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        self.assertEqual(sql, [COMMENT_STMT])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(LanguageToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            LanguageToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
