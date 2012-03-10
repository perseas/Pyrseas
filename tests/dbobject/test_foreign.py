# -*- coding: utf-8 -*-
"""Test text search objects"""

import unittest

from pyrseas.testutils import PyrseasTestCase, fix_indent

CREATE_FDW_STMT = "CREATE FOREIGN DATA WRAPPER fdw1"
CREATE_FS_STMT = "CREATE SERVER fs1 FOREIGN DATA WRAPPER fdw1"
CREATE_UM_STMT = "CREATE USER MAPPING FOR PUBLIC SERVER fs1"
CREATE_FT_STMT = "CREATE FOREIGN TABLE ft1 (c1 integer, c2 text) SERVER fs1"
DROP_FDW_STMT = "DROP FOREIGN DATA WRAPPER IF EXISTS fdw1"
DROP_FS_STMT = "DROP SERVER IF EXISTS fs1"
DROP_UM_STMT = "DROP USER MAPPING IF EXISTS FOR PUBLIC SERVER fs1"
COMMENT_FDW_STMT = "COMMENT ON FOREIGN DATA WRAPPER fdw1 IS " \
    "'Test foreign data wrapper fdw1'"
COMMENT_FS_STMT = "COMMENT ON SERVER fs1 IS 'Test server fs1'"


class ForeignDataWrapperToMapTestCase(PyrseasTestCase):
    """Test mapping of existing foreign data wrappers"""

    def test_map_fd_wrapper(self):
        "Map an existing foreign data wrapper"
        dbmap = self.db.execute_and_map(CREATE_FDW_STMT)
        self.assertEqual(dbmap['foreign data wrapper fdw1'], {})

    def test_map_wrapper_validator(self):
        "Map a foreign data wrapper with a validator function"
        dbmap = self.db.execute_and_map("CREATE FOREIGN DATA WRAPPER fdw1 "
                                        "VALIDATOR postgresql_fdw_validator")
        self.assertEqual(dbmap['foreign data wrapper fdw1'], {
                'validator': 'postgresql_fdw_validator'})

    def test_map_wrapper_options(self):
        "Map a foreign data wrapper with options"
        dbmap = self.db.execute_and_map("CREATE FOREIGN DATA WRAPPER fdw1 "
                                        "OPTIONS (debug 'true')")
        self.assertEqual(dbmap['foreign data wrapper fdw1'], {
                'options': ['debug=true']})

    def test_map_fd_wrapper_comment(self):
        "Map a foreign data wrapper with a comment"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        self.db.execute(CREATE_FDW_STMT)
        dbmap = self.db.execute_and_map(COMMENT_FDW_STMT)
        self.assertEqual(dbmap['foreign data wrapper fdw1']['description'],
                         'Test foreign data wrapper fdw1')


class ForeignDataWrapperToSqlTestCase(PyrseasTestCase):
    """Test SQL generation for input foreign data wrappers"""

    def test_create_fd_wrapper(self):
        "Create a foreign data wrapper that didn't exist"
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_FDW_STMT)

    def test_create_wrapper_validator(self):
        "Create a foreign data wrapper with a validator function"
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {
                    'validator': 'postgresql_fdw_validator'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "CREATE FOREIGN DATA WRAPPER fdw1 "
                         "VALIDATOR postgresql_fdw_validator")

    def test_create_wrapper_options(self):
        "Create a foreign data wrapper with options"
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {
                    'options': ['debug=true']}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "CREATE FOREIGN DATA WRAPPER fdw1 "
                         "OPTIONS (debug 'true')")

    def test_bad_map_fd_wrapper(self):
        "Error creating a foreign data wrapper with a bad map"
        inmap = self.std_map()
        inmap.update({'fdw1': {}})
        self.assertRaises(KeyError, self.db.process_map, inmap)

    def test_drop_fd_wrapper(self):
        "Drop an existing foreign data wrapper"
        self.db.execute_commit(CREATE_FDW_STMT)
        dbsql = self.db.process_map(self.std_map())
        self.assertEqual(dbsql[0], "DROP FOREIGN DATA WRAPPER fdw1")

    def test_alter_wrapper_options(self):
        "Change foreign data wrapper options"
        self.db.execute_commit(CREATE_FDW_STMT +
                               " OPTIONS (opt1 'valA', opt2 'valB')")
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {
                    'options': ['opt1=valX', 'opt3=valY']}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "ALTER FOREIGN DATA WRAPPER fdw1 OPTIONS "
                         "(SET opt1 'valX', opt3 'valY', DROP opt2)")

    def test_comment_on_fd_wrapper(self):
        "Create a comment for an existing foreign data wrapper"
        self.db.execute_commit(CREATE_FDW_STMT)
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {
                    'description': "Test foreign data wrapper fdw1"}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql[0], COMMENT_FDW_STMT)


