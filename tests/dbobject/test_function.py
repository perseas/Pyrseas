# -*- coding: utf-8 -*-
"""Test functions"""

import unittest

from utils import PyrseasTestCase, fix_indent, new_std_map

CREATE_STMT1 = "CREATE FUNCTION f1() RETURNS text LANGUAGE sql AS " \
    "$_$SELECT 'dummy'::text$_$ IMMUTABLE"
DROP_STMT1 = "DROP FUNCTION IF EXISTS f1()"
CREATE_STMT2 = "CREATE FUNCTION f1(integer, integer) RETURNS integer " \
    "LANGUAGE sql AS $_$SELECT $1 + $2$_$"
DROP_STMT2 = "DROP FUNCTION IF EXISTS f1(integer, integer)"
COMMENT_STMT = "COMMENT ON FUNCTION f1(integer, integer) IS 'Test function f1'"


class FunctionToMapTestCase(PyrseasTestCase):
    """Test mapping of existing functions"""

    def test_map_function(self):
        "Map a very simple function with no arguments"
        expmap = {'language': 'sql', 'returns': 'text',
                  'source': "SELECT 'dummy'::text", 'volatility': 'immutable'}
        dbmap = self.db.execute_and_map(CREATE_STMT1)
        self.assertEqual(dbmap['schema public']['function f1()'], expmap)

    def test_map_function_with_args(self):
        "Map a function with two arguments"
        expmap = {'language': 'sql', 'returns': 'integer',
                  'arguments': 'integer, integer',
                  'source': "SELECT $1 + $2"}
        dbmap = self.db.execute_and_map(CREATE_STMT2)
        self.assertEqual(dbmap['schema public'] \
                             ['function f1(integer, integer)'], expmap)

    def test_map_function_comment(self):
        "Map a function comment"
        self.db.execute(DROP_STMT2)
        self.db.execute(CREATE_STMT2)
        dbmap = self.db.execute_and_map(COMMENT_STMT)
        self.assertEqual(dbmap['schema public'] \
                             ['function f1(integer, integer)']['description'],
                         'Test function f1')


class FunctionToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input functions"""

    def test_create_function(self):
        "Create a very simple function with no arguments"
        self.db.execute_commit(DROP_STMT1)
        inmap = new_std_map()
        inmap['schema public'].update({'function f1()': {
                    'language': 'sql', 'returns': 'text',
                    'source': "SELECT 'dummy'::text",
                    'volatility': 'immutable'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_STMT1)

    def test_create_function_with_args(self):
        "Create a function with two arguments"
        self.db.execute_commit(DROP_STMT2)
        inmap = new_std_map()
        inmap['schema public'].update({
                'function f1(integer, integer)': {
                    'language': 'sql', 'returns': 'integer',
                    'source': "SELECT $1 + $2"}})
        dbsql = self.db.process_map(inmap)

    def test_create_function_in_schema(self):
        "Create a function within a non-public schema"
        self.db.execute("CREATE SCHEMA s1")
        self.db.execute_commit(DROP_STMT1)
        inmap = new_std_map()
        inmap.update({'schema s1': {'function f1()': {
                    'language': 'sql', 'returns': 'text',
                    'source': "SELECT 'dummy'::text",
                    'volatility': 'immutable'}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), "CREATE FUNCTION s1.f1() "
                         "RETURNS text LANGUAGE sql "
                         "AS $_$SELECT 'dummy'::text$_$ IMMUTABLE")
        self.db.execute_commit("DROP SCHEMA s1 CASCADE")

    def test_bad_function_map(self):
        "Error creating a function with a bad map"
        inmap = new_std_map()
        inmap['schema public'].update({'f1()': {
                    'language': 'sql', 'returns': 'text',
                    'source': "SELECT 'dummy'::text"}})
        self.assertRaises(KeyError, self.db.process_map, inmap)

    def test_drop_function(self):
        "Drop an existing function with no arguments"
        self.db.execute(DROP_STMT1)
        self.db.execute_commit(CREATE_STMT1)
        dbsql = self.db.process_map(new_std_map())
        self.assertEqual(dbsql, ["DROP FUNCTION f1()"])

    def test_drop_function_with_args(self):
        "Drop an existing function which has arguments"
        self.db.execute(DROP_STMT2)
        self.db.execute_commit(CREATE_STMT2)
        dbsql = self.db.process_map(new_std_map())
        self.assertEqual(dbsql[0], "DROP FUNCTION f1(integer, integer)")

    def test_change_function_defn(self):
        "Change function definition"
        self.db.execute(DROP_STMT1)
        self.db.execute_commit(CREATE_STMT1)
        inmap = new_std_map()
        inmap['schema public'].update({'function f1()': {
                    'language': 'sql', 'returns': 'text',
                    'source': "SELECT 'example'::text",
                    'volatility': 'immutable'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), "CREATE OR REPLACE "
                         "FUNCTION f1() RETURNS text LANGUAGE sql "
                         "AS $_$SELECT 'example'::text$_$ IMMUTABLE")

    def test_function_with_comment(self):
        "Create a function with a comment"
        self.db.execute_commit(DROP_STMT2)
        inmap = new_std_map()
        inmap['schema public'].update({
                'function f1(integer, integer)': {
                    'description': 'Test function f1',
                    'language': 'sql', 'returns': 'integer',
                    'source': "SELECT $1 + $2"}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_STMT2)
        self.assertEqual(dbsql[1], COMMENT_STMT)

    def test_comment_on_function(self):
        "Create a comment for an existing function"
        self.db.execute(DROP_STMT2)
        self.db.execute_commit(CREATE_STMT2)
        inmap = new_std_map()
        inmap['schema public'].update({
                'function f1(integer, integer)': {
                    'description': 'Test function f1',
                    'language': 'sql', 'returns': 'integer',
                    'source': "SELECT $1 + $2"}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [COMMENT_STMT])

    def test_drop_function_comment(self):
        "Drop a comment on an existing function"
        self.db.execute(DROP_STMT2)
        self.db.execute(CREATE_STMT2)
        self.db.execute_commit(COMMENT_STMT)
        inmap = new_std_map()
        inmap['schema public'].update({
                'function f1(integer, integer)': {
                    'language': 'sql', 'returns': 'integer',
                    'source': "SELECT $1 + $2"}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql,
                         ["COMMENT ON FUNCTION f1(integer, integer) IS NULL"])

    def test_change_function_comment(self):
        "Change existing comment on a function"
        self.db.execute(DROP_STMT2)
        self.db.execute(CREATE_STMT2)
        self.db.execute_commit(COMMENT_STMT)
        inmap = new_std_map()
        inmap['schema public'].update({
                'function f1(integer, integer)': {
                    'description': 'Changed function f1',
                    'language': 'sql', 'returns': 'integer',
                    'source': "SELECT $1 + $2"}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [
                "COMMENT ON FUNCTION f1(integer, integer) IS "
                "'Changed function f1'"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(FunctionToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            FunctionToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
