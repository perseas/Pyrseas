# -*- coding: utf-8 -*-
"""Test audit columns"""

import pytest

from pyrseas.testutils import AugmentToMapTestCase

CREATE_STMT = "CREATE TABLE t1 (c1 integer, c2 text)"
FUNC_SRC1 = """
BEGIN
  NEW.modified_by_user = SESSION_USER;
  NEW.modified_timestamp = CURRENT_TIMESTAMP;
  RETURN NEW;
END"""

FUNC_SRC2 = """
BEGIN
  NEW.updated = CURRENT_TIMESTAMP;
  RETURN NEW;
END"""


class AuditColumnsTestCase(AugmentToMapTestCase):
    """Test mapping of audit column augmentations"""

    def test_predef_column(self):
        "Add predefined audit column"
        augmap = {'schema sd': {'table t1': {
            'audit_columns': 'created_date_only'}}}
        dbmap = self.to_map([CREATE_STMT], augmap)
        expmap = {'columns': [
            {'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
            {'created_date': {'type': 'date', 'not_null': True,
                              'default': "('now'::text)::date"}}]}
        assert expmap == dbmap['schema sd']['table t1']

    def test_unknown_table(self):
        "Error on non-existent table"
        augmap = {'schema sd': {'table t2': {
            'audit_columns': 'created_date_only'}}}
        with pytest.raises(KeyError):
            self.to_map([CREATE_STMT], augmap)

    def test_bad_audit_spec(self):
        "Error on bad audit column specification"
        augmap = {'schema sd': {'table t1': {
            'audit_column': 'created_date_only'}}}
        with pytest.raises(KeyError):
            self.to_map([CREATE_STMT], augmap)

    def test_unknown_audit_spec(self):
        "Error on non-existent audit column specification"
        augmap = {'schema sd': {'table t1': {
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
            'schema sd': {'table t1': {
                'audit_columns': 'modified_date_only'}}}
        dbmap = self.to_map([CREATE_STMT], augmap)
        expmap = {'columns': [
            {'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
            {'modified_date': {'type': 'date', 'not_null': True,
                               'default': "('now'::text)::date"}}]}
        assert expmap == dbmap['schema sd']['table t1']

    def test_rename_column(self):
        "Add predefined audit column but with new name"
        augmap = {'augmenter': {'columns': {
            'modified_timestamp': {'name': 'updated'}}},
            'schema sd': {'table t1': {
                'audit_columns': 'modified_only'}}}
        dbmap = self.to_map([CREATE_STMT], augmap)
        colmap = {'columns': [
            {'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
            {'updated': {'type': 'timestamp with time zone',
                         'not_null': True}}],
            'triggers': {'t1_20_audit_modified_only': {
                'events': ['insert', 'update'], 'level': 'row',
                'procedure': 'sd.audit_modified', 'timing': 'before'}}}
        funcmap = {'language': 'plpgsql', 'returns': 'trigger',
                   'security_definer': True, 'description':
                   'Provides modified_timestamp values for audit columns.',
                   'source': FUNC_SRC2}
        assert dbmap['schema sd']['table t1'] == colmap
        assert dbmap['schema sd']['function audit_modified()'] == funcmap

    def test_change_column_type(self):
        "Add predefined audit column but with changed datatype"
        augmap = {'augmenter': {'columns': {'created_date': {'type': 'text'}}},
                  'schema sd': {'table t1': {
                      'audit_columns': 'created_date_only'}}}
        dbmap = self.to_map([CREATE_STMT], augmap)
        expmap = {'columns': [
            {'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
            {'created_date': {'type': 'text', 'not_null': True,
                              'default': "('now'::text)::date"}}]}
        assert expmap == dbmap['schema sd']['table t1']

    def test_columns_with_trigger(self):
        "Add predefined audit columns with trigger"
        augmap = {'schema sd': {'table t1': {'audit_columns': 'default'}}}
        dbmap = self.to_map([CREATE_STMT], augmap)
        expmap = {'columns': [
            {'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
            {'modified_by_user': {'type': 'character varying(63)',
                                  'not_null': True}},
            {'modified_timestamp': {'type': 'timestamp with time zone',
                                    'not_null': True}}],
            'triggers': {'t1_20_audit_default': {
                'events': ['update'], 'level': 'row',
                'procedure': 'sd.audit_default', 'timing': 'before'}}}
        assert expmap == dbmap['schema sd']['table t1']
        assert dbmap['schema sd']['function audit_default()'][
            'returns'] == 'trigger'
        assert dbmap['schema sd']['function audit_default()'][
            'source'] == FUNC_SRC1

    def test_nondefault_schema_with_trigger(self):
        "Add predefined audit columns with trigger in a non-default schema"
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
                'procedure': 's1.audit_default', 'timing': 'before'}}}
        assert expmap == dbmap['schema s1']['table t1']
        assert dbmap['schema s1']['function audit_default()']['returns'] == \
            'trigger'
        assert dbmap['schema s1']['function audit_default()'][
            'source'] == FUNC_SRC1

    def test_skip_existing_columns(self):
        "Do not add already existing audit columns"
        stmts = [CREATE_STMT,
                 "ALTER TABLE t1 ADD modified_by_user varchar(63) NOT NULL",
                 "ALTER TABLE t1 ADD modified_timestamp "
                 "timestamp with time zone NOT NULL"]
        augmap = {'schema sd': {'table t1': {
            'audit_columns': 'default'}}}
        dbmap = self.to_map(stmts, augmap)
        expmap = [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                  {'modified_by_user': {'type': 'character varying(63)',
                                        'not_null': True}},
                  {'modified_timestamp': {'type': 'timestamp with time zone',
                                          'not_null': True}}]
        assert expmap == dbmap['schema sd']['table t1']['columns']

    def test_change_existing_columns(self):
        "Change already existing audit columns"
        stmts = [CREATE_STMT, "ALTER TABLE t1 ADD modified_by_user text ",
                 "ALTER TABLE t1 ADD modified_timestamp "
                 "timestamp with time zone NOT NULL"]
        augmap = {'schema sd': {'table t1': {'audit_columns': 'default'}}}
        dbmap = self.to_map(stmts, augmap)
        expmap = [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                  {'modified_by_user': {'type': 'character varying(63)',
                                        'not_null': True}},
                  {'modified_timestamp': {'type': 'timestamp with time zone',
                                          'not_null': True}}]
        assert expmap == dbmap['schema sd']['table t1']['columns']

    def test_custom_function_template(self):
        "Add new (non-predefined) audit trigger using a function template"
        template = """
        BEGIN
          NEW.{{modified_by_user}} = SESSION_USER;
          NEW.{{modified_timestamp}} = CURRENT_TIMESTAMP::timestamp(0);
          RETURN NEW;
        END"""
        source = """
        BEGIN
          NEW.modified_by_user = SESSION_USER;
          NEW.modified_timestamp = CURRENT_TIMESTAMP::timestamp(0);
          RETURN NEW;
        END"""
        augmap = {
            'augmenter': {
                'audit_columns': {'custom': {
                    'columns': ['modified_by_user', 'modified_timestamp'],
                    'triggers': ['custom_audit']}},
                'function_templates': {'custom_template': template},
                'functions': {'custom_audit()': {
                    'description': 'Maintain custom audit columns',
                    'language': 'plpgsql',
                    'returns': 'trigger',
                    'security_definer': True,
                    'source': '{{custom_template}}'}},
                'triggers': {'custom_audit': {
                    'events': ['insert', 'update'],
                    'level': 'row',
                    'name': '{{table_name}}_20_custom_audit',
                    'procedure': 'custom_audit',
                    'timing': 'before'}}},
            'schema sd': {'table t1': {
                'audit_columns': 'custom'}}}
        dbmap = self.to_map([CREATE_STMT], augmap)
        expmap = {'columns': [
            {'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
            {'modified_by_user': {'type': 'character varying(63)',
                                  'not_null': True}},
            {'modified_timestamp': {'type': 'timestamp with time zone',
                                    'not_null': True}}],
            'triggers': {'t1_20_custom_audit': {
                'events': ['insert', 'update'], 'level': 'row',
                'procedure': 'sd.custom_audit', 'timing': 'before'}}}
        assert expmap == dbmap['schema sd']['table t1']
        assert dbmap['schema sd']['function custom_audit()'][
            'returns'] == 'trigger'
        assert dbmap['schema sd']['function custom_audit()'][
            'source'] == source

    def test_custom_function_inline_with_column_substitution(self):
        "Add new (non-predefined) audit trigger using an inline definition"
        template = """
        BEGIN
          NEW.{{modified_by_user}} = SESSION_USER;
          NEW.{{modified_timestamp}} = CURRENT_TIMESTAMP::timestamp(0);
          RETURN NEW;
        END"""
        source = """
        BEGIN
          NEW.modified_by_user = SESSION_USER;
          NEW.modified_timestamp = CURRENT_TIMESTAMP::timestamp(0);
          RETURN NEW;
        END"""
        augmap = {
            'augmenter': {
                'audit_columns': {'custom': {
                    'columns': ['modified_by_user', 'modified_timestamp'],
                    'triggers': ['custom_audit']}},
                'functions': {'custom_audit()': {
                    'description': 'Maintain custom audit columns',
                    'language': 'plpgsql',
                    'returns': 'trigger',
                    'security_definer': True,
                    'source': template}},
                'triggers': {'custom_audit': {
                    'events': ['insert', 'update'],
                    'level': 'row',
                    'name': '{{table_name}}_20_custom_audit',
                    'procedure': 'custom_audit',
                    'timing': 'before'}}},
            'schema sd': {'table t1': {
                'audit_columns': 'custom'}}}
        dbmap = self.to_map([CREATE_STMT], augmap)
        expmap = {'columns': [
            {'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
            {'modified_by_user': {'type': 'character varying(63)',
                                  'not_null': True}},
            {'modified_timestamp': {'type': 'timestamp with time zone',
                                    'not_null': True}}],
            'triggers': {'t1_20_custom_audit': {
                'events': ['insert', 'update'], 'level': 'row',
                'procedure': 'sd.custom_audit', 'timing': 'before'}}}
        assert expmap == dbmap['schema sd']['table t1']
        assert dbmap['schema sd']['function custom_audit()'][
            'returns'] == 'trigger'
        assert dbmap['schema sd']['function custom_audit()'][
            'source'] == source
