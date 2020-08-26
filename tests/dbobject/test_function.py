# -*- coding: utf-8 -*-
"""Test functions"""

import pytest

from inspect import cleandoc

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

SOURCE1 = "SELECT 'dummy'::text"
CREATE_STMT1 = "CREATE FUNCTION sd.f1() RETURNS text LANGUAGE sql IMMUTABLE " \
    "AS $_$%s$_$" % SOURCE1

SOURCE2 = "SELECT GREATEST($1, $2)"
CREATE_STMT2 = "CREATE FUNCTION sd.f1(integer, integer) RETURNS integer " \
    "LANGUAGE sql IMMUTABLE AS $_$%s$_$" % SOURCE2
COMMENT_STMT = "COMMENT ON FUNCTION sd.f1(integer, integer) IS " \
               "'Test function f1'"

SOURCE3 = "SELECT * FROM generate_series($1, $2)"
CREATE_STMT3 = "CREATE FUNCTION f2(integer, integer) RETURNS SETOF integer " \
    "ROWS 20 LANGUAGE sql IMMUTABLE AS $_$%s$_$" % SOURCE3

SOURCE4 = "SELECT $1 + $2"
CREATE_STMT4 = "CREATE FUNCTION fadd(integer, integer) RETURNS integer " \
    "LANGUAGE sql IMMUTABLE AS $_$%s$_$" % SOURCE4

SOURCE5 = "SELECT $1 - $2"
CREATE_STMT5 = "CREATE FUNCTION fsub(integer, integer) RETURNS integer " \
    "LANGUAGE sql IMMUTABLE AS $_$%s$_$" % SOURCE5


class FunctionToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing functions"""

    def test_map_function1(self):
        "Map a very simple function with no arguments"
        dbmap = self.to_map([CREATE_STMT1])
        expmap = {'language': 'sql', 'returns': 'text',
                  'source': SOURCE1, 'volatility': 'immutable'}
        assert dbmap['schema sd']['function f1()'] == expmap

    def test_map_function_with_args(self):
        "Map a function with two arguments"
        stmts = ["CREATE FUNCTION f1(integer, integer) RETURNS integer "
                 "LANGUAGE sql AS $_$%s$_$" % SOURCE2]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['function f1(integer, integer)'] == \
            {'language': 'sql', 'returns': 'integer', 'source': SOURCE2}

    def test_map_function_default_args(self):
        "Map a function with default arguments"
        stmts = ["CREATE FUNCTION f1(integer, integer) RETURNS integer "
                 "LANGUAGE sql AS $_$%s$_$" % SOURCE2]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['function f1(integer, integer)'] == \
            {'language': 'sql', 'returns': 'integer', 'source': SOURCE2}

    def test_map_void_function(self):
        "Map a function returning void"
        stmts = ["CREATE TABLE t1 (c1 integer, c2 text)",
                 "CREATE FUNCTION f1() RETURNS void LANGUAGE sql AS "
                 "$_$INSERT INTO t1 VALUES (1, 'dummy')$_$"]
        dbmap = self.to_map(stmts)
        expmap = {'language': 'sql', 'returns': 'void',
                  'source': "INSERT INTO t1 VALUES (1, 'dummy')"}
        assert dbmap['schema sd']['function f1()'] == expmap

    def test_map_setof_row_function(self):
        "Map a function returning a set of rows"
        stmts = ["CREATE TABLE t1 (c1 integer, c2 text)",
                 "CREATE FUNCTION f1() RETURNS SETOF t1 LANGUAGE sql AS "
                 "$_$SELECT * FROM t1$_$"]
        dbmap = self.to_map(stmts)
        expmap = {'language': 'sql', 'returns': 'SETOF sd.t1',
                  'source': "SELECT * FROM t1"}
        assert dbmap['schema sd']['function f1()'] == expmap

    def test_map_security_definer_function(self):
        "Map a function that is SECURITY DEFINER"
        stmts = ["CREATE FUNCTION f1() RETURNS text LANGUAGE sql "
                 "SECURITY DEFINER AS $_$%s$_$" % SOURCE1]
        dbmap = self.to_map(stmts)
        expmap = {'language': 'sql', 'returns': 'text',
                  'source': SOURCE1, 'security_definer': True}
        assert dbmap['schema sd']['function f1()'] == expmap

    def test_map_c_lang_function(self):
        "Map a dynamically loaded C language function"
        # NOTE 1: Needs contrib/spi module to be available
        # NOTE 2: Needs superuser privilege
        stmts = ["CREATE FUNCTION autoinc() RETURNS trigger "
                 "AS '$libdir/autoinc' LANGUAGE c"]
        dbmap = self.to_map(stmts, superuser=True)
        expmap = {'language': 'c', 'obj_file': '$libdir/autoinc',
                  'link_symbol': 'autoinc', 'returns': 'trigger'}
        assert dbmap['schema sd']['function autoinc()'] == expmap

    def test_map_function_config(self):
        "Map a function with a configuration parameter"
        stmts = ["CREATE FUNCTION f1() RETURNS date LANGUAGE sql SET "
                 "datestyle to postgres, dmy AS $_$SELECT CURRENT_DATE$_$"]
        dbmap = self.to_map(stmts)
        expmap = {'language': 'sql', 'returns': 'date',
                  'configuration': ['DateStyle=postgres, dmy'],
                  'source': "SELECT CURRENT_DATE"}
        assert dbmap['schema sd']['function f1()'] == expmap

    def test_map_function_comment(self):
        "Map a function comment"
        dbmap = self.to_map([CREATE_STMT2, COMMENT_STMT])
        assert dbmap['schema sd']['function f1(integer, integer)'][
            'description'] == 'Test function f1'

    def test_map_function_rows(self):
        "Map a function rows"
        dbmap = self.to_map([CREATE_STMT3])
        assert dbmap['schema sd']['function f2(integer, integer)'][
            'rows'] == 20

    def test_map_function_leakproof(self):
        "Map a function with LEAKPROOF qualifier"
        stmt = CREATE_STMT4.replace("IMMUTABLE", "IMMUTABLE LEAKPROOF")
        dbmap = self.to_map([stmt], superuser=True)
        expmap = {'language': 'sql', 'returns': 'integer', 'leakproof': True,
                  'source': SOURCE4, 'volatility': 'immutable'}
        assert dbmap['schema sd']['function fadd(integer, integer)'] == \
            expmap


class FunctionToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input functions"""

    def test_create_function1(self):
        "Create a very simple function with no arguments"
        inmap = self.std_map()
        inmap['schema sd'].update({'function f1()': {
            'language': 'sql', 'returns': 'text', 'source': SOURCE1,
            'volatility': 'immutable'}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[1]) == CREATE_STMT1

    def test_create_function_with_args(self):
        "Create a function with two arguments"
        inmap = self.std_map()
        inmap['schema sd'].update({
            'function f1(integer, integer)': {
                'language': 'sql', 'returns': 'integer', 'source': SOURCE2}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[1]) == "CREATE FUNCTION sd.f1(integer, integer)"\
            " RETURNS integer LANGUAGE sql AS $_$%s$_$" % SOURCE2

    def test_create_setof_row_function(self):
        "Create a function returning a set of rows"
        inmap = self.std_map()
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}},
                        {'c2': {'type': 'text'}}]}})
        inmap['schema sd'].update({
            'function f1()': {'language': 'sql', 'returns': 'SETOF t1',
                              'source': "SELECT * FROM t1"}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[2]) == "CREATE FUNCTION sd.f1() RETURNS " \
            "SETOF t1 LANGUAGE sql AS $_$SELECT * FROM t1$_$"

    def test_create_setof_row_function_rows(self):
        "Create a function returning a set of rows with suggested number"
        inmap = self.std_map()
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}},
                        {'c2': {'type': 'text'}}]}})
        inmap['schema sd'].update({
            'function f1()': {'language': 'sql', 'returns': 'SETOF t1',
                              'source': "SELECT * FROM t1", 'rows': 50}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[2]) == "CREATE FUNCTION sd.f1() RETURNS SETOF " \
            "t1 LANGUAGE sql ROWS 50 AS $_$SELECT * FROM t1$_$"

    def test_create_security_definer_function(self):
        "Create a SECURITY DEFINER function"
        inmap = self.std_map()
        inmap['schema sd'].update({'function f1()': {
            'language': 'sql', 'returns': 'text', 'source': SOURCE1,
            'security_definer': True}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[1]) == "CREATE FUNCTION sd.f1() RETURNS text " \
            "LANGUAGE sql SECURITY DEFINER AS $_$%s$_$" % SOURCE1

    def test_create_c_lang_function(self):
        "Create a dynamically loaded C language function"
        # NOTE 1: Needs contrib/spi module to be available
        # NOTE 2: Needs superuser privilege
        inmap = self.std_map()
        inmap['schema sd'].update({'function autoinc()': {
            'language': 'c', 'returns': 'trigger',
            'obj_file': '$libdir/autoinc'}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == "CREATE FUNCTION sd.autoinc() " \
            "RETURNS trigger LANGUAGE c AS '$libdir/autoinc', 'autoinc'"

    def test_create_function_config(self):
        "Create a function with a configuration parameter"
        inmap = self.std_map()
        inmap['schema sd'].update({'function f1()': {
            'language': 'sql', 'returns': 'date',
            'configuration': ['DateStyle=postgres, dmy'],
            'source': "SELECT CURRENT_DATE"}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[1]) == "CREATE FUNCTION sd.f1() RETURNS date " \
            "LANGUAGE sql SET DateStyle=postgres, dmy AS " \
            "$_$SELECT CURRENT_DATE$_$"

    def test_create_function_in_schema(self):
        "Create a function within a non-default schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {'function f1()': {
            'language': 'sql', 'returns': 'text', 'source': SOURCE1,
            'volatility': 'immutable'}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        assert fix_indent(sql[1]) == "CREATE FUNCTION s1.f1() RETURNS text " \
            "LANGUAGE sql IMMUTABLE AS $_$%s$_$" % SOURCE1

    def test_bad_function_map(self):
        "Error creating a function with a bad map"
        inmap = self.std_map()
        inmap['schema sd'].update({'f1()': {
            'language': 'sql', 'returns': 'text', 'source': SOURCE1}})
        with pytest.raises(KeyError):
            self.to_sql(inmap)

    def test_drop_function1(self):
        "Drop an existing function with no arguments"
        sql = self.to_sql(self.std_map(), [CREATE_STMT1])
        assert sql == ["DROP FUNCTION sd.f1()"]

    def test_drop_function_with_args(self):
        "Drop an existing function which has arguments"
        sql = self.to_sql(self.std_map(), [CREATE_STMT2])
        assert sql == ["DROP FUNCTION sd.f1(integer, integer)"]

    def test_change_function_defn(self):
        "Change function definition"
        inmap = self.std_map()
        inmap['schema sd'].update({'function f1()': {
            'language': 'sql', 'returns': 'text',
            'source': "SELECT 'example'::text", 'volatility': 'immutable'}})
        sql = self.to_sql(inmap, [CREATE_STMT1])
        assert fix_indent(sql[1]) == "CREATE OR REPLACE FUNCTION sd.f1() " \
            "RETURNS text LANGUAGE sql IMMUTABLE AS " \
            "$_$SELECT 'example'::text$_$"

    def test_function_with_comment(self):
        "Create a function with a comment"
        inmap = self.std_map()
        inmap['schema sd'].update({
            'function f1(integer, integer)': {
                'description': 'Test function f1', 'language': 'sql',
                'returns': 'integer', 'source': SOURCE2}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[1]) == "CREATE FUNCTION sd.f1(integer, integer)"\
            " RETURNS integer LANGUAGE sql AS $_$%s$_$" % SOURCE2
        assert sql[2] == COMMENT_STMT

    def test_comment_on_function(self):
        "Create a comment for an existing function"
        inmap = self.std_map()
        inmap['schema sd'].update({
            'function f1(integer, integer)': {
                'description': 'Test function f1', 'language': 'sql',
                'returns': 'integer', 'source': SOURCE2}})
        sql = self.to_sql(inmap, [CREATE_STMT2])
        assert sql == [COMMENT_STMT]

    def test_drop_function_comment(self):
        "Drop a comment on an existing function"
        stmts = [CREATE_STMT2, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema sd'].update({
            'function f1(integer, integer)': {
                'language': 'sql', 'returns': 'integer', 'source': SOURCE2}})
        sql = self.to_sql(inmap, stmts)
        assert sql == ["COMMENT ON FUNCTION sd.f1(integer, integer) IS NULL"]

    def test_change_function_comment(self):
        "Change existing comment on a function"
        stmts = [CREATE_STMT2, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema sd'].update({
            'function f1(integer, integer)': {
                'description': 'Changed function f1', 'language': 'sql',
                'returns': 'integer', 'source': SOURCE2}})
        sql = self.to_sql(inmap, stmts)
        assert sql == ["COMMENT ON FUNCTION sd.f1(integer, integer) IS "
                       "'Changed function f1'"]

    def test_function_leakproof(self):
        "Create a function with LEAKPROOF qualifier"
        inmap = self.std_map()
        inmap['schema sd'].update({
            'function f1(integer, integer)': {
                'language': 'sql', 'returns': 'integer', 'leakproof': True,
                'source': SOURCE4, 'volatility': 'immutable'}})
        sql = self.to_sql(inmap, superuser=True)
        assert fix_indent(sql[1]) == "CREATE FUNCTION sd.f1(integer, integer)"\
            " RETURNS integer LANGUAGE sql IMMUTABLE LEAKPROOF AS " \
            "$_$%s$_$" % SOURCE4

    def test_alter_function_leakproof(self):
        "Change a function with LEAKPROOF qualifier"
        inmap = self.std_map()
        inmap['schema sd'].update({
            'function fadd(integer, integer)': {
                'language': 'sql', 'returns': 'integer',
                'source': SOURCE4, 'volatility': 'immutable'}})
        stmt = CREATE_STMT4.replace("IMMUTABLE", "IMMUTABLE LEAKPROOF")
        sql = self.to_sql(inmap, [stmt], superuser=True)
        assert fix_indent(sql[0]) == \
            "ALTER FUNCTION sd.fadd(integer, integer) NOT LEAKPROOF"

    def test_change_function_return_type(self):
        source = lambda rtype: "SELECT '127.0.0.1'::{}".format(rtype)
        old_type = 'text'
        new_type = 'inet'
        statement = lambda rtype: cleandoc("""
            CREATE OR REPLACE FUNCTION sd.fget_addr()
            RETURNS {rtype}
            LANGUAGE sql
            IMMUTABLE
            AS $_${body}$_$"""
        ).format(
            rtype=rtype,
            body=source(rtype),
        ).replace('\n', ' ')

        inmap = self.std_map()
        inmap['schema sd'].update({
            'function fget_addr()': {
                'language': 'sql',
                'returns': new_type,
                'source': source(new_type),
            }
        })
        sql = self.to_sql(inmap, [statement(old_type)])
        assert statement(new_type) == fix_indent(sql[1])


class AggregateToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing aggregates"""

    def test_map_aggregate_simple(self):
        "Map a simple aggregate"
        stmts = [CREATE_STMT2, "CREATE AGGREGATE a1 (integer) ("
                 "SFUNC = f1, STYPE = integer)"]
        dbmap = self.to_map(stmts)
        expmap = {'sfunc': 'f1', 'stype': 'integer'}
        assert dbmap['schema sd']['function f1(integer, integer)'] == \
            {'language': 'sql', 'returns': 'integer', 'source': SOURCE2,
             'volatility': 'immutable'}
        assert dbmap['schema sd']['aggregate a1(integer)'] == expmap

    def test_map_aggregate_init_final(self):
        "Map an aggregate with an INITCOND and a FINALFUNC"
        stmts = [CREATE_STMT2,
                 "CREATE FUNCTION f2(integer) RETURNS float "
                 "LANGUAGE sql AS $_$SELECT $1::float$_$ IMMUTABLE",
                 "CREATE AGGREGATE a1 (integer) (SFUNC = f1, STYPE = integer, "
                 "FINALFUNC = f2, INITCOND = '-1')"]
        dbmap = self.to_map(stmts)
        expmap = {'sfunc': 'f1', 'stype': 'integer',
                  'initcond': '-1', 'finalfunc': 'f2'}
        assert dbmap['schema sd']['function f1(integer, integer)'] == \
            {'language': 'sql', 'returns': 'integer', 'source': SOURCE2,
             'volatility': 'immutable'}
        assert dbmap['schema sd']['function f2(integer)'] == \
            {'language': 'sql', 'returns': 'double precision',
             'source': "SELECT $1::float", 'volatility': 'immutable'}
        assert dbmap['schema sd']['aggregate a1(integer)'] == expmap

    def test_map_aggregate_sortop(self):
        "Map an aggregate with a SORTOP"
        stmts = [CREATE_STMT2, "CREATE AGGREGATE a1 (integer) ("
                 "SFUNC = f1, STYPE = integer, SORTOP = >)"]
        dbmap = self.to_map(stmts)
        expmap = {'sfunc': 'f1', 'stype': 'integer',
                  'sortop': 'pg_catalog.>'}
        assert dbmap['schema sd']['aggregate a1(integer)'] == expmap

    def test_map_moving_aggregate(self):
        "Map a moving-aggregate mode function"
        if self.db.version < 90400:
            self.skipTest('Only available on PG 9.4 and later')
        stmts = [CREATE_STMT4, CREATE_STMT5,
                 "CREATE AGGREGATE a1 (integer) (sfunc = fadd, "
                 "stype = integer, initcond = '0', msfunc = fadd, "
                 "minvfunc = fsub, mstype = integer, minitcond = '0')"]
        dbmap = self.to_map(stmts)
        expmap = {'sfunc': 'fadd', 'stype': 'integer', 'initcond': '0',
                  'msfunc': 'fadd', 'minvfunc': 'fsub', 'mstype': 'integer',
                  'minitcond': '0'}
        assert dbmap['schema sd']['aggregate a1(integer)'] == expmap

    def test_map_ordered_set_aggregate(self):
        "Map an ordered-set aggregate"
        if self.db.version < 90400:
            self.skipTest('Only available on PG 9.4 and later')
        stmts = [CREATE_STMT2, "CREATE AGGREGATE a1 (integer ORDER BY "
                 "integer) (sfunc = f1, stype = integer)"]
        dbmap = self.to_map(stmts)
        expmap = {'sfunc': 'f1', 'stype': 'integer', 'kind': 'ordered'}
        assert dbmap['schema sd'][
            'aggregate a1(integer ORDER BY integer)'] == expmap

    def test_map_aggregate_restricted(self):
        "Map an aggregate with restricted parallel safety"
        if self.db.version < 90600:
            self.skipTest('Only available on PG 9.6 and later')
        stmts = [CREATE_STMT2, "CREATE AGGREGATE a1 (integer) ("
                 "SFUNC = f1, STYPE = integer, PARALLEL = RESTRICTED)"]
        dbmap = self.to_map(stmts)
        expmap = {'sfunc': 'f1', 'stype': 'integer', 'parallel': 'restricted'}
        assert dbmap['schema sd']['aggregate a1(integer)'] == expmap


class AggregateToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input aggregates"""

    def test_create_aggregate_simple(self):
        "Create a simple aggregate"
        inmap = self.std_map()
        inmap['schema sd'].update({'function f1(integer, integer)': {
            'language': 'sql', 'returns': 'integer', 'source': SOURCE2,
            'volatility': 'immutable'}})
        inmap['schema sd'].update({'aggregate a1(integer)': {
            'sfunc': 'f1', 'stype': 'integer'}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[1]) == CREATE_STMT2
        assert fix_indent(sql[2]) == "CREATE AGGREGATE sd.a1(integer) " \
            "(SFUNC = sd.f1, STYPE = integer)"

    def test_create_aggregate_sortop(self):
        "Create an aggregate that specifies a sort operator"
        inmap = self.std_map()
        inmap['schema sd'].update({'function f1(float, float)': {
            'language': 'sql', 'returns': 'float', 'source': SOURCE2,
            'volatility': 'immutable'}})
        inmap['schema sd'].update({'aggregate a1(float)': {
            'sfunc': 'f1', 'stype': 'float', 'sortop': 'pg_catalog.>'}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[2]) == "CREATE AGGREGATE sd.a1(float) " \
            "(SFUNC = sd.f1, STYPE = float, SORTOP = OPERATOR(pg_catalog.>))"

    def test_create_aggregate_init_final(self):
        "Create an aggregate with an INITCOND and a FINALFUNC"
        inmap = self.std_map()
        inmap['schema sd'].update({'function f1(integer, integer)': {
            'language': 'sql', 'returns': 'integer', 'source': SOURCE2,
            'volatility': 'immutable'}})
        inmap['schema sd'].update({'function f2(integer)': {
            'language': 'sql', 'returns': 'double precision',
            'source': "SELECT $1::float", 'volatility': 'immutable'}})
        inmap['schema sd'].update({'aggregate a1(integer)': {
            'sfunc': 'f1', 'stype': 'integer', 'initcond': '-1',
            'finalfunc': 'f2'}})
        sql = self.to_sql(inmap)
        funcs = sorted(sql[1:3])
        assert fix_indent(funcs[0]) == CREATE_STMT2
        assert fix_indent(funcs[1]) == "CREATE FUNCTION sd.f2(integer) " \
            "RETURNS double precision LANGUAGE sql IMMUTABLE " \
            "AS $_$SELECT $1::float$_$"
        assert fix_indent(sql[3]) == "CREATE AGGREGATE sd.a1(integer) " \
            "(SFUNC = sd.f1, STYPE = integer, FINALFUNC = sd.f2, " \
            "INITCOND = '-1')"

    def test_drop_aggregate(self):
        "Drop an existing aggregate"
        stmts = [CREATE_STMT2, "CREATE AGGREGATE agg1 (integer) "
                 "(SFUNC = f1, STYPE = integer)"]
        sql = self.to_sql(self.std_map(), stmts)
        assert sql[0] == "DROP AGGREGATE sd.agg1(integer)"
        assert sql[1] == "DROP FUNCTION sd.f1(integer, integer)"

    def test_create_moving_aggregate(self):
        "Create a moving-aggregate mode function"
        if self.db.version < 90400:
            self.skipTest('Only available on PG 9.4 and later')
        inmap = self.std_map()
        inmap['schema sd'].update(
            {'function fadd(integer, integer)': {
                'language': 'sql', 'returns': 'integer', 'source': SOURCE4,
                'volatility': 'immutable'},
             'function fsub(integer, integer)': {
                 'language': 'sql', 'returns': 'integer', 'source': SOURCE5,
                 'volatility': 'immutable'},
             'aggregate a1(integer)': {
                 'sfunc': 'fadd', 'stype': 'integer', 'initcond': '0',
                 'msfunc': 'fadd', 'minvfunc': 'fsub', 'mstype': 'integer',
                 'minitcond': '0'}})
        sql = self.to_sql(inmap, [CREATE_STMT4, CREATE_STMT5])
        assert fix_indent(sql[0]) == "CREATE AGGREGATE sd.a1(integer) (" \
            "SFUNC = sd.fadd, STYPE = integer, INITCOND = '0', " \
            "MSFUNC = sd.fadd, MINVFUNC = sd.fsub, MSTYPE = integer, " \
            "MINITCOND = '0')"

    def test_create_hypothetical_set_aggregate(self):
        "Create a hypothetical-set aggregate"
        if self.db.version < 90400:
            self.skipTest('Only available on PG 9.4 and later')
        inmap = self.std_map()
        inmap['schema sd'].update({
            'function f1(integer, integer)': {
                'language': 'sql', 'returns': 'integer', 'source': SOURCE2,
                'volatility': 'immutable'},
            'aggregate a1(integer ORDER BY integer)': {
                'kind': 'hypothetical', 'sfunc': 'f1', 'stype': 'integer'}})
        sql = self.to_sql(inmap, [CREATE_STMT2])
        assert fix_indent(sql[0]) == "CREATE AGGREGATE sd.a1(integer " \
            "ORDER BY integer) (SFUNC = sd.f1, STYPE = integer, HYPOTHETICAL)"

    def test_create_aggregate_parallel_safe(self):
        "Create an aggregate with parallel safety"
        if self.db.version < 90600:
            self.skipTest('Only available on PG 9.6 and later')
        inmap = self.std_map()
        inmap['schema sd'].update({
            'function f1(integer, integer)': {
                'language': 'sql', 'returns': 'integer', 'source': SOURCE2,
                'volatility': 'immutable'},
            'aggregate a1(integer ORDER BY integer)': {
                'sfunc': 'f1', 'stype': 'integer', 'parallel': 'safe'}})
        sql = self.to_sql(inmap, [CREATE_STMT2])
        assert fix_indent(sql[0]) == "CREATE AGGREGATE sd.a1(integer " \
            "ORDER BY integer) (SFUNC = sd.f1, STYPE = integer, " \
            "PARALLEL = SAFE)"
