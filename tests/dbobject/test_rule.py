# -*- coding: utf-8 -*-
"""Test rules"""

import unittest

from pyrseas.testutils import PyrseasTestCase, fix_indent

CREATE_TABLE_STMT = "CREATE TABLE t1 (c1 integer, c2 text)"
CREATE_STMT = "CREATE RULE r1 AS ON %s TO t1 DO %s"
COMMENT_STMT = "COMMENT ON RULE r1 ON t1 IS 'Test rule r1'"


class RuleToMapTestCase(PyrseasTestCase):
    """Test mapping of existing rules"""

    def test_map_rule_nothing(self):
        "Map a rule to do nothing"
        self.db.execute(CREATE_TABLE_STMT)
        expmap = {'r1': {'event': 'insert',
                              'actions': 'NOTHING'}}
        dbmap = self.db.execute_and_map(CREATE_STMT % ('INSERT', 'NOTHING'))
        self.assertEqual(dbmap['schema public']['table t1']['rules'],
                         expmap)

    def test_map_rule_instead(self):
        "Map rule with an INSTEAD action"
        self.db.execute(CREATE_TABLE_STMT)
        expmap = {'r1': {'event': 'update', 'instead': True,
                              'actions': 'NOTHING'}}
        dbmap = self.db.execute_and_map(CREATE_STMT % ('UPDATE',
                                                       'INSTEAD NOTHING'))
        self.assertEqual(dbmap['schema public']['table t1']['rules'],
                         expmap)

    def test_map_rule_conditional(self):
        "Map rule with a qualification"
        self.db.execute(CREATE_TABLE_STMT)
        expmap = {'r1': {
                'event': 'delete', 'condition': "(old.c1 < 1000)",
                'actions': "INSERT INTO t1 (c1, c2) VALUES (" \
                    "(old.c1 + 1000), old.c2)"}}
        dbmap = self.db.execute_and_map(
            "CREATE RULE r1 AS ON DELETE TO t1 WHERE OLD.c1 < 1000"
            "DO INSERT INTO t1 VALUES (OLD.c1 + 1000, OLD.c2)")
        self.assertEqual(dbmap['schema public']['table t1']['rules'],
                         expmap)

    def test_map_rule_multi_actions(self):
        "Map rule with multiple actions"
        self.db.execute(CREATE_TABLE_STMT)
        expmap = {'r1': {
                'event': 'update',
                'actions': "(INSERT INTO t1 (c1) VALUES ((old.c1 + 100)); "
                "INSERT INTO t1 (c1) VALUES ((old.c1 + 200)); )"}}
        dbmap = self.db.execute_and_map(CREATE_STMT % (
                'UPDATE', "(INSERT INTO t1 (c1) VALUES (old.c1 + 100); "
                "INSERT INTO t1 (c1) VALUES (old.c1 + 200))"))
        self.assertEqual(dbmap['schema public']['table t1']['rules'],
                         expmap)

    def test_map_rule_comment(self):
        "Map a rule comment"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_STMT % ('INSERT', 'NOTHING'))
        dbmap = self.db.execute_and_map(COMMENT_STMT)
        self.assertEqual(dbmap['schema public']['table t1']['rules']
                         ['r1']['description'], 'Test rule r1')


class RuleToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input rules"""

    def test_create_rule_nothing(self):
        "Create a rule"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'rules': {'r1': {'event': 'insert',
                                     'actions': 'NOTHING'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_TABLE_STMT)
        self.assertEqual(fix_indent(dbsql[1]), CREATE_STMT % (
                'INSERT', 'NOTHING'))

    def test_create_rule_instead(self):
        "Create a rule with an INSTEAD action"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'rules': {'r1': {'event': 'update', 'instead': True,
                                     'actions': 'NOTHING'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_TABLE_STMT)
        self.assertEqual(fix_indent(dbsql[1]),
                         "CREATE RULE r1 AS ON UPDATE TO t1 "
                         "DO INSTEAD NOTHING")

    def test_create_rule_conditional(self):
        "Create a rule with qualification"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'rules': {'r1': {'event': 'delete',
                                     'condition': "old.c1 < 1000",
                                     'actions': "INSERT INTO t1 VALUES (" \
                                         "old.c1 + 1000, old.c2)"}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_TABLE_STMT)
        self.assertEqual(fix_indent(dbsql[1]), "CREATE RULE r1 AS ON DELETE "
                         "TO t1 WHERE old.c1 < 1000 "
                         "DO INSERT INTO t1 VALUES (old.c1 + 1000, old.c2)")

    def test_create_rule_multi_actions(self):
        "Create a rule with multiple actions"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'rules': {'r1': {
                            'event': 'update', 'actions':
                                "(INSERT INTO t1 VALUES (old.c1 + 100); " \
                                "INSERT INTO t1 VALUES (old.c1 + 200));)"}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_TABLE_STMT)
        self.assertEqual(fix_indent(dbsql[1]), "CREATE RULE r1 AS ON UPDATE "
                         "TO t1 DO (INSERT INTO t1 VALUES (old.c1 + 100); "
                         "INSERT INTO t1 VALUES (old.c1 + 200));)")

    def test_create_rule_in_schema(self):
        "Create a rule within a non-public schema"
        self.db.execute("DROP SCHEMA IF EXISTS s1 CASCADE")
        self.db.execute_commit("CREATE SCHEMA s1")
        inmap = self.std_map()
        inmap.update({'schema s1': {
                    'table t1': {
                        'columns': [{'c1': {'type': 'integer'}},
                                    {'c2': {'type': 'text'}}],
                    'rules': {'r1': {'event': 'insert',
                                     'actions': 'NOTHING'}}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]), "CREATE RULE r1 "
                         "AS ON INSERT TO s1.t1 DO NOTHING")
        self.db.execute_commit("DROP SCHEMA s1 CASCADE")

    def test_drop_rule(self):
        "Drop an existing rule"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute_commit(CREATE_STMT % ('INSERT', 'NOTHING'))
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}]}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["DROP RULE r1 ON t1"])

    def test_drop_rule_table(self):
        "Drop an existing rule and the related table"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute_commit(CREATE_STMT % ('INSERT', 'NOTHING'))
        dbsql = self.db.process_map(self.std_map())
        self.assertEqual(dbsql[0], "DROP RULE r1 ON t1")
        self.assertEqual(dbsql[1], "DROP TABLE t1")

    def test_rule_with_comment(self):
        "Create a rule with a comment"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'rules': {'r1': {'event': 'insert',
                                     'description': 'Test rule r1',
                                     'actions': 'NOTHING'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql[2], COMMENT_STMT)

    def test_comment_on_rule(self):
        "Create a comment on an existing rule"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute_commit(CREATE_STMT % ('INSERT', 'NOTHING'))
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'rules': {'r1': {'event': 'insert',
                                     'description': 'Test rule r1',
                                     'actions': 'NOTHING'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [COMMENT_STMT])

    def test_drop_rule_comment(self):
        "Drop the comment on an existing rule"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_STMT % ('INSERT', 'NOTHING'))
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'rules': {'r1': {'event': 'insert',
                                     'actions': 'NOTHING'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql,
                         ["COMMENT ON RULE r1 ON t1 IS NULL"])

    def test_change_rule_comment(self):
        "Change existing comment on a rule"
        self.db.execute(CREATE_TABLE_STMT)
        self.db.execute(CREATE_STMT % ('INSERT', 'NOTHING'))
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'rules': {'r1': {'event': 'insert',
                                     'description': 'Changed rule r1',
                                     'actions': 'NOTHING'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [
                "COMMENT ON RULE r1 ON t1 IS 'Changed rule r1'"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(RuleToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            RuleToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
