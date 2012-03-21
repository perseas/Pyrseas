# -*- coding: utf-8 -*-
"""Test conversions"""

import unittest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_STMT = "CREATE CONVERSION c1 FOR 'LATIN1' TO 'UTF8' " \
    "FROM iso8859_1_to_utf8"
DROP_STMT = "DROP CONVERSION IF EXISTS c1"
COMMENT_STMT = "COMMENT ON CONVERSION c1 IS 'Test conversion c1'"


class ConversionToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing conversions"""

    def test_map_conversion(self):
        "Map a conversion"
        dbmap = self.to_map([CREATE_STMT])
        expmap = {'source_encoding': 'LATIN1', 'dest_encoding': 'UTF8',
                  'function': 'iso8859_1_to_utf8'}
        self.assertEqual(dbmap['schema public']['conversion c1'], expmap)

    def test_map_conversion_comment(self):
        "Map a conversion comment"
        dbmap = self.to_map([CREATE_STMT, COMMENT_STMT])
        self.assertEqual(dbmap['schema public']['conversion c1']
                         ['description'], 'Test conversion c1')


class ConversionToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input conversions"""

    def test_create_conversion(self):
        "Create a conversion"
        inmap = self.std_map()
        inmap['schema public'].update({'conversion c1': {
                    'source_encoding': 'LATIN1', 'dest_encoding': 'UTF8',
                    'function': 'iso8859_1_to_utf8'}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), CREATE_STMT)

    def test_create_conversion_schema(self):
        "Create a conversion in a non-public schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {'conversion c1': {
                    'source_encoding': 'LATIN1', 'dest_encoding': 'UTF8',
                    'function': 'iso8859_1_to_utf8', 'default': True}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        self.assertEqual(fix_indent(sql[0]),
                         "CREATE DEFAULT CONVERSION s1.c1 FOR 'LATIN1' TO "
                         "'UTF8' FROM iso8859_1_to_utf8")

    def test_bad_conversion_map(self):
        "Error creating a conversion with a bad map"
        inmap = self.std_map()
        inmap['schema public'].update({'c1': {
                    'source_encoding': 'LATIN1', 'dest_encoding': 'UTF8',
                    'function': 'iso8859_1_to_utf8'}})
        self.assertRaises(KeyError, self.to_sql, inmap)

    def test_drop_conversion(self):
        "Drop an existing conversion"
        sql = self.to_sql(self.std_map(), [CREATE_STMT])
        self.assertEqual(sql[0], "DROP CONVERSION c1")

    def test_conversion_with_comment(self):
        "Create a conversion with a comment"
        inmap = self.std_map()
        inmap['schema public'].update({'conversion c1': {
                    'description': 'Test conversion c1',
                    'source_encoding': 'LATIN1', 'dest_encoding': 'UTF8',
                    'function': 'iso8859_1_to_utf8'}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), CREATE_STMT)
        self.assertEqual(sql[1], COMMENT_STMT)

    def test_comment_on_conversion(self):
        "Create a comment for an existing conversion"
        inmap = self.std_map()
        inmap['schema public'].update({'conversion c1': {
                    'description': 'Test conversion c1',
                    'source_encoding': 'LATIN1', 'dest_encoding': 'UTF8',
                    'function': 'iso8859_1_to_utf8'}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        self.assertEqual(sql, [COMMENT_STMT])

    def test_drop_conversion_comment(self):
        "Drop a comment on an existing conversion"
        stmts = [CREATE_STMT, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema public'].update({'conversion c1': {
                    'source_encoding': 'LATIN1', 'dest_encoding': 'UTF8',
                    'function': 'iso8859_1_to_utf8'}})
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(sql, ["COMMENT ON CONVERSION c1 IS NULL"])

    def test_change_conversion_comment(self):
        "Change existing comment on a conversion"
        stmts = [CREATE_STMT, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema public'].update({'conversion c1': {
                    'description': 'Changed conversion c1',
                    'source_encoding': 'LATIN1', 'dest_encoding': 'UTF8',
                    'function': 'iso8859_1_to_utf8'}})
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(sql, [
                "COMMENT ON CONVERSION c1 IS 'Changed conversion c1'"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(
        ConversionToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            ConversionToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
