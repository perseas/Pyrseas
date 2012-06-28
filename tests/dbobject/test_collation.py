# -*- coding: utf-8 -*-
"""Test collations

These tests require that the locale fr_FR.utf8 be installed.
"""

import unittest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_STMT = "CREATE COLLATION c1 (LC_COLLATE = 'fr_FR.utf8', " \
    "LC_CTYPE = 'fr_FR.utf8')"
COMMENT_STMT = "COMMENT ON COLLATION c1 IS 'Test collation c1'"


class CollationToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing collations"""

    def test_map_collation(self):
        "Map a collation"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        dbmap = self.to_map([CREATE_STMT])
        expmap = {'lc_collate': 'fr_FR.utf8', 'lc_ctype': 'fr_FR.utf8'}
        self.assertEqual(dbmap['schema public']['collation c1'], expmap)

    def test_map_collation_comment(self):
        "Map a collation comment"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        dbmap = self.to_map([CREATE_STMT, COMMENT_STMT])
        self.assertEqual(dbmap['schema public']['collation c1']
                         ['description'], 'Test collation c1')

    def test_map_column_collation(self):
        "Map a table with a column collation"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        dbmap = self.to_map(
            [CREATE_STMT, "CREATE TABLE t1 (c1 integer, c2 text COLLATE c1)"])
        expmap = {'columns': [
                    {'c1': {'type': 'integer'}},
                    {'c2': {'type': 'text', 'collation': 'c1'}}]}
        self.assertEqual(dbmap['schema public']['table t1'], expmap)


class CollationToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input collations"""

    def test_create_collation(self):
        "Create a collation"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap['schema public'].update({'collation c1': {
                    'lc_collate': 'fr_FR.utf8', 'lc_ctype': 'fr_FR.utf8'}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), CREATE_STMT)

    def test_create_collation_schema(self):
        "Create a collation in a non-public schema"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap.update({'schema s1': {'collation c1': {
                    'lc_collate': 'fr_FR.utf8', 'lc_ctype': 'fr_FR.utf8'}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        self.assertEqual(fix_indent(sql[0]),
                         "CREATE COLLATION s1.c1 (LC_COLLATE = 'fr_FR.utf8', "
                         "LC_CTYPE = 'fr_FR.utf8')")

    def test_bad_collation_map(self):
        "Error creating a collation with a bad map"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap['schema public'].update({'c1': {
                    'lc_collate': 'fr_FR.utf8', 'lc_ctype': 'fr_FR.utf8'}})
        self.assertRaises(KeyError, self.to_sql, inmap)

    def test_drop_collation(self):
        "Drop an existing collation"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        sql = self.to_sql(self.std_map(), [CREATE_STMT])
        self.assertEqual(sql[0], "DROP COLLATION c1")

    def test_collation_with_comment(self):
        "Create a collation with a comment"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap['schema public'].update({'collation c1': {
                    'description': 'Test collation c1',
                    'lc_collate': 'fr_FR.utf8', 'lc_ctype': 'fr_FR.utf8'}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), CREATE_STMT)
        self.assertEqual(sql[1], COMMENT_STMT)

    def test_create_table_column_collation(self):
        "Create a table with a column with non-default collation"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer', 'not_null': True}},
                                {'c2': {'type': 'text', 'collation': 'c1'}}]}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]),
                         "CREATE TABLE t1 (c1 integer NOT NULL, "
                         "c2 text COLLATE c1)")


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(
        CollationToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            CollationToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
