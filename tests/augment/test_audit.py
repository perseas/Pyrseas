# -*- coding: utf-8 -*-
"""Test audit columns"""

import pytest

from pyrseas.testutils import AugmentToMapTestCase

CREATE_STMT = "CREATE TABLE t1 (c1 integer, c2 text)"
FUNC_SRC = """\
BEGIN
  NEW.modified_by_user = CURRENT_USER;
  NEW.modified_timestamp = CURRENT_TIMESTAMP;
  RETURN NEW;
END"""


class AuditColumnsTestCase(AugmentToMapTestCase):
    """Test mapping of audit column augmentations"""

    def test_predef_column(self):
        "Add predefined audit column"
        augmap = {'schema public': {'table t1': {
            'audit_columns': 'created_date_only'}}}
        dbmap = self.to_map([CREATE_STMT], augmap)
        expmap = {'columns': [
            {'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
            {'created_date': {'type': 'date', 'not_null': True,
                              'default': "('now'::text)::date"}}]}
        assert expmap == dbmap['schema public']['table t1']

    def test_unknown_table(self):
        "Error on non-existent table"
        augmap = {'schema public': {'table t2': {
            'audit_columns': 'created_date_only'}}}
        with pytest.raises(KeyError):
            self.to_map([CREATE_STMT], augmap)

    def test_bad_audit_spec(self):
        "Error on bad audit column specification"
        augmap = {'schema public': {'table t1': {
            'audit_column': 'created_date_only'}}}
        with pytest.raises(KeyError):
            self.to_map([CREATE_STMT], augmap)

    def test_unknown_audit_spec(self):
        "Error on non-existent audit column specification"
        augmap = {'schema public': {'table t1': {
            'audit_columns': 'created_date'}}}
        with pytest.raises(KeyError):
            self.to_map([CREATE_STMT], augmap)

    def test_new_column(self):
        "Add new (non-predefined) audit column"
        augmap = {'augmenter': {'columns': {
            'modified_date': {'type': 'date', 'not_null': True,
                              'default': "('now'::text)::date"}},
            'audit_columns': {'modified_date_only': {
                'columns': ['modified_date']}}},
            'schema public': {'table t1': {
                'audit_columns': 'modified_date_only'}}}
        dbmap = self.to_map([CREATE_STMT], augmap)
        expmap = {'columns': [
            {'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
            {'modified_date': {'type': 'date', 'not_null': True,
                               'default': "('now'::text)::date"}}]}
        assert expmap == dbmap['schema public']['table t1']

    def test_rename_column(self):
        "Add predefined audit column but with new name"
        augmap = {'augmenter': {'columns': {
            'created_date': {'name': 'created'}}},
            'schema public': {'table t1': {
                'audit_columns': 'created_date_only'}}}
        dbmap = self.to_map([CREATE_STMT], augmap)
        expmap = {'columns': [
            {'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
            {'created': {'type': 'date', 'not_null': True,
                         'default': "('now'::text)::date"}}]}
        assert expmap == dbmap['schema public']['table t1']

    def test_change_column_type(self):
        "Add predefined audit column but with changed datatype"
        augmap = {'augmenter': {'columns': {'created_date': {'type': 'text'}}},
                  'schema public': {'table t1': {
                  'audit_columns': 'created_date_only'}}}
        dbmap = self.to_map([CREATE_STMT], augmap)
        expmap = {'columns': [
            {'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
            {'created_date': {'type': 'text', 'not_null': True,
                              'default': "('now'::text)::date"}}]}
        assert expmap == dbmap['schema public']['table t1']

    def test_columns_with_trigger(self):
        "Add predefined audit columns with trigger"
        augmap = {'schema public': {'table t1': {'audit_columns': 'default'}}}
        dbmap = self.to_map([CREATE_STMT], augmap)
        expmap = {'columns': [
            {'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
            {'modified_by_user': {'type': 'character varying(63)',
                                  'not_null': True}},
            {'modified_timestamp': {'type': 'timestamp with time zone',
                                    'not_null': True}}],
            'triggers': {'t1_20_audit_default': {
                'events': ['update'], 'level': 'row',
                'procedure': 'audit_default()', 'timing': 'before'}}}
        assert expmap == dbmap['schema public']['table t1']
        assert dbmap['schema public']['function audit_default()'][
            'returns'] == 'trigger'
        assert dbmap['schema public']['function audit_default()'][
            'source'] == FUNC_SRC

    def test_nonpublic_schema_with_trigger(self):
        "Add predefined audit columns with trigger in a non-public schema"
        stmts = ["CREATE SCHEMA s1",
                 "CREATE TABLE s1.t1 (c1 integer, c2 text)"]
        augmap = {'schema s1': {'table t1': {'audit_columns': 'default'}}}
        dbmap = self.to_map(stmts, augmap)
        expmap = {'columns': [
            {'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
            {'modified_by_user': {'type': 'character varying(63)',
                                  'not_null': True}},
            {'modified_timestamp': {'type': 'timestamp with time zone',
                                    'not_null': True}}],
            'triggers': {'t1_20_audit_default': {
                'events': ['update'], 'level': 'row',
                'procedure': 's1.audit_default()', 'timing': 'before'}}}
        assert expmap == dbmap['schema s1']['table t1']
        assert dbmap['schema s1']['function audit_default()']['returns'] == \
            'trigger'
        assert dbmap['schema s1']['function audit_default()'][
            'source'] == FUNC_SRC

    def test_skip_existing_columns(self):
        "Do not add already existing audit columns"
        stmts = [CREATE_STMT,
                 "ALTER TABLE t1 ADD modified_by_user varchar(63) NOT NULL",
                 "ALTER TABLE t1 ADD modified_timestamp "
                 "timestamp with time zone NOT NULL"]
        augmap = {'schema public': {'table t1': {
            'audit_columns': 'default'}}}
        dbmap = self.to_map(stmts, augmap)
        expmap = [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                  {'modified_by_user': {'type': 'character varying(63)',
                                        'not_null': True}},
                  {'modified_timestamp': {'type': 'timestamp with time zone',
                                          'not_null': True}}]
        assert expmap == dbmap['schema public']['table t1']['columns']

    def test_change_existing_columns(self):
        "Change already existing audit columns"
        stmts = [CREATE_STMT, "ALTER TABLE t1 ADD modified_by_user text ",
                 "ALTER TABLE t1 ADD modified_timestamp "
                 "timestamp with time zone NOT NULL"]
        augmap = {'schema public': {'table t1': {'audit_columns': 'default'}}}
        dbmap = self.to_map(stmts, augmap)
        expmap = [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                  {'modified_by_user': {'type': 'character varying(63)',
                                        'not_null': True}},
                  {'modified_timestamp': {'type': 'timestamp with time zone',
                                          'not_null': True}}]
        assert expmap == dbmap['schema public']['table t1']['columns']
