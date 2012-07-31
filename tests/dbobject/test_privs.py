# -*- coding: utf-8 -*-
"""Test object privileges

The majority of other tests exclude access privileges.  These
explicitly request it.  In addition, the roles 'user1' and 'user2'
should have been previously defined.
"""

import unittest

from pyrseas.testutils import DatabaseToMapTestCase

CREATE_TABLE = "CREATE TABLE t1 (c1 integer, c2 text)"
SOURCE1 = "SELECT 'dummy'::text"
CREATE_FUNC = "CREATE FUNCTION f1() RETURNS text LANGUAGE sql IMMUTABLE AS " \
    "$_$%s$_$" % SOURCE1


class PrivilegeToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of object privilege information"""

    def test_map_schema(self):
        "Map a schema with some GRANTs"
        stmts = ["CREATE SCHEMA s1", "GRANT USAGE ON SCHEMA s1 TO PUBLIC",
                 "GRANT CREATE, USAGE ON SCHEMA s1 TO user1"]
        dbmap = self.to_map(stmts, no_privs=False)
        expmap = {'privileges': [{self.db.user: ['all']},
                                 {'PUBLIC': ['usage']}, {'user1': ['all']}]}
        self.assertEqual(dbmap['schema s1'], expmap)

    def test_map_table(self):
        "Map a table with various GRANTs"
        stmts = [CREATE_TABLE, "GRANT SELECT ON t1 TO PUBLIC",
                 "GRANT INSERT, UPDATE ON t1 TO user1",
                 "GRANT REFERENCES, TRIGGER ON t1 TO user2 WITH GRANT OPTION"]
        dbmap = self.to_map(stmts, no_privs=False)
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}}],
                  'privileges': [{self.db.user: ['all']},
                                 {'PUBLIC': ['select']},
                                 {'user1': ['insert', 'update']},
                                 {'user2': [
                        {'trigger': {'grantable': True}},
                        {'references': {'grantable': True}}]}]}
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_map_sequence(self):
        "Map a sequence with various GRANTs"
        stmts = ["CREATE SEQUENCE seq1",
                 "GRANT SELECT ON SEQUENCE seq1 TO PUBLIC",
                 "GRANT USAGE, UPDATE ON SEQUENCE seq1 TO user1"]
        dbmap = self.to_map(stmts, no_privs=False)
        expmap = {'start_value': 1, 'increment_by': 1, 'max_value': None,
                  'min_value': None, 'cache_value': 1,
                  'privileges': [{self.db.user: ['all']},
                                 {'PUBLIC': ['select']},
                                 {'user1': ['usage', 'update']}]}
        self.assertEqual(dbmap['schema public']['sequence seq1'], expmap)

    def test_map_view(self):
        "Map a view with various GRANTs"
        stmts = ["CREATE VIEW v1 AS SELECT now()::date AS today",
                 "GRANT SELECT ON v1 TO PUBLIC",
                 "GRANT REFERENCES ON v1 TO user1"]
        dbmap = self.to_map(stmts, no_privs=False)
        expmap = {'definition': " SELECT now()::date AS today;",
                  'privileges': [{self.db.user: ['all']},
                                 {'PUBLIC': ['select']},
                                 {'user1': ['references']}]}
        self.assertEqual(dbmap['schema public']['view v1'], expmap)

    def test_map_function(self):
        "Map a function with a GRANT and REVOKE from PUBLIC"
        stmts = [CREATE_FUNC, "REVOKE ALL ON FUNCTION f1() FROM PUBLIC",
                 "GRANT EXECUTE ON FUNCTION f1() TO user1"]
        dbmap = self.to_map(stmts, no_privs=False)
        expmap = {'language': 'sql', 'returns': 'text',
                  'source': SOURCE1, 'volatility': 'immutable',
                  'privileges': [{self.db.user: ['execute']},
                                 {'user1': ['execute']}]}
        self.assertEqual(dbmap['schema public']['function f1()'], expmap)

    def test_map_language(self):
        "Map a  language but REVOKE default privilege"
        if self.db.version >= 90100:
            self.skipTest('Only available before PG 9.1')
        stmts = ["DROP LANGUAGE IF EXISTS plperl CASCADE",
                 "CREATE LANGUAGE plperl",
                 "REVOKE USAGE ON LANGUAGE plperl FROM PUBLIC"]
        dbmap = self.to_map(stmts, no_privs=False)
        self.db.execute_commit("DROP LANGUAGE plperl")
        expmap = {'trusted': True, 'privileges': [{self.db.user: ['usage']}]}
        self.assertEqual(dbmap['language plperl'], expmap)

    def test_map_fd_wrapper(self):
        "Map a foreign data wrapper with a GRANT"
        stmts = ["CREATE FOREIGN DATA WRAPPER fdw1",
                 "GRANT USAGE ON FOREIGN DATA WRAPPER fdw1 TO PUBLIC"]
        dbmap = self.to_map(stmts, no_privs=False)
        expmap = {'privileges': [{self.db.user: ['usage']},
                                 {'PUBLIC': ['usage']}]}
        self.assertEqual(dbmap['foreign data wrapper fdw1'], expmap)

    def test_map_server(self):
        "Map a foreign server with a GRANT"
        stmts = ["CREATE FOREIGN DATA WRAPPER fdw1",
                 "CREATE SERVER fs1 FOREIGN DATA WRAPPER fdw1",
                 "GRANT USAGE ON FOREIGN SERVER fs1 TO user1"]
        dbmap = self.to_map(stmts, no_privs=False)
        expmap = {'privileges': [{self.db.user: ['usage']},
                                 {'user1': ['usage']}]}
        self.assertEqual(dbmap['foreign data wrapper fdw1']['server fs1'],
                         expmap)

    def test_map_foreign_table(self):
        "Map a foreign table with various GRANTs"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        stmts = ["CREATE FOREIGN DATA WRAPPER fdw1",
                 "CREATE SERVER fs1 FOREIGN DATA WRAPPER fdw1",
                 "CREATE FOREIGN TABLE ft1 (c1 integer, c2 text) SERVER fs1",
                 "GRANT SELECT ON ft1 TO PUBLIC",
                 "GRANT INSERT, UPDATE ON ft1 TO user1"]
        dbmap = self.to_map(stmts, no_privs=False)
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}}], 'server': 'fs1',
                  'privileges': [{self.db.user: ['all']},
                                 {'PUBLIC': ['select']},
                                 {'user1': ['insert', 'update']}]}
        self.assertEqual(dbmap['schema public']['foreign table ft1'], expmap)


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(PrivilegeToMapTestCase)
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
