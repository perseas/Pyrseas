# -*- coding: utf-8 -*-
"""Test object ownership

The majority of other tests exclude owner information.  These
explicitly request it.
"""

import unittest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_TABLE = "CREATE TABLE t1 (c1 integer, c2 text)"
SOURCE1 = "SELECT 'dummy'::text"
CREATE_FUNC = "CREATE FUNCTION f1() RETURNS text LANGUAGE sql IMMUTABLE AS " \
    "$_$%s$_$" % SOURCE1
CREATE_TYPE = "CREATE TYPE t1 AS (x integer, y integer)"


class OwnerToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of object owner information"""

    def test_map_type(self):
        "Map a composite type"
        dbmap = self.to_map([CREATE_TYPE], no_owner=False)
        expmap = {'attributes': [{'x': {'type': 'integer'}},
                                 {'y': {'type': 'integer'}}],
                  'owner': self.db.user}
        self.assertEqual(dbmap['schema public']['type t1'], expmap)

    def test_map_table(self):
        "Map a table"
        dbmap = self.to_map([CREATE_TABLE], no_owner=False)
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}}],
                  'owner': self.db.user}
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_map_function(self):
        "Map a function"
        dbmap = self.to_map([CREATE_FUNC], no_owner=False)
        expmap = {'language': 'sql', 'returns': 'text', 'owner': self.db.user,
                  'source': SOURCE1, 'volatility': 'immutable'}
        self.assertEqual(dbmap['schema public']['function f1()'], expmap)


class OwnerToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation of owner object information"""

    def test_create_type(self):
        "Create a composite type"
        inmap = self.std_map()
        inmap['schema public'].update({'type t1': {
                    'attributes': [{'x': {'type': 'integer'}},
                                 {'y': {'type': 'integer'}}],
                    'owner': self.db.user}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), CREATE_TYPE)
        self.assertEqual(sql[1], "ALTER TYPE t1 OWNER TO %s" % self.db.user)

    def test_create_table(self):
        "Create a table"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'owner': self.db.user}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), CREATE_TABLE)
        self.assertEqual(sql[1], "ALTER TABLE t1 OWNER TO %s" % self.db.user)

    def test_create_function(self):
        "Create a function in a schema and a comment"
        inmap = self.std_map()
        inmap.update({'schema s1': {'function f1()': {
                    'language': 'sql', 'returns': 'text',
                    'source': SOURCE1, 'volatility': 'immutable',
                    'owner': self.db.user, 'description': 'Test function'}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        # skip first two statements as those are tested elsewhere
        self.assertEqual(sql[2], "ALTER FUNCTION s1.f1() OWNER TO %s"
                         % self.db.user)
        # to verify correct order of invocation of ownable and commentable
        self.assertEqual(sql[3], "COMMENT ON FUNCTION s1.f1() IS "
                         "'Test function'")

    def test_change_table_owner(self):
        "Change the owner of a table"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'owner': 'someuser'}})
        sql = self.to_sql(inmap, [CREATE_TABLE])
        self.assertEqual(sql[0], "ALTER TABLE t1 OWNER TO someuser")


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(OwnerToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            OwnerToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
