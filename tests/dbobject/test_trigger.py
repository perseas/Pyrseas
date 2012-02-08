# -*- coding: utf-8 -*-
"""Test triggers"""

import unittest

from pyrseas.testutils import PyrseasTestCase, fix_indent

FUNC_SRC = "BEGIN NEW.c3 := CURRENT_TIMESTAMP; RETURN NEW; END"
CREATE_TABLE_STMT = "CREATE TABLE t1 (c1 integer, c2 text, " \
    "c3 timestamp with time zone)"
CREATE_FUNC_STMT = "CREATE FUNCTION f1() RETURNS trigger LANGUAGE plpgsql " \
    "AS $_$%s$_$" % FUNC_SRC
CREATE_STMT = "CREATE TRIGGER tr1 BEFORE INSERT OR UPDATE ON t1 " \
    "FOR EACH ROW EXECUTE PROCEDURE f1()"
DROP_TABLE_STMT = "DROP TABLE IF EXISTS t1"
DROP_FUNC_STMT = "DROP FUNCTION IF EXISTS f1()"
COMMENT_STMT = "COMMENT ON TRIGGER tr1 ON t1 IS 'Test trigger tr1'"


class TriggerToMapTestCase(PyrseasTestCase):
    """Test mapping of existing triggers"""

    def setUp(self):
        super(self.__class__, self).setUp()
        if self.db.version < 90000:
            if not self.db.is_plpgsql_installed():
                self.db.execute_commit("CREATE LANGUAGE plpgsql")

    def test_map_trigger(self):
        "Map a simple trigger"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_FUNC_STMT)
        expmap = {'tr1': {'timing': 'before', 'events': ['insert', 'update'],
                          'level': 'row', 'procedure': 'f1()'}}
        dbmap = self.db.execute_and_map(CREATE_STMT)
        self.assertEqual(dbmap['schema public']['table t1']['triggers'],
                         expmap)

    def test_map_trigger2(self):
        "Map another simple trigger with different attributes"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_FUNC_STMT)
        expmap = {'tr1': {'timing': 'after', 'events': ['delete', 'truncate'],
                          'level': 'statement', 'procedure': 'f1()'}}
        dbmap = self.db.execute_and_map(
            "CREATE TRIGGER tr1 AFTER DELETE OR TRUNCATE ON t1 " \
                "EXECUTE PROCEDURE f1()")
        self.assertEqual(dbmap['schema public']['table t1']['triggers'],
                         expmap)

    def test_map_trigger_update_cols(self):
        "Map trigger with UPDATE OF columns"
        if self.db.version < 90000:
            return True
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_FUNC_STMT)
        expmap = {'tr1': {'timing': 'after', 'events': ['insert', 'update'],
                          'columns': ['c1', 'c2'], 'level': 'row',
                          'procedure': 'f1()'}}
        dbmap = self.db.execute_and_map(
            "CREATE TRIGGER tr1 AFTER INSERT OR UPDATE OF c1, c2 ON t1 "
            "FOR EACH ROW EXECUTE PROCEDURE f1()")
        self.assertEqual(dbmap['schema public']['table t1']['triggers'],
                         expmap)

    def test_map_trigger_conditional(self):
        "Map trigger with a WHEN qualification"
        if self.db.version < 90000:
            return True
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_FUNC_STMT)
        expmap = {'tr1': {'timing': 'after', 'events': ['update'],
                          'level': 'row', 'procedure': 'f1()',
                          'condition': '(old.c2 IS DISTINCT FROM new.c2)'}}
        dbmap = self.db.execute_and_map(
            "CREATE TRIGGER tr1 AFTER UPDATE ON t1 FOR EACH ROW "
            "WHEN (OLD.c2 IS DISTINCT FROM NEW.c2) EXECUTE PROCEDURE f1()")
        self.assertEqual(dbmap['schema public']['table t1']['triggers'],
                         expmap)

    def test_map_trigger_comment(self):
        "Map a trigger comment"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_FUNC_STMT)
        self.db.execute(CREATE_STMT)
        dbmap = self.db.execute_and_map(COMMENT_STMT)
        self.assertEqual(dbmap['schema public']['table t1']['triggers']
                         ['tr1']['description'], 'Test trigger tr1')


class ConstraintTriggerToMapTestCase(PyrseasTestCase):
    """Test mapping of existing constraint triggers"""

    def setUp(self):
        super(self.__class__, self).setUp()
        if self.db.version < 90000:
            if not self.db.is_plpgsql_installed():
                self.db.execute_commit("CREATE LANGUAGE plpgsql")

    def test_map_trigger(self):
        "Map a simple constraint trigger"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_FUNC_STMT)
        expmap = {'tr1': {'constraint': True, 'timing': 'after',
                          'events': ['insert', 'update'],
                          'level': 'row', 'procedure': 'f1()'}}
        dbmap = self.db.execute_and_map(
            "CREATE CONSTRAINT TRIGGER tr1 AFTER INSERT OR UPDATE ON t1 "
            "FOR EACH ROW EXECUTE PROCEDURE f1()")
        self.assertEqual(dbmap['schema public']['table t1']['triggers'],
                         expmap)

    def test_map_trigger_deferrable(self):
        "Map a deferrable, initially deferred constraint trigger"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_FUNC_STMT)
        expmap = {'tr1': {'constraint': True, 'deferrable': True,
                          'initially_deferred': True, 'timing': 'after',
                          'events': ['insert', 'update'],
                          'level': 'row', 'procedure': 'f1()'}}
        dbmap = self.db.execute_and_map(
            "CREATE CONSTRAINT TRIGGER tr1 AFTER INSERT OR UPDATE ON t1 "
            "DEFERRABLE INITIALLY DEFERRED "
            "FOR EACH ROW EXECUTE PROCEDURE f1()")
        self.assertEqual(dbmap['schema public']['table t1']['triggers'],
                         expmap)


class TriggerToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input triggers"""

    def setUp(self):
        super(self.__class__, self).setUp()
        if self.db.version < 90000:
            if not self.db.is_plpgsql_installed():
                self.db.execute_commit("CREATE LANGUAGE plpgsql")

    def test_create_trigger(self):
        "Create a simple trigger"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
                    'language': 'plpgsql', 'returns': 'trigger',
                    'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'timestamp with time zone'}}],
                    'triggers': {'tr1': {
                            'timing': 'before', 'events': ['insert', 'update'],
                            'level': 'row', 'procedure': 'f1()'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]), CREATE_FUNC_STMT)
        self.assertEqual(fix_indent(dbsql[2]), CREATE_TABLE_STMT)
        self.assertEqual(fix_indent(dbsql[3]), CREATE_STMT)

    def test_create_trigger2(self):
        "Create another simple trigger with"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
                    'language': 'plpgsql', 'returns': 'trigger',
                    'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'timestamp with time zone'}}],
                    'triggers': {'tr1': {'timing': 'after',
                                         'events': ['delete', 'truncate'],
                                         'procedure': 'f1()'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]), CREATE_FUNC_STMT)
        self.assertEqual(fix_indent(dbsql[2]), CREATE_TABLE_STMT)
        self.assertEqual(fix_indent(dbsql[3]),
                         "CREATE TRIGGER tr1 AFTER DELETE OR TRUNCATE ON t1 "
                         "FOR EACH STATEMENT EXECUTE PROCEDURE f1()")

    def test_create_trigger_update_cols(self):
        "Create a trigger with UPDATE OF columns"
        if self.db.version < 90000:
            return True
        inmap = self.std_map()
        inmap['schema public'].update({'function f1()': {
                    'language': 'plpgsql', 'returns': 'trigger',
                    'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'timestamp with time zone'}}],
                    'triggers': {'tr1': {
                            'timing': 'before', 'events': ['insert', 'update'],
                            'columns': ['c1', 'c2'],
                            'level': 'row', 'procedure': 'f1()'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]), CREATE_FUNC_STMT)
        self.assertEqual(fix_indent(dbsql[2]), CREATE_TABLE_STMT)
        self.assertEqual(fix_indent(dbsql[3]), "CREATE TRIGGER tr1 "
                         "BEFORE INSERT OR UPDATE OF c1, c2 "
                         "ON t1 FOR EACH ROW EXECUTE PROCEDURE f1()")

    def test_create_trigger_conditional(self):
        "Create a trigger with a WHEN qualification"
        if self.db.version < 90000:
            return True
        inmap = self.std_map()
        inmap['schema public'].update({'function f1()': {
                    'language': 'plpgsql', 'returns': 'trigger',
                    'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'timestamp with time zone'}}],
                    'triggers': {'tr1': {
                            'timing': 'before', 'events': ['update'],
                            'level': 'row', 'procedure': 'f1()',
                            'condition':
                                '(old.c2 IS DISTINCT FROM new.c2)'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]), CREATE_FUNC_STMT)
        self.assertEqual(fix_indent(dbsql[2]), CREATE_TABLE_STMT)
        self.assertEqual(fix_indent(dbsql[3]), "CREATE TRIGGER tr1 "
                         "BEFORE UPDATE ON t1 FOR EACH ROW "
                         "WHEN ((old.c2 IS DISTINCT FROM new.c2)) "
                         "EXECUTE PROCEDURE f1()")

    def test_create_trigger_in_schema(self):
        "Create a trigger within a non-public schema"
        self.db.execute("DROP SCHEMA IF EXISTS s1 CASCADE")
        self.db.execute_commit("CREATE SCHEMA s1")
        inmap = self.std_map(plpgsql_installed=True)
        inmap.update({'schema s1': {'function f1()': {
                        'language': 'plpgsql', 'returns': 'trigger',
                        'source': FUNC_SRC},
                      'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'timestamp with time zone'}}],
                    'triggers': {'tr1': {
                            'timing': 'before', 'events': ['insert', 'update'],
                            'level': 'row', 'procedure': 'f1()'}}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[3]), "CREATE TRIGGER tr1 "
                         "BEFORE INSERT OR UPDATE ON s1.t1 FOR EACH ROW "
                         "EXECUTE PROCEDURE f1()")
        self.db.execute_commit("DROP SCHEMA s1 CASCADE")

    def test_drop_trigger(self):
        "Drop an existing trigger"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_FUNC_STMT)
        self.db.execute_commit(CREATE_STMT)
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
                    'language': 'plpgsql', 'returns': 'trigger',
                    'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {
                                'type': 'timestamp with time zone'}}]}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["DROP TRIGGER tr1 ON t1"])

    def test_drop_trigger_table(self):
        "Drop an existing trigger and the related table"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_FUNC_STMT)
        self.db.execute_commit(CREATE_STMT)
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
                    'language': 'plpgsql', 'returns': 'trigger',
                    'source': FUNC_SRC}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql[0], "DROP TRIGGER tr1 ON t1")
        self.assertEqual(dbsql[1], "DROP TABLE t1")

    def test_trigger_with_comment(self):
        "Create a trigger with a comment"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
                    'language': 'plpgsql', 'returns': 'trigger',
                    'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'timestamp with time zone'}}],
                    'triggers': {'tr1': {
                            'description': 'Test trigger tr1',
                            'timing': 'before', 'events': ['insert', 'update'],
                            'level': 'row', 'procedure': 'f1()'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]), CREATE_FUNC_STMT)
        self.assertEqual(fix_indent(dbsql[2]), CREATE_TABLE_STMT)
        self.assertEqual(fix_indent(dbsql[3]), CREATE_STMT)
        self.assertEqual(dbsql[4], COMMENT_STMT)

    def test_comment_on_trigger(self):
        "Create a comment on an existing trigger"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_FUNC_STMT)
        self.db.execute_commit(CREATE_STMT)
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
                    'language': 'plpgsql', 'returns': 'trigger',
                    'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'timestamp with time zone'}}],
                    'triggers': {'tr1': {
                            'description': 'Test trigger tr1',
                            'timing': 'before', 'events': ['insert', 'update'],
                            'level': 'row', 'procedure': 'f1()'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [COMMENT_STMT])

    def test_drop_trigger_comment(self):
        "Drop a comment on an existing trigger"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_FUNC_STMT)
        self.db.execute(CREATE_STMT)
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
                    'language': 'plpgsql', 'returns': 'trigger',
                    'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'timestamp with time zone'}}],
                    'triggers': {'tr1': {
                            'timing': 'before', 'events': ['insert', 'update'],
                            'level': 'row', 'procedure': 'f1()'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql,
                         ["COMMENT ON TRIGGER tr1 ON t1 IS NULL"])

    def test_change_trigger_comment(self):
        "Change existing comment on a trigger"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_FUNC_STMT)
        self.db.execute(CREATE_STMT)
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
                    'language': 'plpgsql', 'returns': 'trigger',
                    'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'timestamp with time zone'}}],
                    'triggers': {'tr1': {
                            'description': 'Changed trigger tr1',
                            'timing': 'before', 'events': ['insert', 'update'],
                            'level': 'row', 'procedure': 'f1()'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [
                "COMMENT ON TRIGGER tr1 ON t1 IS 'Changed trigger tr1'"])


class ConstraintTriggerToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input triggers"""

    def setUp(self):
        super(self.__class__, self).setUp()
        if self.db.version < 90000:
            if not self.db.is_plpgsql_installed():
                self.db.execute_commit("CREATE LANGUAGE plpgsql")

    def test_create_trigger(self):
        "Create a constraint trigger"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
                    'language': 'plpgsql', 'returns': 'trigger',
                    'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'timestamp with time zone'}}],
                    'triggers': {'tr1': {
                            'constraint': True, 'timing': 'after',
                            'events': ['insert', 'update'],
                            'level': 'row', 'procedure': 'f1()'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]), CREATE_FUNC_STMT)
        self.assertEqual(fix_indent(dbsql[2]), CREATE_TABLE_STMT)
        self.assertEqual(fix_indent(dbsql[3]), "CREATE CONSTRAINT TRIGGER tr1 "
                         "AFTER INSERT OR UPDATE ON t1 "
                         "FOR EACH ROW EXECUTE PROCEDURE f1()")

    def test_create_trigger_deferrable(self):
        "Create a deferrable constraint trigger"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema public'].update({'function f1()': {
                    'language': 'plpgsql', 'returns': 'trigger',
                    'source': FUNC_SRC}})
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}},
                                {'c3': {'type': 'timestamp with time zone'}}],
                    'triggers': {'tr1': {
                            'constraint': True, 'deferrable': True,
                            'initially_deferred': True, 'timing': 'after',
                            'events': ['insert', 'update'],
                            'level': 'row', 'procedure': 'f1()'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]), CREATE_FUNC_STMT)
        self.assertEqual(fix_indent(dbsql[2]), CREATE_TABLE_STMT)
        self.assertEqual(fix_indent(dbsql[3]), "CREATE CONSTRAINT TRIGGER tr1 "
                         "AFTER INSERT OR UPDATE ON t1 DEFERRABLE INITIALLY "
                         "DEFERRED FOR EACH ROW EXECUTE PROCEDURE f1()")


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(TriggerToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            TriggerToSqlTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            ConstraintTriggerToMapTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            ConstraintTriggerToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
