# -*- coding: utf-8 -*-
"""Utility functions and classes for testing Pyrseas"""

import sys
import os
import getpass
import tempfile
from unittest import TestCase

import yaml

from pyrseas.config import Config
from pyrseas.database import Database
from pyrseas.augmentdb import AugmentDatabase
from pyrseas.lib.dbconn import DbConnection
from pyrseas.lib.dbutils import pgexecute, PostgresDb


def fix_indent(stmt):
    "Fix specifications which are in a new line with indentation"
    return stmt.replace('   ', ' ').replace('  ', ' ').replace('\n ', ' '). \
        replace('( ', '(')


def remove_temp_files(tmpdir, prefix=''):
    "Remove files in a temporary directory"
    for tfile in glob.glob(os.path.join(tmpdir, prefix + '*')):
        if os.path.isdir(tfile):
            for entry in os.listdir(tfile):
                entry = os.path.join(tmpdir, tfile, entry)
                if os.path.isdir(entry):
                    for file in os.listdir(entry):
                        os.remove(os.path.join(entry, file))
                    os.rmdir(entry)
                else:
                    os.remove(entry)
            os.rmdir(tfile)
        else:
            os.remove(tfile)


TEST_DBNAME = os.environ.get("PYRSEAS_TEST_DB", 'pyrseas_testdb')
TEST_USER = os.environ.get("PYRSEAS_TEST_USER", getpass.getuser())
TEST_HOST = os.environ.get("PYRSEAS_TEST_HOST", None)
TEST_PORT = int(os.environ.get("PYRSEAS_TEST_PORT", 5432))
PG_OWNER = 'postgres'
TEST_DIR = os.path.join(tempfile.gettempdir(),
                        os.environ.get("PYRSEAS_TEST_DIR", 'pyrseas_test'))
TRAVIS = (os.environ.get("TRAVIS", 'false') == 'true')


