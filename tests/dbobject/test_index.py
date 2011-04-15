# -*- coding: utf-8 -*-
"""Test indexes"""

import unittest

from utils import PyrseasTestCase, fix_indent, new_std_map


class IndexToMapTestCase(PyrseasTestCase):
    """Test mapping of created indexes"""

    def test_index_1(self):
        "Map a single-column index"
        self.db.execute("CREATE TABLE t1 (c1 INTEGER, c2 TEXT)")
        ddlstmt = "CREATE INDEX t1_idx ON t1 (c1)"
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}}],
                  'indexes': {'t1_idx': {'columns': ['c1'],
                                          'access_method': 'btree'}}}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_index_2(self):
        "Map a two-column index"
        self.db.execute("CREATE TABLE t1 (c1 INTEGER, c2 CHAR(5), c3 TEXT)")
        ddlstmt = "CREATE UNIQUE INDEX t1_idx ON t1 (c1, c2)"
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'character(5)'}},
                              {'c3': {'type': 'text'}}],
                  'indexes': {'t1_idx': {'columns': ['c1', 'c2'],
                                          'unique': True,
                                          'access_method': 'btree'}}}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_index_3(self):
        "Map a table with a unique index and a non-unique GIN index"
        self.db.execute("CREATE TABLE t1 (c1 INTEGER, c2 CHAR(5), "
                        "c3 tsvector)")
        self.db.execute("CREATE UNIQUE INDEX t1_idx_1 ON t1 (c1, c2)")
        ddlstmt = "CREATE INDEX t1_idx_2 ON t1 USING gin (c3)"
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'character(5)'}},
                              {'c3': {'type': 'tsvector'}}],
                  'indexes': {'t1_idx_1': {'columns': ['c1', 'c2'],
                                            'unique': True,
                                            'access_method': 'btree'},
                              't1_idx_2': {'columns': ['c3'],
                                            'access_method': 'gin'}}}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)


class IndexToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input indexes"""

    def test_create_table_with_index(self):
        "Create new table with a single column index"
        self.db.execute_commit("DROP TABLE IF EXISTS t1")
        inmap = new_std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'indexes': {'t1_idx': {
                            'columns': ['c1'],
                            'access_method': 'btree'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "CREATE TABLE t1 (c1 integer, c2 text)")
        self.assertEqual(dbsql[1],
                         "CREATE INDEX t1_idx ON t1 USING btree (c1)")

    def test_add_index(self):
        "Add a two-column unique index to an existing table"
        self.db.execute("DROP TABLE IF EXISTS t1")
        self.db.execute_commit("CREATE TABLE t1 (c1 INTEGER NOT NULL, "
                        "c2 INTEGER NOT NULL, c3 TEXT)")
        inmap = new_std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [
                        {'c1': {'type': 'integer', 'not_null': True}},
                        {'c2': {'type': 'integer', 'not_null': True}},
                        {'c3': {'type': 'text'}}],
                    'indexes': {'t1_idx': {
                            'columns': ['c2', 'c1'],
                            'unique': True}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql,
                         ["CREATE UNIQUE INDEX t1_idx ON t1 (c2, c1)"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(IndexToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            IndexToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
