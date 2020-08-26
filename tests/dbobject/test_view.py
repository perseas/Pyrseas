# -*- coding: utf-8 -*-
"""Test views"""

import pytest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_STMT = "CREATE VIEW sd.v1 AS SELECT now()::date AS today"
CREATE_TBL = "CREATE TABLE sd.t1 (c1 integer, c2 text, c3 integer)"
CREATE_STMT2 = "CREATE VIEW sd.v1 AS SELECT c1, c3 * 2 AS c2 FROM t1"
COMMENT_STMT = "COMMENT ON VIEW sd.v1 IS 'Test view v1'"
VIEW_DEFN = " SELECT now()::date AS today;"


class ViewToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of created views"""

    def test_map_view_no_table(self):
        "Map a created view without a table dependency"
        dbmap = self.to_map([CREATE_STMT])
        expmap = {'columns': [{'today': {'type': 'date'}}],
                  'definition': VIEW_DEFN}
        assert dbmap['schema sd']['view v1'] == expmap

    def test_map_view_table(self):
        "Map a created view with a table dependency"
        stmts = [CREATE_TBL, CREATE_STMT2]
        dbmap = self.to_map(stmts)
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'integer'}}],
                  'depends_on': ['table t1'],
                  'definition': " SELECT t1.c1,"
                  "\n    t1.c3 * 2 AS c2\n   FROM sd.t1;"}
        assert dbmap['schema sd']['view v1'] == expmap

    def test_map_view_columns(self):
        "Map a complex view's columns in addition to its definition"
        stmts = ["CREATE TABLE t1 (c1 INTEGER UNIQUE)",
                 "CREATE TABLE t2 (c2 INTEGER PRIMARY KEY REFERENCES t1(c1))",
                 "CREATE VIEW v1 AS SELECT (ROW(t1.*)::t2).*, t1, 5 AS const "
                 "FROM t1"]
        dbmap = self.to_map(stmts)
        expmap = {'columns': [{'c2': {'type': 'integer'}},
                              {'t1': {'type': 'sd.t1'}},
                              {'const': {'type': 'integer'}}],
                  'definition': " SELECT (ROW(t1.c1)::sd.t2).c2 AS c2,"
                  "\n    t1.*::sd.t1 AS t1,\n    5 AS const\n   FROM sd.t1;",
                  'depends_on': ['table t1']}
        assert dbmap['schema sd']['view v1'] == expmap

    def test_map_view_comment(self):
        "Map a view with a comment"
        dbmap = self.to_map([CREATE_STMT, COMMENT_STMT])
        assert dbmap['schema sd']['view v1']['description'] == \
            'Test view v1'


class ViewToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input views"""

    def test_create_view_no_table(self):
        "Create a view with no table dependency"
        inmap = self.std_map()
        inmap['schema sd'].update({'view v1': {'definition': VIEW_DEFN}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_STMT

    def test_create_view(self):
        "Create a view"
        inmap = self.std_map()
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'integer'}}]}})
        inmap['schema sd'].update({'view v1': {
            'definition': "SELECT c1, c3 * 2 AS c2 FROM t1"}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_TBL
        assert fix_indent(sql[1]) == CREATE_STMT2

    def test_create_view_in_schema(self):
        "Create a view within a non-default schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {'view v1': {'definition': VIEW_DEFN}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        assert fix_indent(sql[0]) == \
            "CREATE VIEW s1.v1 AS SELECT now()::date AS today"

    def test_bad_view_map(self):
        "Error creating a view with a bad map"
        inmap = self.std_map()
        inmap['schema sd'].update({'v1': {'definition': VIEW_DEFN}})
        with pytest.raises(KeyError):
            self.to_sql(inmap)

    def test_drop_view_no_table(self):
        "Drop an existing view without a table dependency"
        sql = self.to_sql(self.std_map(), [CREATE_STMT])
        assert sql == ["DROP VIEW sd.v1"]

    def test_drop_view(self):
        "Drop an existing view with table dependencies"
        stmts = ["CREATE TABLE t1 (c1 INTEGER, c2 TEXT)",
                 "CREATE TABLE t2 (c1 INTEGER, c3 TEXT)",
                 "CREATE VIEW v1 AS SELECT t1.c1, c2, c3 "
                 "FROM t1 JOIN t2 ON (t1.c1 = t2.c1)"]
        sql = self.to_sql(self.std_map(), stmts)
        assert sql[0] == "DROP VIEW sd.v1"
        # can't control which table will be dropped first
        drt1 = 1
        drt2 = 2
        if 't1' in sql[2]:
            drt1 = 2
            drt2 = 1
        assert sql[drt1] == "DROP TABLE sd.t1"
        assert sql[drt2] == "DROP TABLE sd.t2"

    def test_rename_view(self):
        "Rename an existing view"
        inmap = self.std_map()
        inmap['schema sd'].update({'view v2': {
            'oldname': 'v1', 'definition': VIEW_DEFN}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        assert sql == ["ALTER VIEW sd.v1 RENAME TO v2"]

    def test_bad_rename_view(self):
        "Error renaming a non-existing view"
        inmap = self.std_map()
        inmap['schema sd'].update({'view v2': {
            'oldname': 'v3', 'definition': VIEW_DEFN}})
        with pytest.raises(KeyError):
            self.to_sql(inmap, [CREATE_STMT])

    def test_change_view_defn(self):
        "Change view definition"
        inmap = self.std_map()
        inmap['schema sd'].update({'view v1': {
            'columns': [{'today': {'type': 'date'}}],
            'definition': " SELECT 'now'::text::date AS today;"}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        assert fix_indent(sql[0]) == "CREATE OR REPLACE VIEW sd.v1 AS " \
            "SELECT 'now'::text::date AS today"

    def test_change_column_name(self):
        "Attempt rename view column name (disallowed)"
        inmap = self.std_map()
        inmap['schema sd'].update({'view v1': {
            'columns': [{'todays_date': {'type': 'date'}}],
            'definition': " SELECT now()::date AS todays_date;"}})
        with pytest.raises(KeyError):
            sql = self.to_sql(inmap, [CREATE_STMT])

    def test_change_column_type(self):
        "Change view column type to different type (disallowed)"
        inmap = self.std_map()
        inmap['schema sd'].update({'view v1': {
            'columns': [{'c1': {'type': 'integer'}},
                        {'c2': {'type': 'numeric'}}],
            'definition': " SELECT c1, c3 * 2.0 AS c2 FROM t1;"}})
        with pytest.raises(TypeError):
            sql = self.to_sql(inmap, [CREATE_TBL, CREATE_STMT2])

    def test_view_depend_pk(self):
        "Create a view that depends on a primary key.  See issue #72"
        inmap = self.std_map()
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}},
                        {'c2': {'type': 'text'}}],
            'primary_key': {'t1_pkey': {'columns': ['c1']}}},
            'view v1': {
                'definition': " SELECT t1.c1,\n    t1.c2\n   FROM t1\n  "
                "GROUP BY t1.c1;",
                'depends_on': ['table t1']}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == "CREATE TABLE sd.t1 (c1 integer, c2 text)"
        assert fix_indent(sql[1]) == "ALTER TABLE sd.t1 ADD CONSTRAINT " \
            "t1_pkey PRIMARY KEY (c1)"
        assert fix_indent(sql[2]) == "CREATE VIEW sd.v1 AS SELECT t1.c1, " \
            "t1.c2 FROM t1 GROUP BY t1.c1"

    def test_view_with_comment(self):
        "Create a view with a comment"
        inmap = self.std_map()
        inmap['schema sd'].update({'view v1': {
            'definition': VIEW_DEFN, 'description': "Test view v1"}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_STMT
        assert sql[1] == COMMENT_STMT

    def test_comment_on_view(self):
        "Create a comment for an existing view"
        inmap = self.std_map()
        inmap['schema sd'].update({'view v1': {
            'columns': [{'today': {'type': 'date'}}],
            'definition': VIEW_DEFN, 'description': "Test view v1"}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        assert sql == [COMMENT_STMT]

    def test_drop_view_comment(self):
        "Drop the comment on an existing view"
        stmts = [CREATE_STMT, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema sd'].update({'view v1': {
            'columns': [{'today': {'type': 'date'}}],
            'definition': VIEW_DEFN}})
        sql = self.to_sql(inmap, stmts)
        assert sql == ["COMMENT ON VIEW sd.v1 IS NULL"]

    def test_change_view_comment(self):
        "Change existing comment on a view"
        stmts = [CREATE_STMT, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema sd'].update({'view v1': {
            'columns': [{'today': {'type': 'date'}}],
            'definition': VIEW_DEFN, 'description': "Changed view v1"}})
        sql = self.to_sql(inmap, stmts)
        assert sql == ["COMMENT ON VIEW sd.v1 IS 'Changed view v1'"]
