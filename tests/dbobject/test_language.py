# -*- coding: utf-8 -*-
"""Test languages"""

import unittest

from utils import PyrseasTestCase

CREATE_STMT = "CREATE LANGUAGE plperl"
DROP_STMT = "DROP LANGUAGE IF EXISTS plperl CASCADE"


class LanguageToMapTestCase(PyrseasTestCase):
    """Test mapping of existing languages"""

    def test_map_language(self):
        "Map an existing language"
        self.db.execute(DROP_STMT)
        dbmap = self.db.execute_and_map(CREATE_STMT)
        self.assertEqual(dbmap['language plperl'], {'trusted': True})


class LanguageToSqlTestCase(PyrseasTestCase):
    """Test SQL generation for input languages"""

    def tearDown(self):
        self.db.execute_commit(DROP_STMT)
        self.db.close()

    def test_create_language(self):
        "Create a language that didn't exist"
        self.db.execute_commit(DROP_STMT)
        dbsql = self.db.process_map({'language plperl': {}})
        self.assertEqual(dbsql, [CREATE_STMT])

    def test_bad_language_map(self):
        "Error creating a language with a bad map"
        self.assertRaises(KeyError, self.db.process_map, {'plperl': {}})

    def test_drop_language(self):
        "Drop an existing language"
        self.db.execute(DROP_STMT)
        self.db.execute_commit(CREATE_STMT)
        dbsql = self.db.process_map({})
        self.assertEqual(dbsql, ["DROP LANGUAGE plperl"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(LanguageToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            LanguageToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
