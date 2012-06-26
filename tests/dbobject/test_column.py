# -*- coding: utf-8 -*-
"""Test columns"""

import unittest

from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_STMT1 = "CREATE TABLE t1 (c1 integer, c2 text)"
CREATE_STMT2 = "CREATE TABLE t1 (c1 integer, c2 text, c3 date)"
CREATE_STMT3 = "CREATE TABLE t1 (c1 integer, c2 text, c3 date, c4 text)"
DROP_COL_STMT = "ALTER TABLE t1 DROP COLUMN c3"


class ColumnToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation of column-related statements from input schemas"""

    def test_set_column_not_null(self):
        "Change a nullable column to NOT NULL"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                'columns': [{'c1': {'type': 'integer', 'not_null': True}},
                            {'c2': {'type': 'text'}}]}})
        sql = self.to_sql(inmap, [CREATE_STMT1])
        self.assertEqual(fix_indent(sql[0]),
                         "ALTER TABLE t1 ALTER COLUMN c1 SET NOT NULL")

    def test_change_column_types(self):
        "Change the datatypes of two columns"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'bigint'}},
                                {'c2': {'type': 'varchar(25)'}}]}})
        sql = self.to_sql(inmap, [CREATE_STMT1])
        self.assertEqual(fix_indent(sql[0]),
                         "ALTER TABLE t1 ALTER COLUMN c1 TYPE bigint")
        self.assertEqual(fix_indent(sql[1]),
                         "ALTER TABLE t1 ALTER COLUMN c2 TYPE varchar(25)")

    def test_add_column1(self):
        "Add new column to a table"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'date'}},
                                {'c4': {'type': 'text'}}]}})
        sql = self.to_sql(inmap, [CREATE_STMT2])
        self.assertEqual(fix_indent(sql[0]),
                         "ALTER TABLE t1 ADD COLUMN c4 text")

    def test_add_column2(self):
        "Add column to a table that has a dropped column"
        stmts = [CREATE_STMT2, "ALTER TABLE t1 DROP COLUMN c2"]
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'date'}}]}})
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(len(sql), 1)
        self.assertEqual(fix_indent(sql[0]),
                         "ALTER TABLE t1 ADD COLUMN c2 text")

    def test_add_column3(self):
        "No change on a table that has a dropped column"
        stmts = [CREATE_STMT3, DROP_COL_STMT]
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c4': {'type': 'text'}}]}})
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(len(sql), 0)

    def test_add_column4(self):
        "Add two columns to a table that has a dropped column"
        stmts = [CREATE_STMT2, DROP_COL_STMT]
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'date'}},
                                {'c4': {'type': 'text'}}]}})
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(fix_indent(sql[0]),
                         "ALTER TABLE t1 ADD COLUMN c3 date")
        self.assertEqual(fix_indent(sql[1]),
                         "ALTER TABLE t1 ADD COLUMN c4 text")

    def test_drop_column1(self):
        "Drop a column from the end of a table"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'date'}}]}})
        sql = self.to_sql(inmap, [CREATE_STMT3])
        self.assertEqual(fix_indent(sql[0]), "ALTER TABLE t1 DROP COLUMN c4")

    def test_drop_column2(self):
        "Drop a column from the middle of a table"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c4': {'type': 'text'}}]}})
        sql = self.to_sql(inmap, [CREATE_STMT3])
        self.assertEqual(fix_indent(sql[0]), "ALTER TABLE t1 DROP COLUMN c3")

    def test_drop_column3(self):
        "Drop a column from the beginning of a table"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c2': {'type': 'text'}},
                                {'c3': {'type': 'date'}},
                                {'c4': {'type': 'text'}}]}})
        sql = self.to_sql(inmap, [CREATE_STMT3])
        self.assertEqual(fix_indent(sql[0]), "ALTER TABLE t1 DROP COLUMN c1")

    def test_rename_column(self):
        "Rename a table column"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c3': {'type': 'text', 'oldname': 'c2'}}]}})
        sql = self.to_sql(inmap, [CREATE_STMT1])
        self.assertEqual(sql[0], "ALTER TABLE t1 RENAME COLUMN c2 TO c3")

    def test_drop_add_column1(self):
        "Drop and re-add table column from the end, almost like a RENAME"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c4': {'type': 'date'}}]}})
        sql = self.to_sql(inmap, [CREATE_STMT2])
        self.assertEqual(fix_indent(sql[0]),
                         "ALTER TABLE t1 ADD COLUMN c4 date")
        self.assertEqual(sql[1], "ALTER TABLE t1 DROP COLUMN c3")

    def test_drop_add_column2(self):
        "Drop and re-add table column from the beginning"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c2': {'type': 'text'}},
                                {'c3': {'type': 'date'}},
                                {'c4': {'type': 'text'}}]}})
        sql = self.to_sql(inmap, [CREATE_STMT2])
        self.assertEqual(fix_indent(sql[0]),
                         "ALTER TABLE t1 ADD COLUMN c4 text")
        self.assertEqual(sql[1], "ALTER TABLE t1 DROP COLUMN c1")

    def test_drop_add_column3(self):
        "Drop and re-add table columns from table with dropped column"
        stmts = [CREATE_STMT2, DROP_COL_STMT]
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c2': {'type': 'text'}},
                                {'c3': {'type': 'date'}},
                                {'c4': {'type': 'text'}}]}})
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(fix_indent(sql[0]),
                         "ALTER TABLE t1 ADD COLUMN c3 date")
        self.assertEqual(fix_indent(sql[1]),
                         "ALTER TABLE t1 ADD COLUMN c4 text")
        self.assertEqual(sql[2], "ALTER TABLE t1 DROP COLUMN c1")

    def test_drop_column_in_schema(self):
        "Drop a column from a table in a non-public schema"
        stmts = ["CREATE SCHEMA s1",
                 "CREATE TABLE s1.t1 (c1 integer, c2 text, c3 date)"]
        inmap = self.std_map()
        inmap.update({'schema s1': {'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}]}}})
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(fix_indent(sql[0]),
                         "ALTER TABLE s1.t1 DROP COLUMN c3")


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(ColumnToSqlTestCase)
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
