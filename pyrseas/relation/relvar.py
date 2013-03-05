# -*- coding: utf-8 -*-
"""
    pyrseas.relation.relvar
"""
from psycopg2 import DatabaseError

from pyrseas.relation import Attribute, Tuple
from pyrseas.relation.tuple import tuple_values_dict


class RelVar(object):
    "A relation variable, commonly known as database table"

    def __init__(self, name, attribs, key=[], extname=None):
        """Initialize a relation variable

        :param name: relvar name
        :param attribs: list of Attributes
        :param key: list of attribute names forming the key
        :param extname: external name for relvar
        """
        self.name = name
        self.attributes = tuple([(attr.name, attr) for attr in attribs])
        self._required_attribs = [
            attrname for attrname, attr in self.attributes if (
                not attr.sysdefault and not attr.nullable)]
        self.key = key
        self.extname = extname or name

    def connect(self, dbconn):
        """Specify the database where the relvar is present

        :param dbconn: DbConnection object
        """
        self.db = dbconn

    def tuple(self, *args, **kwargs):
        """Return a Tuple based on relvar and passed-in arguments

        :param args: positional arguments corresponding to attributes
        :param kwargs: keyword arguments corresponding to attributes
        :return: Tuple
        """
        kwargs.update(dict(list(zip([name for name, attr in self.attributes],
                                    args))))
        attribs = []
        namelist = []
        attrs = dict(self.attributes)
        for (argname, argval) in list(kwargs.items()):
            attr = attrs[argname]
            attribs.append(Attribute(
                argname, attr.type, argval, nullable=attr.nullable,
                sysdefault=attr.sysdefault))
            namelist.append(argname)
        for name in self._required_attribs:
            if name not in namelist:
                raise ValueError("Missing required attribute: %s" % name)

        return Tuple(attribs)

    def key_tuple(self, *args, **kwargs):
        """Return a Tuple of key attributes, with given values

        :param args: positional arguments corresponding to key attributes
        :param kwargs: keyword arguments corresponding to key attributes
        :return: Tuple
        """
        kwargs.update(dict(list(zip(self.key, args))))
        return Tuple([Attribute(name, type(val), val) for name, val in
                     list(kwargs.items())])

    def default_tuple(self):
        """Return a Tuple of key and required attributes, with default values

        :return: Tuple
        """
        attrs = self.key[:]
        attrs.extend([name for name in self._required_attribs
                      if not name in attrs])
        return Tuple([Attribute(name, attr.type)
                      for name, attr in self.attributes if name in attrs])

    def insert_one(self, newtuple, retkey=False):
        """Execute a single-tuple INSERT command

        :param newtuple: the tuple to be inserted
        :param retkey: indicates assigned key values should be returned
        """
        attrnames = [name for name, typ in newtuple._heading]
        targets = '(%s)' % ", ".join(attrnames)
        values_list = 'VALUES (%s)' % ", ".join(
            ['%%(%s)s' % name for name in attrnames])
        cmd = "INSERT INTO %s %s %s" % (self.name, targets, values_list)
        if retkey:
            cmd += " RETURNING %s" % ", ".join(self.key)
        curs = self.db.execute(cmd, tuple_values_dict(newtuple))
        if curs.rowcount != 1:
            self.db.rollback()
            raise DatabaseError("Failed to add %s %r" % (self.extname, self))
        if retkey:
            attrdict = dict(self.attributes)
            rettuple = Tuple([Attribute(name, attrdict[name].type)
                              for name in self.key])
            row = curs.fetchone()
            for attr, type_ in rettuple._heading:
                setattr(rettuple, attr, row[attr])
        curs.close()
        if retkey:
            return rettuple

    def where_clause(self, tuple_version=False):
        """Return WHERE clause for use by get, update and delete methods

        :param tuple_version: indicates whether tuple_version should be added
        :return: string
        """
        clause = "WHERE %s" % " AND ".join(
            ['%s = %%(_kv_%s)s' % (attr, attr) for attr in self.key])
        if tuple_version:
            clause += " AND xmin = %(xmin)s"
        return clause

    def key_values(self, tup):
        """Return dictionary of key values for use by get_one method

        :param tup: Tuple object to get key values from
        :return: dictionary
        """
        return {'_kv_%s' % attr: getattr(tup, attr) for attr in self.key}

    def key_values_update(self, keytuple, currtuple=None):
        """Return dictionary of key values for use by update and delete

        :param keytuple: Tuple object to get key values from
        :param currtuple: previous version of tuple
        :return: dictionary

        This includes {'xmin': tuple_version}.
        """
        keyvals = self.key_values(keytuple)
        verstuple = keytuple if currtuple is None else currtuple
        keyvals.update(xmin=verstuple._tuple_version)
        return keyvals

    def update_one(self, newtuple, keytuple, currtuple=None):
        """Execute a single-tuple UPDATE command using the primary key

        :param newtuple: Tuple with new values
        :param keytuple: Tuple with key values
        :param currtuple: previous version of newtuple
        """
        def update_one_cmd():
            if changed_values or not hasattr(self, 'update_one_cmd'):
                setlist = "SET %s" % ", ".join(
                    ['%s = %%(%s)s' % (c, c) for c in
                     list(changed_values.keys())])
                self.update_one_cmd = "UPDATE %s %s %s" % (
                    self.name, setlist,
                    self.where_clause(currtuple is not None))
            return self.update_one_cmd

        if currtuple:
            changed_values = tuple_values_dict(currtuple, newtuple)
            if not changed_values:
                return
        else:
            changed_values = tuple_values_dict(newtuple)
        values = self.key_values_update(keytuple, currtuple)
        values.update(changed_values)
        curs = self.db.execute(update_one_cmd(), values)
        if curs.rowcount != 1:
            self.db.rollback()
            raise DatabaseError("Failed to update %s %r" % (
                self.extname, self))
        curs.close()

    def delete_one(self, keytuple, currtuple=None):
        """Execute a single-tuple DELETE command using the primary key

        :param keytuple: Tuple with key values
        :param currtuple: tuple from previous get
        """
        def delete_one_cmd():
            if not hasattr(self, 'delete_one_cmd'):
                self.delete_one_cmd = "DELETE FROM %s %s" % (
                    self.name, self.where_clause(currtuple is not None))
            return self.delete_one_cmd

        values = self.key_values_update(keytuple, currtuple)
        curs = self.db.execute(delete_one_cmd(), values)
        if curs.rowcount != 1:
            self.db.rollback()
            raise DatabaseError("Failed to delete %s %r" % (
                self.extname, self))
        curs.close()

    def get_one(self, keytuple):
        """Execute a single-tuple retrieval and return the tuple data

        :param keytuple: Tuple with key values
        :return: Tuple or None
        """
        attrdict = dict(self.attributes)
        attrnames = list(attrdict.keys())

        def get_one_qry():
            if not hasattr(self, 'get_one_qry'):
                from_clause = self.name
                self.get_one_qry = "SELECT %s.xmin, %s FROM %s %s" % (
                    self.name, ", ".join(attrnames), from_clause,
                    self.where_clause())
            return self.get_one_qry

        key = self.key_values(keytuple)
        row = self.db.fetchone(get_one_qry(), key)
        self.db.rollback()
        if not row:
            return None
        tup = Tuple([Attribute(name, attrdict[name].type, row[name],
                               nullable=attrdict[name].nullable,
                               sysdefault=attrdict[name].sysdefault)
                     for name in attrnames])
        tup._tuple_version = row['xmin']
        return tup
