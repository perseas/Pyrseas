from pyrseas.database import Database
from pyrseas.config import Config
from collections import namedtuple


def test_table():
    cfg = Config()
    cfg['database'] = {'dbname': '', 'host': '', 'username': '', 'password': '', 'port': 0}
    cfg['options'] = namedtuple('Options', ['schemas', 'revert'])(*[[], False])
    if 'datacopy' in cfg:
        del cfg['datacopy']
    db = Database(cfg)

    test_cases = [
        {
            "name": "simple type change",
            "a": {'schema public': 
                    {'table foo': 
                        {'columns': [
                            {'month': {'not_null': False, 'type': 'integer', 'default': '0'}}, 
                            {'year': {'default': "''::character varying", 'not_null': True, 'type': 'character varying'}}
                            ]
                        }
                    }
                },
            "b": {'schema public': 
                    {'table foo': 
                        {'columns': [
                            {'month': {'default': "''::character varying", 'not_null': True, 'type': 'character varying'}},
                            {'year': {'default': "''::character varying", 'not_null': True, 'type': 'character varying'}}
                            ]
                        }
                    }
                },
            "expected": ["ALTER TABLE foo\n    ALTER COLUMN month SET NOT NULL, ALTER COLUMN month DROP DEFAULT, ALTER COLUMN month TYPE character varying USING month::character varying, ALTER COLUMN month SET DEFAULT ''::character varying"]
        },
        {
            "name": "Reorder columns with type change",
            "a": {'schema public': 
                    {'table foo': 
                        {'columns': [
                            {'year': {'default': "''::character varying", 'not_null': True, 'type': 'character varying'}},
                            {'month': {'not_null': False, 'type': 'integer', 'default': '0'}}, 
                            ]
                        }
                    }
                },
            "b": {'schema public': 
                    {'table foo': 
                        {'columns': [
                            {'month': {'default': "''::character varying", 'not_null': True, 'type': 'character varying'}},
                            {'year': {'default': "''::character varying", 'not_null': True, 'type': 'character varying'}},
                            ]
                        }
                    }
                },
            "expected": ["ALTER TABLE foo\n    ALTER COLUMN month SET NOT NULL, ALTER COLUMN month DROP DEFAULT, ALTER COLUMN month TYPE character varying USING month::character varying, ALTER COLUMN month SET DEFAULT ''::character varying"]
        },
        {
            # The drop index should happen before while the creation should happen after
            "name": "Reorder columns with changing indexes",
            "a": {'schema public':
                    {'table foo':
                        {'columns': [
                            {'year': {'default': "''::character varying", 'not_null': True, 'type': 'character varying'}},
                            {'month': {'default': "''::character varying", 'not_null': True, 'type': 'character varying'}},
                            ],
                        'indexes' : {
                            'indx_reference_mips_adjustments_month3': {
                                'access_method': 'gin',
                                'keys':[{"month": {'opclass': 'gin_trgm_ops'}}],
                                },
                            },
                        },
                    },
                },
            "b": {'schema public':
                    {'table foo':
                        {'columns': [
                            {'month': {'not_null': False, 'type': 'integer', 'default': '0'}},
                            {'year': {'default': "''::character varying", 'not_null': True, 'type': 'character varying'}},
                            ],
                        'indexes' : {
                            'indx_reference_mips_adjustments_month': { 'keys':["month"] },
                            },
                        },
                    }
                },
            "expected": ["DROP INDEX indx_reference_mips_adjustments_month3", "ALTER TABLE foo\n    ALTER COLUMN month DROP NOT NULL, ALTER COLUMN month DROP DEFAULT, ALTER COLUMN month TYPE integer USING month::integer, ALTER COLUMN month SET DEFAULT 0", "CREATE INDEX indx_reference_mips_adjustments_month ON foo (month)"]
        },
    ]

    for test_case in test_cases:
        assert test_case["expected"] == db.diff_two_map(test_case["a"], test_case["b"], quote_reserved=False), test_case["name"]
