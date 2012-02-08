# -*- coding: utf-8 -*-
"""Test domains"""

import unittest

from pyrseas.testutils import PyrseasTestCase, fix_indent

CREATE_STMT = "CREATE DOMAIN d1 AS integer"
DROP_STMT = "DROP DOMAIN IF EXISTS d1"
COMMENT_STMT = "COMMENT ON DOMAIN d1 IS 'Test domain d1'"


class DomainToMapTestCase(PyrseasTestCase):
    """Test mapping of created domains"""

    def test_domain(self):
        "Map a simple domain"
        self.db.execute_commit(DROP_STMT)
        expmap = {'type': 'integer'}
        dbmap = self.db.execute_and_map(CREATE_STMT)
        self.assertEqual(dbmap['schema public']['domain d1'], expmap)

    def test_domain_not_null(self):
        "Map a domain with a NOT NULL constraint"
        self.db.execute_commit(DROP_STMT)
        ddlstmt = CREATE_STMT + " NOT NULL"
        expmap = {'type': 'integer', 'not_null': True}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['domain d1'], expmap)

    def test_domain_default(self):
        "Map a domain with a DEFAULT"
        self.db.execute_commit(DROP_STMT)
        ddlstmt = "CREATE DOMAIN d1 AS date DEFAULT CURRENT_DATE"
        expmap = {'type': 'date', 'default': "('now'::text)::date"}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['domain d1'], expmap)

    def test_domain_check(self):
        "Map a domain with a CHECK constraint"
        self.db.execute_commit(DROP_STMT)
        ddlstmt = CREATE_STMT + " CHECK (VALUE >= 1888)"
        expmap = {'type': 'integer', 'check_constraints': {
                'd1_check': {'expression': '(VALUE >= 1888)'}}}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['domain d1'], expmap)


class DomainToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input domains"""

    def test_create_domain(self):
        "Create a simple domain"
        self.db.execute_commit(DROP_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'domain d1': {'type': 'integer'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [CREATE_STMT])

    def test_create_domain_default(self):
        "Create a domain with a DEFAULT and NOT NULL"
        self.db.execute_commit(DROP_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'domain d1': {
                    'type': 'integer', 'not_null': True, 'default': 0}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [CREATE_STMT + " NOT NULL DEFAULT 0"])

    def test_create_domain_check(self):
        "Create a domain with a CHECK constraint"
        self.db.execute_commit(DROP_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'domain d1': {
                    'type': 'integer', 'check_constraints': {
                        'd1_check': {'expression': '(VALUE >= 1888)'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_STMT
                         + " CONSTRAINT d1_check CHECK (VALUE >= 1888)")

    def test_drop_domain(self):
        "Drop an existing domain"
        self.db.execute(DROP_STMT)
        self.db.execute_commit(CREATE_STMT)
        inmap = self.std_map()
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["DROP DOMAIN d1"])

    def test_rename_domain(self):
        "Rename an existing domain"
        self.db.execute(DROP_STMT)
        self.db.execute_commit(CREATE_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'domain d2': {
                    'oldname': 'd1', 'type': 'integer'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["ALTER DOMAIN d1 RENAME TO d2"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(DomainToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            DomainToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
