# -*- coding: utf-8 -*-
"""Test constraints"""

import unittest

from pyrseas.testutils import PyrseasTestCase, fix_indent

COMMENT_STMT = "COMMENT ON CONSTRAINT cns1 ON t1 IS 'Test constraint cns1'"


class CheckConstraintToMapTestCase(PyrseasTestCase):
    """Test mapping of created CHECK constraints"""

    def test_check_constraint_1(self):
        "Map a table with a CHECK constraint"
        ddlstmt = "CREATE TABLE t1 (c1 INTEGER, c2 SMALLINT CHECK (c2 < 1000))"
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'smallint'}}],
                  'check_constraints': {'t1_c2_check': {
                    'columns': ['c2'],
                    'expression': '(c2 < 1000)'}}}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_check_constraint_2(self):
        "Map a table with a two-column, named CHECK constraint"
        ddlstmt = "CREATE TABLE t1 (c1 INTEGER, c2 INTEGER, " \
            "CONSTRAINT t1_check_ratio CHECK (c2 * 100 / c1 <= 50))"
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'integer'}}],
                  'check_constraints': {'t1_check_ratio': {
                    'columns': ['c2', 'c1'],
                    'expression': '(((c2 * 100) / c1) <= 50)'}}}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)


class CheckConstraintToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input CHECK constraints"""

    def test_create_w_check_constraint(self):
        "Create new table with a single column CHECK constraint"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'check_constraints': {'t1_c1_check': {
                            'columns': ['c1'],
                            'expression': 'c1 > 0 and c1 < 1000000'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "CREATE TABLE t1 (c1 integer, c2 text)")
        self.assertEqual(fix_indent(dbsql[1]),
                         "ALTER TABLE t1 ADD CONSTRAINT t1_c1_check "
                         "CHECK (c1 > 0 and c1 < 1000000)")

    def test_add_check_constraint(self):
        "Add a two-column CHECK constraint to an existing table"
        self.db.execute_commit("CREATE TABLE t1 (c1 INTEGER NOT NULL, "
                        "c2 INTEGER NOT NULL, c3 TEXT)")
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                'columns': [
                    {'c1': {'type': 'integer', 'not_null': True}},
                    {'c2': {'type': 'integer', 'not_null': True}},
                    {'c3': {'type': 'text'}}],
                'check_constraints': {'t1_check_2_1': {
                        'columns': ['c2', 'c1'],
                        'expression': 'c2 != c1'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "ALTER TABLE t1 ADD CONSTRAINT t1_check_2_1 "
                         "CHECK (c2 != c1)")


class PrimaryKeyToMapTestCase(PyrseasTestCase):
    """Test mapping of created PRIMARY KEYs"""

    map_pkey1 = {'columns': [{'c1': {'type': 'integer', 'not_null': True}},
                             {'c2': {'type': 'text'}}],
                 'primary_key': {'t1_pkey': {'columns': ['c1'],
                                             'access_method': 'btree'}}}
    map_pkey2 = {'columns': [
            {'c1': {'type': 'integer', 'not_null': True}},
            {'c2': {'type': 'character(5)', 'not_null': True}},
            {'c3': {'type': 'text'}}],
                 'primary_key': {'t1_pkey': {'columns': ['c2', 'c1'],
                                             'access_method': 'btree'}}}

    map_pkey3 = {'columns': [{'c1': {'type': 'integer', 'not_null': True}},
                             {'c2': {'type': 'text'}}],
                 'primary_key': {'t1_prim_key': {'columns': ['c1'],
                                                 'access_method': 'btree'}}}

    def test_primary_key_1(self):
        "Map a table with a single-column primary key"
        ddlstmt = "CREATE TABLE t1 (c1 INTEGER PRIMARY KEY, c2 TEXT)"
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], self.map_pkey1)

    def test_primary_key_2(self):
        "Map a table with a single-column primary key, table-level constraint"
        ddlstmt = "CREATE TABLE t1 (c1 INTEGER, c2 TEXT, PRIMARY KEY (c1))"
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], self.map_pkey1)

    def test_primary_key_3(self):
        "Map a table with two-column primary key, atypical order"
        ddlstmt = """CREATE TABLE t1 (c1 INTEGER, c2 CHAR(5), c3 TEXT,
                                      PRIMARY KEY (c2, c1))"""
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], self.map_pkey2)

    def test_primary_key_4(self):
        "Map a table with a named primary key constraint"
        ddlstmt = """CREATE TABLE t1 (c1 INTEGER, c2 TEXT,
                                  CONSTRAINT t1_prim_key PRIMARY KEY (c1))"""
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], self.map_pkey3)

    def test_primary_key_5(self):
        "Map a table with a named primary key, column level constraint"
        ddlstmt = """CREATE TABLE t1 (
                            c1 INTEGER CONSTRAINT t1_prim_key PRIMARY KEY,
                            c2 TEXT)"""
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], self.map_pkey3)


class PrimaryKeyToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input PRIMARY KEYs"""

    def test_create_with_primary_key(self):
        "Create new table with single column primary key"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'text'}},
                                {'c2': {'type': 'integer'}}],
                    'primary_key': {'t1_pkey': {
                            'columns': ['c2'],
                            'access_method': 'btree'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "CREATE TABLE t1 (c1 text, c2 integer)")
        self.assertEqual(fix_indent(dbsql[1]),
                         "ALTER TABLE t1 ADD CONSTRAINT t1_pkey "
                         "PRIMARY KEY (c2)")

    def test_add_primary_key(self):
        "Add a two-column primary key to an existing table"
        self.db.execute_commit("CREATE TABLE t1 (c1 INTEGER NOT NULL, "
                        "c2 INTEGER NOT NULL, c3 TEXT)")
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [
                        {'c1': {'type': 'integer', 'not_null': True}},
                        {'c2': {'type': 'integer', 'not_null': True}},
                        {'c3': {'type': 'text'}}],
                    'primary_key': {'t1_pkey': {
                            'columns': ['c1', 'c2'],
                            'access_method': 'btree'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "ALTER TABLE t1 ADD CONSTRAINT t1_pkey "
                         "PRIMARY KEY (c1, c2)")

    def test_drop_primary_key(self):
        "Drop a primary key on an existing table"
        self.db.execute_commit("CREATE TABLE t1 (c1 INTEGER NOT NULL "
                               "PRIMARY KEY, c2 TEXT)")
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer', 'not_null': True},
                                 'c2': {'type': 'text'}}]}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["ALTER TABLE t1 DROP CONSTRAINT t1_pkey"])


