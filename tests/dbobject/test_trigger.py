# -*- coding: utf-8 -*-
"""Test triggers"""

import pytest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

FUNC_SRC = "BEGIN NEW.c3 := CURRENT_DATE; RETURN NEW; END"
FUNC_INSTEAD_SRC = "BEGIN INSERT INTO t1 VALUES (NEW.c1, NEW.c2, now()); " \
    "RETURN NULL; END"
CREATE_TABLE_STMT = "CREATE TABLE sd.t1 (c1 integer, c2 text, " \
    "c3 date)"
CREATE_TABLE_STMT2 = "CREATE TABLE t1 (c1 integer, c2 text, " \
    "c3 text, tsidx tsvector)"
CREATE_FUNC_STMT = "CREATE FUNCTION sd.f1() RETURNS trigger LANGUAGE plpgsql" \
    " AS $_$%s$_$" % FUNC_SRC
CREATE_STMT = "CREATE TRIGGER tr1 BEFORE INSERT OR UPDATE ON sd.t1 " \
    "FOR EACH ROW EXECUTE PROCEDURE sd.f1()"
COMMENT_STMT = "COMMENT ON TRIGGER tr1 ON sd.t1 IS 'Test trigger tr1'"


class TriggerToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing triggers"""

    def test_map_trigger1(self):
        "Map a simple trigger"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT, CREATE_STMT]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['table t1']['triggers'] == {
            'tr1': {'timing': 'before', 'events': ['insert', 'update'],
                    'level': 'row', 'procedure': 'sd.f1'}}

    def test_map_trigger2(self):
        "Map another simple trigger with different attributes"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT,
                 "CREATE TRIGGER tr1 AFTER DELETE OR TRUNCATE ON t1 "
                 "EXECUTE PROCEDURE f1()"]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['table t1']['triggers'] == {
            'tr1': {'timing': 'after', 'events': ['delete', 'truncate'],
                    'level': 'statement', 'procedure': 'sd.f1'}}

    def test_map_trigger_update_cols(self):
        "Map trigger with UPDATE OF columns"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT,
                 "CREATE TRIGGER tr1 AFTER INSERT OR UPDATE OF c1, c2 ON t1 "
                 "FOR EACH ROW EXECUTE PROCEDURE f1()"]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['table t1']['triggers'] == {
            'tr1': {'timing': 'after', 'events': ['insert', 'update'],
                    'columns': ['c1', 'c2'], 'level': 'row',
                    'procedure': 'sd.f1'}}

    def test_map_trigger_conditional(self):
        "Map trigger with a WHEN qualification"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT,
                 "CREATE TRIGGER tr1 AFTER UPDATE ON t1 FOR EACH ROW "
                 "WHEN (OLD.c2 IS DISTINCT FROM NEW.c2) "
                 "EXECUTE PROCEDURE f1()"]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['table t1']['triggers'] == {
            'tr1': {'timing': 'after', 'events': ['update'],
                    'level': 'row', 'procedure': 'sd.f1',
                    'condition': '(old.c2 IS DISTINCT FROM new.c2)'}}

    def test_map_trigger_instead(self):
        "Map an INSTEAD OF trigger"
        stmts = [CREATE_TABLE_STMT, "CREATE VIEW v1 AS SELECT c1, c2 FROM t1",
                 "CREATE FUNCTION f1() RETURNS trigger LANGUAGE plpgsql AS "
                 "$_$%s$_$" % FUNC_INSTEAD_SRC,
                 "CREATE TRIGGER tr1 INSTEAD OF INSERT ON v1 "
                 "FOR EACH ROW EXECUTE PROCEDURE f1()"]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['view v1']['triggers'] == {
            'tr1': {'timing': 'instead of', 'events': ['insert'],
                    'level': 'row', 'procedure': 'sd.f1'}}

    def test_map_tsvector_trigger(self):
        "Map a text search (tsvector) trigger"
        stmts = [
            CREATE_TABLE_STMT2,
            "CREATE TRIGGER tr1 BEFORE INSERT OR UPDATE ON sd.t1 "
            "FOR EACH ROW EXECUTE PROCEDURE "
            "tsvector_update_trigger('tsidx', 'pg_catalog.english', 'c2')"]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['table t1']['triggers'] == {
            'tr1': {'timing': 'before', 'events': ['insert', 'update'],
                    'level': 'row',
                    'procedure': {'name': 'tsvector_update_trigger',
                                  'arguments':
                                  "'tsidx', 'pg_catalog.english', 'c2'"}}}

    def test_map_trigger_function_distinct_schemas(self):
        "Map a trigger in a non-default schema with function in different one"
        stmts = ["CREATE SCHEMA s1", "CREATE TABLE s1.t1 (c1 integer, "
                 "c2 text, c3 date)", "CREATE SCHEMA s2",
                 "CREATE FUNCTION s2.f1() RETURNS trigger LANGUAGE plpgsql AS "
                 "$_$%s$_$" % FUNC_SRC,
                 "CREATE TRIGGER tr1 BEFORE INSERT OR UPDATE ON s1.t1 "
                 "FOR EACH ROW EXECUTE PROCEDURE s2.f1()"]
        dbmap = self.to_map(stmts)
        assert dbmap['schema s1']['table t1']['triggers'] == {
            'tr1': {'timing': 'before', 'events': ['insert', 'update'],
                    'level': 'row', 'procedure': 's2.f1'}}

    def test_map_trigger_comment(self):
        "Map a trigger comment"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT, CREATE_STMT,
                 COMMENT_STMT]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['table t1']['triggers']['tr1'][
            'description'] == 'Test trigger tr1'


class ConstraintTriggerToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing constraint triggers"""

    def test_map_trigger(self):
        "Map a simple constraint trigger"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT,
                 "CREATE CONSTRAINT TRIGGER tr1 AFTER INSERT OR UPDATE ON t1 "
                 "FOR EACH ROW EXECUTE PROCEDURE f1()"]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['table t1']['triggers'] == {
            'tr1': {'constraint': True, 'timing': 'after',
                    'events': ['insert', 'update'], 'level': 'row',
                    'procedure': 'sd.f1'}}

    def test_map_trigger_deferrable(self):
        "Map a deferrable, initially deferred constraint trigger"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT,
                 "CREATE CONSTRAINT TRIGGER tr1 AFTER INSERT OR UPDATE ON t1 "
                 "DEFERRABLE INITIALLY DEFERRED "
                 "FOR EACH ROW EXECUTE PROCEDURE f1()"]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['table t1']['triggers'] == {
            'tr1': {'constraint': True, 'deferrable': True,
                    'initially_deferred': True, 'timing': 'after',
                    'events': ['insert', 'update'], 'level': 'row',
                    'procedure': 'sd.f1'}}


class TriggerToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input triggers"""

    def test_create_trigger1(self):
        "Create a simple trigger"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'date'}}],
            'triggers': {'tr1': {
                'timing': 'before', 'events': ['insert', 'update'],
                'level': 'row', 'procedure': 'sd.f1'}}}})
        sql = self.to_sql(inmap)
        crt0, crt1 = (0, 1) if 'TABLE' in sql[0] else (1, 0)
        assert fix_indent(sql[crt0]) == CREATE_TABLE_STMT
        assert fix_indent(sql[crt1]) == CREATE_FUNC_STMT
        assert fix_indent(sql[2]) == CREATE_STMT

    def test_create_trigger2(self):
        "Create another simple trigger with"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'date'}}],
            'triggers': {'tr1': {'timing': 'after',
                                 'events': ['delete', 'truncate'],
                                 'procedure': 'sd.f1'}}}})
        sql = self.to_sql(inmap)
        crt0, crt1 = (0, 1) if 'TABLE' in sql[0] else (1, 0)
        assert fix_indent(sql[crt0]) == CREATE_TABLE_STMT
        assert fix_indent(sql[crt1]) == CREATE_FUNC_STMT
        assert fix_indent(sql[2]) == "CREATE TRIGGER tr1 AFTER DELETE OR " \
            "TRUNCATE ON sd.t1 FOR EACH STATEMENT EXECUTE PROCEDURE sd.f1()"

    def test_create_trigger_update_cols(self):
        "Create a trigger with UPDATE OF columns"
        inmap = self.std_map()
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'date'}}],
            'triggers': {'tr1': {'timing': 'before', 'events': [
                'insert', 'update'], 'columns': ['c1', 'c2'], 'level': 'row',
                'procedure': 'sd.f1'}}}})
        sql = self.to_sql(inmap)
        crt0, crt1 = (0, 1) if 'TABLE' in sql[0] else (1, 0)
        assert fix_indent(sql[crt0]) == CREATE_TABLE_STMT
        assert fix_indent(sql[crt1]) == CREATE_FUNC_STMT
        assert fix_indent(sql[2]) == "CREATE TRIGGER tr1 BEFORE INSERT OR " \
            "UPDATE OF c1, c2 ON sd.t1 FOR EACH ROW EXECUTE PROCEDURE sd.f1()"

    def test_create_trigger_conditional(self):
        "Create a trigger with a WHEN qualification"
        inmap = self.std_map()
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'date'}}],
            'triggers': {'tr1': {'timing': 'before', 'events': [
                'update'], 'level': 'row', 'procedure': 'sd.f1',
                'condition': '(old.c2 IS DISTINCT FROM new.c2)'}}}})
        sql = self.to_sql(inmap)
        crt0, crt1 = (0, 1) if 'TABLE' in sql[0] else (1, 0)
        assert fix_indent(sql[crt0]) == CREATE_TABLE_STMT
        assert fix_indent(sql[crt1]) == CREATE_FUNC_STMT
        assert fix_indent(sql[2]) == "CREATE TRIGGER tr1 BEFORE UPDATE " \
            "ON sd.t1 FOR EACH ROW WHEN ((old.c2 IS DISTINCT FROM new.c2)) " \
            "EXECUTE PROCEDURE sd.f1()"

    def test_create_trigger_instead(self):
        "Create an INSTEAD OF trigger"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger',
            'source': FUNC_INSTEAD_SRC}})
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'date'}}]},
            'view v1': {'definition': "SELECT c1, c2 FROM t1",
                        'triggers': {'tr1': {'timing': 'instead of',
                                             'events': ['insert'],
                                             'level': 'row',
                                             'procedure': 'sd.f1'}}}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_TABLE_STMT
        cr1, cr2 = (1, 2) if 'VIEW' in sql[1] else (2, 1)
        assert fix_indent(sql[cr1]) == \
            "CREATE VIEW sd.v1 AS SELECT c1, c2 FROM t1"
        assert fix_indent(sql[cr2]) == "CREATE FUNCTION sd.f1() RETURNS " \
            "trigger LANGUAGE plpgsql AS $_$%s$_$" % FUNC_INSTEAD_SRC
        assert fix_indent(sql[3]) == "CREATE TRIGGER tr1 INSTEAD OF INSERT " \
            "ON sd.v1 FOR EACH ROW EXECUTE PROCEDURE sd.f1()"

    def test_add_tsvector_trigger(self):
        "Add a text search (tsvector) trigger"
        inmap = self.std_map()
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'text'}},
                        {'tsidx': {'type': 'tsvector'}}],
            'triggers': {'t1_tsidx_update': {
                'timing': 'before',
                'events': ['insert', 'update'], 'level': 'row',
                'procedure': {'name': 'tsvector_update_trigger',
                              'arguments':
                              "'tsidx', 'pg_catalog.english', 'c2'"}}}}})
        sql = self.to_sql(inmap, [CREATE_TABLE_STMT2])
        assert fix_indent(sql[0]) == "CREATE TRIGGER t1_tsidx_update BEFORE" \
            " INSERT OR UPDATE ON sd.t1 FOR EACH ROW EXECUTE PROCEDURE " \
            "tsvector_update_trigger('tsidx', 'pg_catalog.english', 'c2')"

    def test_change_tsvector_trigger(self):
        "Change a text search (tsvector) trigger"
        inmap = self.std_map()
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'text'}},
                        {'tsidx': {'type': 'tsvector'}}],
            'triggers': {'t1_tsidx_update': {
                'timing': 'before', 'events': ['insert', 'update'],
                'level': 'row',
                'procedure': {'name': "tsvector_update_trigger",
                              'arguments':
                              "'tsidx', 'pg_catalog.english', 'c2', 'c3'"}}}}})
        stmts = [CREATE_TABLE_STMT2,
                 "CREATE TRIGGER t1_tsidx_update BEFORE INSERT OR UPDATE ON "
                 "t1 FOR EACH ROW EXECUTE PROCEDURE tsvector_update_trigger"
                 "('tsidx', 'pg_catalog.english', 'c2')"]
        sql = self.to_sql(inmap, stmts)
        assert sql[0] == "DROP TRIGGER t1_tsidx_update ON sd.t1"
        assert fix_indent(sql[1]) == "CREATE TRIGGER t1_tsidx_update BEFORE" \
            " INSERT OR UPDATE ON sd.t1 FOR EACH ROW EXECUTE PROCEDURE " \
            "tsvector_update_trigger('tsidx', 'pg_catalog.english', " \
            "'c2', 'c3')"

    def test_create_trigger_function_distinct_schemas(self):
        "Create a trigger in non-default schema with function in different one"
        inmap = self.std_map(plpgsql_installed=True)
        inmap.update({'schema s2': {'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}},
                     'schema s1': {
                         'table t1': {
                             'columns': [
                                 {'c1': {'type': 'integer'}},
                                 {'c2': {'type': 'text'}},
                                 {'c3': {'type': 'date'}}],
                             'triggers': {'tr1': {
                                 'timing': 'before',
                                 'events': ['insert', 'update'],
                                 'level': 'row', 'procedure': 's2.f1'}}}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1", "CREATE SCHEMA s2"])
        assert fix_indent(sql[2]) == "CREATE TRIGGER tr1 BEFORE INSERT OR " \
            "UPDATE ON s1.t1 FOR EACH ROW EXECUTE PROCEDURE s2.f1()"

    def test_drop_trigger(self):
        "Drop an existing trigger"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT, CREATE_STMT]
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'date'}}]}})
        sql = self.to_sql(inmap, stmts)
        assert sql == ["DROP TRIGGER tr1 ON sd.t1"]

    def test_drop_trigger_table(self):
        "Drop an existing trigger and the related table"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT, CREATE_STMT]
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        sql = self.to_sql(inmap, stmts)
        assert sql[0] == "DROP TRIGGER tr1 ON sd.t1"
        assert sql[1] == "DROP TABLE sd.t1"

    def test_trigger_with_comment(self):
        "Create a trigger with a comment"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'date'}}],
            'triggers': {'tr1': {
                'description': 'Test trigger tr1',
                'timing': 'before', 'events': ['insert', 'update'],
                'level': 'row', 'procedure': 'sd.f1'}}}})
        sql = self.to_sql(inmap)
        crt0, crt1 = (0, 1) if 'TABLE' in sql[0] else (1, 0)
        assert fix_indent(sql[crt0]) == CREATE_TABLE_STMT
        assert fix_indent(sql[crt1]) == CREATE_FUNC_STMT
        assert fix_indent(sql[2]) == CREATE_STMT
        assert sql[3] == COMMENT_STMT

    def test_comment_on_trigger(self):
        "Create a comment on an existing trigger"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT, CREATE_STMT]
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'date'}}],
            'triggers': {'tr1': {
                'description': 'Test trigger tr1',
                'timing': 'before', 'events': ['insert', 'update'],
                'level': 'row', 'procedure': 'sd.f1'}}}})
        sql = self.to_sql(inmap, stmts)
        assert sql == [COMMENT_STMT]

    def test_drop_trigger_comment(self):
        "Drop a comment on an existing trigger"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT, CREATE_STMT,
                 COMMENT_STMT]
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'date'}}],
            'triggers': {'tr1': {
                'timing': 'before', 'events': ['insert', 'update'],
                'level': 'row', 'procedure': 'sd.f1'}}}})
        sql = self.to_sql(inmap, stmts)
        assert sql == ["COMMENT ON TRIGGER tr1 ON sd.t1 IS NULL"]

    def test_change_trigger_comment(self):
        "Change existing comment on a trigger"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT, CREATE_STMT,
                 COMMENT_STMT]
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'date'}}],
            'triggers': {'tr1': {
                'description': 'Changed trigger tr1',
                'timing': 'before', 'events': ['insert', 'update'],
                'level': 'row', 'procedure': 'sd.f1'}}}})
        sql = self.to_sql(inmap, stmts)
        assert sql == [
            "COMMENT ON TRIGGER tr1 ON sd.t1 IS 'Changed trigger tr1'"]


class ConstraintTriggerToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input triggers"""

    def test_create_trigger(self):
        "Create a constraint trigger"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'date'}}],
            'triggers': {'tr1': {
                'constraint': True, 'timing': 'after',
                'events': ['insert', 'update'], 'level': 'row',
                'procedure': 'sd.f1'}}}})
        sql = self.to_sql(inmap)
        crt0, crt1 = (0, 1) if 'TABLE' in sql[0] else (1, 0)
        assert fix_indent(sql[crt0]) == CREATE_TABLE_STMT
        assert fix_indent(sql[crt1]) == CREATE_FUNC_STMT
        assert fix_indent(sql[2]) == "CREATE CONSTRAINT TRIGGER tr1 AFTER " \
            "INSERT OR UPDATE ON sd.t1 FOR EACH ROW EXECUTE PROCEDURE sd.f1()"

    def test_create_trigger_deferrable(self):
        "Create a deferrable constraint trigger"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'date'}}],
            'triggers': {'tr1': {
                'constraint': True, 'deferrable': True,
                'initially_deferred': True, 'timing': 'after',
                'events': ['insert', 'update'], 'level': 'row',
                'procedure': 'sd.f1'}}}})
        sql = self.to_sql(inmap)
        crt0, crt1 = (0, 1) if 'TABLE' in sql[0] else (1, 0)
        assert fix_indent(sql[crt0]) == CREATE_TABLE_STMT
        assert fix_indent(sql[crt1]) == CREATE_FUNC_STMT
        assert fix_indent(sql[2]) == "CREATE CONSTRAINT TRIGGER tr1 " \
            "AFTER INSERT OR UPDATE ON sd.t1 DEFERRABLE INITIALLY " \
            "DEFERRED FOR EACH ROW EXECUTE PROCEDURE sd.f1()"
