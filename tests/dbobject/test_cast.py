# -*- coding: utf-8 -*-
"""Test casts"""

import unittest

from pyrseas.testutils import PyrseasTestCase, fix_indent

SOURCE = "SELECT CAST($1::int AS boolean)"
CREATE_FUNC = "CREATE FUNCTION int2_bool(smallint) RETURNS boolean " \
    "LANGUAGE sql IMMUTABLE AS $_$%s$_$" % SOURCE
CREATE_DOMAIN = "CREATE DOMAIN d1 AS integer"
CREATE_STMT1 = "CREATE CAST (smallint AS boolean) WITH FUNCTION " \
    "int2_bool(smallint)"
CREATE_STMT3 = "CREATE CAST (d1 AS integer) WITH INOUT AS IMPLICIT"
DROP_STMT = "DROP CAST IF EXISTS (smallint AS boolean)"
COMMENT_STMT = "COMMENT ON CAST (smallint AS boolean) IS 'Test cast 1'"


class CastToMapTestCase(PyrseasTestCase):
    """Test mapping of existing casts"""

    def test_map_cast_function(self):
        "Map a cast with a function"
        self.db.execute(CREATE_FUNC)
        expmap = {'function': 'int2_bool(smallint)', 'context': 'explicit',
                  'method': 'function'}
        dbmap = self.db.execute_and_map(CREATE_STMT1)
        self.assertEqual(dbmap['cast (smallint as boolean)'], expmap)

    def test_map_cast_inout(self):
        "Map a cast with INOUT"
        self.db.execute(CREATE_DOMAIN)
        expmap = {'context': 'implicit', 'method': 'inout'}
        dbmap = self.db.execute_and_map(CREATE_STMT3)
        self.assertEqual(dbmap['cast (d1 as integer)'], expmap)

    def test_map_cast_comment(self):
        "Map a cast comment"
        self.db.execute(CREATE_FUNC)
        self.db.execute(CREATE_STMT1)
        dbmap = self.db.execute_and_map(COMMENT_STMT)
        self.assertEqual(dbmap['cast (smallint as boolean)']['description'],
                         'Test cast 1')


class CastToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input casts"""

    def test_create_cast_function(self):
        "Create a cast with a function"
        self.db.execute_commit(DROP_STMT)
        self.db.execute(CREATE_FUNC)
        inmap = self.std_map()
        inmap.update({'cast (smallint as boolean)': {
                    'function': 'int2_bool(smallint)', 'context': 'explicit',
                    'method': 'function'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_STMT1)

    def test_create_cast_inout(self):
        "Create a cast with INOUT"
        self.db.execute(CREATE_DOMAIN)
        self.db.execute_commit("DROP CAST IF EXISTS (d1 AS integer)")
        inmap = self.std_map()
        inmap.update({'cast (d1 as integer)': {
                    'context': 'implicit', 'method': 'inout'}})
        inmap['schema public'].update({'domain d1': {'type': 'integer'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_STMT3)

    def test_create_cast_schema(self):
        "Create a cast using a type/domain in a non-public schema"
        self.db.execute_commit("DROP SCHEMA IF EXISTS s1 CASCADE")
        self.db.execute("CREATE SCHEMA s1")
        self.db.execute("CREATE DOMAIN s1.d1 AS integer")
        self.db.execute_commit("DROP CAST IF EXISTS (integer AS s1.d1)")
        inmap = self.std_map()
        inmap.update({'cast (integer as s1.d1)': {
                    'context': 'assignment', 'method': 'binary coercible'}})
        inmap.update({'schema s1': {'domain d1': {'type': 'integer'}}})
        dbsql = self.db.process_map(inmap)
        self.db.execute_commit("DROP SCHEMA s1 CASCADE")
        self.assertEqual(fix_indent(dbsql[0]),
                         "CREATE CAST (integer AS s1.d1) WITHOUT FUNCTION "
                         "AS ASSIGNMENT")

    def test_bad_cast_map(self):
        "Error creating a cast with a bad map"
        inmap = self.std_map()
        inmap.update({'(smallint as boolean)': {
                    'function': 'int2_bool(smallint)', 'context': 'explicit',
                    'method': 'function'}})
        self.assertRaises(KeyError, self.db.process_map, inmap)

    def test_drop_cast(self):
        "Drop an existing cast"
        self.db.execute(DROP_STMT)
        self.db.execute(CREATE_FUNC)
        self.db.execute_commit(CREATE_STMT1)
        dbsql = self.db.process_map(self.std_map())
        self.assertEqual(dbsql[0], "DROP CAST (smallint AS boolean)")

    def test_cast_with_comment(self):
        "Create a cast with a comment"
        self.db.execute_commit(DROP_STMT)
        inmap = self.std_map()
        inmap.update({'cast (smallint as boolean)': {
                    'description': 'Test cast 1',
                    'function': 'int2_bool(smallint)', 'context': 'explicit',
                    'method': 'function'}})
        inmap['schema public'].update({'function int2_bool(smallint)': {
                    'returns': 'boolean', 'language': 'sql',
                    'immutable': True, 'source': SOURCE}})
        dbsql = self.db.process_map(inmap)
        # dbsql[0] -> SET, dbsql[1] -> CREATE FUNCTION
        self.assertEqual(fix_indent(dbsql[2]), CREATE_STMT1)
        self.assertEqual(dbsql[3], COMMENT_STMT)

    def test_comment_on_cast(self):
        "Create a comment for an existing cast"
        self.db.execute(DROP_STMT)
        self.db.execute(CREATE_FUNC)
        self.db.execute_commit(CREATE_STMT1)
        inmap = self.std_map()
        inmap.update({'cast (smallint as boolean)': {
                    'description': 'Test cast 1',
                    'function': 'int2_bool(smallint)', 'context': 'explicit',
                    'method': 'function'}})
        inmap['schema public'].update({'function int2_bool(smallint)': {
                    'returns': 'boolean', 'language': 'sql',
                    'immutable': True, 'source': SOURCE}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [COMMENT_STMT])

    def test_drop_cast_comment(self):
        "Drop a comment on an existing cast"
        self.db.execute(DROP_STMT)
        self.db.execute(CREATE_FUNC)
        self.db.execute(CREATE_STMT1)
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map()
        inmap.update({'cast (smallint as boolean)': {
                    'function': 'int2_bool(smallint)', 'context': 'explicit',
                    'method': 'function'}})
        inmap['schema public'].update({'function int2_bool(smallint)': {
                    'returns': 'boolean', 'language': 'sql',
                    'immutable': True, 'source': SOURCE}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [
                "COMMENT ON CAST (smallint AS boolean) IS NULL"])

    def test_change_cast_comment(self):
        "Change existing comment on a cast"
        self.db.execute(DROP_STMT)
        self.db.execute(CREATE_FUNC)
        self.db.execute(CREATE_STMT1)
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map()
        inmap.update({'cast (smallint as boolean)': {
                    'description': 'Changed cast 1',
                    'function': 'int2_bool(smallint)', 'context': 'explicit',
                    'method': 'function'}})
        inmap['schema public'].update({'function int2_bool(smallint)': {
                    'returns': 'boolean', 'language': 'sql',
                    'immutable': True, 'source': SOURCE}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [
                "COMMENT ON CAST (smallint AS boolean) IS 'Changed cast 1'"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(CastToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            CastToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
