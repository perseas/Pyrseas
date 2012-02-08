# -*- coding: utf-8 -*-
"""Test enums and other types"""

import unittest

from pyrseas.testutils import PyrseasTestCase, fix_indent

CREATE_COMPOSITE_STMT = "CREATE TYPE t1 AS (x integer, y integer, z integer)"
CREATE_ENUM_STMT = "CREATE TYPE t1 AS ENUM ('red', 'green', 'blue')"
CREATE_SHELL_STMT = "CREATE TYPE t1"
CREATE_FUNC_IN = "CREATE FUNCTION t1textin(cstring) RETURNS t1 " \
    "LANGUAGE internal IMMUTABLE STRICT AS $$textin$$"
CREATE_FUNC_OUT = "CREATE FUNCTION t1textout(t1) RETURNS cstring " \
    "LANGUAGE internal IMMUTABLE STRICT AS $$textout$$"
CREATE_TYPE_STMT = "CREATE TYPE t1 (INPUT = t1textin, OUTPUT = t1textout)"
DROP_STMT = "DROP TYPE IF EXISTS t1 CASCADE"
COMMENT_STMT = "COMMENT ON TYPE t1 IS 'Test type t1'"


class CompositeToMapTestCase(PyrseasTestCase):
    """Test mapping of created composite types"""

    def test_composite(self):
        "Map a composite type"
        expmap = {'attributes': [{'x': 'integer'}, {'y': 'integer'},
                                 {'z': 'integer'}]}
        dbmap = self.db.execute_and_map(CREATE_COMPOSITE_STMT)
        self.assertEqual(dbmap['schema public']['type t1'], expmap)


class CompositeToSqlTestCase(PyrseasTestCase):
    """Test mapping of created composite types"""

    def test_create_composite(self):
        "Create a composite type"
        inmap = self.std_map()
        inmap['schema public'].update({'type t1': {
                    'attributes': [{'x': 'integer'}, {'y': 'integer'},
                                   {'z': 'integer'}]}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_COMPOSITE_STMT)

    def test_drop_composite(self):
        "Drop an existing composite"
        self.db.execute_commit(CREATE_COMPOSITE_STMT)
        inmap = self.std_map()
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["DROP TYPE t1"])

    def test_rename_composite(self):
        "Rename an existing composite"
        self.db.execute_commit(CREATE_COMPOSITE_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'type t2': {
                    'oldname': 't1',
                    'attributes': [{'x': 'integer'}, {'y': 'integer'},
                                   {'z': 'integer'}]}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["ALTER TYPE t1 RENAME TO t2"])


class EnumToMapTestCase(PyrseasTestCase):
    """Test mapping of created enum types"""

    def test_enum(self):
        "Map an enum"
        expmap = {'labels': ['red', 'green', 'blue']}
        dbmap = self.db.execute_and_map(CREATE_ENUM_STMT)
        self.assertEqual(dbmap['schema public']['type t1'], expmap)


class EnumToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input enums"""

    def test_create_enum(self):
        "Create an enum"
        inmap = self.std_map()
        inmap['schema public'].update({'type t1': {
                    'labels': ['red', 'green', 'blue']}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_ENUM_STMT)

    def test_drop_enum(self):
        "Drop an existing enum"
        self.db.execute_commit(CREATE_ENUM_STMT)
        inmap = self.std_map()
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["DROP TYPE t1"])

    def test_rename_enum(self):
        "Rename an existing enum"
        self.db.execute_commit(CREATE_ENUM_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'type t2': {
                    'oldname': 't1', 'labels': ['red', 'green', 'blue']}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["ALTER TYPE t1 RENAME TO t2"])


class BaseTypeToMapTestCase(PyrseasTestCase):
    """Test mapping of created base type types"""

    def test_base_type(self):
        "Map a base type"
        self.db.execute(CREATE_SHELL_STMT)
        self.db.execute(CREATE_FUNC_IN)
        self.db.execute(CREATE_FUNC_OUT)
        expmap = {'input': 't1textin', 'output': 't1textout',
                  'internallength': 'variable', 'alignment': 'int4',
                  'storage': 'plain', 'category': 'U'}
        dbmap = self.db.execute_and_map(CREATE_TYPE_STMT)
        self.assertEqual(dbmap['schema public']['type t1'], expmap)

    def test_base_type_category(self):
        "Map a base type"
        self.db.execute(CREATE_SHELL_STMT)
        self.db.execute(CREATE_FUNC_IN)
        self.db.execute(CREATE_FUNC_OUT)
        expmap = {'input': 't1textin', 'output': 't1textout',
                  'internallength': 'variable', 'alignment': 'int4',
                  'storage': 'plain', 'category': 'S'}
        dbmap = self.db.execute_and_map("CREATE TYPE t1 (INPUT = t1textin, "
                                        "OUTPUT = t1textout, CATEGORY = 'S')")
        self.assertEqual(dbmap['schema public']['type t1'], expmap)


class BaseTypeToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input base types"""

    def test_create_base_type(self):
        "Create a base type"
        inmap = self.std_map()
        inmap['schema public'].update({'type t1': {
                    'input': 't1textin', 'output': 't1textout',
                    'internallength': 'variable', 'alignment': 'int4',
                    'storage': 'plain'}, 'function t1textin(cstring)': {
                    'language': 'internal', 'returns': 't1', 'strict': True,
                    'volatility': 'immutable', 'source': 'textin'},
                                       'function t1textout(t1)': {
                    'language': 'internal', 'returns': 'cstring',
                    'strict': True, 'volatility': 'immutable',
                    'source': 'textout'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_SHELL_STMT)
        self.assertEqual(fix_indent(dbsql[1]), CREATE_FUNC_IN)
        self.assertEqual(fix_indent(dbsql[2]), CREATE_FUNC_OUT)
        self.assertEqual(fix_indent(dbsql[3]),
                         "CREATE TYPE t1 (INPUT = t1textin, "
                         "OUTPUT = t1textout, INTERNALLENGTH = variable, "
                         "ALIGNMENT = int4, STORAGE = plain)")

    def test_drop_type(self):
        "Drop an existing base type"
        self.db.execute(CREATE_SHELL_STMT)
        self.db.execute(CREATE_FUNC_IN)
        self.db.execute(CREATE_FUNC_OUT)
        self.db.execute_commit(CREATE_TYPE_STMT)
        inmap = self.std_map()
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["DROP TYPE t1 CASCADE"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(CompositeToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            CompositeToSqlTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            EnumToMapTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            EnumToSqlTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            BaseTypeToMapTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            BaseTypeToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
