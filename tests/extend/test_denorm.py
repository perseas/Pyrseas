# -*- coding: utf-8 -*-
"""Test denormalized columns"""

import unittest

from pyrseas.testutils import ExtensionToMapTestCase


CREATE_STMT1 = "CREATE TABLE %st1 (c11 integer PRIMARY KEY, c12 text%s)"
CREATE_STMT2 = "CREATE TABLE %st2 (c21 integer PRIMARY KEY, c22 text, " \
    "c23 integer NOT NULL REFERENCES %st1 (c11))"
CHILD_FUNC_SRC = """\
BEGIN
    IF TG_OP = 'INSERT' THEN
        SELECT c12
               INTO NEW.c12_copy
        FROM public.t1
        WHERE c11 = NEW.c23;
    ELSIF TG_OP = 'UPDATE' AND (
           NEW.c23 IS DISTINCT FROM OLD.c23 OR
           NEW.c12_copy IS NULL) THEN
        SELECT c12
               INTO NEW.c12_copy
        FROM public.t1
        WHERE c11 = NEW.c23;
    ELSE
        NEW.c12_copy := OLD.c12_copy;
    END IF;
    RETURN NEW;
END """
PARENT_FUNC_SRC = """\
BEGIN
    IF TG_OP = 'UPDATE' AND (
            NEW.c12 IS DISTINCT FROM OLD.c12) THEN
        UPDATE public.t2
        SET c12_copy = NULL
        WHERE c23 = NEW.c23;
    END IF;
    RETURN NULL;
END """

CHILD_FUNC_SRC2 = """\
BEGIN
    IF TG_OP = 'INSERT' THEN
        SELECT c12, c13, c14
               INTO NEW.c12_copy, NEW.c13, NEW.child_c14
        FROM sp.t1
        WHERE c11 = NEW.c23;
    ELSIF TG_OP = 'UPDATE' AND (
           NEW.c23 IS DISTINCT FROM OLD.c23 OR
           NEW.c12_copy IS NULL OR
           NEW.c13 IS NULL OR
           NEW.child_c14 IS NULL) THEN
        SELECT c12, c13, c14
               INTO NEW.c12_copy, NEW.c13, NEW.child_c14
        FROM sp.t1
        WHERE c11 = NEW.c23;
    ELSE
        NEW.c12_copy := OLD.c12_copy;
        NEW.c13 := OLD.c13;
        NEW.child_c14 := OLD.child_c14;
    END IF;
    RETURN NEW;
END """
PARENT_FUNC_SRC2 = """\
BEGIN
    IF TG_OP = 'UPDATE' AND (
            NEW.c12 IS DISTINCT FROM OLD.c12) THEN
        UPDATE sc.t2
        SET c12_copy = NULL
        WHERE c23 = NEW.c23;
    END IF;
    IF TG_OP = 'UPDATE' AND (
            NEW.c13 IS DISTINCT FROM OLD.c13) THEN
        UPDATE sc.t2
        SET c13 = NULL
        WHERE c23 = NEW.c23;
    END IF;
    IF TG_OP = 'UPDATE' AND (
            NEW.c14 IS DISTINCT FROM OLD.c14) THEN
        UPDATE sc.t2
        SET child_c14 = NULL
        WHERE c23 = NEW.c23;
    END IF;
    RETURN NULL;
END """


