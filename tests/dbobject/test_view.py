# -*- coding: utf-8 -*-
"""Test views"""

import unittest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_STMT = "CREATE VIEW v1 AS SELECT now()::date AS today"
COMMENT_STMT = "COMMENT ON VIEW v1 IS 'Test view v1'"
VIEW_DEFN = " SELECT now()::date AS today;"


class ViewToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of created views"""

    def test_map_view_no_table(self):
        "Map a created view without a table dependency"
        dbmap = self.to_map([CREATE_STMT])
        expmap = {'definition': VIEW_DEFN}
        self.assertEqual(dbmap['schema public']['view v1'], expmap)

    def test_map_view(self):
        "Map a created view with a table dependency"
        stmts = ["CREATE TABLE t1 (c1 INTEGER, c2 TEXT, c3 INTEGER)",
                 "CREATE VIEW v1 AS SELECT c1, c3 * 2 FROM t1"]
        dbmap = self.to_map(stmts)
        expmap = {'definition': " SELECT t1.c1, t1.c3 * 2\n   FROM t1;"}
        self.assertEqual(dbmap['schema public']['view v1'], expmap)

    def test_map_view_comment(self):
        "Map a view with a comment"
        dbmap = self.to_map([CREATE_STMT, COMMENT_STMT])
        self.assertEqual(dbmap['schema public']['view v1']['description'],
                         'Test view v1')


class ViewToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input views"""

    def test_create_view_no_table(self):
        "Create a view with no table dependency"
        inmap = self.std_map()
        inmap['schema public'].update({'view v1': {'definition': VIEW_DEFN}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), CREATE_STMT)

    def test_create_view(self):
        "Create a view"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'integer'}}]}})
        inmap['schema public'].update({'view v1': {
                    'definition': "SELECT c1, c3 * 2 FROM t1"}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), "CREATE TABLE t1 (c1 integer, "
                         "c2 text, c3 integer)")
        self.assertEqual(fix_indent(sql[1]), "CREATE VIEW v1 AS "
                         "SELECT c1, c3 * 2 FROM t1")

    def test_create_view_in_schema(self):
        "Create a view within a non-public schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {'view v1': {'definition': VIEW_DEFN}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        self.assertEqual(fix_indent(sql[0]), "CREATE VIEW s1.v1 AS "
                         "SELECT now()::date AS today")

    def test_bad_view_map(self):
        "Error creating a view with a bad map"
        inmap = self.std_map()
        inmap['schema public'].update({'v1': {'definition': VIEW_DEFN}})
        self.assertRaises(KeyError, self.to_sql, inmap)

    def test_drop_view_no_table(self):
        "Drop an existing view without a table dependency"
        sql = self.to_sql(self.std_map(), [CREATE_STMT])
        self.assertEqual(sql, ["DROP VIEW v1"])

    def test_drop_view(self):
        "Drop an existing view with table dependencies"
        stmts = ["CREATE TABLE t1 (c1 INTEGER, c2 TEXT)",
                 "CREATE TABLE t2 (c1 INTEGER, c3 TEXT)",
                 "CREATE VIEW v1 AS SELECT t1.c1, c2, c3 "
                 "FROM t1 JOIN t2 ON (t1.c1 = t2.c1)"]
        sql = self.to_sql(self.std_map(), stmts)
        self.assertEqual(sql[0], "DROP VIEW v1")
        # can't control which table will be dropped first
        drt1 = 1
        drt2 = 2
        if 't1' in sql[2]:
            drt1 = 2
            drt2 = 1
        self.assertEqual(sql[drt1], "DROP TABLE t1")
        self.assertEqual(sql[drt2], "DROP TABLE t2")

    def test_rename_view(self):
        "Rename an existing view"
        inmap = self.std_map()
        inmap['schema public'].update({'view v2': {
                    'oldname': 'v1', 'definition': VIEW_DEFN}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        self.assertEqual(sql, ["ALTER VIEW v1 RENAME TO v2"])

    def test_bad_rename_view(self):
        "Error renaming a non-existing view"
        inmap = self.std_map()
        inmap['schema public'].update({'view v2': {
                    'oldname': 'v3', 'definition': VIEW_DEFN}})
        self.assertRaises(KeyError, self.to_sql, inmap, [CREATE_STMT])

    def test_change_view_defn(self):
        "Change view definition"
        inmap = self.std_map()
        inmap['schema public'].update({'view v1': {
                    'definition': " SELECT now()::date AS todays_date;"}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        self.assertEqual(fix_indent(sql[0]), "CREATE OR REPLACE VIEW v1 AS "
                         "SELECT now()::date AS todays_date")

    def test_view_with_comment(self):
        "Create a view with a comment"
        inmap = self.std_map()
        inmap['schema public'].update({'view v1': {
                    'definition': VIEW_DEFN, 'description': "Test view v1"}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), CREATE_STMT)
        self.assertEqual(sql[1], COMMENT_STMT)

    def test_comment_on_view(self):
        "Create a comment for an existing view"
        inmap = self.std_map()
        inmap['schema public'].update({'view v1': {
                    'definition': VIEW_DEFN, 'description': "Test view v1"}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        self.assertEqual(sql, [COMMENT_STMT])

    def test_drop_view_comment(self):
        "Drop the comment on an existing view"
        stmts = [CREATE_STMT, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema public'].update({'view v1': {'definition': VIEW_DEFN}})
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(sql, ["COMMENT ON VIEW v1 IS NULL"])

    def test_change_view_comment(self):
        "Change existing comment on a view"
        stmts = [CREATE_STMT, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema public'].update({'view v1': {
                    'definition': VIEW_DEFN,
                    'description': "Changed view v1"}})
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(sql, ["COMMENT ON VIEW v1 IS 'Changed view v1'"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(ViewToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            ViewToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
