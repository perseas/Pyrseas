# -*- coding: utf-8 -*-
"""Test functions"""

import unittest

from pyrseas.testutils import PyrseasTestCase, fix_indent

SOURCE1 = "SELECT 'dummy'::text"
CREATE_STMT1 = "CREATE FUNCTION f1() RETURNS text LANGUAGE sql IMMUTABLE AS " \
    "$_$%s$_$" % SOURCE1
DROP_STMT1 = "DROP FUNCTION IF EXISTS f1()"

SOURCE2 = "SELECT GREATEST($1, $2)"
CREATE_STMT2 = "CREATE FUNCTION f1(integer, integer) RETURNS integer " \
    "LANGUAGE sql IMMUTABLE AS $_$%s$_$" % SOURCE2
DROP_STMT2 = "DROP FUNCTION IF EXISTS f1(integer, integer)"
COMMENT_STMT = "COMMENT ON FUNCTION f1(integer, integer) IS 'Test function f1'"

SOURCE3 = "SELECT * FROM generate_series($1, $2)"
CREATE_STMT3 = "CREATE FUNCTION f2(integer, integer) RETURNS SETOF integer ROWS 20" \
    "LANGUAGE sql IMMUTABLE AS $_$%s$_$" % SOURCE3


class FunctionToMapTestCase(PyrseasTestCase):
    """Test mapping of existing functions"""

    def test_map_function(self):
        "Map a very simple function with no arguments"
        expmap = {'language': 'sql', 'returns': 'text',
                  'source': SOURCE1, 'volatility': 'immutable'}
        dbmap = self.db.execute_and_map(CREATE_STMT1)
        self.assertEqual(dbmap['schema public']['function f1()'], expmap)

    def test_map_function_with_args(self):
        "Map a function with two arguments"
        expmap = {'language': 'sql', 'returns': 'integer', 'source': SOURCE2}
        dbmap = self.db.execute_and_map(
            "CREATE FUNCTION f1(integer, integer) RETURNS integer "
            "LANGUAGE sql AS $_$%s$_$" % SOURCE2)
        self.assertEqual(dbmap['schema public']
                         ['function f1(integer, integer)'], expmap)

    def test_map_void_function(self):
        "Map a function returning void"
        self.db.execute("CREATE TABLE t1 (c1 integer, c2 text)")
        expmap = {'language': 'sql', 'returns': 'void',
                  'source': "INSERT INTO t1 VALUES (1, 'dummy')"}
        dbmap = self.db.execute_and_map(
            "CREATE FUNCTION f1() RETURNS void LANGUAGE sql AS "
            "$_$INSERT INTO t1 VALUES (1, 'dummy')$_$")
        self.assertEqual(dbmap['schema public']['function f1()'], expmap)

    def test_map_setof_row_function(self):
        "Map a function returning a set of rows"
        self.db.execute("CREATE TABLE t1 (c1 integer, c2 text)")
        expmap = {'language': 'sql', 'returns': 'SETOF t1',
                  'source': "SELECT * FROM t1"}
        dbmap = self.db.execute_and_map(
            "CREATE FUNCTION f1() RETURNS SETOF t1 LANGUAGE sql AS "
            "$_$SELECT * FROM t1$_$")
        self.assertEqual(dbmap['schema public']['function f1()'], expmap)

    def test_map_security_definer_function(self):
        "Map a function that is SECURITY DEFINER"
        expmap = {'language': 'sql', 'returns': 'text',
                  'source': SOURCE1, 'security_definer': True}
        dbmap = self.db.execute_and_map("CREATE FUNCTION f1() RETURNS text "
                                        "LANGUAGE sql SECURITY DEFINER AS "
                                        "$_$%s$_$" % SOURCE1)
        self.assertEqual(dbmap['schema public']['function f1()'], expmap)

    def test_map_c_lang_function(self):
        "Map a dynamically loaded C language function"
        # NOTE 1: Needs contrib/spi module to be available
        # NOTE 2: Needs superuser privilege
        expmap = {'language': 'c', 'obj_file': '$libdir/autoinc',
                  'link_symbol': 'autoinc', 'returns': 'trigger'}
        dbmap = self.db.execute_and_map("CREATE FUNCTION autoinc() RETURNS "
                                        "trigger AS '$libdir/autoinc' "
                                        "LANGUAGE c")
        self.assertEqual(dbmap['schema public']['function autoinc()'], expmap)

    def test_map_function_comment(self):
        "Map a function comment"
        self.db.execute(CREATE_STMT2)
        dbmap = self.db.execute_and_map(COMMENT_STMT)
        self.assertEqual(dbmap['schema public']
                         ['function f1(integer, integer)']['description'],
                         'Test function f1')

    def test_map_function_rows(self):
        "Map a function rows"
        dbmap = self.db.execute_and_map(CREATE_STMT3)
        self.assertEqual(dbmap['schema public']
                         ['function f2(integer, integer)']['rows'],
                         20)


class FunctionToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input functions"""

    def test_create_function(self):
        "Create a very simple function with no arguments"
        self.db.execute_commit(DROP_STMT1)
        inmap = self.std_map()
        inmap['schema public'].update({'function f1()': {
                    'language': 'sql', 'returns': 'text',
                    'source': SOURCE1, 'volatility': 'immutable'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]), CREATE_STMT1)

    def test_create_function_with_args(self):
        "Create a function with two arguments"
        self.db.execute_commit(DROP_STMT2)
        inmap = self.std_map()
        inmap['schema public'].update({
                'function f1(integer, integer)': {
                    'language': 'sql', 'returns': 'integer',
                    'source': SOURCE2}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]),
                         "CREATE FUNCTION f1(integer, integer) RETURNS "
                         "integer LANGUAGE sql AS $_$%s$_$" % SOURCE2)

    def test_create_setof_row_function(self):
        "Create a function returning a set of rows"
        self.db.execute_commit(DROP_STMT1)
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}]}})
        inmap['schema public'].update({
                'function f1()': {
                    'language': 'sql', 'returns': 'SETOF t1',
                    'source': "SELECT * FROM t1"}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[2]),
                         "CREATE FUNCTION f1() RETURNS SETOF t1 LANGUAGE sql "
                         "AS $_$SELECT * FROM t1$_$")

    def test_create_setof_row_function_rows(self):
        "Create a function returning a set of rows with suggested number"
        self.db.execute_commit(DROP_STMT1)
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}]}})
        inmap['schema public'].update({
                'function f1()': {
                    'language': 'sql', 'returns': 'SETOF t1',
                    'source': "SELECT * FROM t1",
                    'rows': 50}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[2]),
                         "CREATE FUNCTION f1() RETURNS SETOF t1 "
                         "LANGUAGE sql ROWS 50 "
                         "AS $_$SELECT * FROM t1$_$")

    def test_create_security_definer_function(self):
        "Create a SECURITY DEFINER function"
        self.db.execute_commit(DROP_STMT1)
        inmap = self.std_map()
        inmap['schema public'].update({'function f1()': {
                    'language': 'sql', 'returns': 'text',
                    'source': SOURCE1, 'security_definer': True}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]),
                         "CREATE FUNCTION f1() RETURNS text LANGUAGE sql "
                         "SECURITY DEFINER AS $_$%s$_$" % SOURCE1)

    def test_create_c_lang_function(self):
        "Create a dynamically loaded C language function"
        # NOTE 1: Needs contrib/spi module to be available
        # NOTE 2: Needs superuser privilege
        self.db.execute_commit("DROP FUNCTION IF EXISTS autoinc()")
        inmap = self.std_map()
        inmap['schema public'].update({'function autoinc()': {
                    'language': 'c', 'returns': 'trigger',
                    'obj_file': '$libdir/autoinc'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]), "CREATE FUNCTION autoinc() "
                         "RETURNS trigger LANGUAGE c AS '$libdir/autoinc', "
                         "'autoinc'")

    def test_create_function_in_schema(self):
        "Create a function within a non-public schema"
        self.db.execute("CREATE SCHEMA s1")
        self.db.execute_commit(DROP_STMT1)
        inmap = self.std_map()
        inmap.update({'schema s1': {'function f1()': {
                    'language': 'sql', 'returns': 'text',
                    'source': SOURCE1, 'volatility': 'immutable'}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]), "CREATE FUNCTION s1.f1() "
                         "RETURNS text LANGUAGE sql IMMUTABLE "
                         "AS $_$%s$_$" % SOURCE1)
        self.db.execute_commit("DROP SCHEMA s1 CASCADE")

    def test_bad_function_map(self):
        "Error creating a function with a bad map"
        inmap = self.std_map()
        inmap['schema public'].update({'f1()': {
                    'language': 'sql', 'returns': 'text',
                    'source': SOURCE1}})
        self.assertRaises(KeyError, self.db.process_map, inmap)

    def test_drop_function(self):
        "Drop an existing function with no arguments"
        self.db.execute(DROP_STMT1)
        self.db.execute_commit(CREATE_STMT1)
        dbsql = self.db.process_map(self.std_map())
        self.assertEqual(dbsql, ["DROP FUNCTION f1()"])

    def test_drop_function_with_args(self):
        "Drop an existing function which has arguments"
        self.db.execute(DROP_STMT2)
        self.db.execute_commit(CREATE_STMT2)
        dbsql = self.db.process_map(self.std_map())
        self.assertEqual(dbsql[0], "DROP FUNCTION f1(integer, integer)")

    def test_change_function_defn(self):
        "Change function definition"
        self.db.execute(DROP_STMT1)
        self.db.execute_commit(CREATE_STMT1)
        inmap = self.std_map()
        inmap['schema public'].update({'function f1()': {
                    'language': 'sql', 'returns': 'text',
                    'source': "SELECT 'example'::text",
                    'volatility': 'immutable'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]), "CREATE OR REPLACE "
                         "FUNCTION f1() RETURNS text LANGUAGE sql IMMUTABLE "
                         "AS $_$SELECT 'example'::text$_$")

    def test_function_with_comment(self):
        "Create a function with a comment"
        self.db.execute_commit(DROP_STMT2)
        inmap = self.std_map()
        inmap['schema public'].update({
                'function f1(integer, integer)': {
                    'description': 'Test function f1',
                    'language': 'sql', 'returns': 'integer',
                    'source': SOURCE2}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]),
                         "CREATE FUNCTION f1(integer, integer) RETURNS "
                         "integer LANGUAGE sql AS $_$%s$_$" % SOURCE2)
        self.assertEqual(dbsql[2], COMMENT_STMT)

    def test_comment_on_function(self):
        "Create a comment for an existing function"
        self.db.execute(DROP_STMT2)
        self.db.execute_commit(CREATE_STMT2)
        inmap = self.std_map()
        inmap['schema public'].update({
                'function f1(integer, integer)': {
                    'description': 'Test function f1',
                    'language': 'sql', 'returns': 'integer',
                    'source': SOURCE2}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [COMMENT_STMT])

    def test_drop_function_comment(self):
        "Drop a comment on an existing function"
        self.db.execute(DROP_STMT2)
        self.db.execute(CREATE_STMT2)
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({
                'function f1(integer, integer)': {
                    'language': 'sql', 'returns': 'integer',
                    'source': SOURCE2}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql,
                         ["COMMENT ON FUNCTION f1(integer, integer) IS NULL"])

    def test_change_function_comment(self):
        "Change existing comment on a function"
        self.db.execute(DROP_STMT2)
        self.db.execute(CREATE_STMT2)
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({
                'function f1(integer, integer)': {
                    'description': 'Changed function f1',
                    'language': 'sql', 'returns': 'integer',
                    'source': SOURCE2}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [
                "COMMENT ON FUNCTION f1(integer, integer) IS "
                "'Changed function f1'"])


class AggregateToMapTestCase(PyrseasTestCase):
    """Test mapping of existing aggregates"""

    def test_map_aggregate(self):
        "Map a simple aggregate"
        self.db.execute(CREATE_STMT2)
        expmap = {'sfunc': 'f1(integer,integer)', 'stype': 'integer'}
        dbmap = self.db.execute_and_map("CREATE AGGREGATE a1 (integer) ("
                                        "SFUNC = f1, STYPE = integer)")
        self.assertEqual(dbmap['schema public'][
                'function f1(integer, integer)'], {
                'language': 'sql', 'returns': 'integer',
                'source': SOURCE2,
                'volatility': 'immutable'})
        self.assertEqual(dbmap['schema public'][
                'aggregate a1(integer)'], expmap)

    def test_map_aggregate_init_final(self):
        "Map an aggregate with an INITCOND and a FINALFUNC"
        self.db.execute(CREATE_STMT2)
        self.db.execute("CREATE FUNCTION f2(integer) RETURNS float "
                        "LANGUAGE sql AS $_$SELECT $1::float$_$ IMMUTABLE")
        expmap = {'sfunc': 'f1(integer,integer)', 'stype': 'integer',
                  'initcond': '-1', 'finalfunc': 'f2(integer)'}
        dbmap = self.db.execute_and_map(
            "CREATE AGGREGATE a1 (integer) (SFUNC = f1, STYPE = integer, "
            "FINALFUNC = f2, INITCOND = '-1')")
        self.assertEqual(dbmap['schema public'][
                'function f1(integer, integer)'], {
                'language': 'sql', 'returns': 'integer',
                'source': SOURCE2,
                'volatility': 'immutable'})
        self.assertEqual(dbmap['schema public']['function f2(integer)'],
                         {'language': 'sql', 'returns': 'double precision',
                          'source': "SELECT $1::float",
                          'volatility': 'immutable'})
        self.assertEqual(dbmap['schema public']['aggregate a1(integer)'],
                         expmap)

    def test_map_aggregate_sortop(self):
        "Map an aggregate with a SORTOP"
        self.db.execute(CREATE_STMT2)
        expmap = {'sfunc': 'f1(integer,integer)', 'stype': 'integer',
                  'sortop': 'pg_catalog.>'}
        dbmap = self.db.execute_and_map(
            "CREATE AGGREGATE a1 (integer) (SFUNC = f1, STYPE = integer, "
            "SORTOP = >)")
        self.assertEqual(dbmap['schema public']['aggregate a1(integer)'],
                         expmap)


class AggregateToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input aggregates"""

    def test_create_aggregate(self):
        "Create a simple aggregate"
        self.db.execute("DROP AGGREGATE IF EXISTS a1(integer)")
        self.db.execute_commit(DROP_STMT2)
        inmap = self.std_map()
        inmap['schema public'].update({'function f1(integer, integer)': {
                    'language': 'sql', 'returns': 'integer',
                    'source': SOURCE2,
                    'volatility': 'immutable'}})
        inmap['schema public'].update({'aggregate a1(integer)': {
                    'sfunc': 'f1', 'stype': 'integer'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]), CREATE_STMT2)
        self.assertEqual(fix_indent(dbsql[2]),
                         "CREATE AGGREGATE a1(integer) "
                         "(SFUNC = f1, STYPE = integer)")

    def test_create_aggregate_init_final(self):
        "Create an aggregate with an INITCOND and a FINALFUNC"
        self.db.execute("DROP AGGREGATE IF EXISTS a1(integer)")
        self.db.execute_commit("DROP FUNCTION IF EXISTS f2(integer)")
        self.db.execute_commit(DROP_STMT2)
        inmap = self.std_map()
        inmap['schema public'].update({'function f1(integer, integer)': {
                    'language': 'sql', 'returns': 'integer',
                    'source': SOURCE2,
                    'volatility': 'immutable'}})
        inmap['schema public'].update({'function f2(integer)': {
                    'language': 'sql', 'returns': 'double precision',
                    'source': "SELECT $1::float",
                    'volatility': 'immutable'}})
        inmap['schema public'].update({'aggregate a1(integer)': {
                    'sfunc': 'f1', 'stype': 'integer', 'initcond': '-1',
                    'finalfunc': 'f2(integer)'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]), CREATE_STMT2)
        self.assertEqual(fix_indent(dbsql[2]),
                         "CREATE FUNCTION f2(integer) "
                         "RETURNS double precision LANGUAGE sql IMMUTABLE "
                         "AS $_$SELECT $1::float$_$")
        self.assertEqual(fix_indent(dbsql[3]),
                         "CREATE AGGREGATE a1(integer) "
                         "(SFUNC = f1, STYPE = integer, FINALFUNC = f2, "
                         "INITCOND = '-1')")

    def test_drop_aggregate(self):
        "Drop an existing aggregate"
        self.db.execute(CREATE_STMT2)
        self.db.execute_commit("CREATE AGGREGATE agg1 (integer) "
                               "(SFUNC = f1, STYPE = integer)")
        inmap = self.std_map()
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql[0], "DROP AGGREGATE agg1(integer)")
        self.assertEqual(dbsql[1], "DROP FUNCTION f1(integer, integer)")


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(FunctionToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            FunctionToSqlTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            AggregateToMapTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            AggregateToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