class ForeignServerToMapTestCase(PyrseasTestCase):
    """Test mapping of existing foreign servers"""

    def test_map_server(self):
        "Map an existing foreign server"
        self.db.execute(CREATE_FDW_STMT)
        dbmap = self.db.execute_and_map(CREATE_FS_STMT)
        self.assertEqual(dbmap['foreign data wrapper fdw1'],
                         {'server fs1': {}})

    def test_map_server_type_version(self):
        "Map a foreign server with type and version"
        self.db.execute(CREATE_FDW_STMT)
        dbmap = self.db.execute_and_map(
            "CREATE SERVER fs1 TYPE 'test' VERSION '1.0' "
            "FOREIGN DATA WRAPPER fdw1")
        self.assertEqual(dbmap['foreign data wrapper fdw1'], {'server fs1': {
                    'type': 'test', 'version': '1.0'}})

    def test_map_server_options(self):
        "Map a foreign server with options"
        self.db.execute(CREATE_FDW_STMT)
        dbmap = self.db.execute_and_map(
            "CREATE SERVER fs1 FOREIGN DATA WRAPPER fdw1 "
            "OPTIONS (dbname 'test')")
        self.assertEqual(dbmap['foreign data wrapper fdw1'], {'server fs1': {
                    'options': ['dbname=test']}})

    def test_map_server_comment(self):
        "Map a foreign server with a comment"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute(CREATE_FS_STMT)
        dbmap = self.db.execute_and_map(COMMENT_FS_STMT)
        self.assertEqual(dbmap['foreign data wrapper fdw1'], {'server fs1': {
                        'description': 'Test server fs1'}})


class ForeignServerToSqlTestCase(PyrseasTestCase):
    """Test SQL generation for input foreign servers"""

    def test_create_server(self):
        "Create a foreign server that didn't exist"
        self.db.execute_commit(CREATE_FDW_STMT)
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_FS_STMT)

    def test_create_wrapper_server(self):
        "Create a foreign data wrapper and its server"
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_FDW_STMT)
        self.assertEqual(fix_indent(dbsql[1]), CREATE_FS_STMT)

    def test_create_server_type_version(self):
        "Create a foreign server with type and version"
        self.db.execute_commit(CREATE_FDW_STMT)
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {
                            'type': 'test', 'version': '1.0'}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
            "CREATE SERVER fs1 TYPE 'test' VERSION '1.0' "
            "FOREIGN DATA WRAPPER fdw1")

    def test_create_server_options(self):
        "Create a foreign server with options"
        self.db.execute_commit(CREATE_FDW_STMT)
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {
                            'options': ['dbname=test']}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
            "CREATE SERVER fs1 FOREIGN DATA WRAPPER fdw1 "
            "OPTIONS (dbname 'test')")

    def test_bad_map_server(self):
        "Error creating a foreign server with a bad map"
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'fs1': {}}})
        self.assertRaises(KeyError, self.db.process_map, inmap)

    def test_drop_server(self):
        "Drop an existing foreign server"
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute_commit(CREATE_FS_STMT)
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql[0], "DROP SERVER fs1")

    def test_add_server_options(self):
        "Add options to a foreign server"
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute_commit(CREATE_FS_STMT)
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {
                            'options': ['opt1=valA', 'opt2=valB']}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
            "ALTER SERVER fs1 OPTIONS (opt1 'valA', opt2 'valB')")

    def test_drop_server_wrapper(self):
        "Drop an existing foreign data wrapper and its server"
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute_commit(CREATE_FS_STMT)
        dbsql = self.db.process_map(self.std_map())
        self.assertEqual(dbsql[0], "DROP SERVER fs1")
        self.assertEqual(dbsql[1], "DROP FOREIGN DATA WRAPPER fdw1")

    def test_comment_on_server(self):
        "Create a comment for an existing foreign server"
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute_commit(CREATE_FS_STMT)
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {
                                'description': "Test server fs1"}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [COMMENT_FS_STMT])


class UserMappingToMapTestCase(PyrseasTestCase):
    """Test mapping of existing user mappings"""

    def test_map_user_mapping(self):
        "Map an existing user mapping"
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute(CREATE_FS_STMT)
        dbmap = self.db.execute_and_map(CREATE_UM_STMT)
        self.assertEqual(dbmap['foreign data wrapper fdw1']['server fs1']
                         ['user mappings'], {'PUBLIC': {}})

    def test_map_user_mapping_options(self):
        "Map a user mapping with options"
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute(CREATE_FS_STMT)
        dbmap = self.db.execute_and_map(CREATE_UM_STMT +
            " OPTIONS (user 'john', password 'doe')")
        self.assertEqual(dbmap['foreign data wrapper fdw1']['server fs1'],
                         {'user mappings': {'PUBLIC': {
                        'options': ['user=john', 'password=doe']}}})


