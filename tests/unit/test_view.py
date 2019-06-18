from pyrseas.database import Database
from pyrseas.config import Config
from collections import namedtuple


def test_view():
    cfg = Config()
    cfg['database'] = {'dbname': '', 'host': '', 'username': '', 'password': '', 'port': 0}
    cfg['options'] = namedtuple('Options', ['schemas', 'revert'])(*[[], False])
    if 'datacopy' in cfg:
        del cfg['datacopy']
    db = Database(cfg)

    test_cases = [
        {
            "name": "Nothing to be done",
            "a": {'schema public':
                    {'view foo':
                        {
                            'definition': 'select * from t1',
                            'description': 'comment on foo',
                            'owner': 'postgres',
                        },
                    },
                },
            "b": {'schema public':
                    {'view foo':
                        {
                            'definition': 'select * from t1',
                            'description': 'comment on foo',
                            'owner': 'postgres',
                        },
                    },
                },
            "expected": []
        },
        {
            "name": "Change comment",
            "a": {'schema public':
                    {'view foo':
                        {
                            'definition': 'select * from t1',
                            'description': 'comment on foo',
                            'owner': 'oldowner',
                        },
                    },
                },
            "b": {'schema public':
                    {'view foo':
                        {
                            'definition': 'select * from t1',
                            'description': 'new comment on foo',
                            'owner': 'newowner',
                        },
                    },
                },
            "expected": [
		"ALTER VIEW foo OWNER TO newowner",
                "COMMENT ON VIEW foo IS 'new comment on foo'",
            ],
        },
    ]

    for test_case in test_cases:
        assert test_case["expected"] == db.diff_two_map(test_case["a"], test_case["b"], quote_reserved=False), test_case["name"]
