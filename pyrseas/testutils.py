# -*- coding: utf-8 -*-
"""Utility functions and classes for testing Pyrseas"""

import sys
import os
import getpass
import tempfile
import glob
import subprocess
from unittest import TestCase

import yaml

from pyrseas.config import Config
from pyrseas.database import Database
from pyrseas.augmentdb import AugmentDatabase
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
        "Drop schemas and other objects"
        STD_DROP = 'DROP %s IF EXISTS "%s" CASCADE'
        # Schemas
        curs = pgexecute(
            self.conn,
            """SELECT nspname FROM pg_namespace
               WHERE nspname != 'information_schema'
                     AND substring(nspname for 3) != 'pg_'
               ORDER BY nspname""")
        objs = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for obj in objs:
                self.execute(STD_DROP % ('SCHEMA', obj["nspname"]))
        self.conn.commit()

        # Extensions
        curs = pgexecute(
            self.conn,
            """SELECT extname FROM pg_extension
                      JOIN pg_namespace n ON (extnamespace = n.oid)
               WHERE nspname != 'information_schema'
               AND extname != 'plpgsql'""")
        exts = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for ext in exts:
            self.execute(STD_DROP % ('EXTENSION', ext["extname"]))
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
                ump["username"], ump["srvname"]))
        self.conn.commit()

        # Servers
        curs = pgexecute(self.conn, "SELECT srvname FROM pg_foreign_server")
        servs = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for srv in servs:
            self.execute(STD_DROP % ('SERVER', srv["srvname"]))
        self.conn.commit()

        # Foreign data wrappers
        curs = pgexecute(self.conn,
                         "SELECT fdwname FROM pg_foreign_data_wrapper")
        fdws = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for fdw in fdws:
            self.execute(STD_DROP % ('FOREIGN DATA WRAPPER', fdw["fdwname"]))
        self.conn.commit()

        # Create default schema
        self.execute("CREATE SCHEMA sd")
        self.execute("set search_path='sd', 'pg_catalog'")
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
        if 'database' not in self.cfg:
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

    @staticmethod
    def sort_privileges(data):
        try:
            sorted_privlist = []
            for sortedItem in sorted([list(i.keys())[0]
                                      for i in data['privileges']]):
                sorted_privlist.append(
                    [item for item in data['privileges']
                     if list(item.keys())[0] == sortedItem][0])
            data['privileges'] = sorted_privlist
        finally:
            return data


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
        self.config_options(schemas=schemas, revert=revert),
        self.cfg.merge(config)
        return self.database().diff_map(inmap, quote_reserved=quote_reserved)

    def std_map(self, plpgsql_installed=False):
        "Return a standard schema map for the default database"
        base = {'schema sd': {
                'owner': self.db.user,
                'privileges': []}}
        base.update({'extension plpgsql': {
            'schema': 'pg_catalog', 'owner': PG_OWNER,
            'description': "PL/pgSQL procedural language"}})
        return base


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

    def add_public_schema(self, db):
        db.execute("CREATE SCHEMA IF NOT EXISTS public")
        db.execute("ALTER SCHEMA public OWNER TO postgres")
        db.execute("COMMENT ON SCHEMA public IS "
                         "'standard public schema'")
        db.execute("DROP SCHEMA IF EXISTS sd")
        db.conn.commit()

    def remove_public_schema(self, db):
        db.execute("DROP SCHEMA IF EXISTS public CASCADE")
        db.conn.commit()

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
