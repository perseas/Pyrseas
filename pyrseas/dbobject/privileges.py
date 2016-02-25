# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.privileges
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This defines functions for dealing with access privileges.
"""

PRIVCODES = {'a': 'insert', 'r': 'select', 'w': 'update', 'd': 'delete',
             'D': 'truncate', 'x': 'references', 't': 'trigger',
             'X': 'execute', 'U': 'usage', 'C': 'create'}
PRIVILEGES = dict((v, k) for k, v in list(PRIVCODES.items()))


def _split_privs(privspec):
    """Split the aclitem into three parts

    :param privspec: privilege specification (aclitem)
    :return: tuple with grantee, privilege codes and granto
    """
    (usr, prvgrant) = privspec.split('=')
    if usr == '':
        usr = 'PUBLIC'
    (privcodes, grantor) = prvgrant.split('/')
    return (usr, privcodes, grantor)


def _expand_priv_lists(obj, privcodes, subobj):
    """Convert privilege code strings to expanded lists

    :param obj: the object on which the privilege is granted
    :param privcodes: string of privilege codes
    :param subobj: sub-object name (e.g., column name)
    :return: tuple of lists with decoded privileges
    """
    privs = []
    wgo = []
    if privcodes == obj.allprivs and len(obj.allprivs) > 1:
        privs = ['ALL']
    else:
        if subobj:
            subobj = ' (%s)' % subobj
        for code in sorted(PRIVCODES.keys()):
            if code in privcodes:
                priv = PRIVCODES[code].upper() + subobj
                if code + '*' in privcodes:
                    wgo.append(priv)
                else:
                    privs.append(priv)
    return (privs, wgo)


def privileges_to_map(privspec, allprivs, owner):
    """Map a set of privileges in PostgreSQL format to YAML-suitable format

    :param privspec: privilege specification
    :param allprivs: privilege list equal to ALL
    :param owner: object owner
    :return: dictionary

    Access privileges are specified as aclitem's as follows:
    <grantee>=<privlist>/<grantor>.  The grantee and grantor are user
    names.  The privlist is a set of single letter codes, each letter
    optionally followed by an asterisk to indicate WITH GRANT OPTION.
    """
    (usr, privcodes, grantor) = _split_privs(privspec)
    privs = []
    if privcodes == allprivs and len(allprivs) > 1:
        privs = ['all']
    else:
        for code in sorted(PRIVCODES.keys()):
            if code in privcodes:
                priv = PRIVCODES[code]
                if code + '*' in privcodes:
                    priv = {priv: {'grantable': True}}
                privs.append(priv)
    if owner and grantor != owner:
        privs = {'privs': privs, 'grantor': grantor}
    return {usr: privs}


def privileges_from_map(privlist, allprivs, owner):
    """Map privileges from YAML-suitable format to an internal list

    :param privspec: privilege specification
    :param allprivs: privilege list equal to ALL
    :param owner: object owner
    :return: list
    """
    retlist = []
    for priv in privlist:
        usr = list(priv.keys())[0]
        privs = priv[usr]
        grantor = owner
        if 'grantor' in privs:
            grantor = privs['grantor']
            privs = privs['privs']
        if usr == 'PUBLIC':
            usr = ''
        prvcodes = ''
        if privs == ['all']:
            prvcodes = allprivs
        else:
            for prv in privs:
                if isinstance(prv, dict):
                    key = list(prv.keys())[0]
                else:
                    key = prv
                if key in PRIVILEGES:
                    prvcodes += PRIVILEGES[key]
                if isinstance(prv, dict) and isinstance(prv[key], dict) and \
                        'grantable' in prv[key] and prv[key]['grantable']:
                    prvcodes += '*'
        retlist.append("%s=%s/%s" % (usr, prvcodes, grantor))
    return retlist


def add_grant(obj, privspec, subobj=''):
    """Return GRANT statements on the object based on the privilege spec

    :param obj: the object on which the privilege is granted
    :param privspec: the privilege specification (aclitem)
    :param subobj: sub-object name (e.g., column name)
    :return: list of GRANT statements
    """
    (usr, privcodes, grantor) = _split_privs(privspec)
    (privs, wgo) = _expand_priv_lists(obj, privcodes, subobj)
    objtype = obj.objtype
    if hasattr(obj, 'privobjtype'):
        objtype = obj.privobjtype
    stmts = []
    if privs:
        stmts.append("GRANT %s ON %s %s TO %s" % (
            ', '.join(privs), objtype, obj.identifier(), usr))
    if wgo:
        stmts.append("GRANT %s ON %s %s TO %s WITH GRANT OPTION" % (
            ', '.join(wgo), objtype, obj.identifier(), usr))
    return stmts


def add_revoke(obj, privspec, subobj=''):
    """Return REVOKE statements on the object based on the privilege spec

    :param obj: the object on which the privilege is to be revoked
    :param privspec: the privilege specification (aclitem)
    :param subobj: sub-object name (e.g., column name)
    :return: list of REVOKE statements
    """
    (usr, privcodes, grantor) = _split_privs(privspec)
    (privs, wgo) = _expand_priv_lists(obj, privcodes, subobj)
    objtype = obj.objtype
    if hasattr(obj, 'privobjtype'):
        objtype = obj.privobjtype
    stmts = []
    if wgo:
        stmts.append("REVOKE %s ON %s %s FROM %s" % (
            ', '.join(wgo), objtype, obj.identifier(), usr))
    if privs:
        stmts.append("REVOKE %s ON %s %s FROM %s" % (
            ', '.join(privs), objtype, obj.identifier(), usr))
    return stmts


def diff_privs(currobj, currlist, newobj, newlist, subobj=''):
    """Return GRANT or REVOKE statements to adjust object privileges

    :param currobj: current object
    :param currlist: list of current privileges
    :param newobj: new object
    :param newlist: list of new privileges
    :param subobj: sub-object (e.g., column name)
    :return: list of GRANT and REVOKE statements
    """
    def rejoin(privdict, usr, grantor):
        return '%s=%s/%s' % ('' if usr == 'PUBLIC' else usr,
                             privdict[(usr, grantor)], grantor)

    stmts = []
    currprivs = {}
    newprivs = {}
    for privspec in currlist:
        if privspec:
            (usr, privcodes, grantor) = _split_privs(privspec)
            currprivs[(usr, grantor)] = privcodes
    for privspec in newlist:
        if privspec:
            (usr, privcodes, grantor) = _split_privs(privspec)
            newprivs[(usr, grantor)] = privcodes
    for (usr, gtor) in currprivs:
        if (usr, gtor) not in newprivs:
            stmts.append(add_revoke(currobj, rejoin(currprivs, usr, gtor),
                                    subobj))
    for (usr, gtor) in newprivs:
        if (usr, gtor) not in currprivs:
            stmts.append(add_grant(newobj, rejoin(newprivs, usr, gtor),
                                   subobj))
        else:
            if sorted(currprivs[(usr, gtor)]) != sorted(newprivs[(usr, gtor)]):
                stmts.append(add_revoke(currobj, rejoin(currprivs, usr, gtor),
                                        subobj))
                stmts.append(add_grant(newobj, rejoin(newprivs, usr, gtor),
                                       subobj))
    return stmts
