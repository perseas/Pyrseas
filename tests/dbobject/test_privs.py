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
CREATE_FDW = "CREATE FOREIGN DATA WRAPPER fdw1"
CREATE_FS = "CREATE SERVER fs1 FOREIGN DATA WRAPPER fdw1"
GRANT_SELECT = "GRANT SELECT ON TABLE t1 TO %s"
GRANT_INSUPD = "GRANT INSERT, UPDATE ON TABLE t1 TO %s"


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
        stmts = [CREATE_TABLE, GRANT_SELECT % 'PUBLIC', GRANT_INSUPD % 'user1',
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
        stmts = [CREATE_TABLE, GRANT_SELECT % 'PUBLIC',
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
        stmts = [CREATE_FDW,
                 "GRANT USAGE ON FOREIGN DATA WRAPPER fdw1 TO PUBLIC"]
        dbmap = self.to_map(stmts, no_privs=False, superuser=True)
        expmap = {'privileges': [{self.db.user: ['usage']},
                                 {'PUBLIC': ['usage']}]}
        self.assertEqual(dbmap['foreign data wrapper fdw1'], expmap)

    def test_map_server(self):
        "Map a foreign server with a GRANT"
        stmts = [CREATE_FDW, CREATE_FS,
                 "GRANT USAGE ON FOREIGN SERVER fs1 TO user1"]
        dbmap = self.to_map(stmts, no_privs=False, superuser=True)
        expmap = {'privileges': [{self.db.user: ['usage']},
                                 {'user1': ['usage']}]}
        self.assertEqual(dbmap['foreign data wrapper fdw1']['server fs1'],
                         expmap)

    def test_map_foreign_table(self):
        "Map a foreign table with various GRANTs"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        stmts = [CREATE_FDW, CREATE_FS,
                 "CREATE FOREIGN TABLE ft1 (c1 integer, c2 text) SERVER fs1",
                 "GRANT SELECT ON ft1 TO PUBLIC",
                 "GRANT INSERT, UPDATE ON ft1 TO user1"]
        dbmap = self.to_map(stmts, no_privs=False, superuser=True)
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}}], 'server': 'fs1',
                  'privileges': [{self.db.user: ['all']},
                                 {'PUBLIC': ['select']},
                                 {'user1': ['insert', 'update']}]}
        self.assertEqual(dbmap['schema public']['foreign table ft1'], expmap)


class PrivilegeToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation of privilege information (GRANTs)"""

    def test_create_schema(self):
        "Create a schema with various privileges"
        inmap = self.std_map()
        inmap.update({'schema s1': {
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'PUBLIC': ['usage', 'create']}]}})
        sql = self.to_sql(inmap)
        # sql[0] = CREATE SCHEMA
        # sql[1] = ALTER SCHEMA OWNER
        self.assertEqual(sql[2], "GRANT ALL ON SCHEMA s1 TO %s" % self.db.user)
        self.assertEqual(sql[3], "GRANT ALL ON SCHEMA s1 TO PUBLIC")

    def test_schema_new_grant(self):
        "Grant privileges on an existing schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'PUBLIC': ['create']}]}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        self.assertEqual(len(sql), 2)
        sql = sorted(sql)
        self.assertEqual(sql[0], "GRANT ALL ON SCHEMA s1 TO %s" % self.db.user)
        self.assertEqual(sql[1], "GRANT CREATE ON SCHEMA s1 TO PUBLIC")

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
        self.assertEqual(sql[3], GRANT_SELECT % 'PUBLIC')
        self.assertEqual(sql[4], GRANT_INSUPD % 'user1')
        self.assertEqual(sql[5], "GRANT TRIGGER, REFERENCES ON TABLE t1 "
                         "TO user2 WITH GRANT OPTION")

    def test_create_column_grants(self):
        "Create a table with colum-level privileges"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {
                                'type': 'integer',
                                'privileges': [{'user1': ['insert']}]}},
                                {'c2': {'type': 'text',
                                        'privileges': [{'user1': ['insert']},
                                                       {'user2': [
                                            'insert', 'update']}]}}],
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'PUBLIC': ['select']}]}})
        sql = self.to_sql(inmap)
        self.assertEqual(len(sql), 7)
        # sql[0] = CREATE TABLE
        # sql[1] = ALTER TABLE OWNER
        self.assertEqual(sql[2], "GRANT ALL ON TABLE t1 TO %s" % self.db.user)
        self.assertEqual(sql[3],  GRANT_SELECT % 'PUBLIC')
        self.assertEqual(sql[4], "GRANT INSERT (c1) ON TABLE t1 TO user1")
        self.assertEqual(sql[5], "GRANT INSERT (c2) ON TABLE t1 TO user1")
        self.assertEqual(sql[6],
                         "GRANT INSERT (c2), UPDATE (c2) ON TABLE t1 TO user2")

    def test_table_new_grant(self):
        "Grant select privileges on an existing table"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'user1': ['select']}]}})
        sql = self.to_sql(inmap, [CREATE_TABLE])
        self.assertEqual(len(sql), 2)
        sql = sorted(sql)
        self.assertEqual(sql[0], "GRANT ALL ON TABLE t1 TO %s" % self.db.user)
        self.assertEqual(sql[1],  GRANT_SELECT % 'user1')

    def test_table_change_grant(self):
        "Grant select privileges on an existing table"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'PUBLIC': ['select']},
                                   {'user1': ['insert', 'update']}]}})
        sql = self.to_sql(inmap, [CREATE_TABLE,
                                   GRANT_SELECT % 'user1'])
        self.assertEqual(len(sql), 3)
        self.assertEqual(sql[0], "REVOKE SELECT ON TABLE t1 FROM user1")
        sql[1:2] = sorted(sql[1:2])
        self.assertEqual(sql[1], GRANT_INSUPD % 'user1')
        self.assertEqual(sql[2], GRANT_SELECT % 'PUBLIC')

    def test_column_change_grants(self):
        "Change existing colum-level privileges"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {
                                'type': 'integer',
                                        'privileges': [{'user1': ['insert']},
                                                       {'user2': [
                                            'insert', 'update']}]}},
                                {'c2': {'type': 'text',
                                'privileges': [{'user1': ['insert']}]}}],
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'PUBLIC': ['select']}]}})
        stmts = [CREATE_TABLE, GRANT_SELECT % 'PUBLIC',
                 "GRANT INSERT (c1, c2) ON t1 TO user1",
                 "GRANT INSERT (c2), UPDATE (c2) ON t1 TO user2"]
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(len(sql), 2)
        self.assertEqual(sql[0],
                         "GRANT INSERT (c1), UPDATE (c1) ON TABLE t1 TO user2")
        self.assertEqual(sql[1], "REVOKE INSERT (c2), UPDATE (c2) ON TABLE t1 "
                         "FROM user2")

    def test_table_revoke_all(self):
        "Revoke all privileges on an existing table"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'owner': self.db.user}})
        stmts = [CREATE_TABLE, GRANT_SELECT % 'PUBLIC', GRANT_INSUPD % 'user1']
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(len(sql), 3)
        sql = sorted(sql)
        self.assertEqual(sql[0], "REVOKE ALL ON TABLE t1 FROM %s" %
                         self.db.user)
        self.assertEqual(sql[1], "REVOKE INSERT, UPDATE ON TABLE t1 "
                         "FROM user1")
        self.assertEqual(sql[2], "REVOKE SELECT ON TABLE t1 FROM PUBLIC")

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

    def test_sequence_new_grant(self):
        "Grant privileges on an existing sequence"
        inmap = self.std_map()
        inmap['schema public'].update({'sequence seq1': {
                    'start_value': 1, 'increment_by': 1, 'max_value': None,
                    'min_value': None, 'cache_value': 1,
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'PUBLIC': ['select']}]}})
        sql = self.to_sql(inmap, ["CREATE SEQUENCE seq1"])
        self.assertEqual(len(sql), 2)
        sql = sorted(sql)
        self.assertEqual(sql[0], "GRANT ALL ON SEQUENCE seq1 TO %s" %
                         self.db.user)
        self.assertEqual(sql[1], "GRANT SELECT ON SEQUENCE seq1 TO PUBLIC")

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

    def test_view_new_grant(self):
        "Grant privileges on an existing view"
        inmap = self.std_map()
        inmap['schema public'].update({'view v1': {
                    'definition': " SELECT now()::date AS today;",
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'user1': ['select']}]}})
        sql = self.to_sql(inmap,
                          ["CREATE VIEW v1 AS SELECT now()::date AS today"])
        self.assertEqual(len(sql), 2)
        sql = sorted(sql)
        self.assertEqual(sql[0], "GRANT ALL ON TABLE v1 TO %s" % self.db.user)
        self.assertEqual(sql[1], "GRANT SELECT ON TABLE v1 TO user1")

    def test_create_function(self):
        "Create a function with some privileges"
        inmap = self.std_map()
        inmap['schema public'].update({'function f1()': {
                    'language': 'sql', 'returns': 'text',
                    'source': SOURCE1, 'volatility': 'immutable',
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'PUBLIC': ['execute']}]}})
        sql = self.to_sql(inmap)
        # sql[0] = SET check_function_bodies
        # sql[1] = CREATE FUNCTION
        # sql[2] = ALTER FUNCTION OWNER
        self.assertEqual(sql[3], "GRANT EXECUTE ON FUNCTION f1() TO %s" %
                         self.db.user)
        self.assertEqual(sql[4], "GRANT EXECUTE ON FUNCTION f1() TO PUBLIC")

    def test_function_new_grant(self):
        "Grant privileges on an existing function"
        inmap = self.std_map()
        inmap['schema public'].update({'function f1()': {
                    'language': 'sql', 'returns': 'text',
                    'source': SOURCE1, 'volatility': 'immutable',
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'PUBLIC': ['execute']}]}})
        sql = self.to_sql(inmap, [CREATE_FUNC])
        self.assertEqual(len(sql), 2)
        sql = sorted(sql)
        # assumes self.db.user > PUBLIC
        self.assertEqual(sql[0], "GRANT EXECUTE ON FUNCTION f1() TO PUBLIC")
        self.assertEqual(sql[1], "GRANT EXECUTE ON FUNCTION f1() TO %s" %
                         self.db.user)

    def test_create_fd_wrapper(self):
        "Create a foreign data wrapper with some privileges"
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'PUBLIC': ['usage']}]}})
        sql = self.to_sql(inmap)
        # sql[0] = CREATE FDW
        # sql[1] = ALTER FDW OWNER
        self.assertEqual(sql[2], "GRANT USAGE ON FOREIGN DATA WRAPPER fdw1 "
                         "TO %s" % self.db.user)
        self.assertEqual(sql[3], "GRANT USAGE ON FOREIGN DATA WRAPPER fdw1 "
                         "TO PUBLIC")

    def test_fd_wrapper_new_grant(self):
        "Grant privileges on an existing foreign data wrapper"
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'PUBLIC': ['usage']}]}})
        sql = self.to_sql(inmap, [CREATE_FDW], superuser=True)
        self.assertEqual(len(sql), 2)
        sql = sorted(sql)
        # assumes self.db.user > PUBLIC
        self.assertEqual(sql[0], "GRANT USAGE ON FOREIGN DATA WRAPPER fdw1 "
                         "TO PUBLIC")
        self.assertEqual(sql[1], "GRANT USAGE ON FOREIGN DATA WRAPPER fdw1 "
                         "TO %s" % self.db.user)

    def test_create_server(self):
        "Create a foreign server with some privileges"
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'user2': ['usage']}]}}})
        sql = self.to_sql(inmap, [CREATE_FDW], superuser=True)
        # sql[0] = CREATE SERVER
        # sql[1] = ALTER SERVER OWNER
        self.assertEqual(sql[2], "GRANT USAGE ON FOREIGN SERVER fs1 TO %s" %
                         self.db.user)
        self.assertEqual(sql[3], "GRANT USAGE ON FOREIGN SERVER fs1 TO user2")

    def test_server_new_grant(self):
        "Grant privileges on an existing foreign server"
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'user2': ['usage']}]}}})
        sql = self.to_sql(inmap, [CREATE_FDW, CREATE_FS], superuser=True)
        self.assertEqual(len(sql), 2)
        sql = sorted(sql)
        self.assertEqual(sql[0], "GRANT USAGE ON FOREIGN SERVER fs1 TO %s" %
                         self.db.user)
        self.assertEqual(sql[1], "GRANT USAGE ON FOREIGN SERVER fs1 TO user2")

    def test_create_foreign_table(self):
        "Create a foreign table with some privileges"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {}}})
        inmap['schema public'].update({'foreign table ft1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}], 'server': 'fs1',
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'PUBLIC': ['select']},
                                   {'user1': ['insert', 'update']}]}})
        sql = self.to_sql(inmap, [CREATE_FDW, CREATE_FS], superuser=True)
        # sql[0] = CREATE TABLE
        # sql[1] = ALTER TABLE OWNER
        self.assertEqual(sql[2], "GRANT ALL ON TABLE ft1 TO %s" % self.db.user)
        self.assertEqual(sql[3], "GRANT SELECT ON TABLE ft1 TO PUBLIC")
        self.assertEqual(sql[4], "GRANT INSERT, UPDATE ON TABLE ft1 TO user1")

    def test_foreign_table_new_grant(self):
        "Grant privileges on an existing foreign table"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {}}})
        inmap['schema public'].update({'foreign table ft1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}], 'server': 'fs1',
                    'owner': self.db.user,
                    'privileges': [{self.db.user: ['all']},
                                   {'PUBLIC': ['select']},
                                   {'user1': ['insert', 'update']}]}})
        sql = self.to_sql(inmap, [
                CREATE_FDW, CREATE_FS,
                "CREATE FOREIGN TABLE ft1 (c1 integer, c2 text) SERVER fs1"],
                          superuser=True)
        self.assertEqual(len(sql), 3)
        sql = sorted(sql)
        self.assertEqual(sql[0], "GRANT ALL ON TABLE ft1 TO %s" % self.db.user)
        self.assertEqual(sql[1], "GRANT INSERT, UPDATE ON TABLE ft1 TO user1")
        self.assertEqual(sql[2], "GRANT SELECT ON TABLE ft1 TO PUBLIC")


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(PrivilegeToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            PrivilegeToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
