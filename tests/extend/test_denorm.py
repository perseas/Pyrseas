# -*- coding: utf-8 -*-
"""Test denormalized columns"""

import unittest

from pyrseas.testutils import ExtensionToMapTestCase


CREATE_STMT1 = "CREATE TABLE t1 (c11 integer PRIMARY KEY, c12 text)"
CREATE_STMT2 = "CREATE TABLE t2 (c21 integer PRIMARY KEY, c22 text, " \
    "c23 integer NOT NULL REFERENCES t1 (c11))"
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


class CopyDenormalizationTestCase(ExtensionToMapTestCase):
    """Test mapping of copy denormalization extensions"""

    def test_copy_column(self):
        "Copy a column from a 'parent' table"
        stmts = [CREATE_STMT1, CREATE_STMT2]
        extmap = {'schema public': {'table t2': {'denorm_columns': [
                        {'c12_copy': {'copy': 'c12',
                                      'foreign_key': 't2_c23_fkey'}}]}}}
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
                       "Copies into column t2.c12_copy from t1.c12.",
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
                      "Forces cascade of t1.c12 onto t2.c12_copy.",
                  'language': 'plpgsql', 'returns': 'trigger',
                  'source': PARENT_FUNC_SRC}
        self.assertEqual(dbmap['schema public']['table t2'], childtbl)
        self.assertEqual(dbmap['schema public']['function t2_denorm()'],
                         childfnc)
        self.assertEqual(dbmap['schema public']['table t1'], partbl)
        self.assertEqual(dbmap['schema public']['function t1_cascade()'],
                         parfnc)


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(
        CopyDenormalizationTestCase)
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