class ForeignKeyToMapTestCase(PyrseasTestCase):
    """Test mapping of created FOREIGN KEYs"""

    map_fkey1 = {'columns': [{'c1': {'type': 'integer'}},
                             {'c2': {'type': 'integer'}},
                             {'c3': {'type': 'text'}}],
                 'foreign_keys': {'t1_c2_fkey': {
                    'columns': ['c2'],
                    'references': {'schema': 'public', 'table': 't2',
                                   'columns': ['pc1']}}}}

    map_fkey2 = {'columns': [{'c1': {'type': 'integer'}},
                             {'c2': {'type': 'character(5)'}},
                             {'c3': {'type': 'integer'}},
                             {'c4': {'type': 'date'}},
                             {'c5': {'type': 'text'}}],
                 'foreign_keys': {'t1_c2_fkey': {
                    'columns': ['c2', 'c3', 'c4'],
                    'references': {'schema': 'public', 'table': 't2',
                                   'columns': ['pc2', 'pc1', 'pc3']}}}}

    map_fkey3 = {'columns': [{'c1': {'type': 'integer'}},
                             {'c2': {'type': 'character(5)'}},
                             {'c3': {'type': 'integer'}},
                             {'c4': {'type': 'date'}},
                             {'c5': {'type': 'text'}}],
                 'foreign_keys': {'t1_fgn_key': {
                    'columns': ['c2', 'c3', 'c4'],
                    'references': {'schema': 'public', 'table': 't2',
                                   'columns': ['pc2', 'pc1', 'pc3']}}}}

    map_fkey4 = {'columns': [{'c1': {'type': 'integer', 'not_null': True}},
                             {'c2': {'type': 'character(5)',
                                     'not_null': True}},
                             {'c3': {'type': 'integer'}},
                             {'c4': {'type': 'date'}},
                             {'c5': {'type': 'text'}}],
                 'primary_key': {'t1_prim_key': {'columns': ['c1', 'c2'],
                                                 'access_method': 'btree'}},
                 'foreign_keys': {'t1_fgn_key1': {
                    'columns': ['c2', 'c3', 'c4'],
                    'references': {'schema': 'public', 'table': 't2',
                                   'columns': ['pc2', 'pc1', 'pc3']}},
                                  't1_fgn_key2': {
                    'columns': ['c2'],
                    'references': {'schema': 'public', 'table': 't3',
                                   'columns': ['qc1']}}}}

    def test_foreign_key_1(self):
        "Map a table with a single-column foreign key on another table"
        self.db.execute("CREATE TABLE t2 (pc1 INTEGER PRIMARY KEY, pc2 TEXT)")
        ddlstmt = """CREATE TABLE t1 (c1 INTEGER,
                          c2 INTEGER REFERENCES t2 (pc1), c3 TEXT)"""
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], self.map_fkey1)

    def test_foreign_key_2(self):
        "Map a table with a single-column foreign key, table level constraint"
        self.db.execute("CREATE TABLE t2 (pc1 INTEGER PRIMARY KEY, pc2 TEXT)")
        ddlstmt = """CREATE TABLE t1 (c1 INTEGER, c2 INTEGER, c3 TEXT,
                            FOREIGN KEY (c2) REFERENCES t2 (pc1))"""
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], self.map_fkey1)

    def test_foreign_key_3(self):
        "Map a table with a three-column foreign key"
        self.db.execute("""CREATE TABLE t2 (pc1 INTEGER, pc2 CHAR(5), pc3 DATE,
                                  pc4 TEXT, PRIMARY KEY (pc2, pc1, pc3))""")
        ddlstmt = """CREATE TABLE t1 (c1 INTEGER, c2 CHAR(5), c3 INTEGER,
                            c4 DATE, c5 TEXT,
                            FOREIGN KEY (c2, c3, c4)
                                REFERENCES t2 (pc2, pc1, pc3))"""
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], self.map_fkey2)

    def test_foreign_key_4(self):
        "Map a table with a named, three-column foreign key"
        self.db.execute("""CREATE TABLE t2 (pc1 INTEGER, pc2 CHAR(5), pc3 DATE,
                                  pc4 TEXT, PRIMARY KEY (pc2, pc1, pc3))""")
        ddlstmt = """CREATE TABLE t1 (c1 INTEGER, c2 CHAR(5), c3 INTEGER,
                            c4 DATE, c5 TEXT,
                            CONSTRAINT t1_fgn_key FOREIGN KEY (c2, c3, c4)
                                REFERENCES t2 (pc2, pc1, pc3))"""
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], self.map_fkey3)

    def test_foreign_key_5(self):
        "Map a table with a primary key and two foreign keys"
        self.db.execute("""CREATE TABLE t2 (pc1 INTEGER, pc2 CHAR(5), pc3 DATE,
                                  pc4 TEXT, PRIMARY KEY (pc2, pc1, pc3))""")
        self.db.execute("CREATE TABLE t3 (qc1 CHAR(5) PRIMARY KEY, qc2 text)")
        ddlstmt = """CREATE TABLE t1 (c1 INTEGER, c2 CHAR(5), c3 INTEGER,
                            c4 DATE, c5 TEXT,
                            CONSTRAINT t1_prim_key PRIMARY KEY (c1, c2),
                            CONSTRAINT t1_fgn_key1 FOREIGN KEY (c2, c3, c4)
                                REFERENCES t2 (pc2, pc1, pc3),
                            CONSTRAINT t1_fgn_key2 FOREIGN KEY (c2)
                                REFERENCES t3 (qc1))"""
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], self.map_fkey4)

    def test_foreign_key_actions(self):
        "Map a table with foreign key ON UPDATE/ON DELETE actions"
        self.db.execute("CREATE TABLE t2 (pc1 INTEGER PRIMARY KEY, pc2 TEXT)")
        ddlstmt = """CREATE TABLE t1 (c1 INTEGER, c2 INTEGER, c3 TEXT,
                            FOREIGN KEY (c2) REFERENCES t2 (pc1)
                                ON UPDATE RESTRICT ON DELETE SET NULL)"""
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'integer'}},
                              {'c3': {'type': 'text'}}],
                  'foreign_keys': {'t1_c2_fkey': {
                    'columns': ['c2'],
                    'on_update': 'restrict',
                    'on_delete': 'set null',
                    'references': {'schema': 'public', 'table': 't2',
                                   'columns': ['pc1']}}}}
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], expmap)

    def test_cross_schema_foreign_key(self):
        "Map a table with a foreign key on a table in another schema"
        self.db.execute("DROP SCHEMA IF EXISTS s1 CASCADE")
        self.db.execute("CREATE SCHEMA s1")
        self.db.execute("CREATE TABLE t2 (pc1 INTEGER PRIMARY KEY, pc2 TEXT)")
        ddlstmt = """CREATE TABLE s1.t1 (c1 INTEGER PRIMARY KEY,
                          c2 INTEGER REFERENCES t2 (pc1), c3 TEXT)"""
        dbmap = self.db.execute_and_map(ddlstmt)
        self.db.execute_commit("DROP SCHEMA s1 CASCADE")
        t2map = {'columns': [{'pc1': {'type': 'integer', 'not_null': True}},
                             {'pc2': {'type': 'text'}}],
                 'primary_key': {'t2_pkey': {
                    'columns': ['pc1'], 'access_method': 'btree'}}}
        t1map = {'table t1': {
                'columns': [{'c1': {'type': 'integer', 'not_null': True}},
                            {'c2': {'type': 'integer'}},
                            {'c3': {'type': 'text'}}],
                'primary_key': {'t1_pkey': {
                        'columns': ['c1'],
                        'access_method': 'btree'}},
                'foreign_keys': {'t1_c2_fkey': {
                        'columns': ['c2'],
                        'references': {'schema': 'public', 'table': 't2',
                                       'columns': ['pc1']}}}}}
        self.assertEqual(dbmap['schema public']['table t2'], t2map)
        self.assertEqual(dbmap['schema s1'], t1map)

    def test_multiple_foreign_key(self):
        "Map a table with its primary key referenced by two others"
        self.db.execute("CREATE TABLE t1 (pc1 integer PRIMARY KEY, pc2 text)")
        ddlstmt = """CREATE TABLE t2 (c1 integer,
                          c2 integer REFERENCES t1 (pc1), c3 text,
                          c4 integer REFERENCES t1 (pc1))"""
        dbmap = self.db.execute_and_map(ddlstmt)
        t1map = {'columns': [{'pc1': {'type': 'integer', 'not_null': True}},
                             {'pc2': {'type': 'text'}}],
                 'primary_key': {'t1_pkey': {
                    'columns': ['pc1'], 'access_method': 'btree'}}}
        t2map = {'columns': [{'c1': {'type': 'integer'}},
                             {'c2': {'type': 'integer'}},
                             {'c3': {'type': 'text'}},
                             {'c4': {'type': 'integer'}}],
                 'foreign_keys': {'t2_c2_fkey': {
                    'columns': ['c2'],
                    'references': {'schema': 'public', 'table': 't1',
                                   'columns': ['pc1']}},
                                  't2_c4_fkey': {
                    'columns': ['c4'],
                    'references': {'schema': 'public', 'table': 't1',
                                   'columns': ['pc1']}}}}
        self.assertEqual(dbmap['schema public']['table t1'], t1map)
        self.assertEqual(dbmap['schema public']['table t2'], t2map)

    def test_foreign_key_dropped_column(self):
        "Map a table with a foreign key after a column has been dropped"
        self.db.execute("CREATE TABLE t1 (pc1 integer PRIMARY KEY, pc2 text)")
        self.db.execute("CREATE TABLE t2 (c1 integer, c2 text, c3 smallint, "
                       "c4 integer REFERENCES t1 (pc1))")
        ddlstmt = "ALTER TABLE t2 DROP COLUMN c3"
        dbmap = self.db.execute_and_map(ddlstmt)
        t2map = {'columns': [{'c1': {'type': 'integer'}},
                             {'c2': {'type': 'text'}},
                             {'c4': {'type': 'integer'}}],
                 'foreign_keys': {'t2_c4_fkey': {
                    'columns': ['c4'],
                    'references': {'schema': 'public', 'table': 't1',
                                   'columns': ['pc1']}}}}
        self.assertEqual(dbmap['schema public']['table t2'], t2map)

    def test_foreign_key_deferred(self):
        "check constraints deferred status"
        self.db.execute("CREATE TABLE t2 (pc1 INTEGER PRIMARY KEY, pc2 TEXT)")
        ddlstmt = """CREATE TABLE t1 (c1 INTEGER,
              c2 INTEGER REFERENCES t2 (pc1),
              c3 INTEGER REFERENCES t2 (pc1) DEFERRABLE,
              c4 INTEGER REFERENCES t2 (pc1) DEFERRABLE INITIALLY DEFERRED
              )"""
        dbmap = self.db.execute_and_map(ddlstmt)
        fks = dbmap['schema public']['table t1']['foreign_keys']
        self.assertTrue(not fks['t1_c2_fkey'].get('deferrable'))
        self.assertTrue(not fks['t1_c2_fkey'].get('deferred'))
        self.assertTrue(fks['t1_c3_fkey'].get('deferrable'))
        self.assertTrue(not fks['t1_c3_fkey'].get('deferred'))
        self.assertTrue(fks['t1_c4_fkey'].get('deferrable'))
        self.assertTrue(fks['t1_c4_fkey'].get('deferred'))


class ForeignKeyToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input FOREIGN KEYs"""

    def test_create_with_foreign_key(self):
        "Create a table with a foreign key constraint"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c11': {'type': 'integer'}},
                                {'c12': {'type': 'text'}}]},
                                   'table t2': {
                    'columns': [{'c21': {'type': 'integer'}},
                                {'c22': {'type': 'text'}},
                                {'c23': {'type': 'integer'}}],
                    'foreign_keys': {'t2_c23_fkey': {
                            'columns': ['c23'],
                            'references': {'columns': ['c11'],
                                           'table': 't1'}}}}})
        dbsql = self.db.process_map(inmap)
        # can't control which table will be created first
        crt1 = 0
        crt2 = 1
        if 't1' in dbsql[1]:
            crt1 = 1
            crt2 = 0
        self.assertEqual(fix_indent(dbsql[crt1]),
                             "CREATE TABLE t1 (c11 integer, c12 text)")
        self.assertEqual(fix_indent(dbsql[crt2]),
                         "CREATE TABLE t2 (c21 integer, c22 text, "
                         "c23 integer)")
        self.assertEqual(fix_indent(dbsql[2]),
                         "ALTER TABLE t2 ADD CONSTRAINT t2_c23_fkey "
                         "FOREIGN KEY (c23) REFERENCES t1 (c11)")

    def test_create_foreign_key_deferred(self):
        "Create a table with various foreign key deferring constraint"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c11': {'type': 'integer'}},
                                {'c12': {'type': 'text'}}]},
                                   'table t2': {
                    'columns': [{'c21': {'type': 'integer'}},
                                {'c22': {'type': 'text'}},
                                {'c23': {'type': 'integer'}},
                                {'c24': {'type': 'integer'}},
                                {'c25': {'type': 'integer'}},
                                ],
                    'foreign_keys': {
                        't2_c23_fkey': {
                            'columns': ['c23'],
                            'references': {'columns': ['c11'],
                                           'table': 't1'}},
                        't2_c24_fkey': {
                            'columns': ['c24'],
                            'references': {'columns': ['c11'],
                                           'table': 't1'},
                            'deferrable': True},
                        't2_c25_fkey': {
                            'columns': ['c25'],
                            'references': {'columns': ['c11'],
                                           'table': 't1'},
                            'deferrable': True,
                            'deferred': True}}}})

        dbsql = self.db.process_map(inmap)

        # can't control which table/constraint will be created first
        dbsql[0:2] = list(sorted(dbsql[0:2]))
        dbsql[2:5] = list(sorted(dbsql[2:5]))

        self.assertEqual(fix_indent(dbsql[0]),
                             "CREATE TABLE t1 (c11 integer, c12 text)")
        self.assertEqual(fix_indent(dbsql[1]),
                         "CREATE TABLE t2 (c21 integer, c22 text, "
                         "c23 integer, c24 integer, c25 integer)")
        self.assertEqual(fix_indent(dbsql[2]),
                         "ALTER TABLE t2 ADD CONSTRAINT t2_c23_fkey "
                         "FOREIGN KEY (c23) REFERENCES t1 (c11)")
        self.assertEqual(fix_indent(dbsql[3]),
                         "ALTER TABLE t2 ADD CONSTRAINT t2_c24_fkey "
                         "FOREIGN KEY (c24) REFERENCES t1 (c11) "
                         "DEFERRABLE")
        self.assertEqual(fix_indent(dbsql[4]),
                         "ALTER TABLE t2 ADD CONSTRAINT t2_c25_fkey "
                         "FOREIGN KEY (c25) REFERENCES t1 (c11) "
                         "DEFERRABLE INITIALLY DEFERRED")

    def test_add_foreign_key(self):
        "Add a two-column foreign key to an existing table"
        self.db.execute("CREATE TABLE t1 (c11 INTEGER NOT NULL, "
                        "c12 INTEGER NOT NULL, c13 TEXT, "
                        "PRIMARY KEY (c11, c12))")
        self.db.execute_commit("CREATE TABLE t2 (c21 INTEGER NOT NULL, "
                               "c22 TEXT, c23 INTEGER, c24 INTEGER, "
                               "PRIMARY KEY (c21))")
        inmap = self.std_map()
        inmap['schema public'].update({
                'table t1': {'columns': [
                        {'c11': {'type': 'integer', 'not_null': True}},
                        {'c12': {'type': 'integer', 'not_null': True}},
                        {'c13': {'type': 'text'}}],
                             'primary_key': {'t1_pkey': {
                            'columns': ['c11', 'c12'],
                            'access_method': 'btree'}}},
                'table t2': {'columns': [
                        {'c21': {'type': 'integer', 'not_null': True}},
                        {'c22': {'type': 'text'}},
                        {'c23': {'type': 'integer'}},
                        {'c24': {'type': 'integer'}}],
                             'primary_key': {'t2_pkey': {
                            'columns': ['c21'],
                            'access_method': 'btree'}},
                             'foreign_keys': {'t2_c23_fkey': {
                            'columns': ['c23', 'c24'],
                            'references': {'columns': ['c11', 'c12'],
                                           'table': 't1'}}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "ALTER TABLE t2 ADD CONSTRAINT t2_c23_fkey "
                         "FOREIGN KEY (c23, c24) REFERENCES t1 (c11, c12)")

    def test_drop_foreign_key(self):
        "Drop a foreign key on an existing table"
        self.db.execute("CREATE TABLE t1 (c11 INTEGER NOT NULL, c12 TEXT, "
                        "PRIMARY KEY (c11))")
        self.db.execute_commit("CREATE TABLE t2 (c21 INTEGER NOT NULL "
                               "PRIMARY KEY, c22 INTEGER NOT NULL "
                               "REFERENCES t1 (c11), c23 TEXT)")
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c11': {'type': 'integer', 'not_null': True}},
                                {'c12': {'type': 'text'}}],
                    'primary_key': {'t1_pkey': {'columns': ['c11']}}},
                                       'table t2': {
                    'columns': [{'c21': {'type': 'integer', 'not_null': True}},
                                {'c22': {'type': 'integer', 'not_null': True}},
                                {'c23': {'type': 'text'}}],
                    'primary_key': {'t2_pkey': {'columns': ['c21']}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["ALTER TABLE t2 DROP CONSTRAINT t2_c22_fkey"])

    def test_create_foreign_key_actions(self):
        "Create a table with foreign key ON UPDATE/ON DELETE actions"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c11': {'type': 'integer'}},
                                {'c12': {'type': 'text'}}]},
                                   'table t2': {
                    'columns': [{'c21': {'type': 'integer'}},
                                {'c22': {'type': 'text'}},
                                {'c23': {'type': 'integer'}}],
                    'foreign_keys': {'t2_c23_fkey': {
                            'columns': ['c23'],
                            'on_update': 'cascade',
                            'on_delete': 'set default',
                            'references': {'columns': ['c11'],
                                           'table': 't1'}}}}})
        dbsql = self.db.process_map(inmap)
        # won't check CREATE TABLEs explicitly here (see first test instead)
        self.assertEqual(fix_indent(dbsql[2]),
                         "ALTER TABLE t2 ADD CONSTRAINT t2_c23_fkey "
                         "FOREIGN KEY (c23) REFERENCES t1 (c11) "
                         "ON UPDATE CASCADE ON DELETE SET DEFAULT")


class UniqueConstraintToMapTestCase(PyrseasTestCase):
    """Test mapping of created UNIQUE constraints"""

    map_unique1 = {'columns': [{'c1': {'type': 'integer'}},
                               {'c2': {'type': 'text'}}],
                   'unique_constraints': {'t1_c1_key': {
                'columns': ['c1'], 'access_method': 'btree'}}}

    map_unique2 = {'columns': [{'c1': {'type': 'integer'}},
                               {'c2': {'type': 'character(5)'}},
                               {'c3': {'type': 'text'}}],
                   'unique_constraints': {'t1_c1_c2_key': {
                'columns': ['c1', 'c2'], 'access_method': 'btree'}}}

    map_unique3 = {'columns': [{'c1': {'type': 'integer'}},
                               {'c2': {'type': 'text'}}],
                   'unique_constraints': {'t1_unique_key': {
                'columns': ['c1'], 'access_method': 'btree'}}}

    def test_unique_1(self):
        "Map a table with a single-column unique constraint"
        ddlstmt = "CREATE TABLE t1 (c1 INTEGER UNIQUE, c2 TEXT)"
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], self.map_unique1)

    def test_unique_2(self):
        "Map a table with a single-column unique constraint, table level"
        ddlstmt = "CREATE TABLE t1 (c1 INTEGER, c2 TEXT, UNIQUE (c1))"
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], self.map_unique1)

    def test_unique_3(self):
        "Map a table with a two-column unique constraint"
        ddlstmt = """CREATE TABLE t1 (c1 INTEGER, c2 CHAR(5), c3 TEXT,
                                    UNIQUE (c1, c2))"""
        dbmap = self.db.execute_and_map(ddlstmt)
        if self.db.version < 90000:
            self.map_unique2.update({'unique_constraints': {'t1_c1_key': {
                'columns': ['c1', 'c2'], 'access_method': 'btree'}}})
        self.assertEqual(dbmap['schema public']['table t1'], self.map_unique2)

    def test_unique_4(self):
        "Map a table with a named unique constraint"
        ddlstmt = """CREATE TABLE t1 (c1 INTEGER, c2 TEXT,
                                  CONSTRAINT t1_unique_key UNIQUE (c1))"""
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], self.map_unique3)

    def test_unique_5(self):
        "Map a table with a named unique constraint, column level"
        ddlstmt = """CREATE TABLE t1 (
                            c1 INTEGER CONSTRAINT t1_unique_key UNIQUE,
                            c2 TEXT)"""
        dbmap = self.db.execute_and_map(ddlstmt)
        self.assertEqual(dbmap['schema public']['table t1'], self.map_unique3)


class UniqueConstraintToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input UNIQUE constraints"""

    def test_create_w_unique_constraint(self):
        "Create new table with a single column unique constraint"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'unique_constraints': {'t1_c1_key': {
                            'columns': ['c1'],
                            'access_method': 'btree'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "CREATE TABLE t1 (c1 integer, c2 text)")
        self.assertEqual(fix_indent(dbsql[1]),
                         "ALTER TABLE t1 ADD CONSTRAINT t1_c1_key "
                         "UNIQUE (c1)")

    def test_add_unique_constraint(self):
        "Add a two-column unique constraint to an existing table"
        self.db.execute_commit("CREATE TABLE t1 (c1 INTEGER NOT NULL, "
                        "c2 INTEGER NOT NULL, c3 TEXT)")
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                'columns': [
                    {'c1': {'type': 'integer', 'not_null': True}},
                    {'c2': {'type': 'integer', 'not_null': True}},
                    {'c3': {'type': 'text'}}],
                'unique_constraints': {'t1_c2_key': {
                        'columns': ['c2', 'c1'],
                        'unique': True}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "ALTER TABLE t1 ADD CONSTRAINT t1_c2_key "
                         "UNIQUE (c2, c1)")

    def test_drop_unique_constraint(self):
        "Drop a unique constraint on an existing table"
        self.db.execute_commit("CREATE TABLE t1 (c1 INTEGER NOT NULL UNIQUE, "
                               "c2 TEXT)")
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer', 'not_null': True},
                                 'c2': {'type': 'text'}}]}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["ALTER TABLE t1 DROP CONSTRAINT t1_c1_key"])


