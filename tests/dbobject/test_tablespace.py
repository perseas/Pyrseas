# -*- coding: utf-8 -*-
"""Test tablespaces

These tests require the existence of tablespaces ts1 and ts2.
They should be owned by the user running the tests or the user should
have been granted CREATE (or ALL) privileges on the tablespaces.
"""

import unittest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent


CREATE_TABLE = "CREATE TABLE t1 (c1 integer, c2 text) TABLESPACE ts1"
CREATE_PRIM_KEY = "CREATE TABLE t1 (c1 integer PRIMARY KEY " \
    "USING INDEX TABLESPACE ts1, c2 text)"


class ToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of created tables"""

    def test_map_table(self):
        "Map a table using a tablespace"
        dbmap = self.to_map([CREATE_TABLE])
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}}],
                  'tablespace': 'ts1'}
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_map_primary_key(self):
        "Map a table with a PRIMARY KEY using a tablespace"
        dbmap = self.to_map([CREATE_PRIM_KEY])
        expmap = {'columns': [{'c1': {'type': 'integer', 'not_null': True}},
                              {'c2': {'type': 'text'}}],
                  'primary_key': {'t1_pkey': {'columns': ['c1'],
                                              'tablespace': 'ts1'}}}
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_map_index(self):
        "Map an index using a tablespace"
        dbmap = self.to_map(["CREATE TABLE t1 (c1 integer, c2 text)",
                             "CREATE UNIQUE INDEX t1_idx ON t1 (c1) "
                             "TABLESPACE ts1"])
        expmap = {'t1_idx': {'keys': ['c1'], 'tablespace': 'ts1',
                             'unique': True}}
        self.assertEqual(dbmap['schema public']['table t1']['indexes'], expmap)


class ToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation of table statements from input schemas"""

    def test_create_table(self):
        "Create a table in a tablespace"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                               {'c2': {'type': 'text'}}],
                    'tablespace': 'ts1'}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), CREATE_TABLE)

    def test_move_table(self):
        "Move a table from one tablespace to another"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                               {'c2': {'type': 'text'}}],
                    'tablespace': 'ts2'}})
        sql = self.to_sql(inmap, [CREATE_TABLE])
        self.assertEqual(fix_indent(sql[0]),
                         "ALTER TABLE t1 SET TABLESPACE ts2")

    def test_create_primary_key(self):
        "Create a table with a PRIMARY KEY in a different tablespace"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer', 'not_null': True}},
                               {'c2': {'type': 'text'}}],
                    'primary_key': {'t1_pkey': {'columns': ['c1'],
                                                'tablespace': 'ts2'}},
                    'tablespace': 'ts1'}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), "CREATE TABLE t1 "
                         "(c1 integer NOT NULL, c2 text) TABLESPACE ts1")
        self.assertEqual(fix_indent(sql[1]), "ALTER TABLE t1 ADD CONSTRAINT "
                         "t1_pkey PRIMARY KEY (c1) USING INDEX TABLESPACE ts2")

    def test_create_index(self):
        "Create an index using a tablespace"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                               {'c2': {'type': 'text'}}],
                    'indexes': {'t1_idx': {
                            'keys': ['c1'], 'tablespace': 'ts2',
                            'unique': True}},
                    'tablespace': 'ts1'}})
        sql = self.to_sql(inmap, [CREATE_TABLE])
        self.assertEqual(fix_indent(sql[0]), "CREATE UNIQUE INDEX t1_idx "
                         "ON t1 (c1) TABLESPACE ts2")

    def test_move_index(self):
        "Move a index from one tablespace to another"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                               {'c2': {'type': 'text'}}],
                    'indexes': {'t1_idx': {
                            'keys': ['c1'], 'tablespace': 'ts2'}}}})
        stmts = ["CREATE TABLE t1 (c1 integer, c2 text)",
                 "CREATE INDEX t1_idx ON t1 (c1) TABLESPACE ts1"]
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(fix_indent(sql[0]),
                         "ALTER INDEX t1_idx SET TABLESPACE ts2")


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(ToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(ToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
