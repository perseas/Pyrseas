# -*- coding: utf-8 -*-
"""Pyrseas unit tests"""

import unittest

import test_language
import test_cast
import test_schema
import test_type
import test_domain
import test_sequence
import test_table
import test_column
import test_constraint
import test_index
import test_view
import test_function
import test_operator
import test_operfamily
import test_operclass
import test_trigger
import test_rule
import test_conversion
import test_textsearch
import test_foreign


def suite():
    tests = unittest.TestSuite()
    tests.addTest(test_language.suite())
    tests.addTest(test_cast.suite())
    tests.addTest(test_schema.suite())
    tests.addTest(test_type.suite())
    tests.addTest(test_domain.suite())
    tests.addTest(test_sequence.suite())
    tests.addTest(test_table.suite())
    tests.addTest(test_column.suite())
    tests.addTest(test_constraint.suite())
    tests.addTest(test_index.suite())
    tests.addTest(test_view.suite())
    tests.addTest(test_function.suite())
    tests.addTest(test_operator.suite())
    tests.addTest(test_operfamily.suite())
    tests.addTest(test_operclass.suite())
    tests.addTest(test_trigger.suite())
    tests.addTest(test_rule.suite())
    tests.addTest(test_conversion.suite())
    tests.addTest(test_textsearch.suite())
    tests.addTest(test_foreign.suite())
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
