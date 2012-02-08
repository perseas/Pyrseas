# -*- coding: utf-8 -*-
"""Test conversions"""

import unittest

from pyrseas.testutils import PyrseasTestCase, fix_indent

CREATE_STMT = "CREATE CONVERSION c1 FOR 'LATIN1' TO 'UTF8' " \
    "FROM iso8859_1_to_utf8"
DROP_STMT = "DROP CONVERSION IF EXISTS c1"
COMMENT_STMT = "COMMENT ON CONVERSION c1 IS 'Test conversion c1'"


class ConversionToMapTestCase(PyrseasTestCase):
    """Test mapping of existing conversions"""

    def test_map_conversion(self):
        "Map a conversion"
        expmap = {'source_encoding': 'LATIN1', 'dest_encoding': 'UTF8',
                  'function': 'iso8859_1_to_utf8'}
        dbmap = self.db.execute_and_map(CREATE_STMT)
        self.assertEqual(dbmap['schema public']['conversion c1'], expmap)

    def test_map_conversion_comment(self):
        "Map a conversion comment"
        self.db.execute(CREATE_STMT)
        dbmap = self.db.execute_and_map(COMMENT_STMT)
        self.assertEqual(dbmap['schema public']['conversion c1']
                         ['description'], 'Test conversion c1')


class ConversionToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input conversions"""

    def test_create_conversion(self):
        "Create a conversion"
        inmap = self.std_map()
        inmap['schema public'].update({'conversion c1': {
                    'source_encoding': 'LATIN1', 'dest_encoding': 'UTF8',
                    'function': 'iso8859_1_to_utf8'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_STMT)

    def test_create_conversion_schema(self):
        "Create a conversion in a non-public schema"
        self.db.execute_commit("DROP SCHEMA IF EXISTS s1 CASCADE")
        self.db.execute_commit("CREATE SCHEMA s1")
        inmap = self.std_map()
        inmap.update({'schema s1': {'conversion c1': {
                    'source_encoding': 'LATIN1', 'dest_encoding': 'UTF8',
                    'function': 'iso8859_1_to_utf8', 'default': True}}})
        dbsql = self.db.process_map(inmap)
        self.db.execute_commit("DROP SCHEMA s1 CASCADE")
        self.assertEqual(fix_indent(dbsql[0]),
                         "CREATE DEFAULT CONVERSION s1.c1 FOR 'LATIN1' TO "
                         "'UTF8' FROM iso8859_1_to_utf8")

    def test_bad_conversion_map(self):
        "Error creating a conversion with a bad map"
        inmap = self.std_map()
        inmap['schema public'].update({'c1': {
                    'source_encoding': 'LATIN1', 'dest_encoding': 'UTF8',
                    'function': 'iso8859_1_to_utf8'}})
        self.assertRaises(KeyError, self.db.process_map, inmap)

    def test_drop_conversion(self):
        "Drop an existing conversion"
        self.db.execute_commit(CREATE_STMT)
        dbsql = self.db.process_map(self.std_map())
        self.assertEqual(dbsql[0], "DROP CONVERSION c1")

    def test_conversion_with_comment(self):
        "Create a conversion with a comment"
        inmap = self.std_map()
        inmap['schema public'].update({'conversion c1': {
                    'description': 'Test conversion c1',
                    'source_encoding': 'LATIN1', 'dest_encoding': 'UTF8',
                    'function': 'iso8859_1_to_utf8'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_STMT)
        self.assertEqual(dbsql[1], COMMENT_STMT)

    def test_comment_on_conversion(self):
        "Create a comment for an existing conversion"
        self.db.execute_commit(CREATE_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'conversion c1': {
                    'description': 'Test conversion c1',
                    'source_encoding': 'LATIN1', 'dest_encoding': 'UTF8',
                    'function': 'iso8859_1_to_utf8'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [COMMENT_STMT])

    def test_drop_conversion_comment(self):
        "Drop a comment on an existing conversion"
        self.db.execute(CREATE_STMT)
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'conversion c1': {
                    'source_encoding': 'LATIN1', 'dest_encoding': 'UTF8',
                    'function': 'iso8859_1_to_utf8'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["COMMENT ON CONVERSION c1 IS NULL"])

    def test_change_conversion_comment(self):
        "Change existing comment on a conversion"
        self.db.execute(CREATE_STMT)
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'conversion c1': {
                    'description': 'Changed conversion c1',
                    'source_encoding': 'LATIN1', 'dest_encoding': 'UTF8',
                    'function': 'iso8859_1_to_utf8'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [
                "COMMENT ON CONVERSION c1 IS 'Changed conversion c1'"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(
        ConversionToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            ConversionToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
