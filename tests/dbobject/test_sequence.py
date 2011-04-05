# -*- coding: utf-8 -*-
"""Test schemas"""

import unittest

from utils import PyrseasTestCase, fix_indent

DROP_STMT = "DROP SEQUENCE IF EXISTS seq1"


class SequenceToMapTestCase(PyrseasTestCase):
    """Test mapping of created sequences"""

    def test_map_sequence(self):
        "Map a created sequence"
        ddlstmt = "CREATE SEQUENCE seq1"
        expmap = {'start_value': 1, 'increment_by': 1, 'max_value': None,
                  'min_value': None, 'cache_value': 1}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['sequence seq1'],
                         expmap)


class SequenceToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input sequences"""

    def test_create_sequence(self):
        "Create a sequence"
        self.db.execute_commit(DROP_STMT)
        inmap = {'schema public': {'sequence seq1': {
                    'start_value': 1, 'increment_by': 1, 'max_value': None,
                    'min_value': None, 'cache_value': 1}}}
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "CREATE SEQUENCE seq1 START WITH 1 "
                         "INCREMENT BY 1 NO MAXVALUE NO MINVALUE CACHE 1")

    def test_create_sequence_in_schema(self):
        "Create a sequence within a non-public schema"
        self.db.execute("CREATE SCHEMA s1")
        self.db.execute_commit(DROP_STMT)
        inmap = {'schema s1': {'sequence seq1': {
                    'start_value': 1, 'increment_by': 1, 'max_value': None,
                    'min_value': None, 'cache_value': 1}}}
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "CREATE SEQUENCE s1.seq1 START WITH 1 "
                         "INCREMENT BY 1 NO MAXVALUE NO MINVALUE CACHE 1")
        self.db.execute_commit("DROP SCHEMA s1 CASCADE")

    def test_bad_sequence_map(self):
        "Error creating a sequence with a bad map"
        inmap = {'schema public': {'seq1': {
                    'start_value': 1, 'increment_by': 1, 'max_value': None,
                    'min_value': None, 'cache_value': 1}}}
        self.assertRaises(KeyError, self.db.process_map, inmap)

    def test_drop_sequence(self):
        "Drop an existing sequence"
        self.db.execute(DROP_STMT)
        self.db.execute_commit("CREATE SEQUENCE seq1")
        dbsql = self.db.process_map({'schema public': {}})
        self.assertEqual(dbsql, ["DROP SEQUENCE seq1"])

    def test_rename_sequence(self):
        "Rename an existing sequence"
        self.db.execute(DROP_STMT)
        self.db.execute_commit("CREATE SEQUENCE seq1")
        inmap = {'schema public': {'sequence seq2': {
                    'oldname': 'seq1',
                    'start_value': 1, 'increment_by': 1, 'max_value': None,
                    'min_value': None, 'cache_value': 1}}}
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["ALTER SEQUENCE seq1 RENAME TO seq2"])

    def test_bad_rename_sequence(self):
        "Error renaming a non-existing sequence"
        self.db.execute(DROP_STMT)
        self.db.execute_commit("CREATE SEQUENCE seq1")
        inmap = {'schema public': {'sequence seq2': {
                    'oldname': 'seq3',
                    'start_value': 1, 'increment_by': 1, 'max_value': None,
                    'min_value': None, 'cache_value': 1}}}
        self.assertRaises(KeyError, self.db.process_map, inmap)

    def test_change_sequence(self):
        "Change sequence attributes"
        self.db.execute(DROP_STMT)
        self.db.execute_commit("CREATE SEQUENCE seq1")
        inmap = {'schema public': {'sequence seq1': {
                    'start_value': 5, 'increment_by': 10, 'max_value': None,
                    'min_value': None, 'cache_value': 30}}}
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "ALTER SEQUENCE seq1 START WITH 5 INCREMENT BY 10 "
                         "CACHE 30")


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(SequenceToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            SequenceToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
