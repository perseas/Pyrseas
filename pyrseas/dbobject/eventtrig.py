# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.eventtrig
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: EventTrigger derived from
    DbObject, and EventTriggerDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbObject
from pyrseas.dbobject import quote_id, commentable, split_schema_obj

EXEC_PROC = 'EXECUTE PROCEDURE '


class EventTrigger(DbObject):
    """An event trigger"""

    keylist = ['name']
    catalog = 'pg_event_trigger'

    @property
    def objtype(self):
        return "EVENT TRIGGER"

    @commentable
    def create(self):
        """Return SQL statements to CREATE the event trigger

        :return: SQL statements
        """
        filter = ''
        if hasattr(self, 'tags'):
            filter = "\n    WHEN tag IN (%s)" % ", ".join(
                ["'%s'" % tag for tag in self.tags])
        return ["CREATE %s %s\n    ON %s%s\n    EXECUTE PROCEDURE %s" % (
                self.objtype, quote_id(self.name), self.event, filter,
                self.procedure)]

    def get_implied_deps(self, db):
        deps = super(EventTrigger, self).get_implied_deps(db)
        sch, fnc = split_schema_obj(self.procedure)
        deps.add(db.functions[(sch, fnc[:-2] , '')])
        return deps


class EventTriggerDict(DbObjectDict):
    "The collection of event triggers in a database"

    cls = EventTrigger
    query = \
        """SELECT t.oid,
                  evtname AS name, evtevent AS event, rolname AS owner,
                  evtenabled AS enabled, evtfoid::regprocedure AS procedure,
                  evttags AS tags,
                  obj_description(t.oid, 'pg_event_trigger') AS description
           FROM pg_event_trigger t
                JOIN pg_roles ON (evtowner = pg_roles.oid)
           WHERE t.oid NOT IN (SELECT objid FROM pg_depend WHERE deptype = 'e')
           ORDER BY name"""
    enable_modes = {'O': True, 'D': False, 'R': 'replica',
                    'A': 'always'}

    def _from_catalog(self):
        """Initialize the dictionary of triggers by querying the catalogs"""
        if self.dbconn.version < 90300:
            return
        for trig in self.fetch():
            trig.enabled = self.enable_modes[trig.enabled]
            self.by_oid[trig.oid] = self[trig.key()] = trig

    def from_map(self, intriggers, newdb):
        """Initalize the dictionary of triggers by converting the input map

        :param intriggers: YAML map defining the event triggers
        :param newdb: dictionary of input database
        """
        for key in intriggers:
            if not key.startswith('event trigger '):
                raise KeyError("Unrecognized object type: %s" % key)
            trg = key[14:]
            intrig = intriggers[key]
            if not intrig:
                raise ValueError("Event trigger '%s' has no specification" %
                                 trg)
            self[trg] = trig = EventTrigger(name=trg)
            for attr, val in list(intrig.items()):
                setattr(trig, attr, val)
            if 'oldname' in intrig:
                trig.oldname = intrig['oldname']
            if 'description' in intrig:
                trig.description = intrig['description']
