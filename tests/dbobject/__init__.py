# -*- coding: utf-8 -*-
"""Pyrseas unit tests"""

import unittest

import test_language
import test_schema
import test_type
import test_domain
import test_sequence
import test_table
import test_constraint
import test_index
import test_view
import test_function
import test_trigger


def suite():
    tests = unittest.TestSuite()
    tests.addTest(test_language.suite())
    tests.addTest(test_schema.suite())
    tests.addTest(test_type.suite())
    tests.addTest(test_domain.suite())
    tests.addTest(test_sequence.suite())
    tests.addTest(test_table.suite())
    tests.addTest(test_constraint.suite())
    tests.addTest(test_index.suite())
    tests.addTest(test_view.suite())
    tests.addTest(test_function.suite())
    tests.addTest(test_trigger.suite())
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
