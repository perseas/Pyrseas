# -*- coding: utf-8 -*-
"""Test triggers"""

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

FUNC_SRC = "BEGIN NEW.c3 := CURRENT_TIMESTAMP; RETURN NEW; END"
FUNC_INSTEAD_SRC = "BEGIN INSERT INTO t1 VALUES (NEW.c1, NEW.c2, now()); " \
    "RETURN NULL; END"
CREATE_TABLE_STMT = "CREATE TABLE t1 (c1 integer, c2 text, " \
    "c3 timestamp with time zone)"
CREATE_FUNC_STMT = "CREATE FUNCTION f1() RETURNS trigger LANGUAGE plpgsql " \
    "AS $_$%s$_$" % FUNC_SRC
CREATE_STMT = "CREATE TRIGGER tr1 BEFORE INSERT OR UPDATE ON t1 " \
    "FOR EACH ROW EXECUTE PROCEDURE f1()"
DROP_TABLE_STMT = "DROP TABLE IF EXISTS t1"
DROP_FUNC_STMT = "DROP FUNCTION IF EXISTS f1()"
COMMENT_STMT = "COMMENT ON TRIGGER tr1 ON t1 IS 'Test trigger tr1'"


class TriggerToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing triggers"""

    def test_map_trigger1(self):
        "Map a simple trigger"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT, CREATE_STMT]
        dbmap = self.to_map(stmts)
        assert dbmap['schema public']['table t1']['triggers'] == {
            'tr1': {'timing': 'before', 'events': ['insert', 'update'],
                    'level': 'row', 'procedure': 'f1()'}}

    def test_map_trigger2(self):
        "Map another simple trigger with different attributes"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT,
                 "CREATE TRIGGER tr1 AFTER DELETE OR TRUNCATE ON t1 "
                 "EXECUTE PROCEDURE f1()"]
        dbmap = self.to_map(stmts)
        assert dbmap['schema public']['table t1']['triggers'] == {
            'tr1': {'timing': 'after', 'events': ['delete', 'truncate'],
                    'level': 'statement', 'procedure': 'f1()'}}

    def test_map_trigger_update_cols(self):
        "Map trigger with UPDATE OF columns"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT,
                 "CREATE TRIGGER tr1 AFTER INSERT OR UPDATE OF c1, c2 ON t1 "
                 "FOR EACH ROW EXECUTE PROCEDURE f1()"]
        dbmap = self.to_map(stmts)
        assert dbmap['schema public']['table t1']['triggers'] == {
            'tr1': {'timing': 'after', 'events': ['insert', 'update'],
                    'columns': ['c1', 'c2'], 'level': 'row',
                    'procedure': 'f1()'}}

    def test_map_trigger_conditional(self):
        "Map trigger with a WHEN qualification"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT,
                 "CREATE TRIGGER tr1 AFTER UPDATE ON t1 FOR EACH ROW "
                 "WHEN (OLD.c2 IS DISTINCT FROM NEW.c2) "
                 "EXECUTE PROCEDURE f1()"]
        dbmap = self.to_map(stmts)
        assert dbmap['schema public']['table t1']['triggers'] == {
            'tr1': {'timing': 'after', 'events': ['update'],
                    'level': 'row', 'procedure': 'f1()',
                    'condition': '(old.c2 IS DISTINCT FROM new.c2)'}}

    def test_map_trigger_instead(self):
        "Map an INSTEAD OF trigger"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        stmts = [CREATE_TABLE_STMT, "CREATE VIEW v1 AS SELECT c1, c2 FROM t1",
                 "CREATE FUNCTION f1() RETURNS trigger LANGUAGE plpgsql AS "
                 "$_$%s$_$" % FUNC_INSTEAD_SRC,
                 "CREATE TRIGGER tr1 INSTEAD OF INSERT ON v1 "
                 "FOR EACH ROW EXECUTE PROCEDURE f1()"]
        dbmap = self.to_map(stmts)
        assert dbmap['schema public']['view v1']['triggers'] == {
            'tr1': {'timing': 'instead of', 'events': ['insert'],
                    'level': 'row', 'procedure': 'f1()'}}

    def test_map_trigger_comment(self):
        "Map a trigger comment"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT, CREATE_STMT,
                 COMMENT_STMT]
        dbmap = self.to_map(stmts)
        assert dbmap['schema public']['table t1']['triggers']['tr1'][
            'description'] == 'Test trigger tr1'


class ConstraintTriggerToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing constraint triggers"""

    def test_map_trigger(self):
        "Map a simple constraint trigger"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT,
                 "CREATE CONSTRAINT TRIGGER tr1 AFTER INSERT OR UPDATE ON t1 "
                 "FOR EACH ROW EXECUTE PROCEDURE f1()"]
        dbmap = self.to_map(stmts)
        assert dbmap['schema public']['table t1']['triggers'] == {
            'tr1': {'constraint': True, 'timing': 'after',
                    'events': ['insert', 'update'], 'level': 'row',
                    'procedure': 'f1()'}}

    def test_map_trigger_deferrable(self):
        "Map a deferrable, initially deferred constraint trigger"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT,
                 "CREATE CONSTRAINT TRIGGER tr1 AFTER INSERT OR UPDATE ON t1 "
                 "DEFERRABLE INITIALLY DEFERRED "
                 "FOR EACH ROW EXECUTE PROCEDURE f1()"]
        dbmap = self.to_map(stmts)
        assert dbmap['schema public']['table t1']['triggers'] == {
            'tr1': {'constraint': True, 'deferrable': True,
                    'initially_deferred': True, 'timing': 'after',
                    'events': ['insert', 'update'], 'level': 'row',
                    'procedure': 'f1()'}}


class TriggerToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input triggers"""

    def test_create_trigger1(self):
        "Create a simple trigger"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'timestamp with time zone'}}],
            'triggers': {'tr1': {
                'timing': 'before', 'events': ['insert', 'update'],
                'level': 'row', 'procedure': 'f1()'}}}})
        sql = self.to_sql(inmap)
        crt0, crt1 = (0, 1) if 'TABLE' in sql[0] else (1, 0)
        assert fix_indent(sql[crt0]) == CREATE_TABLE_STMT
        assert fix_indent(sql[crt1]) == CREATE_FUNC_STMT
        assert fix_indent(sql[2]) == CREATE_STMT

    def test_create_trigger2(self):
        "Create another simple trigger with"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'timestamp with time zone'}}],
            'triggers': {'tr1': {'timing': 'after',
                                 'events': ['delete', 'truncate'],
                                 'procedure': 'f1()'}}}})
        sql = self.to_sql(inmap)
        crt0, crt1 = (0, 1) if 'TABLE' in sql[0] else (1, 0)
        assert fix_indent(sql[crt0]) == CREATE_TABLE_STMT
        assert fix_indent(sql[crt1]) == CREATE_FUNC_STMT
        assert fix_indent(sql[2]) == "CREATE TRIGGER tr1 AFTER DELETE OR " \
            "TRUNCATE ON t1 FOR EACH STATEMENT EXECUTE PROCEDURE f1()"

    def test_create_trigger_update_cols(self):
        "Create a trigger with UPDATE OF columns"
        if self.db.version < 90000:
            self.skipTest('Only available on PG 9.0')
        inmap = self.std_map()
        inmap['schema public'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'timestamp with time zone'}}],
            'triggers': {'tr1': {'timing': 'before', 'events': [
                'insert', 'update'], 'columns': ['c1', 'c2'], 'level': 'row',
                'procedure': 'f1()'}}}})
        sql = self.to_sql(inmap)
        crt0, crt1 = (0, 1) if 'TABLE' in sql[0] else (1, 0)
        assert fix_indent(sql[crt0]) == CREATE_TABLE_STMT
        assert fix_indent(sql[crt1]) == CREATE_FUNC_STMT
        assert fix_indent(sql[2]) == "CREATE TRIGGER tr1 BEFORE INSERT OR " \
            "UPDATE OF c1, c2 ON t1 FOR EACH ROW EXECUTE PROCEDURE f1()"

    def test_create_trigger_conditional(self):
        "Create a trigger with a WHEN qualification"
        if self.db.version < 90000:
            self.skipTest('Only available on PG 9.0')
        inmap = self.std_map()
        inmap['schema public'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'timestamp with time zone'}}],
            'triggers': {'tr1': {'timing': 'before', 'events': [
                'update'], 'level': 'row', 'procedure': 'f1()',
                'condition': '(old.c2 IS DISTINCT FROM new.c2)'}}}})
        sql = self.to_sql(inmap)
        crt0, crt1 = (0, 1) if 'TABLE' in sql[0] else (1, 0)
        assert fix_indent(sql[crt0]) == CREATE_TABLE_STMT
        assert fix_indent(sql[crt1]) == CREATE_FUNC_STMT
        assert fix_indent(sql[2]) == "CREATE TRIGGER tr1 BEFORE UPDATE " \
            "ON t1 FOR EACH ROW WHEN ((old.c2 IS DISTINCT FROM new.c2)) " \
            "EXECUTE PROCEDURE f1()"

    def test_create_trigger_instead(self):
        "Create an INSTEAD OF trigger"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger',
            'source': FUNC_INSTEAD_SRC}})
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'timestamp with time zone'}}]},
            'view v1': {'definition': "SELECT c1, c2 FROM t1",
                        'triggers': {'tr1': {'timing': 'instead of',
                                             'events': ['insert'],
                                             'level': 'row',
                                             'procedure': 'f1()'}}}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_TABLE_STMT
        cr1, cr2 = (1, 2) if 'VIEW' in sql[1] else (2, 1)
        assert fix_indent(sql[cr1]) == \
            "CREATE VIEW v1 AS SELECT c1, c2 FROM t1"
        assert fix_indent(sql[cr2]) == "CREATE FUNCTION f1() RETURNS " \
            "trigger LANGUAGE plpgsql AS $_$%s$_$" % FUNC_INSTEAD_SRC
        assert fix_indent(sql[3]) == "CREATE TRIGGER tr1 INSTEAD OF INSERT " \
            "ON v1 FOR EACH ROW EXECUTE PROCEDURE f1()"

    def test_create_trigger_in_schema(self):
        "Create a trigger within a non-public schema"
        inmap = self.std_map(plpgsql_installed=True)
        inmap.update({'schema s1': {'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC},
            'table t1': {
                'columns': [{'c1': {'type': 'integer'}},
                            {'c2': {'type': 'text'}},
                            {'c3': {'type': 'timestamp with time zone'}}],
                'triggers': {'tr1': {
                    'timing': 'before', 'events': ['insert', 'update'],
                    'level': 'row', 'procedure': 's1.f1()'}}}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        assert fix_indent(sql[2]) == "CREATE TRIGGER tr1 BEFORE INSERT OR " \
            "UPDATE ON s1.t1 FOR EACH ROW EXECUTE PROCEDURE s1.f1()"

    def test_drop_trigger(self):
        "Drop an existing trigger"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT, CREATE_STMT]
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'timestamp with time zone'}}]}})
        sql = self.to_sql(inmap, stmts)
        assert sql == ["DROP TRIGGER tr1 ON t1"]

    def test_drop_trigger_table(self):
        "Drop an existing trigger and the related table"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT, CREATE_STMT]
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        sql = self.to_sql(inmap, stmts)
        assert sql[0] == "DROP TRIGGER tr1 ON t1"
        assert sql[1] == "DROP TABLE t1"

    def test_trigger_with_comment(self):
        "Create a trigger with a comment"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'timestamp with time zone'}}],
            'triggers': {'tr1': {
                'description': 'Test trigger tr1',
                'timing': 'before', 'events': ['insert', 'update'],
                'level': 'row', 'procedure': 'f1()'}}}})
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
        inmap['schema public'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'timestamp with time zone'}}],
            'triggers': {'tr1': {
                'description': 'Test trigger tr1',
                'timing': 'before', 'events': ['insert', 'update'],
                'level': 'row', 'procedure': 'f1()'}}}})
        sql = self.to_sql(inmap, stmts)
        assert sql == [COMMENT_STMT]

    def test_drop_trigger_comment(self):
        "Drop a comment on an existing trigger"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT, CREATE_STMT,
                 COMMENT_STMT]
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'timestamp with time zone'}}],
            'triggers': {'tr1': {
                'timing': 'before', 'events': ['insert', 'update'],
                'level': 'row', 'procedure': 'f1()'}}}})
        sql = self.to_sql(inmap, stmts)
        assert sql == ["COMMENT ON TRIGGER tr1 ON t1 IS NULL"]

    def test_change_trigger_comment(self):
        "Change existing comment on a trigger"
        stmts = [CREATE_TABLE_STMT, CREATE_FUNC_STMT, CREATE_STMT,
                 COMMENT_STMT]
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'timestamp with time zone'}}],
            'triggers': {'tr1': {
                'description': 'Changed trigger tr1',
                'timing': 'before', 'events': ['insert', 'update'],
                'level': 'row', 'procedure': 'f1()'}}}})
        sql = self.to_sql(inmap, stmts)
        assert sql == ["COMMENT ON TRIGGER tr1 ON t1 IS 'Changed trigger tr1'"]


class ConstraintTriggerToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input triggers"""

    def test_create_trigger(self):
        "Create a constraint trigger"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'timestamp with time zone'}}],
            'triggers': {'tr1': {
                'constraint': True, 'timing': 'after',
                'events': ['insert', 'update'], 'level': 'row',
                'procedure': 'f1()'}}}})
        sql = self.to_sql(inmap)
        crt0, crt1 = (0, 1) if 'TABLE' in sql[0] else (1, 0)
        assert fix_indent(sql[crt0]) == CREATE_TABLE_STMT
        assert fix_indent(sql[crt1]) == CREATE_FUNC_STMT
        assert fix_indent(sql[2]) == "CREATE CONSTRAINT TRIGGER tr1 AFTER " \
            "INSERT OR UPDATE ON t1 FOR EACH ROW EXECUTE PROCEDURE f1()"

    def test_create_trigger_deferrable(self):
        "Create a deferrable constraint trigger"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'trigger', 'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}},
                        {'c3': {'type': 'timestamp with time zone'}}],
            'triggers': {'tr1': {
                'constraint': True, 'deferrable': True,
                'initially_deferred': True, 'timing': 'after',
                'events': ['insert', 'update'], 'level': 'row',
                'procedure': 'f1()'}}}})
        sql = self.to_sql(inmap)
        crt0, crt1 = (0, 1) if 'TABLE' in sql[0] else (1, 0)
        assert fix_indent(sql[crt0]) == CREATE_TABLE_STMT
        assert fix_indent(sql[crt1]) == CREATE_FUNC_STMT
        assert fix_indent(sql[2]) == "CREATE CONSTRAINT TRIGGER tr1 " \
            "AFTER INSERT OR UPDATE ON t1 DEFERRABLE INITIALLY " \
            "DEFERRED FOR EACH ROW EXECUTE PROCEDURE f1()"
