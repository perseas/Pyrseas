# -*- coding: utf-8 -*-
"""Pyrseas unit tests"""

import unittest

import test_language
import test_schema
import test_sequence
import test_table
import test_constraint
import test_index
import test_view
import test_function


def suite():
    tests = unittest.TestSuite()
    tests.addTest(test_language.suite())
    tests.addTest(test_schema.suite())
    tests.addTest(test_sequence.suite())
    tests.addTest(test_table.suite())
    tests.addTest(test_constraint.suite())
    tests.addTest(test_index.suite())
    tests.addTest(test_view.suite())
    tests.addTest(test_function.suite())
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
