# -*- coding: utf-8 -*-
"""Test enums and other types"""

import unittest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

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


class CompositeToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of created composite types"""

    def test_composite(self):
        "Map a composite type"
        dbmap = self.to_map([CREATE_COMPOSITE_STMT])
        expmap = {'attributes': [{'x': {'type': 'integer'}},
                                 {'y': {'type': 'integer'}},
                                 {'z': {'type': 'integer'}}]}
        self.assertEqual(dbmap['schema public']['type t1'], expmap)

    def test_dropped_attribute(self):
        "Map a composite type which has a dropped attribute"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        stmts = [CREATE_COMPOSITE_STMT, "ALTER TYPE t1 DROP ATTRIBUTE y"]
        dbmap = self.to_map(stmts)
        expmap = {'attributes': [{'x': {'type': 'integer'}},
                                 {'z': {'type': 'integer'}}]}
        self.assertEqual(dbmap['schema public']['type t1'], expmap)


class CompositeToSqlTestCase(InputMapToSqlTestCase):
    """Test creation and modification of composite types"""

    def test_create_composite(self):
        "Create a composite type"
        inmap = self.std_map()
        inmap['schema public'].update({'type t1': {
                    'attributes': [{'x': {'type': 'integer'}},
                                 {'y': {'type': 'integer'}},
                                 {'z': {'type': 'integer'}}]}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), CREATE_COMPOSITE_STMT)

    def test_drop_composite(self):
        "Drop an existing composite"
        sql = self.to_sql(self.std_map(), [CREATE_COMPOSITE_STMT])
        self.assertEqual(sql, ["DROP TYPE t1"])

    def test_rename_composite(self):
        "Rename an existing composite"
        inmap = self.std_map()
        inmap['schema public'].update({'type t2': {
                    'oldname': 't1',
                    'attributes': [{'x': {'type': 'integer'}},
                                 {'y': {'type': 'integer'}},
                                 {'z': {'type': 'integer'}}]}})
        sql = self.to_sql(inmap, [CREATE_COMPOSITE_STMT])
        self.assertEqual(sql, ["ALTER TYPE t1 RENAME TO t2"])

    def test_add_attribute(self):
        "Add an attribute to a composite type"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap['schema public'].update({'type t1': {
                    'attributes': [{'x': {'type': 'integer'}},
                                 {'y': {'type': 'integer'}},
                                 {'z': {'type': 'integer'}}]}})
        sql = self.to_sql(inmap, ["CREATE TYPE t1 AS (x integer, y integer)"])
        self.assertEqual(fix_indent(sql[0]), "ALTER TYPE t1 ADD ATTRIBUTE "
                         "z integer")

    def test_drop_attribute(self):
        "Drop an attribute from a composite type"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap['schema public'].update({'type t1': {
                    'attributes': [{'x': {'type': 'integer'}},
                                 {'z': {'type': 'integer'}}]}})
        sql = self.to_sql(inmap, [CREATE_COMPOSITE_STMT])
        self.assertEqual(fix_indent(sql[0]), "ALTER TYPE t1 DROP ATTRIBUTE y")

    def test_drop_attribute_schema(self):
        "Drop an attribute from a composite type within a non-public schema"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap.update({'schema s1': {'type t1': {
                        'attributes': [{'x': {'type': 'integer'}},
                                       {'z': {'type': 'integer'}}]}}})
        sql = self.to_sql(inmap, [
                "CREATE SCHEMA s1",
                "CREATE TYPE s1.t1 AS (x integer, y integer, z integer)"])
        self.assertEqual(fix_indent(sql[0]),
                         "ALTER TYPE s1.t1 DROP ATTRIBUTE y")

    def test_rename_attribute(self):
        "Rename an attribute of a composite type"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap['schema public'].update({'type t1': {
                    'attributes': [{'x': {'type': 'integer'}},
                                 {'y1': {'type': 'integer', 'oldname': 'y'}},
                                 {'z': {'type': 'integer'}}]}})
        sql = self.to_sql(inmap, [CREATE_COMPOSITE_STMT])
        self.assertEqual(fix_indent(sql[0]), "ALTER TYPE t1 "
                         "RENAME ATTRIBUTE y TO y1")


class EnumToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of created enum types"""

    def test_enum(self):
        "Map an enum"
        dbmap = self.to_map([CREATE_ENUM_STMT])
        expmap = {'labels': ['red', 'green', 'blue']}
        self.assertEqual(dbmap['schema public']['type t1'], expmap)


class EnumToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input enums"""

    def test_create_enum(self):
        "Create an enum"
        inmap = self.std_map()
        inmap['schema public'].update({'type t1': {
                    'labels': ['red', 'green', 'blue']}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), CREATE_ENUM_STMT)

    def test_drop_enum(self):
        "Drop an existing enum"
        sql = self.to_sql(self.std_map(), [CREATE_ENUM_STMT])
        self.assertEqual(sql, ["DROP TYPE t1"])

    def test_rename_enum(self):
        "Rename an existing enum"
        inmap = self.std_map()
        inmap['schema public'].update({'type t2': {
                    'oldname': 't1', 'labels': ['red', 'green', 'blue']}})
        sql = self.to_sql(inmap, [CREATE_ENUM_STMT])
        self.assertEqual(sql, ["ALTER TYPE t1 RENAME TO t2"])


class BaseTypeToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of created base type types"""

    superuser = True

    def test_base_type(self):
        "Map a base type"
        stmts = [CREATE_SHELL_STMT, CREATE_FUNC_IN, CREATE_FUNC_OUT,
                 CREATE_TYPE_STMT]
        dbmap = self.to_map(stmts)
        expmap = {'input': 't1textin', 'output': 't1textout',
                  'internallength': 'variable', 'alignment': 'int4',
                  'storage': 'plain', 'category': 'U'}
        self.assertEqual(dbmap['schema public']['type t1'], expmap)

    def test_base_type_category(self):
        "Map a base type"
        stmts = [CREATE_SHELL_STMT, CREATE_FUNC_IN, CREATE_FUNC_OUT,
                 "CREATE TYPE t1 (INPUT = t1textin, OUTPUT = t1textout, "
                 "CATEGORY = 'S')"]
        dbmap = self.to_map(stmts)
        expmap = {'input': 't1textin', 'output': 't1textout',
                  'internallength': 'variable', 'alignment': 'int4',
                  'storage': 'plain', 'category': 'S'}
        self.assertEqual(dbmap['schema public']['type t1'], expmap)


class BaseTypeToSqlTestCase(InputMapToSqlTestCase):
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
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), CREATE_SHELL_STMT)
        self.assertEqual(fix_indent(sql[1]), CREATE_FUNC_IN)
        self.assertEqual(fix_indent(sql[2]), CREATE_FUNC_OUT)
        self.assertEqual(fix_indent(sql[3]),
                         "CREATE TYPE t1 (INPUT = t1textin, "
                         "OUTPUT = t1textout, INTERNALLENGTH = variable, "
                         "ALIGNMENT = int4, STORAGE = plain)")

    def test_drop_type(self):
        "Drop an existing base type"
        stmts = [CREATE_SHELL_STMT, CREATE_FUNC_IN, CREATE_FUNC_OUT,
                 CREATE_TYPE_STMT]
        sql = self.to_sql(self.std_map(), stmts, superuser=True)
        self.assertEqual(sql, ["DROP TYPE t1 CASCADE"])


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
