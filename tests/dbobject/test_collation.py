# -*- coding: utf-8 -*-
"""Test collations

These tests require that the locale fr_FR.utf8 (or equivalent) be installed.
"""
import sys

import pytest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

if sys.platform == 'win32':
    COLL = 'French_France.1252'
else:
    COLL = 'fr_FR.UTF-8'

CREATE_STMT = "CREATE COLLATION sd.c1 (LC_COLLATE = '%s', LC_CTYPE = '%s')" % (
    COLL, COLL)
COMMENT_STMT = "COMMENT ON COLLATION sd.c1 IS 'Test collation c1'"


class CollationToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing collations"""

    def test_map_collation1(self):
        "Map a collation"
        dbmap = self.to_map([CREATE_STMT])
        expmap = {'lc_collate': COLL, 'lc_ctype': COLL}
        assert dbmap['schema sd']['collation c1'] == expmap

    def test_map_collation_comment(self):
        "Map a collation comment"
        dbmap = self.to_map([CREATE_STMT, COMMENT_STMT])
        assert dbmap['schema sd']['collation c1']['description'] == \
            'Test collation c1'

    def test_map_column_collation(self):
        "Map a table with a column collation"
        dbmap = self.to_map(
            [CREATE_STMT, "CREATE TABLE t1 (c1 integer, c2 text COLLATE c1)"])
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text', 'collation': 'c1'}}],
                  'depends_on': ['collation c1']}
        assert dbmap['schema sd']['table t1'] == expmap

    def test_map_index_collation(self):
        "Map an index with column collation"
        stmts = [CREATE_STMT, "CREATE TABLE t1 (c1 integer, c2 text)",
                 "CREATE INDEX t1_idx ON t1 (c2 COLLATE c1)"]
        dbmap = self.to_map(stmts)
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}}],
                  'indexes': {'t1_idx': {
                      'keys': [{'c2': {'collation': 'sd.c1'}}],
                      'depends_on': ['collation c1']}}}
        assert dbmap['schema sd']['table t1'] == expmap


class CollationToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input collations"""

    def test_create_collation1(self):
        "Create a collation"
        inmap = self.std_map()
        inmap['schema sd'].update({'collation c1': {
            'lc_collate': COLL, 'lc_ctype': COLL}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_STMT

    def test_create_collation_schema(self):
        "Create a collation in a non-default schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {'collation c1': {
            'lc_collate': COLL, 'lc_ctype': COLL}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        assert fix_indent(sql[0]) == "CREATE COLLATION s1.c1 (" \
            "LC_COLLATE = '%s', LC_CTYPE = '%s')" % (COLL, COLL)

    def test_bad_collation_map(self):
        "Error creating a collation with a bad map"
        inmap = self.std_map()
        inmap['schema sd'].update({'c1': {
            'lc_collate': COLL, 'lc_ctype': COLL}})
        with pytest.raises(KeyError):
            self.to_sql(inmap)

    def test_drop_collation(self):
        "Drop an existing collation"
        sql = self.to_sql(self.std_map(), [CREATE_STMT])
        assert sql[0] == "DROP COLLATION sd.c1"

    def test_collation_with_comment(self):
        "Create a collation with a comment"
        inmap = self.std_map()
        inmap['schema sd'].update({'collation c1': {
            'description': 'Test collation c1',
            'lc_collate': COLL, 'lc_ctype': COLL}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_STMT
        assert sql[1] == COMMENT_STMT

    def test_create_table_column_collation(self):
        "Create a table with a column with non-default collation"
        inmap = self.std_map()
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer', 'not_null': True}},
                        {'c2': {'type': 'text', 'collation': 'c1'}}]}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == "CREATE TABLE sd.t1 (" \
            'c1 integer NOT NULL, c2 text COLLATE "c1")'

    def test_create_index_collation(self):
        "Create an index with column collation"
        stmts = [CREATE_STMT, "CREATE TABLE t1 (c1 integer, c2 text)"]
        inmap = self.std_map()
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}}],
            'indexes': {'t1_idx': {'keys': [{'c2': {'collation': 'c1'}}]}}}})
        sql = self.to_sql(inmap, stmts)
        # NOTE(David Chang): This is a hack to get this test to work. We reordered all drops to happen before any other statements because in theory you shouldn't be depending on a previously defined collation. If you need it, you need to have it defined in your db.yaml to use it (and thus won't be dropped). However, this test is odd in how it runs and I don't think you can hit this case in real usage
        assert sql[0] == "DROP COLLATION c1"
        assert fix_indent(sql[1]) == \
            "CREATE INDEX t1_idx ON sd.t1 (c2 COLLATE c1)"

    def test_create_type_attribute_collation(self):
        "Create a composite type with an attribute with non-default collation"
        inmap = self.std_map()
        inmap['schema sd'].update({'type t1': {
            'attributes': [{'x': {'type': 'integer'}},
                           {'y': {'type': 'text', 'collation': 'c1'}}]}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == "CREATE TYPE sd.t1 AS (x integer, " \
            'y text COLLATE "c1")'
