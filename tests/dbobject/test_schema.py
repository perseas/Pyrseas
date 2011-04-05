# -*- coding: utf-8 -*-
"""Test schemas"""

import unittest

from utils import PyrseasTestCase, fix_indent

DROP_STMT = "DROP SCHEMA IF EXISTS s1 CASCADE"


class SchemaToMapTestCase(PyrseasTestCase):
    """Test mapping of created schemas"""

    def test_map_schema(self):
        "Map a created schema"
        self.db.execute(DROP_STMT)
        dbmap = self.db.execute_and_map("CREATE SCHEMA s1")
        self.assertEqual(dbmap, {'schema s1': {}, 'schema public': {}})

    def test_map_table_within_schema(self):
        "Map a schema and a table within it"
        self.db.execute(DROP_STMT)
        self.db.execute("CREATE SCHEMA s1")
        ddlstmt = "CREATE TABLE s1.t1 (c1 INTEGER, c2 TEXT)"
        expmap = {'schema public': {}, 'schema s1': {
                'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}]}}}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap, expmap)


class SchemaToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input schemas"""

    def tearDown(self):
        self.db.execute_commit(DROP_STMT)
        self.db.close()

    def test_create_schema(self):
        "Create a schema that didn't exist"
        self.db.execute_commit(DROP_STMT)
        inmap = {'schema s1': {}}
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["CREATE SCHEMA s1"])

    def test_bad_schema_map(self):
        "Error creating a schema with a bad map"
        inmap = {'s1': {}}
        self.assertRaises(KeyError, self.db.process_map, inmap)

    def test_create_table_within_schema(self):
        "Create a new schema and a table within it"
        self.db.execute_commit(DROP_STMT)
        inmap = {'schema s1': {
                'table t1':
                    {'columns': [{'c1': {'type': 'integer'}},
                                 {'c2': {'type': 'text'}}]}}}
        dbsql = self.db.process_map(inmap)
        expsql = ["CREATE SCHEMA s1",
                 "CREATE TABLE s1.t1 (c1 integer, c2 text)"]
        for i in range(len(expsql)):
            self.assertEqual(fix_indent(dbsql[i]), expsql[i])

    def test_drop_schema(self):
        "Drop an existing schema"
        self.db.execute(DROP_STMT)
        self.db.execute_commit("CREATE SCHEMA s1")
        dbsql = self.db.process_map({})
        self.assertEqual(dbsql, ["DROP SCHEMA s1 CASCADE"])

    def test_rename_schema(self):
        "Rename an existing schema"
        self.db.execute(DROP_STMT)
        self.db.execute_commit("CREATE SCHEMA s1")
        inmap = {'schema s2': {'oldname': 's1'}}
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["ALTER SCHEMA s1 RENAME TO s2"])

    def test_bad_rename_schema(self):
        "Error renaming a non-existing schema"
        self.db.execute(DROP_STMT)
        self.db.execute_commit("CREATE SCHEMA s1")
        inmap = {'schema s2': {'oldname': 's3'}}
        self.assertRaises(KeyError, self.db.process_map, inmap)


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(SchemaToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            SchemaToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
