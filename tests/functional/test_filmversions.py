# -*- coding: utf-8 -*-
"""Test dbtoyaml and yamltodb using film versions schema

See https://pyrseas.wordpress.com/2011/02/07/
version-control-part-2-sql-databases/
"""
import os
from pyrseas.testutils import DbMigrateTestCase
from pyrseas.yamlutil import yamldump


class FilmTestCase(DbMigrateTestCase):

    def setUp(self):
        self.remove_public_schema(self.srcdb)

    @classmethod
    def tearDownClass(cls):
        cls.remove_tempfiles('film-0.')
        cls.remove_tempfiles('usercfg.yaml')
        cls.remove_tempfiles('config.yaml')
        cls.remove_tempfiles('metadata')

    def test_film_version_01(self):
        "Create schema version 0.1"
        self.execute_script(__file__, 'film-schema-0.1.sql')

        # Run pg_dump against source database
        srcdump = self.tempfile_path('film-0.1-src.dump')
        self.run_pg_dump(srcdump, True)

        # Create source YAML file
        srcyaml = self.tempfile_path('film-0.1-src.yaml')
        self.create_yaml(srcyaml, True)

        # Run pg_dump/dbtoyaml against empty target database
        self.run_pg_dump(self.tempfile_path('film-0.0.dump'))
        self.create_yaml(self.tempfile_path('film-0.0.yaml'))

        # Migrate the target database
        self.migrate_target(srcyaml, self.tempfile_path('film-0.1.sql'))

        # Run pg_dump against target database
        targdump = self.tempfile_path('film-0.1.dump')
        self.run_pg_dump(targdump)

        # Create target YAML file
        targyaml = self.tempfile_path('film-0.1.yaml')
        self.create_yaml(targyaml)

        # diff film-0.1-src.dump against film-0.1.dump
        assert self.lines(srcdump) == self.lines(targdump)
        # diff film-0.1-src.yaml against film-0.1.yaml
        assert self.lines(srcyaml) == self.lines(targyaml)

    def test_film_version_02(self):
        "Update schema to version 0.2"
        self.execute_script(__file__, 'film-schema-0.2.sql')

        # Run pg_dump against source database
        srcdump = self.tempfile_path('film-0.2-src.dump')
        self.run_pg_dump(srcdump, True)

        # Create source YAML file
        srcyaml = self.tempfile_path('film-0.2-src.yaml')
        self.create_yaml(srcyaml, True)

        # Migrate the target database
        self.migrate_target(srcyaml, self.tempfile_path('film-0.2.sql'))

        # Run pg_dump against target database
        targdump = self.tempfile_path('film-0.2.dump')
        self.run_pg_dump(targdump)

        # Create target YAML file
        targyaml = self.tempfile_path('film-0.2.yaml')
        self.create_yaml(targyaml)

        # diff film-0.2-src.dump against film-0.2.dump
        assert self.lines(srcdump) == self.lines(targdump)
        # diff film-0.2-src.yaml against film-0.2.yaml
        assert self.lines(srcyaml) == self.lines(targyaml)

    def test_film_version_03(self):
        "Update schema to version 0.3"
        self.execute_script(__file__, 'film-schema-0.3a.sql')
        self.execute_script(__file__, 'film-schema-0.3b.sql')

        # Run pg_dump against source database
        srcdump = self.tempfile_path('film-0.3-src.dump')
        self.run_pg_dump(srcdump, True, True)

        # Create source YAML file
        usercfg = self.tempfile_path("usercfg.yaml")
        with open(usercfg, 'w') as f:
            f.write(yamldump({'repository': {'path': self.tempfile_path('')}}))
        os.environ["PYRSEAS_USER_CONFIG"] = usercfg
        with open(self.tempfile_path("config.yaml"), 'w') as f:
            f.write(yamldump({'datacopy': {'schema sd': ['genre']}}))
        srcyaml = self.tempfile_path('film-0.3-src.yaml')
        self.create_yaml(srcyaml, True)

        # Migrate the target database
        self.migrate_target(srcyaml, self.tempfile_path('film-0.3.sql'))

        # Run pg_dump against target database
        targdump = self.tempfile_path('film-0.3.dump')
        self.run_pg_dump(targdump, False, True)

        # Create target YAML file
        targyaml = self.tempfile_path('film-0.3.yaml')
        self.create_yaml(targyaml)

        # diff film-0.3-src.dump against film-0.3.dump
        assert self.lines(srcdump) == self.lines(targdump)
        # diff film-0.3-src.yaml against film-0.3.yaml
        assert self.lines(srcyaml) == self.lines(targyaml)

    def test_film_version_04(self):
        "Revert to schema version 0.2"
        srcyaml = self.tempfile_path('film-0.2.yaml')
        self.migrate_target(srcyaml, self.tempfile_path('film-0.3-undo.sql'))

        # Run pg_dump against target database
        targdump = self.tempfile_path('film-0.3-undo.dump')
        self.run_pg_dump(targdump)

        # Create target YAML file
        targyaml = self.tempfile_path('film-0.3-undo.yaml')
        self.create_yaml(targyaml)

        # diff film-0.2.dump against film-0.3-undo.dump
        srcdump = self.tempfile_path('film-0.2.dump')
        assert self.lines(srcdump) == self.lines(targdump)
        # diff film-0.2.yaml against film-0.3-undo.yaml
        assert self.lines(srcyaml) == self.lines(targyaml)

    def test_film_version_05(self):
        "Revert to schema version 0.1"
        srcyaml = self.tempfile_path('film-0.1.yaml')
        self.migrate_target(srcyaml, self.tempfile_path('film-0.2-undo.sql'))

        # Run pg_dump against target database
        targdump = self.tempfile_path('film-0.2-undo.dump')
        self.run_pg_dump(targdump)

        # Create target YAML file
        targyaml = self.tempfile_path('film-0.2-undo.yaml')
        self.create_yaml(targyaml)

        # diff film-0.1.dump against film-0.2-undo.dump
        srcdump = self.tempfile_path('film-0.1.dump')
        assert self.lines(srcdump) == self.lines(targdump)
        # diff film-0.1.yaml against film-0.2-undo.yaml
        assert self.lines(srcyaml) == self.lines(targyaml)

    def test_film_version_06(self):
        "Revert to empty schema"
        srcyaml = self.tempfile_path('film-0.0.yaml')
        self.migrate_target(srcyaml, self.tempfile_path('film-0.1-undo.sql'))

        # Run pg_dump against target database
        targdump = self.tempfile_path('film-0.1-undo.dump')
        self.run_pg_dump(targdump)

        # Create target YAML file
        targyaml = self.tempfile_path('film-0.1-undo.yaml')
        self.create_yaml(targyaml)

        # diff film-0.0.dump against film-0.1-undo.dump
        srcdump = self.tempfile_path('film-0.0.dump')
        assert self.lines(srcdump) == self.lines(targdump)
        # diff film-0.0.yaml against film-0.1-undo.yaml
        assert self.lines(srcyaml) == self.lines(targyaml)