class PgTestDb(PostgresDb):
    """A PostgreSQL database connection for testing."""

    def clear(self):
        "Drop tables and other objects"
        STD_DROP = 'DROP %s IF EXISTS "%s" CASCADE'
        # Schemas other than 'public'
        curs = pgexecute(
            self.conn,
            """SELECT nspname FROM pg_namespace
               WHERE nspname NOT IN ('public', 'information_schema')
                     AND substring(nspname for 3) != 'pg_'
               ORDER BY nspname""")
        objs = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for obj in objs:
                self.execute(STD_DROP % ('SCHEMA', obj[0]))
        self.conn.commit()

        # Extensions
        if self.version >= 90100:
            curs = pgexecute(
                self.conn,
                """SELECT extname FROM pg_extension
                          JOIN pg_namespace n ON (extnamespace = n.oid)
                   WHERE nspname NOT IN ('information_schema')
                     AND extname != 'plpgsql'""")
            exts = curs.fetchall()
            curs.close()
            self.conn.rollback()
            for ext in exts:
                self.execute(STD_DROP % ('EXTENSION', ext[0]))
            self.conn.commit()

        # Tables, sequences and views
        curs = pgexecute(
            self.conn,
            """SELECT relname, relkind FROM pg_class
                      JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
               WHERE relkind in ('r', 'S', 'v', 'f', 'm')
                     AND nspname NOT IN ('pg_catalog', 'information_schema')
               ORDER BY relkind DESC""")
        objs = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for obj in objs:
            if obj['relkind'] == 'r':
                objtype = 'TABLE'
            elif obj['relkind'] == 'S':
                objtype = 'SEQUENCE'
            elif obj['relkind'] == 'v':
                objtype = 'VIEW'
            elif obj['relkind'] == 'f':
                objtype = 'FOREIGN TABLE'
            elif obj['relkind'] == 'm':
                objtype = 'MATERIALIZED VIEW'
            self.execute(STD_DROP % (objtype, obj[0]))
        self.conn.commit()

        # Types (base, composite and enums) and domains
        #
        # TYPEs have to be done before FUNCTIONs because base types depend
        # on functions, and we're using CASCADE. Also, exclude base array
        # types because they depend on the scalar types.
        curs = pgexecute(
            self.conn,
            """SELECT typname, typtype FROM pg_type t
                      JOIN pg_namespace n ON (typnamespace = n.oid)
               WHERE typtype IN ('b', 'c', 'd', 'e')
                 AND NOT (typtype = 'b' AND typarray = 0)
                 AND nspname NOT IN ('pg_catalog', 'pg_toast',
                     'information_schema')""")
        types = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for typ in types:
            self.execute(STD_DROP % ('DOMAIN' if typ['typtype'] == 'd'
                                     else 'TYPE', typ[0]))
        self.conn.commit()

        # Functions
        curs = pgexecute(
            self.conn,
            """SELECT proisagg, p.oid::regprocedure AS proc
               FROM pg_proc p JOIN pg_namespace n ON (pronamespace = n.oid)
               WHERE nspname NOT IN ('pg_catalog', 'information_schema')
               ORDER BY 1, 2""")
        funcs = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for func in funcs:
            self.execute('DROP %s IF EXISTS %s CASCADE' % (
                'AGGREGATE' if func['proisagg'] else 'FUNCTION', func['proc']))
        self.conn.commit()

        # Languages
        if self.version < 90000:
            if self.is_plpgsql_installed():
                self.execute_commit("DROP LANGUAGE plpgsql")

        # Operators
        curs = pgexecute(
            self.conn,
            """SELECT o.oid::regoperator
               FROM pg_operator o JOIN pg_namespace n ON (oprnamespace = n.oid)
               WHERE nspname NOT IN ('pg_catalog', 'information_schema')""")
        opers = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for oper in opers:
            self.execute("DROP OPERATOR IF EXISTS %s CASCADE" % (oper[0]))
        self.conn.commit()

        # Operator families
        curs = pgexecute(
            self.conn,
            """SELECT opfname, amname
               FROM pg_opfamily o JOIN pg_am a ON (opfmethod = a.oid)
                    JOIN pg_namespace n ON (opfnamespace = n.oid)
               WHERE nspname NOT IN ('pg_catalog', 'information_schema')""")
        opfams = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for opfam in opfams:
            self.execute(
                'DROP OPERATOR FAMILY IF EXISTS "%s" USING "%s" CASCADE' % (
                    opfam[0], opfam[1]))
        self.conn.commit()

        # Operator classes
        curs = pgexecute(
            self.conn,
            """SELECT opcname, amname
               FROM pg_opclass o JOIN pg_am a ON (opcmethod = a.oid)
                    JOIN pg_namespace n ON (opcnamespace = n.oid)
               WHERE nspname NOT IN ('pg_catalog', 'information_schema')""")
        opcls = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for opcl in opcls:
            self.execute(
                'DROP OPERATOR CLASS IF EXISTS "%s" USING "%s" CASCADE' % (
                    opcl[0], opcl[1]))
        self.conn.commit()

        # Conversions
        curs = pgexecute(
            self.conn,
            """SELECT conname FROM pg_conversion c
                      JOIN pg_namespace n ON (connamespace = n.oid)
               WHERE nspname NOT IN ('pg_catalog', 'information_schema')""")
        convs = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for cnv in convs:
            self.execute(STD_DROP % ('CONVERSION', cnv[0]))
        self.conn.commit()

        # Collations
        if self.version >= 90100:
            curs = pgexecute(
                self.conn,
                """SELECT collname FROM pg_collation c
                          JOIN pg_namespace n ON (collnamespace = n.oid)
                   WHERE nspname NOT IN (
                         'pg_catalog', 'information_schema')""")
            colls = curs.fetchall()
            curs.close()
            self.conn.rollback()
            for coll in colls:
                self.execute(STD_DROP % ('COLLATION', coll[0]))
            self.conn.commit()

        # User mappings
        curs = pgexecute(
            self.conn,
            """SELECT CASE umuser WHEN 0 THEN 'PUBLIC' ELSE
                  pg_get_userbyid(umuser) END AS username, s.srvname
               FROM pg_user_mappings u
                  JOIN pg_foreign_server s ON (srvid = s.oid)""")
        umaps = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for ump in umaps:
            self.execute('DROP USER MAPPING IF EXISTS FOR "%s" SERVER "%s"' % (
                ump[0], ump[1]))
        self.conn.commit()

        # Servers
        curs = pgexecute(self.conn, "SELECT srvname FROM pg_foreign_server")
        servs = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for srv in servs:
            self.execute(STD_DROP % ('SERVER', srv[0]))
        self.conn.commit()

        # Foreign data wrappers
        curs = pgexecute(self.conn,
                         "SELECT fdwname FROM pg_foreign_data_wrapper")
        fdws = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for fdw in fdws:
            self.execute(STD_DROP % ('FOREIGN DATA WRAPPER', fdw[0]))
        self.conn.commit()

    def is_plpgsql_installed(self):
        "Is PL/pgSQL installed?"
        curs = pgexecute(self.conn,
                         "SELECT 1 FROM pg_language WHERE lanname = 'plpgsql'")
        row = curs.fetchone()
        curs.close()
        return row and True

    def is_superuser(self):
        "Is current user a superuser?"
        curs = pgexecute(self.conn, "SELECT 1 FROM pg_roles WHERE rolsuper "
                         "AND rolname = CURRENT_USER ")
        row = curs.fetchone()
        curs.close()
        return row and True


