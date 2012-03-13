# -*- coding: utf-8 -*-
"""Test audit columns"""

import unittest

from pyrseas.testutils import PyrseasTestCase

CREATE_STMT = "CREATE TABLE t1 (c1 integer, c2 text)"
FUNC_SRC = """\
BEGIN
    NEW.modified_by_user = CURRENT_USER;
    NEW.modified_timestamp = CURRENT_TIMESTAMP;
    RETURN NEW;
END """


class AuditColumnsTestCase(PyrseasTestCase):
    """Test mapping of audit column extensions"""

    def test_predef_column(self):
        "Add predefined audit column"
        self.db.execute_commit(CREATE_STMT)
        extmap = {'schema public': {'table t1': {
                    'audit_columns': 'created_date_only'}}}
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}},
                              {'created_date': {
                    'type': 'date', 'not_null': True,
                    'default': "('now'::text)::date"}}]}
        dbmap = self.db.process_extmap(extmap)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_new_column(self):
        "Add new (non-predefined) audit column"
        self.db.execute_commit(CREATE_STMT)
        extmap = {'extender': {'columns': {
                    'modified_date': {'type': 'date', 'not_null': True,
                                      'default': "('now'::text)::date"}},
                               'audit_columns': {'modified_date_only': {
                    'columns': ['modified_date']}}},
                  'schema public': {'table t1': {
                    'audit_columns': 'modified_date_only'}}}
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}},
                              {'modified_date': {
                    'type': 'date', 'not_null': True,
                    'default': "('now'::text)::date"}}]}
        dbmap = self.db.process_extmap(extmap)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_rename_column(self):
        "Add predefined audit column but with new name"
        self.db.execute_commit(CREATE_STMT)
        extmap = {'extender': {'columns': {
                    'created_date': {'name': 'created'}}},
                  'schema public': {'table t1': {
                    'audit_columns': 'created_date_only'}}}
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}},
                              {'created': {
                    'type': 'date', 'not_null': True,
                    'default': "('now'::text)::date"}}]}
        dbmap = self.db.process_extmap(extmap)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_change_column_type(self):
        "Add predefined audit column but with changed datatype"
        self.db.execute_commit(CREATE_STMT)
        extmap = {'extender': {'columns': {
                    'created_date': {'type': 'text'}}},
                  'schema public': {'table t1': {
                    'audit_columns': 'created_date_only'}}}
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}},
                              {'created_date': {
                    'type': 'text', 'not_null': True,
                    'default': "('now'::text)::date"}}]}
        dbmap = self.db.process_extmap(extmap)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_columns_with_trigger(self):
        "Add predefined audit columns with trigger"
        self.db.execute_commit(CREATE_STMT)
        extmap = {'schema public': {'table t1': {
                    'audit_columns': 'default'}}}
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}},
                              {'modified_by_user': {
                        'type': 'character varying(63)', 'not_null': True}},
                              {'modified_timestamp': {
                        'type': 'timestamp with time zone',
                        'not_null': True}}],
                  'triggers': {'t1_20_aud_dflt': {
                    'events': ['update'], 'level': 'row',
                    'procedure': 'aud_dflt()', 'timing': 'before'}}}
        dbmap = self.db.process_extmap(extmap)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)
        self.assertEqual(dbmap['schema public']['function aud_dflt()'][
                'returns'], 'trigger')
        self.assertEqual(dbmap['schema public']['function aud_dflt()'][
                'source'], FUNC_SRC)

    def test_nonpublic_schema_with_trigger(self):
        "Add predefined audit columns with trigger in a non-public schema"
        self.db.execute("DROP SCHEMA IF EXISTS s1 CASCADE")
        self.db.execute("CREATE SCHEMA s1")
        self.db.execute_commit("CREATE TABLE s1.t1 (c1 integer, c2 text)")
        extmap = {'schema s1': {'table t1': {
                    'audit_columns': 'default'}}}
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}},
                              {'modified_by_user': {
                        'type': 'character varying(63)', 'not_null': True}},
                              {'modified_timestamp': {
                        'type': 'timestamp with time zone',
                        'not_null': True}}],
                  'triggers': {'t1_20_aud_dflt': {
                    'events': ['update'], 'level': 'row',
                    'procedure': 's1.aud_dflt()', 'timing': 'before'}}}
        dbmap = self.db.process_extmap(extmap)
        self.db.execute_commit("DROP SCHEMA s1 CASCADE")
        self.assertEqual(dbmap['schema s1']['table t1'], expmap)
        self.assertEqual(dbmap['schema s1']['function aud_dflt()'][
                'returns'], 'trigger')
        self.assertEqual(dbmap['schema s1']['function aud_dflt()'][
                'source'], FUNC_SRC)

    def test_skip_existing_columns(self):
        "Do not add already existing audit columns"
        self.db.execute(CREATE_STMT)
        self.db.execute("ALTER TABLE t1 ADD modified_by_user varchar(63) "
                        "NOT NULL")
        self.db.execute_commit("ALTER TABLE t1 ADD modified_timestamp "
                               "timestamp with time zone NOT NULL")
        extmap = {'schema public': {'table t1': {
                    'audit_columns': 'default'}}}
        expmap = [{'c1': {'type': 'integer'}},
                  {'c2': {'type': 'text'}},
                  {'modified_by_user': {
                    'type': 'character varying(63)', 'not_null': True}},
                  {'modified_timestamp': {
                    'type': 'timestamp with time zone', 'not_null': True}}]
        dbmap = self.db.process_extmap(extmap)
        self.assertEqual(dbmap['schema public']['table t1']['columns'], expmap)

    def test_change_existing_columns(self):
        "Change already existing audit columns"
        self.db.execute(CREATE_STMT)
        self.db.execute("ALTER TABLE t1 ADD modified_by_user text ")
        self.db.execute_commit("ALTER TABLE t1 ADD modified_timestamp "
                               "timestamp with time zone NOT NULL")
        extmap = {'schema public': {'table t1': {
                    'audit_columns': 'default'}}}
        expmap = [{'c1': {'type': 'integer'}},
                  {'c2': {'type': 'text'}},
                  {'modified_by_user': {
                    'type': 'character varying(63)', 'not_null': True}},
                  {'modified_timestamp': {
                    'type': 'timestamp with time zone', 'not_null': True}}]
        dbmap = self.db.process_extmap(extmap)
        self.assertEqual(dbmap['schema public']['table t1']['columns'], expmap)


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(AuditColumnsTestCase)
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
