#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pyrseas - Framework and utilities to upgrade and maintain databases.
"""

from setuptools import setup

setup(
    name='Pyrseas',
    version='0.5.0',
    packages=['pyrseas', 'pyrseas.dbobject'],
    entry_points={
        'console_scripts': [
            'dbtoyaml = pyrseas.dbtoyaml:main',
            'yamltodb = pyrseas.yamltodb:main']},

    install_requires=[
        'setuptools >= 0.6',
        'psycopg2 >= 2.2',
        'PyYAML >= 3.09'],

    test_suite='tests.dbobject',

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
