#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pyrseas - Framework and utilities to upgrade and maintain databases.
"""
import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True
    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(
    name='Pyrseas',
    version='0.7-dev',
    packages=['pyrseas', 'pyrseas.dbobject', 'pyrseas.lib'],
    entry_points={
        'console_scripts': [
            'dbtoyaml = pyrseas.dbtoyaml:main',
            'yamltodb = pyrseas.yamltodb:main']},

    install_requires=[
        'psycopg2 >= 2.2',
        'PyYAML >= 3.09'],

    tests_require=['pytest'],
    cmdclass = {'test': PyTest},

    author='Joe Abbate',
    author_email='jma@freedomcircle.com',
    description='Framework and utilities to upgrade and maintain databases',
    long_description=open('README').read(),
    url='http://www.pyrseas.org/',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: SQL',
        'Topic :: Database :: Front-Ends',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Software Development :: Version Control'],
    platforms='OS-independent',
    license='BSD')
