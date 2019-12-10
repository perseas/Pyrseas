# -*- coding: utf-8 -*-
"""Test materialized views"""

import pytest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_TABLE = "CREATE TABLE t1 (c1 INTEGER, c2 TEXT, c3 INTEGER)"
VIEW_STMT = "SELECT c1, c3 * 2 AS mc3 FROM t1"
CREATE_STMT = "CREATE MATERIALIZED VIEW mv1 AS " + VIEW_STMT
COMMENT_STMT = "COMMENT ON MATERIALIZED VIEW mv1 IS 'Test matview mv1'"
VIEW_DEFN = " SELECT t1.c1,\n    t1.c3 * 2 AS mc3\n   FROM t1;"


class MatViewToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of created materialized views"""

    def test_map_view_simple(self):
        "Map a created materialized view"
        if self.db.version < 90300:
            self.skipTest('Only available on PG 9.3')
        stmts = [CREATE_TABLE, CREATE_STMT]
        dbmap = self.to_map(stmts)
        expmap = {'definition': VIEW_DEFN, 'with_data': True,
                  'depends_on': ['table t1']}
        assert dbmap['schema public']['materialized view mv1'] == expmap

    def test_map_view_comment(self):
        "Map a materialized view with a comment"
        if self.db.version < 90300:
            self.skipTest('Only available on PG 9.3')
        dbmap = self.to_map([CREATE_TABLE, CREATE_STMT, COMMENT_STMT])
        assert dbmap['schema public']['materialized view mv1'][
            'description'] == 'Test matview mv1'

    def test_map_view_index(self):
        "Map a materialized view with an index"
        if self.db.version < 90300:
            self.skipTest('Only available on PG 9.3')
        stmts = [CREATE_TABLE, CREATE_STMT,
                 "CREATE INDEX idx1 ON mv1 (mc3)"]
        dbmap = self.to_map(stmts)
        expmap = {'definition': VIEW_DEFN, 'with_data': True,
                  'indexes': {'idx1': {'keys': ['mc3']}},
                  'depends_on': ['table t1']}
        assert dbmap['schema public']['materialized view mv1'] == expmap


class MatViewToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input materialized views"""

    def test_create_view(self):
        "Create a materialized view"
        if self.db.version < 90300:
            self.skipTest('Only available on PG 9.3')
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'integer'}}]}})
        inmap['schema public'].update({'materialized view mv1': {
            'definition': "SELECT c1, c3 * 2 AS mc3 FROM t1",
            'depends_on': ['table t1']}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == "CREATE TABLE t1 (c1 integer, " \
            "c2 text, c3 integer)"
        assert fix_indent(sql[1]) == \
            "CREATE MATERIALIZED VIEW mv1 AS SELECT c1, c3 * 2 AS mc3 FROM t1"

    def test_bad_view_map(self):
        "Error creating a materialized view with a bad map"
        if self.db.version < 90300:
            self.skipTest('Only available on PG 9.3')
        inmap = self.std_map()
        inmap['schema public'].update({'mv1': {'definition': VIEW_DEFN}})
        with pytest.raises(KeyError):
            self.to_sql(inmap)

    def test_drop_view(self):
        "Drop an existing materialized view with table dependencies"
        if self.db.version < 90300:
            self.skipTest('Only available on PG 9.3')
        stmts = ["CREATE TABLE t1 (c1 INTEGER, c2 TEXT)",
                 "CREATE TABLE t2 (c1 INTEGER, c3 TEXT)",
                 "CREATE MATERIALIZED VIEW mv1 AS SELECT t1.c1, c2, c3 "
                 "FROM t1 JOIN t2 ON (t1.c1 = t2.c1)"]
        sql = self.to_sql(self.std_map(), stmts)
        assert sql[0] == "DROP MATERIALIZED VIEW mv1"
        # can't control which table will be dropped first
        drt1 = 1
        drt2 = 2
        if 't1' in sql[2]:
            drt1 = 2
            drt2 = 1
        assert sql[drt1] == "DROP TABLE t1"
        assert sql[drt2] == "DROP TABLE t2"

    def test_view_with_comment(self):
        "Create a materialized view with a comment"
        if self.db.version < 90300:
            self.skipTest('Only available on PG 9.3')
        inmap = self.std_map()
        inmap['schema public'].update({'materialized view mv1': {
            'definition': VIEW_STMT, 'description': "Test matview mv1"}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_STMT
        assert sql[1] == COMMENT_STMT

    def test_view_index(self):
        "Create an index on a materialized view"
        if self.db.version < 90300:
            self.skipTest('Only available on PG 9.3')
        stmts = [CREATE_TABLE, CREATE_STMT]
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'integer'}}]}})
        inmap['schema public'].update({'materialized view mv1': {
            'definition': VIEW_DEFN, 'indexes': {'idx1': {'keys': ['mc3']}}}})
        sql = self.to_sql(inmap, stmts)
        assert sql == ["CREATE INDEX idx1 ON mv1 (mc3)"]
