# -*- coding: utf-8 -*-
"""Test materialized views"""

import pytest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_TABLE = "CREATE TABLE t1 (c1 INTEGER, c2 TEXT, c3 INTEGER)"
VIEW_STMT = "SELECT c1, c3 * 2 AS mc3 FROM t1"
CREATE_STMT = "CREATE MATERIALIZED VIEW sd.mv1 AS " + VIEW_STMT
COMMENT_STMT = "COMMENT ON MATERIALIZED VIEW sd.mv1 IS 'Test matview mv1'"
VIEW_DEFN = " SELECT t1.c1,\n    t1.c3 * 2 AS mc3\n   FROM sd.t1;"


class MatViewToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of created materialized views"""

    def test_map_view_simple(self):
        "Map a created materialized view"
        stmts = [CREATE_TABLE, CREATE_STMT]
        dbmap = self.to_map(stmts)
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'mc3': {'type': 'integer'}}],
                  'definition': VIEW_DEFN, 'with_data': True,
                  'depends_on': ['table t1']}
        assert dbmap['schema sd']['materialized view mv1'] == expmap

    def test_map_view_comment(self):
        "Map a materialized view with a comment"
        dbmap = self.to_map([CREATE_TABLE, CREATE_STMT, COMMENT_STMT])
        assert dbmap['schema sd']['materialized view mv1'][
            'description'] == 'Test matview mv1'

    def test_map_view_index(self):
        "Map a materialized view with an index"
        stmts = [CREATE_TABLE, CREATE_STMT,
                 "CREATE INDEX idx1 ON mv1 (mc3)"]
        dbmap = self.to_map(stmts)
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'mc3': {'type': 'integer'}}],
                  'definition': VIEW_DEFN, 'with_data': True,
                  'indexes': {'idx1': {'keys': ['mc3']}},
                  'depends_on': ['table t1']}
        assert dbmap['schema sd']['materialized view mv1'] == expmap


class MatViewToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input materialized views"""

    def test_create_view(self):
        "Create a materialized view"
        inmap = self.std_map()
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'integer'}}]}})
        inmap['schema sd'].update({'materialized view mv1': {
            'columns': [{'c1': {'type': 'integer'}},
                        {'mc3': {'type': 'integer'}}],
            'definition': "SELECT c1, c3 * 2 AS mc3 FROM sd.t1",
            'depends_on': ['table t1']}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == "CREATE TABLE sd.t1 (c1 integer, " \
            "c2 text, c3 integer)"
        assert fix_indent(sql[1]) == "CREATE MATERIALIZED VIEW sd.mv1 AS " \
            "SELECT c1, c3 * 2 AS mc3 FROM sd.t1"

    def test_bad_view_map(self):
        "Error creating a materialized view with a bad map"
        inmap = self.std_map()
        inmap['schema sd'].update({'mv1': {'definition': VIEW_DEFN}})
        with pytest.raises(KeyError):
            self.to_sql(inmap)

    def test_drop_view(self):
        "Drop an existing materialized view with table dependencies"
        stmts = ["CREATE TABLE t1 (c1 INTEGER, c2 TEXT)",
                 "CREATE TABLE t2 (c1 INTEGER, c3 TEXT)",
                 "CREATE MATERIALIZED VIEW mv1 AS SELECT t1.c1, c2, c3 "
                 "FROM t1 JOIN t2 ON (t1.c1 = t2.c1)"]
        sql = self.to_sql(self.std_map(), stmts)
        assert sql[0] == "DROP MATERIALIZED VIEW sd.mv1"
        # can't control which table will be dropped first
        drt1 = 1
        drt2 = 2
        if 't1' in sql[2]:
            drt1 = 2
            drt2 = 1
        assert sql[drt1] == "DROP TABLE sd.t1"
        assert sql[drt2] == "DROP TABLE sd.t2"

    def test_view_with_comment(self):
        "Create a materialized view with a comment"
        inmap = self.std_map()
        inmap['schema sd'].update({'materialized view mv1': {
            'columns': [{'c1': {'type': 'integer'}},
                        {'mc3': {'type': 'integer'}}],
            'definition': VIEW_STMT, 'description': "Test matview mv1"}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_STMT
        assert sql[1] == COMMENT_STMT

    def test_view_index(self):
        "Create an index on a materialized view"
        stmts = [CREATE_TABLE, CREATE_STMT]
        inmap = self.std_map()
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'integer'}}]}})
        inmap['schema sd'].update({'materialized view mv1': {
            'columns': [{'c1': {'type': 'integer'}},
                        {'mc3': {'type': 'integer'}}],
            'definition': VIEW_DEFN, 'indexes': {'idx1': {'keys': ['mc3']}}}})
        sql = self.to_sql(inmap, stmts)
        assert sql == ["CREATE INDEX idx1 ON sd.mv1 (mc3)"]
