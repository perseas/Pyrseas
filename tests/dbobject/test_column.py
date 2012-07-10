# -*- coding: utf-8 -*-
"""Test columns"""

import unittest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

TYPELIST = [
    ('SMALLINT', 'smallint'),
    ('INTEGER', 'integer'),
    ('BIGINT', 'bigint'),
    ('int', 'integer'),
    ('int2', 'smallint'),
    ('int4', 'integer'),
    ('int8', 'bigint'),
    ('NUMERIC', 'numeric'),
    ('NUMERIC(1)', 'numeric(1,0)'),
    ('NUMERIC(12)', 'numeric(12,0)'),
    ('NUMERIC(1000)', 'numeric(1000,0)'),
    ('NUMERIC(12,2)', 'numeric(12,2)'),
    ('NUMERIC(1000,500)', 'numeric(1000,500)'),
    ('DECIMAL', 'numeric'),
    ('dec(9,5)', 'numeric(9,5)'),
    ('REAL', 'real'),
    ('DOUBLE PRECISION', 'double precision'),
    ('FLOAT', 'double precision'),
    ('FLOAT(1)', 'real'),
    ('FLOAT(24)', 'real'),
    ('FLOAT(25)', 'double precision'),
    ('FLOAT(53)', 'double precision'),
    # SERIAL and BIGSERIAL have side effects
    ('MONEY', 'money'),
    ('CHARACTER(1)', 'character(1)'),
    ('CHARACTER VARYING(200000)', 'character varying(200000)'),
    ('CHAR(16)', 'character(16)'),
    ('VARCHAR(256)', 'character varying(256)'),
    ('TEXT', 'text'),
    ('CHAR', 'character(1)'),
    ('CHARACTER VARYING', 'character varying'),
    ('"char"', '"char"'),
    ('name', 'name'),
    ('bytea', 'bytea'),
    ('DATE', 'date'),
    ('TIME', 'time without time zone'),
    ('TIME WITHOUT TIME ZONE', 'time without time zone'),
    ('TIME WITH TIME ZONE', 'time with time zone'),
    ('TIMESTAMP', 'timestamp without time zone'),
    ('TIMESTAMP WITHOUT TIME ZONE', 'timestamp without time zone'),
    ('TIMESTAMP WITH TIME ZONE', 'timestamp with time zone'),
    ('TIME(0)', 'time(0) without time zone'),
    ('TIME(1) WITHOUT TIME ZONE', 'time(1) without time zone'),
    ('TIME(2) WITH TIME ZONE', 'time(2) with time zone'),
    ('TIMESTAMP(3)', 'timestamp(3) without time zone'),
    ('TIMESTAMP(4) WITHOUT TIME ZONE', 'timestamp(4) without time zone'),
    ('TIMESTAMP(5) WITH TIME ZONE', 'timestamp(5) with time zone'),
    ('INTERVAL', 'interval'),
    ('INTERVAL(6)', 'interval(6)'),
    ('INTERVAL YEAR', 'interval year'),
    ('INTERVAL MONTH', 'interval month'),
    ('INTERVAL DAY', 'interval day'),
    ('INTERVAL HOUR', 'interval hour'),
    ('INTERVAL MINUTE', 'interval minute'),
    ('INTERVAL SECOND', 'interval second'),
    ('INTERVAL YEAR TO MONTH', 'interval year to month'),
    ('INTERVAL DAY TO HOUR', 'interval day to hour'),
    ('INTERVAL DAY TO MINUTE', 'interval day to minute'),
    ('INTERVAL DAY TO SECOND', 'interval day to second'),
    ('INTERVAL HOUR TO MINUTE', 'interval hour to minute'),
    ('INTERVAL HOUR TO SECOND', 'interval hour to second'),
    ('INTERVAL MINUTE TO SECOND', 'interval minute to second'),
    ('INTERVAL SECOND(3)', 'interval second(3)'),
    ('INTERVAL HOUR TO SECOND(5)', 'interval hour to second(5)'),
    ('BOOLEAN', 'boolean'),
    ('POINT', 'point'),
    ('LINE', 'line'),
    ('LSEG', 'lseg'),
    ('BOX', 'box'),
    ('PATH', 'path'),
    ('POLYGON', 'polygon'),
    ('CIRCLE', 'circle'),
    ('cidr', 'cidr'),
    ('inet', 'inet'),
    ('macaddr', 'macaddr'),
    ('BIT(2)', 'bit(2)'),
    ('BIT VARYING(100)', 'bit varying(100)'),
    ('BIT', 'bit(1)'),
    ('BIT VARYING', 'bit varying'),
    ('tsvector', 'tsvector'),
    ('tsquery', 'tsquery'),
    ('UUID', 'uuid'),
    ('XML', 'xml')]

