# -*- coding: utf-8 -*-
"""Test indexes"""

import unittest

from pyrseas.testutils import PyrseasTestCase, fix_indent

CREATE_TABLE_STMT = "CREATE TABLE t1 (c1 integer, c2 text)"
CREATE_STMT = "CREATE INDEX t1_idx ON t1 (c1)"
COMMENT_STMT = "COMMENT ON INDEX t1_idx IS 'Test index t1_idx'"


class IndexToMapTestCase(PyrseasTestCase):
    """Test mapping of created indexes"""

    def test_index_1(self):
        "Map a single-column index"
        self.db.execute(CREATE_TABLE_STMT)
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}}],
                  'indexes': {'t1_idx': {'columns': ['c1'],
                                          'access_method': 'btree'}}}
        dbmap = self.db.execute_and_map(CREATE_STMT)
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

    def test_index_function(self):
        "Map an index using a function"
        self.db.execute(CREATE_TABLE_STMT)
        ddlstmt = "CREATE INDEX t1_idx ON t1 ((lower(c2)))"
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}}],
                  'indexes': {'t1_idx': {'expression': 'lower(c2)',
                                          'access_method': 'btree'}}}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_index_col_opts(self):
        "Map an index with various column options"
        self.db.execute("CREATE TABLE t1 (c1 cidr, c2 text)")
        ddlstmt = "CREATE INDEX t1_idx ON t1 (c1 cidr_ops NULLS FIRST, " \
            "c2 DESC)"
        expmap = {'columns': [{'c1': {'type': 'cidr'}},
                              {'c2': {'type': 'text'}}],
                  'indexes': {'t1_idx': {'columns': [
                        {'c1': {'opclass': 'cidr_ops', 'nulls': 'first'}},
                        {'c2': {'order': 'desc'}}],
                                         'access_method': 'btree'}}}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_map_index_comment(self):
        "Map an index comment"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_STMT)
        dbmap = self.db.execute_and_map(COMMENT_STMT)
        self.assertEqual(dbmap['schema public']['table t1']['indexes']
                         ['t1_idx']['description'], 'Test index t1_idx')


class IndexToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input indexes"""

    def test_create_table_with_index(self):
        "Create new table with a single column index"
        inmap = self.std_map()
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
        self.db.execute_commit("CREATE TABLE t1 (c1 INTEGER NOT NULL, "
                        "c2 INTEGER NOT NULL, c3 TEXT)")
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [
                        {'c1': {'type': 'integer', 'not_null': True}},
                        {'c2': {'type': 'integer', 'not_null': True}},
                        {'c3': {'type': 'text'}}],
                    'indexes': {'t1_idx': {'columns': ['c2', 'c1'],
                                           'unique': True}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["CREATE UNIQUE INDEX t1_idx ON t1 (c2, c1)"])

    def test_bad_index(self):
        "Fail on creating an index without columns or expression"
        self.db.execute_commit("DROP TABLE IF EXISTS t1")
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'indexes': {'t1_idx': {'access_method': 'btree'}}}})
        self.assertRaises(KeyError, self.db.process_map, inmap)

    def test_create_index_function(self):
        "Create an index which uses a function"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'indexes': {'t1_idx': {'expression': 'lower(c2)',
                                           'access_method': 'btree'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql[1],
                         "CREATE INDEX t1_idx ON t1 USING btree (lower(c2))")

    def test_create_index_col_opts(self):
        "Create table and an index with column options"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'cidr'}},
                                {'c2': {'type': 'text'}}],
                    'indexes': {'t1_idx': {'columns': [
                                {'c1': {'opclass': 'cidr_ops',
                                        'nulls': 'first'}}, 'c2'],
                                           'access_method': 'btree'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql[1], "CREATE INDEX t1_idx ON t1 USING btree "
                         "(c1 cidr_ops NULLS FIRST, c2)")

    def test_index_with_comment(self):
        "Create an index with a comment"
        self.db.execute_commit(CREATE_TABLE_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'indexes': {'t1_idx': {
                            'columns': ['c1'], 'access_method': 'btree',
                            'description': 'Test index t1_idx'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "CREATE INDEX t1_idx ON t1 USING btree (c1)")
        self.assertEqual(dbsql[1], COMMENT_STMT)

    def test_comment_on_index(self):
        "Create a comment for an existing index"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute_commit(CREATE_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'indexes': {'t1_idx': {
                            'columns': ['c1'], 'access_method': 'btree',
                            'description': 'Test index t1_idx'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [COMMENT_STMT])

    def test_drop_index_comment(self):
        "Drop the comment on an existing index"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_STMT)
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'indexes': {'t1_idx': {
                            'columns': ['c1'], 'access_method': 'btree'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["COMMENT ON INDEX t1_idx IS NULL"])

    def test_change_index_comment(self):
        "Change existing comment on an index"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_STMT)
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'indexes': {'t1_idx': {
                            'columns': ['c1'], 'access_method': 'btree',
                            'description': 'Changed index t1_idx'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [
                "COMMENT ON INDEX t1_idx IS 'Changed index t1_idx'"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(IndexToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            IndexToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
