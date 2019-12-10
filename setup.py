#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pyrseas - Utilities to assist with database schema versioning.
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
    version='0.8.7',
    packages=['pyrseas', 'pyrseas.dbobject', 'pyrseas.lib', 'pyrseas.augment',
             ],
    package_data={'pyrseas': ['config.yaml']},
    entry_points={
        'console_scripts': [
            'dbtoyaml = pyrseas.dbtoyaml:main',
            'yamltodb = pyrseas.yamltodb:main',
            'dbaugment = pyrseas.dbaugment:main']},

    install_requires=[
        'psycopg2-binary >= 2.8.0',
        'PyYAML >= 5.1.0'],

    tests_require=['pytest'],
    cmdclass={'test': PyTest},

    author='David Chang',
    author_email='dchang@devoted.com',
    description='Utilities to assist in database schema versioning',
    long_description=open('README.rst').read(),
    url='https://perseas.github.io/',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: SQL',
        'Topic :: Database :: Front-Ends',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Software Development :: Version Control'],
    platforms='OS-independent',
    license='BSD')