CREATE_STMT1 = "CREATE TABLE t1 (c1 integer, c2 text)"
CREATE_STMT2 = "CREATE TABLE t1 (c1 integer, c2 text, c3 date)"
CREATE_STMT3 = "CREATE TABLE t1 (c1 integer, c2 text, c3 date, c4 text)"
DROP_COL_STMT = "ALTER TABLE t1 DROP COLUMN c3"


class ColumnToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of column-related elements in created tables"""

    def test_data_types(self):
        "Map a table with columns for (almost) each native PostgreSQL type"
        colstab = []
        colsmap = []
        for colnum, (coltype, maptype) in enumerate(TYPELIST):
            col = "c%d" % (colnum + 1)
            colstab.append("%s %s" % (col, coltype))
            colsmap.append({col: {'type': maptype}})
        dbmap = self.to_map(["CREATE TABLE t1 (%s)" % ", ".join(colstab)])
        expmap = {'columns': colsmap}
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_not_null(self):
        "Map a table with a NOT NULL column"
        stmts = ["CREATE TABLE t1 (c1 INTEGER, c2 INTEGER NULL, "
                 "c3 INTEGER NOT NULL)"]
        dbmap = self.to_map(stmts)
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'integer'}},
                              {'c3': {'type': 'integer', 'not_null': True}}]}

        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_column_defaults(self):
        "Map a table with various types and each with a DEFAULT clause"
        stmts = ["CREATE TABLE t1 (c1 INTEGER DEFAULT 12345, "
                 "c2 NUMERIC DEFAULT 98.76, c3 REAL DEFAULT 15e-2, "
                 "c4 TEXT DEFAULT 'Abc def', c5 DATE DEFAULT CURRENT_DATE, "
                 "c6 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, "
                 "c7 BOOLEAN DEFAULT FALSE)"]
        dbmap = self.to_map(stmts)
        expmap = {'columns': [
                    {'c1': {'type': 'integer', 'default': '12345'}},
                    {'c2': {'type': 'numeric', 'default': '98.76'}},
                    {'c3': {'type': 'real', 'default': '0.15'}},
                    {'c4': {'type': 'text', 'default': "'Abc def'::text"}},
                    {'c5': {'type': 'date', 'default': "('now'::text)::date"}},
                    {'c6': {'type': 'timestamp with time zone',
                            'default': 'now()'}},
                    {'c7': {'type': 'boolean', 'default': 'false'}}]}
        self.assertEqual(dbmap['schema public']['table t1'], expmap)


class ColumnToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation of column-related statements from input schemas"""

    def test_create_table_with_defaults(self):
        "Create a table with two column DEFAULTs, one referring to a SEQUENCE"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {
                                'type': 'integer',
                                'not_null': True,
                                'default': "nextval('t1_c1_seq'::regclass)"}},
                                {'c2': {'type': 'text', 'not_null': True}},
                                {'c3': {
                                'type': 'date', 'not_null': True,
                                'default': "('now'::text)::date"}}]},
                                       'sequence t1_c1_seq': {
                    'cache_value': 1, 'increment_by': 1, 'max_value': None,
                    'min_value': None, 'start_value': 1}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]),
                         "CREATE TABLE t1 (c1 integer NOT NULL, "
                         "c2 text NOT NULL, "
                         "c3 date NOT NULL DEFAULT ('now'::text)::date)")
        self.assertEqual(fix_indent(sql[1]),
                         "CREATE SEQUENCE t1_c1_seq START WITH 1 "
                         "INCREMENT BY 1 NO MAXVALUE NO MINVALUE CACHE 1")
        self.assertEqual(sql[2], "ALTER TABLE t1 ALTER COLUMN c1 "
                         "SET DEFAULT nextval('t1_c1_seq'::regclass)")

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

    def test_inherit_add_parent_column(self):
        "Add a column to parent table, child should not add as well"
        stmts = [CREATE_STMT1, "CREATE TABLE t2 (c3 date) INHERITS (t1)"]
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c4': {'type': 'text'}}]}})
        inmap['schema public'].update({'table t2': {
                    'columns': [{'c1': {'type': 'integer', 'inherited': True}},
                                {'c2': {'type': 'text', 'inherited': True}},
                                {'c3': {'type': 'date'}},
                                {'c4': {'type': 'text', 'inherited': True}}],
                    'inherits': ['t1']}})
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(len(sql), 1)
        self.assertEqual(fix_indent(sql[0]), "ALTER TABLE t1 ADD COLUMN "
                         "c4 text")

    def test_inherit_drop_parent_column(self):
        "Drop a column from a parent table, child should not drop as well"
        stmts = [CREATE_STMT1, "CREATE TABLE t2 (c3 date) INHERITS (t1)"]
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}}]}})
        inmap['schema public'].update({'table t2': {
                    'columns': [{'c1': {'type': 'integer', 'inherited': True}},
                                {'c3': {'type': 'date'}}],
                    'inherits': ['t1']}})
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(len(sql), 1)
        self.assertEqual(fix_indent(sql[0]), "ALTER TABLE t1 DROP COLUMN c2")


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(ColumnToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            ColumnToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
