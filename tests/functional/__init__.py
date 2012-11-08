# -*- coding: utf-8 -*-
"""Pyrseas functional tests"""

import unittest

from tests.functional import test_autodoc
from tests.functional import test_filmversions
from tests.functional import test_pagila


def suite():
    tests = unittest.TestSuite()
    tests.addTest(test_autodoc.suite())
    tests.addTest(test_filmversions.suite())
    tests.addTest(test_pagila.suite())
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