class ConstraintCommentTestCase(PyrseasTestCase):
    """Test mapping and creation of comments on constraints"""

    def test_map_pk_comment(self):
        "Map a primary key with a comment"
        self.db.execute("CREATE TABLE t1 (c1 integer CONSTRAINT cns1 "
                        "PRIMARY KEY, c2 text)")
        dbmap = self.db.execute_and_map(COMMENT_STMT)
        self.assertEqual(dbmap['schema public']['table t1']['primary_key']
                         ['cns1']['description'], 'Test constraint cns1')

    def test_map_fk_comment(self):
        "Map a foreign key with a comment"
        self.db.execute("CREATE TABLE t2 (pc1 INTEGER PRIMARY KEY, pc2 TEXT)")
        self.db.execute("CREATE TABLE t1 (c1 INTEGER, c2 INTEGER "
                        "CONSTRAINT cns1 REFERENCES t2 (pc1), c3 TEXT)")
        dbmap = self.db.execute_and_map(COMMENT_STMT)
        self.assertEqual(dbmap['schema public']['table t1']['foreign_keys']
                         ['cns1']['description'], 'Test constraint cns1')

    def test_check_constraint_with_comment(self):
        "Create a CHECK constraint with a comment"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'check_constraints': {'cns1': {
                            'columns': ['c1'], 'expression': 'c1 > 50',
                            'description': 'Test constraint cns1'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "CREATE TABLE t1 (c1 integer, c2 text)")
        self.assertEqual(fix_indent(dbsql[1]),
                         "ALTER TABLE t1 ADD CONSTRAINT cns1 CHECK (c1 > 50)")
        self.assertEqual(dbsql[2], COMMENT_STMT)

    def test_comment_on_primary_key(self):
        "Create a comment for an existing primary key"
        self.db.execute_commit("CREATE TABLE t1 (c1 text CONSTRAINT cns1 "
                               "PRIMARY KEY, c2 integer)")
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'text', 'not_null': True}},
                                {'c2': {'type': 'integer'}}],
                    'primary_key': {'cns1': {
                            'columns': ['c2'], 'access_method': 'btree',
                            'description': 'Test constraint cns1'}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [COMMENT_STMT])

    def test_drop_foreign_key_comment(self):
        "Drop the comment on an existing foreign key"
        self.db.execute("CREATE TABLE t2 (c21 integer PRIMARY KEY, c22 text)")
        self.db.execute("CREATE TABLE t1 (c11 integer, c12 text, "
                        "c13 integer CONSTRAINT cns1 REFERENCES t2 (c21))")
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'table t2': {
                    'columns': [{'c21': {'type': 'integer', 'not_null': True}},
                                {'c22': {'type': 'text'}}],
                    'primary_key': {'t2_pkey': {
                            'columns': ['c21'], 'access_method': 'btree'}}},
                                   'table t1': {
                    'columns': [{'c11': {'type': 'integer'}},
                                {'c12': {'type': 'text'}},
                                {'c13': {'type': 'integer'}}],
                    'foreign_keys': {'cns1': {
                            'columns': ['c13'],
                            'references': {'columns': ['c21'],
                                           'table': 't2'}}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["COMMENT ON CONSTRAINT cns1 ON t1 IS NULL"])

    def test_change_unique_constraint_comment(self):
        "Change existing comment on a unique constraint"
        self.db.execute("CREATE TABLE t1 (c1 integer CONSTRAINT cns1 UNIQUE, "
                        "c2 text)")
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
                    'columns': [{'c1': {'type': 'integer'}},
                                {'c2': {'type': 'text'}}],
                    'unique_constraints': {'cns1': {
                            'columns': ['c1'], 'access_method': 'btree',
                            'description': "Changed constraint cns1"}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, ["COMMENT ON CONSTRAINT cns1 ON t1 IS "
                                 "'Changed constraint cns1'"])

    def test_constraint_comment_schema(self):
        "Add comment on a constraint for a table in another schema"
        self.db.execute("DROP SCHEMA IF EXISTS s1 CASCADE")
        self.db.execute("CREATE SCHEMA s1")
        self.db.execute_commit("CREATE TABLE s1.t1 (c1 integer "
                        "CONSTRAINT cns1 CHECK (c1 > 50), c2 text)")
        inmap = self.std_map()
        inmap.update({'schema s1': {'table t1': {
                        'columns': [{'c1': {'type': 'integer'}},
                                    {'c2': {'type': 'text'}}],
                        'check_constraints': {'cns1': {
                                'columns': ['c1'], 'expression': 'c1 > 50',
                                'description': 'Test constraint cns1'}}}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql[0], "COMMENT ON CONSTRAINT cns1 ON s1.t1 IS "
                         "'Test constraint cns1'")
        self.db.execute_commit("DROP SCHEMA s1 CASCADE")


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(
        CheckConstraintToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            CheckConstraintToSqlTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            PrimaryKeyToMapTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            PrimaryKeyToSqlTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            ForeignKeyToMapTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            ForeignKeyToSqlTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            UniqueConstraintToMapTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            UniqueConstraintToSqlTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            ConstraintCommentTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
