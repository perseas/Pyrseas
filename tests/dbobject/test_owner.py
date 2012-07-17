# -*- coding: utf-8 -*-
"""Test object ownership

The majority of other tests exclude owner information.  These
explicitly request it.
"""

import unittest

from pyrseas.testutils import DatabaseToMapTestCase

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


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(OwnerToMapTestCase)
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
