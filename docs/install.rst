Installation
============

Summary
-------

For the latest release, use::

 pip install Pyrseas

For development::

 git clone git://github.com/perseas/Pyrseas.git
 cd Pyrseas
 python setup.py install

Requirements
------------

Pyrseas provides tools for `Postgres <https://www.postgresql.org>`_,
so obviously you need **Postgres** to start with.  Pyrseas has been
tested with PG 9.4, 9.5, 9.6, 10 and 11, and we'll certainly keep up
with future releases.  Please refer to the `Postgres download page
<https://www.postgresql.org/download>`_ to find a distribution for the
various Linux, Unix and Windows platforms supported.

You will also need **Python**.  Pyrseas was originally developed using
Python 2 and been tested with `Python <http://www.python.org>`_ 2.7,
but that version will no longer be supported effective 1 Jan 2020.  It
has been ported to Python 3 and
tested against versions from 3.2 through 3.7.  Python 3 is the
preferred usage and development environment.  On Linux or \*BSD,
Python may already be part of your distribution or may be available as
a package.  For Windows and Mac OS please refer to the `Python
download page <http://www.python.org/downloads/>`_ for installers and
instructions.

Pyrseas talks to the Postgres DBMS via the **Psycopg2 adapter**.
Pyrseas has been tested with `psycopg2 <http://initd.org/psycopg/>`_
2.5 through 2.7.  Psycopg2 is available as a package on most Linux or
\*BSD distributions and can also be downloaded or installed from PyPI.
Please refer to the `Psycopg download page
<http://initd.org/psycopg/download/>`_ for more details.

.. note:: If you install Pyrseas using ``pip`` (see below) and you
   have not already installed Psycopg2, e.g., when installing into a
   ``virtualenv`` environment created with ``--no-site-packages``, you
   may need to have installed the Postgres and Python development
   packages, and a C compiler, as ``pip`` may download and attempt to
   build and install psycopg2 before installing Pyrseas.

The Pyrseas utilities rely on **PyYAML**, a `YAML <http://yaml.org>`_
library.  This may be available as a package for your operating system
or it can be downloaded from the `Python Package Index (PyPI)
<https://pypi.org/project/PyYAML/>`_.

.. _download:

Downloading
-----------

Pyrseas is available at the following locations:

 - `Python Package Index <https://pypi.org/project/Pyrseas>`_
 - `Postgres Extension Network (PGXN) <https://pgxn.org/dist/pyrseas/>`_
 - `GitHub repository <https://github.com/perseas/Pyrseas>`_

You can download the distribution from PyPI in gzip-compressed tar or
ZIP archive format, but you can download *and* install it using
``Pip``.  See `Python Installer`_ below for details.

PGXN provides a ZIP archive which you can download or you can download
*and* install using the PGXN client (see `PGXN Client`_ below).

The GitHub repository holds the Pyrseas source code, tagged according
to the various releases, e.g., v0.9.0, and including unreleased
modifications.  To access it, you need `Git <https://git-scm.com/>`_
which is available as a package in most OS distributions or can be
downloaded from the `Git download page
<https://git-scm.com/download>`_.  You can fetch the Pyrseas sources by
issuing one of the following commands::

 git clone git://github.com/perseas/Pyrseas.git

or::

 git clone https://github.com/perseas/Pyrseas.git

This will create a ``Pyrseas`` directory tree (you can use a different
target name by adding it to the above commands).  To list available
releases, change to the subdirectory and invoke ``git tag``.  To
switch to a particular release, use::

 git checkout vn.n.n

where *vn.n.n* is the release identifier.  Use ``git checkout master``
to revert to the main (master) branch.  To fetch the latest updates,
use::

 git pull

Installation
------------

Extracting Sources
~~~~~~~~~~~~~~~~~~

Once you have downloaded an archive from PyPI or PGXN, you need to
extract the sources. For a gzip-compressed tar file, use::

 tar xzf Pyrseas-n.n.n.tar.gz

where *n.n.n* is the release version.  For a ZIP archive, use::

 unzip Pyrseas-n.n.n.zip

Both commands above will create a directory ``Pyrseas-n.n.n`` and you
will want to ``cd`` to it before proceeding with the installation.

Installing
~~~~~~~~~~

If you have superuser or similar administrative privileges, you can
install Pyrseas for access by multiple users on your system.  On Linux
and other Unix-flavored systems, you can install from the extracted
``Pyrseas-n.n.n`` source directory or from the root directory of the
``git`` clone, using the following command::

 sudo python setup.py install

That will install the :doc:`dbtoyaml </dbtoyaml>` and :doc:`yamltodb
</yamltodb>` utility scripts in a directory such as
``/usr/local/bin``.  The library sources and bytecode files will be
placed in a ``pyrseas`` subdirectory under ``site-packages`` or
``dist-packages``, e.g.,
``/usr/local/lib/python3.6/dist-packages/pyrseas``.

On Windows, from an account with Administrator privileges, you can
use::

 python setup.py install

That will install the Pyrseas utilities in the ``Scripts`` folder of
your Python installation.  The source and bytecode files will go in
the ``site-packages`` folder, e.g.,
``C:\Python36\Lib\site-packages\pyrseas``.

.. _installer:

Python Installer
~~~~~~~~~~~~~~~~

You can also download and install Pyrseas using `pip
<https://pypi.org/project/pip/>`_. For example, on Linux do::

 sudo pip install Pyrseas

If this is the first time you are installing a Python package, please
do yourself a favor and read and follow the instructions in the
"Distribute & Pip" subsection of the "Installing Python on ..."
section for your platform of the `The Hitchhiker’s Guide to Python!
<http://docs.python-guide.org/en/latest/index.html>`_.

.. note:: On FreeBSD, it has been reported that it is necessary to
          install the Python ``distribute`` package, prior to
          installing Pyrseas with ``pip``.  This may also be necessary
          on other BSD variants.

.. note:: On Windows 64-bit, it has been reported that it is necessary
          to obtain unofficial versions of the ``distribute`` and
          ``PyYAML`` packages, available at `University of California,
          Irvine <https://www.lfd.uci.edu/~gohlke/pythonlibs/>`_. For
          a detailed tutorial, see `this post
          <http://dbadailystuff.com/2012/07/04/install-pyrseas-in-windows/>`_.

``Pip`` can also be used in a Python `virtualenv
<http://virtualenv.pypa.io/en/latest/>`_ environment, in which case
you *don't* need to prefix the commands with ``sudo``.

``Pip`` also provides the ability to uninstall Pyrseas.

PGXN Client
~~~~~~~~~~~

The PGXN `client <https://pypi.org/project/pgxnclient/>`_ (available
at PyPI) can be used to download and install Pyrseas from PGXN.  Usage
is::

 pgxn install pyrseas
