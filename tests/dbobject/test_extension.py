# -*- coding: utf-8 -*-
"""Test extensions"""

import unittest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_STMT = "CREATE EXTENSION pg_trgm"
TRGM_COMMENT = "text similarity measurement and index searching based on " \
    "trigrams"


class ExtensionToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing extensions"""

    def test_map_extension(self):
        "Map an existing extension"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        dbmap = self.to_map([CREATE_STMT])
        self.assertEqual(dbmap['schema public']['extension pg_trgm'],
                         {'version': '1.0', 'description': TRGM_COMMENT})

    def test_map_no_depends(self):
        "Ensure no dependencies are included when mapping an extension"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        dbmap = self.to_map([CREATE_STMT])
        self.assertFalse('type gtrgm' in dbmap['schema public'])
        self.assertFalse('operator %(text, text)' in dbmap['schema public'])
        self.assertFalse('function show_trgm(text)' in dbmap['schema public'])

    def test_map_lang_extension(self):
        "Map a procedural language as an extension"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        dbmap = self.to_map(["CREATE EXTENSION plperl"])
        self.assertEqual(dbmap['schema pg_catalog']['extension plperl'],
                         {'version': '1.0',
                          'description': "PL/Perl procedural language"})
        self.assertFalse('language plperl' in dbmap)

    def test_map_extension_schema(self):
        "Map an existing extension"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        dbmap = self.to_map(["CREATE SCHEMA s1", CREATE_STMT + " SCHEMA s1"])
        self.assertEqual(dbmap['schema s1']['extension pg_trgm'],
                         {'version': '1.0', 'description': TRGM_COMMENT})


class ExtensionToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation for input extensions"""

    def test_create_extension(self):
        "Create a extension that didn't exist"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap['schema public'].update({'extension pg_trgm': {}})
        sql = self.to_sql(inmap)
        self.assertEqual(sql, [CREATE_STMT])

    def test_bad_extension_map(self):
        "Error creating a extension with a bad map"
        inmap = self.std_map()
        inmap['schema public'].update({'pg_trgm': {}})
        self.assertRaises(KeyError, self.to_sql, inmap)

    def test_drop_extension(self):
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        "Drop an existing extension"
        sql = self.to_sql(self.std_map(), [CREATE_STMT])
        self.assertEqual(sql, ["DROP EXTENSION pg_trgm"])

    def test_create_extension_schema(self):
        "Create a extension in a given schema"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap.update({'schema s1': {'extension pg_trgm': {'version': '1.0'}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        self.assertEqual(fix_indent(sql[0]),
                         "CREATE EXTENSION pg_trgm SCHEMA s1 VERSION '1.0'")

    def test_comment_extension(self):
        "Change the comment for an existing extension"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap['schema public'].update({'extension pg_trgm': {
                    'description': "Trigram extension"}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        self.assertEqual(sql, [
                "COMMENT ON EXTENSION pg_trgm IS 'Trigram extension'"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(ExtensionToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            ExtensionToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
