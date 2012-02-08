# -*- coding: utf-8 -*-
"""Test tables"""

import unittest

from pyrseas.testutils import PyrseasTestCase, fix_indent


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

CREATE_STMT = "CREATE TABLE t1 (c1 integer, c2 text)"
COMMENT_STMT = "COMMENT ON TABLE t1 IS 'Test table t1'"


class TableToMapTestCase(PyrseasTestCase):
    """Test mapping of created tables"""

    def test_create_table(self):
        "Map a table with two columns"
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}}]}
        dbmap = self.db.execute_and_map(CREATE_STMT)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_data_types(self):
        "Map a table with columns for (almost) each native PostgreSQL type"
        colstab = []
        colsmap = []
        for colnum, (coltype, maptype) in enumerate(TYPELIST):
            col = "c%d" % (colnum + 1)
            colstab.append("%s %s" % (col, coltype))
            colsmap.append({col: {'type': maptype}})
        ddlstmt = "CREATE TABLE t1 (%s)" % ", ".join(colstab)
        expmap = {'columns': colsmap}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_not_null(self):
        "Map a table with a NOT NULL column"
        ddlstmt = """CREATE TABLE t1 (c1 INTEGER, c2 INTEGER NULL,
                                      c3 INTEGER NOT NULL)"""
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'integer'}},
                              {'c3': {'type': 'integer', 'not_null': True}}]}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_column_defaults(self):
        "Map a table with various types and each with a DEFAULT clause"
        ddlstmt = """CREATE TABLE t1 (c1 INTEGER DEFAULT 12345,
                                      c2 NUMERIC DEFAULT 98.76,
                                      c3 REAL DEFAULT 15e-2,
                                      c4 TEXT DEFAULT 'Abc def',
                                      c5 DATE DEFAULT CURRENT_DATE,
                                      c6 TIMESTAMP WITH TIME ZONE
                                         DEFAULT CURRENT_TIMESTAMP,
                                      c7 BOOLEAN DEFAULT FALSE)"""
        expmap = {'columns': [
                    {'c1': {'type': 'integer', 'default': '12345'}},
                    {'c2': {'type': 'numeric', 'default': '98.76'}},
                    {'c3': {'type': 'real', 'default': '0.15'}},
                    {'c4': {'type': 'text', 'default': "'Abc def'::text"}},
                    {'c5': {'type': 'date', 'default': "('now'::text)::date"}},
                    {'c6': {'type': 'timestamp with time zone',
                            'default': 'now()'}},
                    {'c7': {'type': 'boolean', 'default': 'false'}}]}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_map_table_comment(self):
        "Map a table comment"
        self.db.execute(CREATE_STMT)
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}}],
                  'description': 'Test table t1'}
        dbmap = self.db.execute_and_map(COMMENT_STMT)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_map_table_comment_quotes(self):
        "Map a table comment with quotes"
        self.db.execute(CREATE_STMT)
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}}],
                  'description': "A \"special\" person's table t1"}
        dbmap = self.db.execute_and_map("COMMENT ON TABLE t1 IS "
                                        "'A \"special\" person''s table t1'")
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_map_column_comments(self):
        "Map two column comments"
        self.db.execute(CREATE_STMT)
        self.db.execute("COMMENT ON COLUMN t1.c1 IS 'Test column c1 of t1'")
        ddlstmt = "COMMENT ON COLUMN t1.c2 IS 'Test column c2 of t1'"
        expmap = {'columns': [{'c1': {'type': 'integer', 'description':
                                          'Test column c1 of t1'}},
                              {'c2': {'type': 'text', 'description':
                                          'Test column c2 of t1'}}]}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_map_inherit(self):
        "Map a table that inherits from two other tables"
        self.db.execute(CREATE_STMT)
        self.db.execute("CREATE TABLE t2 (c3 integer)")
        ddlstmt = "CREATE TABLE t3 (c4 text) INHERITS (t1, t2)"
        expmap = {'columns': [{'c1': {'type': 'integer', 'inherited': True}},
                              {'c2': {'type': 'text', 'inherited': True}},
                              {'c3': {'type': 'integer', 'inherited': True}},
                              {'c4': {'type': 'text'}}],
                  'inherits': ['t1', 't2']}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t3'], expmap)


class TableToSqlTestCase(PyrseasTestCase):
    """Test SQL generation of table statements from input schemas"""

    def test_create_table(self):
        "Create a two-column table"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                               {'c2': {'type': 'text'}}]}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_STMT)

    def test_create_table_with_defaults(self):
        "Create a table with two column DEFAULTs, one referring to a SEQUENCE"
        self.db.execute_commit("DROP SEQUENCE IF EXISTS t1_c1_seq")
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
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "CREATE TABLE t1 (c1 integer NOT NULL, "
                         "c2 text NOT NULL, "
                         "c3 date NOT NULL DEFAULT ('now'::text)::date)")
        self.assertEqual(fix_indent(dbsql[1]),
                         "CREATE SEQUENCE t1_c1_seq START WITH 1 "
                         "INCREMENT BY 1 NO MAXVALUE NO MINVALUE CACHE 1")
        self.assertEqual(dbsql[2], "ALTER TABLE t1 ALTER COLUMN c1 "
                         "SET DEFAULT nextval('t1_c1_seq'::regclass)")

    def test_bad_table_map(self):
        "Error creating a table with a bad map"
        inmap = self.std_map()
        inmap['schema public'].update({'t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}]}})
        self.assertRaises(KeyError, self.db.process_map, inmap)

    def test_missing_columns(self):
        "Error creating a table with no columns"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {'columns': []}})
        self.assertRaises(ValueError, self.db.process_map, inmap)

    def test_drop_table(self):
        "Drop an existing table"
        self.db.execute_commit(CREATE_STMT)
        inmap = self.std_map()
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["DROP TABLE t1"])

    def test_rename_table(self):
        "Rename an existing table"
        self.db.execute_commit(CREATE_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'table t2': {
                    'oldname': 't1',
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}]}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["ALTER TABLE t1 RENAME TO t2"])


