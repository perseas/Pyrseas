# -*- coding: utf-8 -*-
"""Test enums and other types"""

import unittest

from utils import PyrseasTestCase, fix_indent, new_std_map

CREATE_ENUM_STMT = "CREATE TYPE t1 AS ENUM ('red', 'green', 'blue')"
DROP_STMT = "DROP TYPE IF EXISTS t1"
COMMENT_STMT = "COMMENT ON TYPE t1 IS 'Test type t1'"


class EnumToMapTestCase(PyrseasTestCase):
    """Test mapping of created enum types"""

    def test_enum(self):
        "Map an enum"
        self.db.execute_commit(DROP_STMT)
        expmap = {'labels': ['red', 'green', 'blue']}
        dbmap = self.db.execute_and_map(CREATE_ENUM_STMT)
        self.assertEqual(dbmap['schema public']['type t1'], expmap)


class EnumToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input enums"""

    def test_create_enum(self):
        "Create an enum"
        self.db.execute_commit(DROP_STMT)
        inmap = new_std_map()
        inmap['schema public'].update({'type t1': {
                    'labels': ['red', 'green', 'blue']}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_ENUM_STMT)

    def test_drop_enum(self):
        "Drop an existing enum"
        self.db.execute(DROP_STMT)
        self.db.execute_commit(CREATE_ENUM_STMT)
        inmap = new_std_map()
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["DROP TYPE t1"])

    def test_rename_enum(self):
        "Rename an existing enum"
        self.db.execute(DROP_STMT)
        self.db.execute_commit(CREATE_ENUM_STMT)
        inmap = new_std_map()
        inmap['schema public'].update({'type t2': {
                    'oldname': 't1', 'labels': ['red', 'green', 'blue']}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["ALTER TYPE t1 RENAME TO t2"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(EnumToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            EnumToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
