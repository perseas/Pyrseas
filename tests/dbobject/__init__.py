# -*- coding: utf-8 -*-
"""Pyrseas unit tests"""

import unittest

import test_schema
import test_sequence
import test_table
import test_constraint
import test_index


def suite():
    tests = unittest.TestSuite()
    tests.addTest(test_schema.suite())
    tests.addTest(test_sequence.suite())
    tests.addTest(test_table.suite())
    tests.addTest(test_constraint.suite())
    tests.addTest(test_index.suite())
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
