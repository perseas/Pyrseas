# -*- coding: utf-8 -*-
"""Test event triggers"""

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

FUNC_SRC = "BEGIN RAISE NOTICE 'Command % executed', tg_tag; END"
CREATE_FUNC_STMT = "CREATE FUNCTION sd.f1() RETURNS event_trigger " \
    "LANGUAGE plpgsql AS $_$%s$_$" % FUNC_SRC
CREATE_STMT = "CREATE EVENT TRIGGER et1 ON ddl_command_end %s" \
    "EXECUTE PROCEDURE sd.f1()"
DROP_TABLE_STMT = "DROP TABLE IF EXISTS t1"
DROP_FUNC_STMT = "DROP FUNCTION IF EXISTS f1()"
COMMENT_STMT = "COMMENT ON EVENT TRIGGER et1 IS 'Test event trigger et1'"


class EventTriggerToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing event triggers"""

    def setUp(self):
        super(self.__class__, self).setUp()
        if self.db.version < 90000:
            if not self.db.is_plpgsql_installed():
                self.db.execute_commit("CREATE LANGUAGE plpgsql")

    def test_map_event_trigger_simple(self):
        "Map a simple event trigger"
        stmts = [CREATE_FUNC_STMT, CREATE_STMT % '']
        dbmap = self.to_map(stmts)
        assert dbmap['event trigger et1'] == {
            'enabled': True, 'event': 'ddl_command_end',
            'procedure': 'sd.f1()'}

    def test_map_event_trigger_filter(self):
        "Map a trigger with tag filter variables"
        stmts = [CREATE_FUNC_STMT, CREATE_STMT % (
            "WHEN tag IN ('CREATE TABLE', 'CREATE VIEW') ")]
        dbmap = self.to_map(stmts)
        assert dbmap['event trigger et1'] == {
            'enabled': True, 'event': 'ddl_command_end',
            'tags': ['CREATE TABLE', 'CREATE VIEW'], 'procedure': 'sd.f1()'}

    def test_map_event_trigger_comment(self):
        "Map a trigger comment"
        stmts = [CREATE_FUNC_STMT, CREATE_STMT % '', COMMENT_STMT]
        dbmap = self.to_map(stmts)
        assert dbmap['event trigger et1']['description'] == \
            'Test event trigger et1'


class EventTriggerToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input triggers"""

    def setUp(self):
        super(self.__class__, self).setUp()
        if self.db.version < 90000:
            if not self.db.is_plpgsql_installed():
                self.db.execute_commit("CREATE LANGUAGE plpgsql")

    def test_create_event_trigger_simple(self):
        "Create a simple event trigger"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'event_trigger',
            'source': FUNC_SRC}})
        inmap.update({'event trigger et1': {
            'enabled': True, 'event': 'ddl_command_end',
            'procedure': 'sd.f1()'}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_FUNC_STMT
        assert fix_indent(sql[1]) == CREATE_STMT % ''

    def test_create_event_trigger_filter(self):
        "Create an event trigger with tag filter variables"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'event_trigger',
            'source': FUNC_SRC}})
        inmap.update({'event trigger et1': {
            'enabled': True, 'event': 'ddl_command_end',
            'procedure': 'sd.f1()', 'tags': ['CREATE TABLE', 'CREATE VIEW']}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_FUNC_STMT
        assert fix_indent(sql[1]) == CREATE_STMT % (
            "WHEN tag IN ('CREATE TABLE', 'CREATE VIEW') ")

    def test_create_event_trigger_func_schema(self):
        "Create an event trigger with function in a non-default schema"
        inmap = self.std_map(plpgsql_installed=True)
        inmap.update({'schema s1': {'function f1()': {
            'language': 'plpgsql', 'returns': 'event_trigger',
            'source': FUNC_SRC}}})
        inmap.update({'event trigger et1': {
            'enabled': True, 'event': 'ddl_command_end',
            'procedure': 's1.f1()'}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        assert fix_indent(sql[0]) == "CREATE FUNCTION s1.f1() " \
            "RETURNS event_trigger LANGUAGE plpgsql AS $_$%s$_$" % FUNC_SRC
        assert fix_indent(sql[1]) == "CREATE EVENT TRIGGER et1 " \
            "ON ddl_command_end EXECUTE PROCEDURE s1.f1()"

    def test_drop_event_trigger(self):
        "Drop an existing event trigger"
        stmts = [CREATE_FUNC_STMT, CREATE_STMT % '']
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'event_trigger',
            'source': FUNC_SRC}})
        sql = self.to_sql(inmap, stmts)
        assert sql == ["DROP EVENT TRIGGER et1"]

    def test_drop_event_trigger_function(self):
        "Drop an existing event trigger and the related function"
        stmts = [CREATE_FUNC_STMT, CREATE_STMT % '']
        inmap = self.std_map(plpgsql_installed=True)
        sql = self.to_sql(inmap, stmts)
        assert sql[0] == "DROP EVENT TRIGGER et1"
        assert sql[1] == "DROP FUNCTION sd.f1()"

    def test_create_event_trigger_with_comment(self):
        "Create an event trigger with a comment"
        inmap = self.std_map(plpgsql_installed=True)
        inmap['schema sd'].update({'function f1()': {
            'language': 'plpgsql', 'returns': 'event_trigger',
            'source': FUNC_SRC}})
        inmap.update({'event trigger et1': {
            'enabled': True, 'event': 'ddl_command_end',
            'procedure': 'sd.f1()', 'description': 'Test event trigger et1'}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_FUNC_STMT
        assert fix_indent(sql[1]) == CREATE_STMT % ''
        assert sql[2] == COMMENT_STMT
