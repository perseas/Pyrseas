# -*- coding: utf-8 -*-
"""Test loading of data from and into static tables"""
import os

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase

CREATE_STMT = "CREATE TABLE t1 (c1 integer, c2 text)"
FILE_PATH = 'table.t1.data'
TABLE_DATA = [(1, 'abc'), (2, 'def'), (3, 'ghi')]
TABLE_DATA2 = [(1, 'abc', 'row 1'), (3, 'ghi', 'row 2'), (2, 'def', 'row 3'),
               (3, 'def', 'row 4')]


class StaticTableToMapTestCase(DatabaseToMapTestCase):
    """Test mapping and copying out of created tables"""

    def tearDown(self):
        self.remove_tempfiles()

    def test_copy_static_table(self):
        "Copy a two-column table to a file"
        self.db.execute(CREATE_STMT)
        for row in TABLE_DATA:
            self.db.execute("INSERT INTO t1 VALUES (%s, %s)", row)
        cfg = {'datacopy': {'schema sd': ['t1']}}
        dbmap = self.to_map([], config=cfg)
        assert dbmap['schema sd']['table t1'] == {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}}]}
        recs = []
        with open(os.path.join(self.cfg['files']['data_path'],
                               "schema.sd", FILE_PATH)) as f:
            for line in f:
                (c1, c2) = line.split(',')
                recs.append((int(c1), c2.rstrip()))
        assert recs == TABLE_DATA

    def test_copy_static_table_pk(self):
        "Copy a table that has a primary key"
        self.db.execute("CREATE TABLE t1 (c1 integer, c2 char(3), c3 text,"
                        "PRIMARY KEY (c2, c1))")
        for row in TABLE_DATA2:
            self.db.execute("INSERT INTO t1 VALUES (%s, %s, %s)", row)
        cfg = {'datacopy': {'schema sd': ['t1']}}
        dbmap = self.to_map([], config=cfg)
        assert dbmap['schema sd']['table t1'] == {
            'columns': [{'c1': {'type': 'integer', 'not_null': True}},
                        {'c2': {'type': 'character(3)', 'not_null': True}},
                        {'c3': {'type': 'text'}}],
            'primary_key': {'t1_pkey': {'columns': ['c2', 'c1']}}}
        recs = []
        with open(os.path.join(self.cfg['files']['data_path'],
                               "schema.sd", FILE_PATH)) as f:
            for line in f:
                (c1, c2, c3) = line.split(',')
                recs.append((int(c1), c2, c3.rstrip()))
        assert recs == sorted(TABLE_DATA2)


class StaticTableToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation of table load statements"""

    def test_load_static_table(self):
        "Truncate and load a two-column table"
        inmap = self.std_map()
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}},
                        {'c2': {'type': 'text'}}]}})
        cfg = {'datacopy': {'schema sd': ['t1']}}
        sql = self.to_sql(inmap, [CREATE_STMT], config=cfg)
        copy_stmt = ("\\copy ", 'sd.t1', " from '",
                     os.path.join(self.cfg['files']['data_path'],
                                  "schema.sd", FILE_PATH), "' csv")
        assert sql[0] == "TRUNCATE ONLY sd.t1"
        assert sql[1] == copy_stmt

    def test_load_static_table_fk(self):
        "Truncate and load a table which has a foreign key dependency"
        stmts = ["CREATE TABLE t1 (pc1 integer PRIMARY KEY, pc2 text)",
                 "CREATE TABLE t2 (c1 integer, c2 integer REFERENCES t1, "
                 "c3 text)"]
        inmap = self.std_map()
        inmap['schema sd'].update({'table t1': {
            'columns': [{'pc1': {'type': 'integer', 'not_null': True}},
                        {'pc2': {'type': 'text'}}],
            'primary_key': {'t1_pkey': {'columns': ['pc1']}}}, 'table t2': {
                'columns': [{'c1': {'type': 'integer'}},
                            {'c2': {'type': 'integer'}},
                            {'c3': {'type': 'text'}}],
                'foreign_keys': {'t2_c2_fkey': {
                    'columns': ['c2'],
                    'references': {'schema': 'sd', 'table': 't1',
                                   'columns': ['pc1']}}}}})
        cfg = {'datacopy': {'schema sd': ['t1']}}
        sql = self.to_sql(inmap, stmts, config=cfg)
        copy_stmt = ("\\copy ", 'sd.t1', " from '",
                     os.path.join(self.cfg['files']['data_path'],
                                  "schema.sd", FILE_PATH), "' csv")
        assert sql[0] == "ALTER TABLE sd.t2 DROP CONSTRAINT t2_c2_fkey"
        assert sql[1] == "TRUNCATE ONLY sd.t1"
        assert sql[2] == copy_stmt
        assert sql[3] == "ALTER TABLE sd.t2 ADD CONSTRAINT t2_c2_fkey " \
            "FOREIGN KEY (c2) REFERENCES sd.t1 (pc1)"
