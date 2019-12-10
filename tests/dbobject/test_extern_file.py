# -*- coding: utf-8 -*-
"""Test external files used in --multiple-files option"""
import sys

import pytest

from pyrseas.testutils import PyrseasTestCase
from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.dbobject.schema import Schema
from pyrseas.dbobject.function import Function
from pyrseas.dbobject.table import Sequence, Table
from pyrseas.dbobject.view import View

if sys.platform == 'win32':
    COLL = 'French_France.1252'
else:
    COLL = 'fr_FR.UTF-8'

CREATE_FDW = "CREATE FOREIGN DATA WRAPPER "
SOURCE1 = "SELECT 'dummy'::text"
SOURCE2 = "SELECT $1::text"
DROP_LANG = "DROP LANGUAGE IF EXISTS plperl CASCADE"
DROP_TSC = "DROP TEXT SEARCH CONFIGURATION IF EXISTS tsc1, tsc2"
DROP_TSP = "DROP TEXT SEARCH PARSER IF EXISTS tsp1 CASCADE"


class ExternalFilenameMapTestCase(DatabaseToMapTestCase):

    def setUp(self):
        super(ExternalFilenameMapTestCase, self).setUp()
        self.remove_tempfiles()

    def test_map_casts(self):
        "Map casts"
        self.to_map(["CREATE FUNCTION int2_bool(smallint) RETURNS boolean "
                     "LANGUAGE sql IMMUTABLE AS "
                     "$_$SELECT CAST($1::int AS boolean)$_$",
                     "CREATE DOMAIN d1 AS integer",
                     "CREATE CAST (smallint AS boolean) WITH FUNCTION "
                     "int2_bool(smallint)",
                     "CREATE CAST (d1 AS integer) WITH INOUT AS IMPLICIT"],
                    superuser=True, multiple_files=True)
        expmap = {'cast (smallint as boolean)': {
            'function': 'int2_bool(smallint)', 'context': 'explicit',
            'method': 'function'}, 'cast (d1 as integer)':
            {'context': 'implicit', 'method': 'inout',
             'depends_on': ['domain d1']}}
        assert self.yaml_load('cast.yaml') == expmap

    def test_map_extension(self):
        "Map extensions"
        TRGM_VERS = '1.4'
        if self.db.version < 90300:
            TRGM_VERS = '1.0'
        elif self.db.version < 90600:
            TRGM_VERS = '1.1'
        elif self.db.version < 110000:
            TRGM_VERS = '1.3'
        self.to_map(["CREATE EXTENSION pg_trgm"], superuser=True,
                    multiple_files=True)
        expmap = {'extension plpgsql': {
            'schema': 'pg_catalog', 'version': '1.0',
            'description': 'PL/pgSQL procedural language'},
            'extension pg_trgm': {'schema': 'public', 'version': TRGM_VERS,
                                  'description': "text similarity measurement "
                                  "and index searching based on trigrams"}}
        assert self.yaml_load('extension.yaml') == expmap

    def test_map_fd_wrappers(self):
        "Map foreign data wrappers"
        self.to_map([CREATE_FDW + "fdw1", CREATE_FDW + "fdw2 "
                     "OPTIONS (debug 'true')"], superuser=True,
                    multiple_files=True)
        expmap = {'foreign data wrapper fdw1': {},
                  'foreign data wrapper fdw2': {'options': ['debug=true']}}
        assert self.yaml_load('foreign_data_wrapper.yaml') == expmap

    def test_map_language(self):
        "Map languages"
        if self.db.version >= 90100:
            self.skipTest('Only available before PG 9.1')
        self.to_map([DROP_LANG, "CREATE LANGUAGE plperl"], multiple_files=True)
        assert self.yaml_load('language.yaml')['language plperl'] == {
            'trusted': True}
        self.db.execute_commit(DROP_LANG)

    def test_collations(self):
        "Map collations"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        self.to_map(["CREATE COLLATION coll1 (LC_COLLATE = '%s', "
                     "LC_CTYPE = '%s')" % (COLL, COLL),
                     "COMMENT ON COLLATION coll1 IS 'A test collation'",
                     "CREATE COLLATION coll2 (LC_COLLATE = '%s', "
                     "LC_CTYPE = '%s')" % (COLL, COLL)],
                    multiple_files=True)
        assert self.yaml_load('collation.yaml', 'schema.public') == {
            'collation coll1': {'lc_collate': COLL, 'lc_ctype': COLL,
                                'description': "A test collation"},
            'collation coll2': {'lc_collate': COLL, 'lc_ctype': COLL}}

    def test_map_conversion(self):
        "Map conversions"
        self.to_map(["CREATE CONVERSION conv1 FOR 'LATIN1' TO 'UTF8' "
                     "FROM iso8859_1_to_utf8",
                     "COMMENT ON CONVERSION conv1 IS 'A test conversion'"],
                    multiple_files=True)
        assert self.yaml_load('conversion.yaml', 'schema.public') == {
            'conversion conv1': {'source_encoding': 'LATIN1',
                                 'dest_encoding': 'UTF8',
                                 'function': 'iso8859_1_to_utf8',
                                 'description': 'A test conversion'}}

    def test_map_functions(self):
        "Map functions"
        self.to_map(["CREATE FUNCTION f1() RETURNS text LANGUAGE sql "
                     "IMMUTABLE AS $_$%s$_$" % SOURCE1,
                     "CREATE FUNCTION f2() RETURNS text LANGUAGE sql "
                     "IMMUTABLE AS $_$%s$_$" % SOURCE1], multiple_files=True)
        expmap = {'language': 'sql', 'returns': 'text',
                  'source': SOURCE1, 'volatility': 'immutable'}
        assert self.yaml_load('function.f1.yaml', 'schema.public') == {
            'function f1()': expmap}
        assert self.yaml_load('function.f2.yaml', 'schema.public') == {
            'function f2()': expmap}

    def test_map_functions_merged(self):
        "Map functions into a merged file"
        self.to_map(["CREATE FUNCTION f3(integer) RETURNS text LANGUAGE sql "
                     "IMMUTABLE AS $_$%s$_$" % SOURCE2,
                     "CREATE FUNCTION f3(real) RETURNS text LANGUAGE sql "
                     "IMMUTABLE AS $_$%s$_$" % SOURCE2], multiple_files=True)
        expmap = {'language': 'sql', 'returns': 'text',
                  'source': SOURCE2, 'volatility': 'immutable'}
        assert self.yaml_load('function.f3.yaml', 'schema.public') == {
            'function f3(integer)': expmap, 'function f3(real)': expmap}

    def test_map_operator(self):
        "Map operators and an operator class"
        self.to_map(["CREATE OPERATOR < (PROCEDURE = int4lt, LEFTARG = int, "
                     "RIGHTARG = int)", "CREATE OPERATOR = (PROCEDURE = "
                     "int4eq, LEFTARG = int, RIGHTARG = int)", "CREATE "
                     "OPERATOR > (PROCEDURE = int4gt, LEFTARG = int, "
                     "RIGHTARG = int)",
                     "CREATE OPERATOR CLASS oc1 FOR TYPE integer USING btree "
                     "AS OPERATOR 1 public.<, OPERATOR 3 public.=, OPERATOR "
                     "5 public.>, FUNCTION 1 btint4cmp(integer,integer)"],
                    superuser=True, multiple_files=True)
        oprmap = {'operator <(integer, integer)': {'procedure': 'int4lt'},
                  'operator =(integer, integer)': {'procedure': 'int4eq'},
                  'operator >(integer, integer)': {'procedure': 'int4gt'}}
        opcmap = {'operator class oc1 using btree': {
            'type': 'integer', 'operators': {
                1: '<(integer,integer)', 3: '=(integer,integer)',
                5: '>(integer,integer)'},
            'functions': {1: 'btint4cmp(integer,integer)'}}}
        assert self.yaml_load('operator.yaml', 'schema.public') == oprmap
        assert self.yaml_load('operator_class.yaml', 'schema.public') == opcmap

    def test_map_operator_family(self):
        "Map operator families"
        self.to_map(["CREATE SCHEMA s1",
                     "CREATE OPERATOR FAMILY s1.of1 USING btree",
                     "CREATE OPERATOR FAMILY s1.of2 USING btree"],
                    superuser=True, multiple_files=True)
        assert self.yaml_load('operator_family.yaml', 'schema.s1') == {
            'operator family of1 using btree': {},
            'operator family of2 using btree': {}}

    def test_map_tables(self):
        "Map tables"
        self.to_map(["CREATE TABLE t1 (c1 integer PRIMARY KEY, c2 text)",
                     "CREATE TABLE t2 (c1 integer, c2 integer, c3 text, "
                     "FOREIGN KEY (c2) REFERENCES t1 (c1))"],
                    multiple_files=True)
        expmap1 = {'table t1': {'columns': [
            {'c1': {'type': 'integer', 'not_null': True}},
            {'c2': {'type': 'text'}}],
            'primary_key': {'t1_pkey': {'columns': ['c1']}}}}
        expmap2 = {'table t2': {'columns': [
            {'c1': {'type': 'integer'}}, {'c2': {'type': 'integer'}},
            {'c3': {'type': 'text'}}],
            'foreign_keys': {'t2_c2_fkey': {'columns': ['c2'], 'references': {
                'schema': 'public', 'table': 't1', 'columns': ['c1']}}}}}
        assert self.yaml_load('table.t1.yaml', 'schema.public') == expmap1
        assert self.yaml_load('table.t2.yaml', 'schema.public') == expmap2

    def test_map_tables_merged(self):
        "Map tables into a merged file"
        self.to_map(["CREATE TABLE account_transfers_with_extra_padding_1 "
                     "(c1 integer, c2 text)",
                     "CREATE TABLE account_transfers_with_extra_padding_2 "
                     "(c1 integer, c2 text)"],
                    multiple_files=True)
        expmap = {'table account_transfers_with_extra_padding_1': {'columns': [
            {'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}}]},
            'table account_transfers_with_extra_padding_2': {'columns': [
                {'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}}]}}
        assert self.yaml_load('table.account_transfers_with_extra_pad.yaml',
                              'schema.public') == expmap

    def test_map_textsearch(self):
        "Map text search components"
        self.to_map([DROP_TSC, DROP_TSP,
                     "CREATE TEXT SEARCH PARSER tsp1 (START = prsd_start, "
                     "GETTOKEN = prsd_nexttoken, END = prsd_end, "
                     "LEXTYPES = prsd_lextype, HEADLINE = prsd_headline)",
                     "CREATE TEXT SEARCH CONFIGURATION tsc1 (PARSER = tsp1)",
                     "CREATE TEXT SEARCH CONFIGURATION tsc2 (PARSER = tsp1)"],
                    superuser=True, multiple_files=True)
        assert self.yaml_load('text_search_configuration.yaml',
                              'schema.public') == \
            {'text search configuration tsc1': {'parser': 'tsp1'},
             'text search configuration tsc2': {'parser': 'tsp1'}}
        assert self.yaml_load('text_search_parser.yaml', 'schema.public') == {
            'text search parser tsp1': {
                'start': 'prsd_start', 'gettoken': 'prsd_nexttoken',
                'end': 'prsd_end', 'lextypes': 'prsd_lextype',
                'headline': 'prsd_headline'}}
        self.db.execute(DROP_TSC)
        self.db.execute_commit(DROP_TSP)

    def test_map_drop_table(self):
        "Map three tables, drop one and map the remaining two"
        self.to_map(["CREATE TABLE t1 (c1 integer, c2 text)",
                     "CREATE TABLE t2 (c1 integer, c2 text)",
                     "CREATE TABLE t3 (c1 integer, c2 text)"],
                    multiple_files=True)
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}}]}
        for tbl in ['t1', 't2', 't3']:
            assert self.yaml_load('table.%s.yaml' % tbl, 'schema.public')[
                'table %s' % tbl] == expmap
        self.to_map(["DROP TABLE t2"], multiple_files=True)
        with pytest.raises(IOError) as exc:
            self.yaml_load('table.t2.yaml', 'schema.public')
        assert 'No such file' in str(exc.value)
        for tbl in ['t1', 't3']:
            assert self.yaml_load('table.%s.yaml' % tbl, 'schema.public')[
                'table %s' % tbl] == expmap


class ExternalFilenameTestCase(PyrseasTestCase):

    def test_function(self):
        "Map a function"
        obj = Function("Weird/Or-what?", 'public', '', None, [], None, None,
                       None, None)
        assert obj.extern_filename() == 'function.weird_or_what_.yaml'

    def test_schema(self):
        "Map a schema"
        obj = Schema(name="A/C Schema")
        assert obj.extern_filename() == 'schema.a_c_schema.yaml'

    def test_long_name_schema(self):
        "Map a schema with a long name"
        nm = 'a_schema_with_a_very_but_very_very_long_long_long_loooonng_name'
        obj = Schema(name=nm)
        assert obj.extern_filename() == 'schema.%s.yaml' % nm

    def test_table(self):
        "Map a table"
        obj = Table("Weird/Or-what?HOW.WeiRD", '', None, None, [])
        assert obj.extern_filename() == 'table.weird_or_what_how_weird.yaml'

    def test_table_unicode(self):
        "Map a table with Unicode characters"
        obj = Table("Fundação\\Größe таблица", '', None, None, [])
        assert obj.extern_filename() == 'table.fundação_größe_таблица.yaml'

    def test_sequence(self):
        "Map a sequence"
        obj = Sequence("Weird/Or-what?_seq", '', None, None, [])
        assert obj.extern_filename() == 'sequence.weird_or_what__seq.yaml'

    def test_view(self):
        "Map a view"
        obj = View("Weirder/Don't You Think?", '', None, None, [], '')
        assert obj.extern_filename() == 'view.weirder_don_t_you_think_.yaml'
