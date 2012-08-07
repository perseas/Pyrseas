# -*- coding: utf-8 -*-
"""Test object privileges

The majority of other tests exclude access privileges.  These
explicitly request it.  In addition, the roles 'user1' and 'user2'
should have been previously defined.
"""

import unittest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

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

    def test_map_column(self):
        "Map a table with GRANTs on column"
        self.maxDiff = None
        stmts = [CREATE_TABLE, "GRANT SELECT ON t1 TO PUBLIC",
                 "GRANT INSERT (c1, c2) ON t1 TO user1",
                 "GRANT INSERT (c2), UPDATE (c2) ON t1 TO user2"]
        dbmap = self.to_map(stmts, no_privs=False)
        expmap = {'columns': [{'c1': {'type': 'integer',
                                      'privileges': [{'user1': ['insert']}]}},
                              {'c2': {'type': 'text',
                                      'privileges': [{'user1': ['insert']},
                                                     {'user2': [
                                        'insert', 'update']}]}}],
                  'privileges': [{self.db.user: ['all']},
                                 {'PUBLIC': ['select']}]}
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


class PrivilegeToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation of privilege information (GRANTs)"""

    def test_create_table(self):
        "Create a table with various privileges"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'PUBLIC': ['select']},
                                   {'user1': ['insert', 'update']},
                                   {'user2': [
                                {'trigger': {'grantable': True}},
                                {'references': {'grantable': True}}]}]}})
        sql = self.to_sql(inmap)
        # sql[0] = CREATE TABLE
        # sql[1] = ALTER TABLE OWNER
        self.assertEqual(sql[2], "GRANT ALL ON TABLE t1 TO %s" % self.db.user)
        self.assertEqual(sql[3], "GRANT SELECT ON TABLE t1 TO PUBLIC")
        self.assertEqual(sql[4], "GRANT INSERT, UPDATE ON TABLE t1 TO user1")
        self.assertEqual(sql[5], "GRANT TRIGGER, REFERENCES ON TABLE t1 "
                         "TO user2 WITH GRANT OPTION")

    def test_create_sequence(self):
        "Create a sequence with some privileges"
        inmap = self.std_map()
        inmap['schema public'].update({'sequence seq1': {
                    'start_value': 1, 'increment_by': 1, 'max_value': None,
                    'min_value': None, 'cache_value': 1,
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'PUBLIC': ['select']}]}})
        sql = self.to_sql(inmap)
        # sql[0] = CREATE SEQUENCE
        # sql[1] = ALTER SEQUENCE OWNER
        self.assertEqual(sql[2], "GRANT ALL ON SEQUENCE seq1 TO %s" %
                         self.db.user)
        self.assertEqual(sql[3], "GRANT SELECT ON SEQUENCE seq1 TO PUBLIC")

    def test_create_view(self):
        "Create a view with some privileges"
        inmap = self.std_map()
        inmap['schema public'].update({'view v1': {
                    'definition': " SELECT now()::date AS today;",
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'user1': ['select']}]}})
        sql = self.to_sql(inmap)
        # sql[0] = CREATE VIEW
        # sql[1] = ALTER VIEW OWNER
        self.assertEqual(sql[2], "GRANT ALL ON TABLE v1 TO %s" % self.db.user)
        self.assertEqual(sql[3], "GRANT SELECT ON TABLE v1 TO user1")


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(PrivilegeToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            PrivilegeToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
