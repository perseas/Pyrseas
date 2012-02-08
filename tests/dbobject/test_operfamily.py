# -*- coding: utf-8 -*-
"""Test operator families"""

import unittest

from pyrseas.testutils import PyrseasTestCase, fix_indent

CREATE_STMT = "CREATE OPERATOR FAMILY of1 USING btree"
DROP_STMT = "DROP OPERATOR FAMILY IF EXISTS of1 USING btree"
COMMENT_STMT = "COMMENT ON OPERATOR FAMILY of1 USING btree IS " \
    "'Test operator family of1'"


class OperatorFamilyToMapTestCase(PyrseasTestCase):
    """Test mapping of existing operators"""

    def test_map_operfam(self):
        "Map an operator family"
        expmap = {}
        dbmap = self.db.execute_and_map(CREATE_STMT)
        self.assertEqual(dbmap['schema public'][
                'operator family of1 using btree'], expmap)

    def test_map_operfam_comment(self):
        "Map an operator family comment"
        self.db.execute(CREATE_STMT)
        dbmap = self.db.execute_and_map(COMMENT_STMT)
        self.assertEqual(dbmap['schema public'][
                'operator family of1 using btree']['description'],
                         'Test operator family of1')


class OperatorFamilyToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input operators"""

    def test_create_operfam(self):
        "Create an operator family"
        inmap = self.std_map()
        inmap['schema public'].update({'operator family of1 using btree': {}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_STMT)

    def test_create_operfam_in_schema(self):
        "Create an operator family within a non-public schema"
        self.db.execute("CREATE SCHEMA s1")
        inmap = self.std_map()
        inmap.update({'schema s1': {'operator family of1 using btree': {}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]),
                         "CREATE OPERATOR FAMILY s1.of1 USING btree")
        self.db.execute_commit("DROP SCHEMA s1 CASCADE")

    def test_drop_operfam(self):
        "Drop an existing operator family"
        self.db.execute_commit(CREATE_STMT)
        dbsql = self.db.process_map(self.std_map())
        self.assertEqual(dbsql, ["DROP OPERATOR FAMILY of1 USING btree"])

    def test_operfam_with_comment(self):
        "Create an operator family with a comment"
        inmap = self.std_map()
        inmap['schema public'].update({
                'operator family of1 using btree': {
                    'description': 'Test operator family of1'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_STMT)
        self.assertEqual(dbsql[1], COMMENT_STMT)

    def test_comment_on_operfam(self):
        "Create a comment for an existing operator family"
        self.db.execute_commit(CREATE_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({
                'operator family of1 using btree': {
                    'description': 'Test operator family of1'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [COMMENT_STMT])

    def test_drop_operfam_comment(self):
        "Drop a comment on an existing operator family"
        self.db.execute(CREATE_STMT)
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({
                'operator family of1 using btree': {}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [
                "COMMENT ON OPERATOR FAMILY of1 USING btree IS NULL"])

    def test_change_operfam_comment(self):
        "Change existing comment on a operator"
        self.db.execute(CREATE_STMT)
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({
                'operator family of1 using btree': {
                    'description': 'Changed operator family of1'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [
                "COMMENT ON OPERATOR FAMILY of1 USING btree IS "
                "'Changed operator family of1'"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(
        OperatorFamilyToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            OperatorFamilyToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
