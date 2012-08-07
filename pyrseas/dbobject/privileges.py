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
    if privcodes == allprivs:
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


def add_grant(obj, privspec):
    """Return GRANT statements on the object based on the privilege spec

    :param obj: the object on which the privilege is granted
    :param privspec: the privilege specification (aclitem)
    :return: list of GRANT statements
    """
    stmts = []
    (usr, privcodes, grantor) = _split_privs(privspec)
    privs = []
    wgo = []
    if privcodes == obj.allprivs:
        privs = ['ALL']
    else:
        for code in sorted(PRIVCODES.keys()):
            if code in privcodes:
                priv = PRIVCODES[code]
                if code + '*' in privcodes:
                    wgo.append(priv.upper())
                else:
                    privs.append(priv.upper())
    if privs:
        stmts.append("GRANT %s ON %s %s TO %s" % (
                ', '.join(privs), obj.privobjtype, obj.name, usr))
    if wgo:
        stmts.append("GRANT %s ON %s %s TO %s WITH GRANT OPTION" % (
                ', '.join(wgo), obj.privobjtype, obj.name, usr))
    return stmts