class CopyDenormalizationTestCase(ExtensionToMapTestCase):
    """Test mapping of copy denormalization extensions"""

    def test_copy_column(self):
        "Copy a column from a 'parent' table"
        stmts = [CREATE_STMT1 % ('', ''), CREATE_STMT2 % ('', '')]
        extmap = {'schema public': {'table t2': {'denorm_columns': [
                        {'copy': {'foreign_key': 't2_c23_fkey', 'columns': [
                                    {'c12': 'c12_copy'}]}}]}}}
        dbmap = self.to_map(stmts, extmap)
        childtbl = {'columns': [{'c21': {'type': 'integer', 'not_null': True}},
                                {'c22': {'type': 'text'}},
                                {'c23': {'type': 'integer', 'not_null': True}},
                                {'c12_copy': {'type': 'text'}}],
                    'primary_key': {'t2_pkey': {'access_method': 'btree',
                                                'columns': ['c21']}},
                    'foreign_keys': {'t2_c23_fkey': {
                    'columns': ['c23'], 'references': {
                        'schema': 'public', 'table': 't1', 'columns':
                            ['c11']}}},
                    'triggers': {'t2_40_denorm': {
                    'timing': 'before', 'events': ['insert', 'update'],
                    'level': 'row', 'procedure': 't2_denorm()'}}}
        childfnc = {'description':
                        "Copies column(s) from public.t1 into public.t2.",
                    'language': 'plpgsql', 'returns': 'trigger',
                    'source': CHILD_FUNC_SRC}
        partbl = {'columns': [{'c11': {'type': 'integer', 'not_null': True}},
                              {'c12': {'type': 'text'}}],
                  'primary_key': {'t1_pkey': {'access_method': 'btree',
                                              'columns': ['c11']}},
                  'triggers': {'t1_60_cascade': {
                    'timing': 'after', 'events': ['update'], 'level': 'row',
                    'procedure': 't1_cascade()'}}}
        parfnc = {'description':
                      "Forces cascade of column(s) from public.t1 onto " \
                      "public.t2.",
                  'language': 'plpgsql', 'returns': 'trigger',
                  'source': PARENT_FUNC_SRC}
        self.assertEqual(dbmap['schema public']['table t2'], childtbl)
        self.assertEqual(dbmap['schema public']['table t1'], partbl)
        self.assertEqual(dbmap['schema public']['function t2_denorm()'],
                         childfnc)
        self.assertEqual(dbmap['schema public']['function t1_cascade()'],
                         parfnc)

    def test_copy_columns_cross_schema(self):
        "Copy two columns from a 'parent' table to a child in another schema"
        stmts = ["CREATE SCHEMA sp", "CREATE SCHEMA sc",
                 CREATE_STMT1 % ("sp.", ", c13 date, c14 boolean"),
                 CREATE_STMT2 % ('sc.', 'sp.')]
        extmap = {'schema sc': {'table t2': {'denorm_columns': [
                        {'copy': {'foreign_key': 't2_c23_fkey', 'columns': [
                                    {'c12': {'suffix': '_copy'}}, 'c13',
                                    {'c14': {'prefix': 'child_'}}]}}]}}}
        dbmap = self.to_map(stmts, extmap)
        childtbl = {'columns': [{'c21': {'type': 'integer', 'not_null': True}},
                                {'c22': {'type': 'text'}},
                                {'c23': {'type': 'integer', 'not_null': True}},
                                {'c12_copy': {'type': 'text'}},
                                {'c13': {'type': 'date'}},
                                {'child_c14': {'type': 'boolean'}}],
                    'primary_key': {'t2_pkey': {'access_method': 'btree',
                                                'columns': ['c21']}},
                    'foreign_keys': {'t2_c23_fkey': {
                    'columns': ['c23'], 'references': {
                        'schema': 'sp', 'table': 't1', 'columns':
                            ['c11']}}},
                    'triggers': {'t2_40_denorm': {
                    'timing': 'before', 'events': ['insert', 'update'],
                    'level': 'row', 'procedure': 'sc.t2_denorm()'}}}
        childfnc = {'description':
                       "Copies column(s) from sp.t1 into sc.t2.",
                    'language': 'plpgsql', 'returns': 'trigger',
                    'source': CHILD_FUNC_SRC2}
        partbl = {'columns': [{'c11': {'type': 'integer', 'not_null': True}},
                              {'c12': {'type': 'text'}},
                              {'c13': {'type': 'date'}},
                              {'c14': {'type': 'boolean'}}],
                  'primary_key': {'t1_pkey': {'access_method': 'btree',
                                              'columns': ['c11']}},
                  'triggers': {'t1_60_cascade': {
                    'timing': 'after', 'events': ['update'], 'level': 'row',
                    'procedure': 'sp.t1_cascade()'}}}
        parfnc = {'description':
                      "Forces cascade of column(s) from sp.t1 onto sc.t2.",
                  'language': 'plpgsql', 'returns': 'trigger',
                  'source': PARENT_FUNC_SRC2}
        self.assertEqual(dbmap['schema sc']['table t2'], childtbl)
        self.assertEqual(dbmap['schema sp']['table t1'], partbl)
        self.assertEqual(dbmap['schema sc']['function t2_denorm()'],
                         childfnc)
        self.assertEqual(dbmap['schema sp']['function t1_cascade()'],
                         parfnc)


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(
        CopyDenormalizationTestCase)
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
