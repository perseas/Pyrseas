# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.eventtrig
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: EventTrigger derived from
    DbObject, and EventTriggerDict derived from DbObjectDict.
"""
from . import DbObjectDict, DbObject
from . import quote_id, commentable
from .function import split_schema_func, join_schema_func

EXEC_PROC = 'EXECUTE PROCEDURE '

ENABLE_MODES = {'O': True, 'D': False, 'R': 'replica', 'A': 'always'}


class EventTrigger(DbObject):
    """An event trigger"""

    keylist = ['name']
    catalog = 'pg_event_trigger'

    def __init__(self, name, description, owner, event, procedure,
                 enabled=False, tags=None,
                 oid=None):
        """Initialize the event trigger

        :param name: trigger name (from evtname)
        :param description: comment text (from obj_description())
        :param owner: owner name (from rolname via evtowner)
        :param event: event that causes firing (from evtevent)
        :param procedure: function to be called (from evtfoid)
        :param enabled: replication mode firing control (from evtenabled)
        :param tags: command tags (from evttags)
        """
        super(EventTrigger, self).__init__(name, description)
        self._init_own_privs(owner, [])
        self.event = event
        if procedure[-2:] == '()':
            procedure = procedure[:-2]
        self.procedure = split_schema_func(None, procedure)
        if enabled is False or enabled is True:
            self.enabled = enabled
        elif len(enabled) == 1:
            self.enabled = ENABLE_MODES[enabled]
        else:
            assert enabled is not None and enabled in ENABLE_MODES.values()
            self.enabled = enabled
        self.tags = tags
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT evtname AS name, evtevent AS event, rolname AS owner,
                   evtenabled AS enabled, evtfoid::regprocedure AS procedure,
                   evttags AS tags, t.oid,
                   obj_description(t.oid, 'pg_event_trigger') AS description
            FROM pg_event_trigger t JOIN pg_roles ON (evtowner = pg_roles.oid)
            WHERE t.oid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e')
            ORDER BY name"""

    @staticmethod
    def from_map(name, inobj):
        """Initialize an event trigger instance from a YAML map

        :param name: trigger name
        :param inobj: YAML map of the event trigger
        :return: event trigger instance
        """
        obj = EventTrigger(
            name, inobj.pop('description', None), inobj.pop('owner', None),
            inobj.pop('event', None), inobj.pop('procedure', None),
            inobj.pop('enabled', False), inobj.pop('tags', None))
        obj.set_oldname(inobj)
        return obj

    @property
    def objtype(self):
        return "EVENT TRIGGER"

    def to_map(self, db, no_owner=False, no_privs=False):
        """Convert an event trigger  definition to a YAML-suitable format

        :param db: db used to tie the objects together
        :return: dictionary
        """
        dct = super(EventTrigger, self).to_map(db, no_owner)
        dct['procedure'] = join_schema_func(self.procedure) + "()"
        if self.tags is None:
            dct.pop('tags')
        return dct

    @commentable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the event trigger

        :return: SQL statements
        """
        filter = ''
        if self.tags is not None:
            filter = "\n    WHEN tag IN (%s)" % ", ".join(
                ["'%s'" % tag for tag in self.tags])
        return ["CREATE %s %s\n    ON %s%s\n    EXECUTE PROCEDURE %s()" % (
                self.objtype, quote_id(self.name), self.event, filter,
                join_schema_func(self.procedure))]

    def get_implied_deps(self, db):
        deps = super(EventTrigger, self).get_implied_deps(db)
        sch, fnc = self.procedure
        deps.add(db.functions[(sch, fnc, '')])
        return deps


class EventTriggerDict(DbObjectDict):
    "The collection of event triggers in a database"

    cls = EventTrigger

    def _from_catalog(self):
        """Initialize the dictionary of triggers by querying the catalogs"""
        if self.dbconn.version < 90300:
            return
        super(EventTriggerDict, self)._from_catalog()

    def from_map(self, intriggers, newdb):
        """Initialize the dictionary of triggers by converting the input map

        :param intriggers: YAML map defining the event triggers
        :param newdb: dictionary of input database
        """
        for key in intriggers:
            if not key.startswith('event trigger '):
                raise KeyError("Unrecognized object type: %s" % key)
            trg = key[14:]
            inobj = intriggers[key]
            if not inobj:
                raise ValueError("Event trigger '%s' has no specification" %
                                 trg)
            self[trg] = EventTrigger.from_map(trg, inobj)
