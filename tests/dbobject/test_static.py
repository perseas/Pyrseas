# -*- coding: utf-8 -*-
"""Test loading of data into static tables"""
import os

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_STMT = "CREATE TABLE t1 (c1 integer, c2 text)"
FILE_PATH = 'table.t1.data'
TABLE_DATA = [(1, 'abc'), (2, 'def'), (3, 'ghi')]


class StaticTableToMapTestCase(DatabaseToMapTestCase):
    """Test mapping and copying out of created tables"""

    def tearDown(self):
        self.remove_tempfiles()

    def test_copy_static_table(self):
        "Copy a two-column table to a file"
        self.db.execute(CREATE_STMT)
        for row in TABLE_DATA:
            self.db.execute("INSERT INTO t1 VALUES (%s, %s)", row)
        cfg = {'datacopy': {'schema public': ['t1']}}
        dbmap = self.to_map([], config=cfg)
        assert dbmap['schema public']['table t1'] == {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}}]}
        recs = []
        with open(os.path.join(self.cfg['files']['data_path'],
                               "schema.public", FILE_PATH)) as f:
            for line in f:
                (c1, c2) = line.split(',')
                recs.append((int(c1), c2.rstrip()))
        assert recs == TABLE_DATA


class StaticTableToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation of table load statements"""

    def test_load_static_table(self):
        "Truncate and load a two-column table"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}},
                        {'c2': {'type': 'text'}}]}})
        cfg = {'datacopy': {'schema public': ['t1']}}
        sql = self.to_sql(inmap, [CREATE_STMT], config=cfg)
        copy_stmt = "\\copy t1 from '%s' csv" % os.path.join(
            self.cfg['files']['data_path'], "schema.public", FILE_PATH)
        assert fix_indent(sql[0]) == "TRUNCATE ONLY t1"
        assert fix_indent(sql[1]) == copy_stmt

    def test_load_static_table_fk(self):
        "Truncate and load a table which has a foreign key dependency"
        stmts = ["CREATE TABLE t1 (pc1 integer PRIMARY KEY, pc2 text)",
                 "CREATE TABLE t2 (c1 integer, c2 integer REFERENCES t1, "
                 "c3 text)"]
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
            'columns': [{'pc1': {'type': 'integer', 'not_null': True}},
                        {'pc2': {'type': 'text'}}],
            'primary_key': {'t1_pkey': {'columns': ['pc1']}}}, 'table t2': {
                'columns': [{'c1': {'type': 'integer'}},
                            {'c2': {'type': 'integer'}},
                            {'c3': {'type': 'text'}}],
                'foreign_keys': {'t2_c2_fkey': {'columns': ['c2'],
                'references': {'schema': 'public', 'table': 't1',
                               'columns': ['pc1']}}}}})
        cfg = {'datacopy': {'schema public': ['t1']}}
        sql = self.to_sql(inmap, stmts, config=cfg)
        copy_stmt = "\\copy t1 from '%s' csv" % os.path.join(
            self.cfg['files']['data_path'], "schema.public", FILE_PATH)
        assert sql[0] == "ALTER TABLE t2 DROP CONSTRAINT t2_c2_fkey"
        assert sql[1] == "TRUNCATE ONLY t1"
        assert sql[2] == copy_stmt
        assert sql[3] == "ALTER TABLE t2 ADD CONSTRAINT t2_c2_fkey " \
            "FOREIGN KEY (c2) REFERENCES t1 (pc1)"