class UserMappingToSqlTestCase(PyrseasTestCase):
    """Test SQL generation for input user mappings"""

    def test_create_user_mapping(self):
        "Create a user mapping that didn't exist"
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute_commit(CREATE_FS_STMT)
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {
                        'user mappings': {'PUBLIC': {}}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_UM_STMT)

    def test_create_wrapper_server_mapping(self):
        "Create a FDW, server and user mapping"
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {
                        'user mappings': {'PUBLIC': {}}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_FDW_STMT)
        self.assertEqual(fix_indent(dbsql[1]), CREATE_FS_STMT)
        self.assertEqual(fix_indent(dbsql[2]), CREATE_UM_STMT)

    def test_create_user_mapping_options(self):
        "Create a user mapping with options"
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute_commit(CREATE_FS_STMT)
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {
                        'user mappings': {'PUBLIC': {
                                'options': ['user=john', 'password=doe']}}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_UM_STMT +
                         " OPTIONS (user 'john', password 'doe')")

    def test_drop_user_mapping(self):
        "Drop an existing user mapping"
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute(CREATE_FS_STMT)
        self.db.execute_commit(CREATE_UM_STMT)
        dbsql = self.db.process_map(self.std_map())
        self.assertEqual(dbsql[0], "DROP USER MAPPING FOR PUBLIC SERVER fs1")

    def test_drop_user_mapping_options(self):
        "Drop options from a user mapping"
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute(CREATE_FS_STMT)
        self.db.execute_commit(CREATE_UM_STMT +
                               " OPTIONS (opt1 'valA', opt2 'valB')")
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {
                        'user mappings': {'PUBLIC': {}}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "ALTER USER MAPPING FOR PUBLIC SERVER fs1 "
                         "OPTIONS (DROP opt1, DROP opt2)")


class ForeignTableToMapTestCase(PyrseasTestCase):
    """Test mapping of existing foreign tables"""

    def test_map_foreign_table(self):
        "Map an existing foreign table"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute(CREATE_FS_STMT)
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}}], 'server': 'fs1'}
        dbmap = self.db.execute_and_map(CREATE_FT_STMT)
        self.assertEqual(dbmap['schema public']['foreign table ft1'], expmap)

    def test_map_foreign_table_options(self):
        "Map a foreign table with options"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute(CREATE_FS_STMT)
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}}], 'server': 'fs1',
                  'options': ['user=jack']}
        dbmap = self.db.execute_and_map(CREATE_FT_STMT +
                                        " OPTIONS (user 'jack')")
        self.assertEqual(dbmap['schema public']['foreign table ft1'], expmap)


class ForeignTableToSqlTestCase(PyrseasTestCase):
    """Test SQL generation for input foreign tables"""

    def test_create_foreign_table(self):
        "Create a foreign table that didn't exist"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute_commit(CREATE_FS_STMT)
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {}}})
        inmap['schema public'].update({'foreign table ft1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}], 'server': 'fs1'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_FT_STMT)

    def test_create_foreign_table_options(self):
        "Create a foreign table with options"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute_commit(CREATE_FS_STMT)
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {}}})
        inmap['schema public'].update({'foreign table ft1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}], 'server': 'fs1',
                    'options': ['user=jack']}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_FT_STMT +
                         " OPTIONS (user 'jack')")

    def test_bad_map_foreign_table(self):
        "Error creating a foreign table with a bad map"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {}}})
        inmap['schema public'].update({'ft1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}], 'server': 'fs1'}})
        self.assertRaises(KeyError, self.db.process_map, inmap)

    def test_drop_foreign_table(self):
        "Drop an existing foreign table"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute(CREATE_FS_STMT)
        self.db.execute_commit(CREATE_FT_STMT)
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql[0], "DROP FOREIGN TABLE ft1")

    def test_drop_foreign_table_server(self):
        "Drop a foreign table and associated server"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute(CREATE_FS_STMT)
        self.db.execute_commit(CREATE_FT_STMT)
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql[0], "DROP FOREIGN TABLE ft1")
        self.assertEqual(dbsql[1], "DROP SERVER fs1")

    def test_alter_foreign_table_options(self):
        "Alter options for a foreign table"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute(CREATE_FS_STMT)
        self.db.execute_commit(CREATE_FT_STMT +
                               " OPTIONS (opt1 'valA', opt2 'valB')")
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {}}})
        inmap['schema public'].update({'foreign table ft1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}], 'server': 'fs1',
                    'options': ['opt1=valX', 'opt2=valY']}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), "ALTER FOREIGN TABLE ft1 "
                         "OPTIONS (SET opt1 'valX', SET opt2 'valY')")

    def test_add_column(self):
        "Add new column to a foreign table"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        self.db.execute(CREATE_FDW_STMT)
        self.db.execute(CREATE_FS_STMT)
        self.db.execute_commit(CREATE_FT_STMT)
        inmap = self.std_map()
        inmap.update({'foreign data wrapper fdw1': {'server fs1': {}}})
        inmap['schema public'].update({'foreign table ft1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'date'}}], 'server': 'fs1'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "ALTER FOREIGN TABLE ft1 ADD COLUMN c3 date")


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(
        ForeignDataWrapperToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            ForeignDataWrapperToSqlTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            ForeignServerToMapTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            ForeignServerToSqlTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            UserMappingToMapTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            UserMappingToSqlTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            ForeignTableToMapTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            ForeignTableToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