def _connect_clear(dbname):
    db = PgTestDb(dbname, TEST_USER, TEST_HOST, TEST_PORT)
    db.connect()
    db.clear()
    return db


class PyrseasTestCase(TestCase):
    """Base class for most test cases"""

    def setUp(self):
        self.db = _connect_clear(TEST_DBNAME)
        self.cfg = Config(sys_only=True)
        if not 'database' in self.cfg:
            self.cfg.update(database={})
        dbc = self.cfg['database']
        dbc['dbname'] = self.db.name
        dbc['username'] = self.db.user
        dbc['password'] = None
        dbc['host'] = self.db.host
        dbc['port'] = self.db.port

    def tearDown(self):
        self.db.close()

    def database(self):
        """The Pyrseas Database instance"""
        return Database(self.cfg)

    def config_options(self, **kwargs):
        class Opts():
            def __init__(self, **kwargs):
                [setattr(self, opt, val) for opt, val in list(kwargs.items())]
        self.cfg['options'] = Opts(**kwargs)


class DatabaseToMapTestCase(PyrseasTestCase):
    """Base class for "database to map" test cases"""

    superuser = False

    def to_map(self, stmts, config={}, schemas=[], tables=[], no_owner=True,
               no_privs=True, superuser=False, multiple_files=False):
        """Execute statements and return a database map.

        :param stmts: list of SQL statements to execute
        :param config: dictionary of configuration information
        :param schemas: list of schemas to map
        :param tables: list of tables to map
        :param no_owner: exclude object owner information
        :param no_privs: exclude privilege information
        :param superuser: must be superuser to run
        :param multiple_files: emulate --multiple_files option
        :return: possibly trimmed map of database
        """
        if (self.superuser or superuser) and not self.db.is_superuser():
            self.skipTest("Must be a superuser to run this test")
        for stmt in stmts:
            self.db.execute(stmt)
        self.db.conn.commit()
        if multiple_files:
            self.cfg.merge({'files': {'metadata_path': os.path.join(
                            TEST_DIR, self.cfg['repository']['metadata'])}})
        if 'datacopy' in config:
            self.cfg.merge({'files': {'data_path': os.path.join(
                            TEST_DIR, self.cfg['repository']['data'])}})
        self.config_options(schemas=schemas, tables=tables, no_owner=no_owner,
                            no_privs=no_privs, multiple_files=multiple_files)
        self.cfg.merge(config)
        return self.database().to_map()

    def yaml_load(self, filename, subdir=None):
        """Read a file in the metadata_path and process it with YAML load

        :param filename: name of the file
        :param subdir: name of a subdirectory where the file is located
        :return: YAML dictionary
        """
        with open(os.path.join(self.cfg['files']['metadata_path'],
                               subdir or '', filename), 'r') as f:
            inmap = f.read()
        return yaml.safe_load(inmap)

    def remove_tempfiles(self):
        remove_temp_files(TEST_DIR)


class InputMapToSqlTestCase(PyrseasTestCase):
    """Base class for "input map to SQL" test cases"""

    superuser = False

    def to_sql(self, inmap, stmts=None, config={}, superuser=False, schemas=[],
               revert=False, quote_reserved=False):
        """Execute statements and compare database to input map.

        :param inmap: dictionary defining target database
        :param stmts: list of SQL database setup statements
        :param config: dictionary of configuration information
        :param superuser: indicates test requires superuser privilege
        :param schemas: list of schemas to diff
        :param revert: generate statements to back out changes
        :param quote_reserved: fetch reserved words
        :return: list of SQL statements
        """
        if (self.superuser or superuser) and not self.db.is_superuser():
            self.skipTest("Must be a superuser to run this test")
        if stmts:
            for stmt in stmts:
                self.db.execute(stmt)
            self.db.conn.commit()

        if 'datacopy' in config:
            self.cfg.merge({'files': {'data_path': os.path.join(
                            TEST_DIR, self.cfg['repository']['data'])}})
        self.config_options(schemas=schemas, revert=revert,
                            quote_reserved=quote_reserved)
        self.cfg.merge(config)
        return self.database().diff_map(inmap)

    def std_map(self, plpgsql_installed=False):
        "Return a standard schema map for the default database"
        base = {'schema public': {
                'owner': PG_OWNER,
                'privileges': [{PG_OWNER: ['all']}, {'PUBLIC': ['all']}],
                'description': 'standard public schema'}}
        if (self.db._version >= 90000 or plpgsql_installed) \
                and self.db._version < 90100:
            base.update({'language plpgsql': {'trusted': True}})
        if self.db._version >= 90100:
            base.update({'extension plpgsql': {
                        'schema': 'pg_catalog',
                        'description': "PL/pgSQL procedural language"}})
        return base


