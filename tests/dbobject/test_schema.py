# -*- coding: utf-8 -*-
"""Test schemas"""

import unittest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_STMT = "CREATE SCHEMA s1"
COMMENT_STMT = "COMMENT ON SCHEMA s1 IS 'Test schema s1'"


class SchemaToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of created schemas"""

    def test_map_schema(self):
        "Map a created schema"
        dbmap = self.to_map([CREATE_STMT])
        self.assertEqual(dbmap['schema s1'], {})

    def test_map_schema_comment(self):
        "Map a schema comment"
        dbmap = self.to_map([CREATE_STMT, COMMENT_STMT])
        self.assertEqual(dbmap['schema s1'], {'description': 'Test schema s1'})

    def test_map_select_schema(self):
        "Map a single schema when three schemas exist"
        stmts = [CREATE_STMT, "CREATE SCHEMA s2", "CREATE SCHEMA s3"]
        dbmap = self.to_map(stmts, ['s2'])
        self.assertEqual(dbmap['schema s2'], {})


class SchemaToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input schemas"""

    _schmap = {'schema s1': {'description': 'Test schema s1'}}

    def test_create_schema(self):
        "Create a schema that didn't exist"
        inmap = self.std_map()
        inmap.update({'schema s1': {}})
        sql = self.to_sql(inmap)
        self.assertEqual(sql, [CREATE_STMT])

    def test_bad_schema_map(self):
        "Error creating a schema with a bad map"
        self.assertRaises(KeyError, self.to_sql, {'s1': {}})

    def test_drop_schema(self):
        "Drop an existing schema"
        sql = self.to_sql(self.std_map(), [CREATE_STMT])
        self.assertEqual(sql, ["DROP SCHEMA s1"])

    def test_rename_schema(self):
        "Rename an existing schema"
        inmap = self.std_map()
        inmap.update({'schema s2': {'oldname': 's1'}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        self.assertEqual(sql, ["ALTER SCHEMA s1 RENAME TO s2"])

    def test_bad_rename_schema(self):
        "Error renaming a non-existing schema"
        inmap = self.std_map()
        inmap.update({'schema s2': {'oldname': 's3'}})
        self.assertRaises(KeyError, self.to_sql, inmap, [CREATE_STMT])

    def test_schema_with_comment(self):
        "Create a schema with a comment"
        inmap = self.std_map()
        inmap.update(self._schmap)
        sql = self.to_sql(inmap)
        self.assertEqual(sql, [CREATE_STMT, COMMENT_STMT])

    def test_comment_on_schema(self):
        "Create a comment for an existing schema"
        inmap = self.std_map()
        inmap.update(self._schmap)
        sql = self.to_sql(inmap, [CREATE_STMT])
        self.assertEqual(sql, [COMMENT_STMT])

    def test_drop_schema_comment(self):
        "Drop a comment on an existing schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {}})
        stmts = [CREATE_STMT, COMMENT_STMT]
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(sql, ["COMMENT ON SCHEMA s1 IS NULL"])

    def test_change_schema_comment(self):
        "Change existing comment on a schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {'description': 'Changed schema s1'}})
        stmts = [CREATE_STMT, COMMENT_STMT]
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(sql, ["COMMENT ON SCHEMA s1 IS 'Changed schema s1'"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(SchemaToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            SchemaToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