class TableCommentToSqlTestCase(PyrseasTestCase):
    """Test SQL generation of table and column COMMENT statements"""

    def _tblmap(self):
        "Return a table input map with a comment"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'description': 'Test table t1',
                    'columns': [{'c1': {'type': 'integer'}},
                               {'c2': {'type': 'text'}}]}})
        return inmap

    def test_table_with_comment(self):
        "Create a table with a comment"
        dbsql = self.db.process_map(self._tblmap())
        self.assertEqual(fix_indent(dbsql[0]), CREATE_STMT)
        self.assertEqual(dbsql[1], COMMENT_STMT)

    def test_comment_on_table(self):
        "Create a comment for an existing table"
        self.db.execute_commit(CREATE_STMT)
        dbsql = self.db.process_map(self._tblmap())
        self.assertEqual(dbsql, [COMMENT_STMT])

    def test_table_comment_quotes(self):
        "Create a table comment with quotes"
        self.db.execute_commit(CREATE_STMT)
        inmap = self._tblmap()
        inmap['schema public']['table t1']['description'] = \
            "A \"special\" person's table t1"
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["COMMENT ON TABLE t1 IS "
                                 "'A \"special\" person''s table t1'"])

    def test_drop_table_comment(self):
        "Drop a comment on an existing table"
        self.db.execute(CREATE_STMT)
        self.db.execute_commit(COMMENT_STMT)
        inmap = self._tblmap()
        del inmap['schema public']['table t1']['description']
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["COMMENT ON TABLE t1 IS NULL"])

    def test_change_table_comment(self):
        "Change existing comment on a table"
        self.db.execute(CREATE_STMT)
        self.db.execute_commit(COMMENT_STMT)
        inmap = self._tblmap()
        inmap['schema public']['table t1'].update(
            {'description': 'Changed table t1'})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["COMMENT ON TABLE t1 IS 'Changed table t1'"])

    def test_create_column_comments(self):
        "Create a table with column comments"
        inmap = self._tblmap()
        inmap['schema public']['table t1']['columns'][0]['c1'].update(
            description='Test column c1')
        inmap['schema public']['table t1']['columns'][1]['c2'].update(
            description='Test column c2')
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_STMT)
        self.assertEqual(dbsql[1], COMMENT_STMT)
        self.assertEqual(dbsql[2],
                         "COMMENT ON COLUMN t1.c1 IS 'Test column c1'")
        self.assertEqual(dbsql[3],
                         "COMMENT ON COLUMN t1.c2 IS 'Test column c2'")

    def test_add_column_comment(self):
        "Add a column comment to an existing table"
        inmap = self._tblmap()
        inmap['schema public']['table t1']['columns'][0]['c1'].update(
            description='Test column c1')
        self.db.execute(CREATE_STMT)
        self.db.execute_commit(COMMENT_STMT)
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql[0],
                         "COMMENT ON COLUMN t1.c1 IS 'Test column c1'")

    def test_add_column_with_comment(self):
        "Add a commented column to an existing table"
        inmap = self._tblmap()
        inmap['schema public']['table t1']['columns'].append({'c3': {
            'description': 'Test column c3', 'type': 'integer'}})
        self.db.execute(CREATE_STMT)
        self.db.execute_commit(COMMENT_STMT)
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "ALTER TABLE t1 ADD COLUMN c3 integer")
        self.assertEqual(dbsql[1],
                         "COMMENT ON COLUMN t1.c3 IS 'Test column c3'")

    def test_drop_column_comment(self):
        "Drop a column comment on an existing table"
        inmap = self._tblmap()
        self.db.execute(CREATE_STMT)
        self.db.execute(COMMENT_STMT)
        self.db.execute_commit("COMMENT ON COLUMN t1.c1 IS 'Test column c1'")
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql[0],
                         "COMMENT ON COLUMN t1.c1 IS NULL")

    def test_change_column_comment(self):
        "Add a column comment to an existing table"
        inmap = self._tblmap()
        inmap['schema public']['table t1']['columns'][0]['c1'].update(
            description='Changed column c1')
        self.db.execute(CREATE_STMT)
        self.db.execute_commit(COMMENT_STMT)
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql[0],
                         "COMMENT ON COLUMN t1.c1 IS 'Changed column c1'")


class TableInheritToSqlTestCase(PyrseasTestCase):
    """Test SQL generation of table inheritance statements"""

    def test_table_inheritance(self):
        "Create a table that inherits from another"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                               {'c2': {'type': 'text'}}]}})
        inmap['schema public'].update({'table t2': {
                    'columns': [{'c1': {'type': 'integer', 'inherited': True}},
                                {'c2': {'type': 'text', 'inherited': True}},
                                {'c3': {'type': 'numeric'}}],
                    'inherits': ['t1']}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_STMT)
        self.assertEqual(fix_indent(dbsql[1]), "CREATE TABLE t2 (c3 numeric) "
                         "INHERITS (t1)")

    def test_drop_inherited(self):
        "Drop tables that inherit from others"
        self.db.execute(CREATE_STMT)
        self.db.execute("CREATE TABLE t2 (c3 numeric) INHERITS (t1)")
        self.db.execute_commit("CREATE TABLE t3 (c4 date) INHERITS (t2)")
        inmap = self.std_map()
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["DROP TABLE t3", "DROP TABLE t2",
                                 "DROP TABLE t1"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(TableToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            TableToSqlTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            TableCommentToSqlTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            TableInheritToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