import glob
import subprocess

TEST_DBNAME_SRC = os.environ.get("PYRSEAS_TEST_DB_SRC", 'pyrseas_testdb_src')


class DbMigrateTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.srcdb = _connect_clear(TEST_DBNAME_SRC)
        cls.db = _connect_clear(TEST_DBNAME)
        progdir = os.path.abspath(os.path.dirname(__file__))
        cls.dbtoyaml = os.path.join(progdir, 'dbtoyaml.py')
        cls.yamltodb = os.path.join(progdir, 'yamltodb.py')
        cls.tmpdir = TEST_DIR
        if not os.path.exists(cls.tmpdir):
            os.mkdir(cls.tmpdir)

    @classmethod
    def remove_tempfiles(cls, prefix):
        remove_temp_files(cls.tmpdir, prefix)

    def execute_script(self, path, scriptname):
        scriptfile = os.path.join(os.path.abspath(os.path.dirname(path)),
                                  scriptname)
        lines = []
        with open(scriptfile, 'r') as fd:
            lines = [line.strip() for line in fd if line != '\n' and
                     not line.startswith('--')]
        self.srcdb.execute_commit(' '.join(lines))

    def tempfile_path(self, filename):
        return os.path.join(self.tmpdir, filename)

    def _db_params(self):
        args = []
        if self.db.host is not None:
            args.append("--host=%s" % self.db.host)
        if self.db.port is not None:
            args.append("--port=%d " % self.db.port)
        if self.db.user is not None:
            args.append("--username=%s" % self.db.user)
        return args

    def lines(self, the_file):
        with open(the_file) as f:
            lines = f.readlines()
        return lines

    def run_pg_dump(self, dumpfile, srcdb=False, incldata=False):
        """Run pg_dump using special scripts or directly (on Travis-CI)

        :param dumpfile: path to the pg_dump output file
        :param srcdb: run against source database
        """
        if TRAVIS:
            pg_dumpver = 'pg_dump'
        else:
            v = self.srcdb._version
            pg_dumpver = "pg_dump%d%d" % (v // 10000,
                                          (v - v // 10000 * 10000) // 100)
            if sys.platform == 'win32':
                pg_dumpver += '.bat'
        dbname = self.srcdb.name if srcdb else self.db.name
        args = [pg_dumpver]
        args.extend(self._db_params())
        if not incldata:
            args.extend(['-s'])
        args.extend(['-f', dumpfile, dbname])
        subprocess.check_call(args)

    def invoke(self, args):
        args.insert(0, sys.executable)
        path = [os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))]
        path.append(os.path.abspath(os.path.join(os.path.dirname(
                    yaml.__file__), '..')))
        env = os.environ.copy()
        env.update({'PYTHONPATH': os.pathsep.join(path)})
        subprocess.check_call(args, env=env)

    def create_yaml(self, yamlfile='', srcdb=False):
        dbname = self.srcdb.name if srcdb else self.db.name
        args = [self.dbtoyaml]
        args.extend(self._db_params())
        if yamlfile:
            args.extend(['-o', yamlfile, dbname])
        else:
            args.extend(['-r', TEST_DIR, '-m', dbname])
        self.invoke(args)

    def migrate_target(self, yamlfile, outfile):
        args = [self.yamltodb]
        args.extend(self._db_params())
        if yamlfile:
            args.extend(['-u', '-o', outfile, self.db.name, yamlfile])
        else:
            args.extend(['-u', '-o', outfile, '-r', TEST_DIR, '-m',
                         self.db.name])
        self.invoke(args)


class AugmentToMapTestCase(PyrseasTestCase):

    def to_map(self, stmts, augmap):
        """Apply an augment map and return a map of the updated database.

        :param stmts: list of SQL statements to execute
        :param augmap: dictionary describing the augmentations
        :return: dictionary of the updated database
        """
        for stmt in stmts:
            self.db.execute(stmt)
        self.db.conn.commit()
        self.config_options(schemas=[], tables=[], no_owner=True,
                            no_privs=True, multiple_files=False)
        db = AugmentDatabase(self.cfg)
        return db.apply(augmap)


class RelationTestCase(object):

    @classmethod
    def setup_class(cls):
        cls.pgdb = PostgresDb(TEST_DBNAME, TEST_USER, TEST_HOST, TEST_PORT)
        cls.pgdb.connect()
        cls.db = DbConnection(TEST_DBNAME, TEST_USER, None, TEST_HOST,
                              TEST_PORT)

    @classmethod
    def teardown_class(cls):
        cls.pgdb.close()
