Installation
============

Summary
-------

For the latest release, use::

 pip install Pyrseas

For development::

 git clone git://github.com/jmafc/Pyrseas.git
 cd Pyrseas
 python setup.py install

Requirements
------------

Pyrseas provides tools for `PostgreSQL <http://www.postgresql.org>`_,
so obviously you need **PostgreSQL** to start with.  Pyrseas has been
tested with PG 8.4, 9.0, 9.1 and 9.2, and we'll certainly keep up with
future releases.  Please refer to section III, `Server Administration
<http://www.postgresql.org/docs/current/interactive/admin.html>`_ of
the PostgreSQL documentation for details on installation, setup and
the various Linux, Unix and Windows platforms supported.

You will also need **Python**.  Pyrseas has been tested with `Python
<http://www.python.org>`_ 2.6 and 2.7, but should also work with 2.5.
It has also been ported to Python 3.2.
On Linux or \*BSD, Python may already be part of your
distribution or may be available as a package.  For Windows and Mac OS
please refer to the `Python download page
<http://www.python.org/download/>`_ for installers and instructions.

Pyrseas talks to the PostgreSQL DBMS via the **Psycopg2 adapter**.
Pyrseas has been tested with `psycopg2 <http://initd.org/psycopg/>`_
2.2 and 2.4.  Psycopg2 is available as a package on most Linux or
\*BSD distributions and can also be downloaded or installed from PyPI.
Please refer to the `Psycopg download page
<http://initd.org/psycopg/download/>`_ for more details.

.. note:: If you install Pyrseas using ``pip`` (see below) and you
   have not already installed Psycopg2, e.g., when installing into a
   ``virtualenv`` environment created with ``--no-site-packages``, you
   will need to have installed the PostgreSQL and Python development
   packages, and a C compiler, as ``pip`` will download and attempt to
   build and install psycopg2 before installing Pyrseas.

The Pyrseas utilities rely on **PyYAML**, a `YAML <http://yaml.org>`_
library.  This may be available as a package for your operating system
or it can be downloaded from the `Python Package Index
<http://pypi.python.org/pypi/PyYAML/>`_.

.. _download:

Downloading
-----------

Pyrseas is available at the following locations:

 - `Python Package Index (PyPI) <http://pypi.python.org/pypi/Pyrseas>`_
 - `PostgreSQL Extension Network (PGXN) <http://pgxn.org/dist/pyrseas/>`_
 - `PgFoundry <http://pgfoundry.org/projects/pyrseas/>`_
 - `GitHub repository <https://github.com/jmafc/Pyrseas>`_

You can download the distribution from PyPI in gzip-compressed tar or
ZIP archive format, but you can download *and* install it using either
``Pip`` or ``Easy Install``.  See `Python Installers`_ below for
details.

PGXN provides a ZIP archive which you can download or you can download
*and* install using the PGXN client (see `PGXN Client`_ below).

PgFoundry offers the distribution in gzip-compressed tar or ZIP
archive format, which can be downloaded and then installed as
described `below <#id1>`_.

The GitHub repository holds the Pyrseas source code, tagged according
to the various releases, e.g., v0.2.0, and including unreleased
modifications.  To access it, you need `Git <http://git-scm.com/>`_
which is available as a package in most OS distributions or can be
downloaded from the `Git download page
<http://git-scm.com/download>`_.  You can fetch the Pyrseas sources by
issuing one of the following commands::

 git clone git://github.com/jmafc/Pyrseas.git

or::

 git clone https://github.com/jmafc/Pyrseas.git

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

Once you have downloaded an archive from PyPI, PGXN or PgFoundry, you
need to extract the sources. For a gzip-compressed tar file, use::

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
``/usr/local/lib/python2.6/dist-packages/pyrseas``.

On Windows, from an account with Administrator privileges, you can
use::

 python setup.py install

That will install the Pyrseas utilities in the ``Scripts`` folder of
your Python installation.  The source and bytecode files will go in
the ``site-packages`` folder, e.g.,
``C:\Python27\Lib\site-packages\pyrseas``.

.. _installers:

Python Installers
~~~~~~~~~~~~~~~~~

You can also download and install Pyrseas using `pip
<http://www.pip-installer.org/en/latest/>`_ or `easy_install
<http://packages.python.org/distribute/easy_install.html>`_. For
example, on Linux do::

 sudo pip install Pyrseas

or::

 sudo easy_install Pyrseas

If this is the first time you are installing a Python package, please
do yourself a favor and read and follow the instructions in the
"Distribute & Pip" subsection of the "Installing Python on ..."
section for your platform of the `The Hitchhiker’s Guide to Python!
<http://docs.python-guide.org/en/latest/index.html>`_.

.. note:: On FreeBSD, it has been reported that it is necessary to
          install the Python ``distribute`` package, prior to
          installing Pyrseas with ``pip``.  This may also be necessary
          on other BSD variants.  See the *Hitchhiker's Guide* above
          for further details.

.. note:: On Windows 64-bit, it has been reported that it is necessary
          to obtain unofficial versions of the ``distribute`` and
          ``PyYAML`` packages, available at `University of California,
          Irvine <http://www.lfd.uci.edu/~gohlke/pythonlibs/>`_. For a
          detailed tutorial, see `this post
          <http://dbadailystuff.com/2012/07/04/install-pyrseas-in-windows/>`_.

``Pip`` and ``easy_install`` can also be used in a Python `virtualenv
<http://www.virtualenv.org/en/latest/>`_ environment, in which case
you *don't* need to prefix the commands with ``sudo``.

``Pip`` also provides the ability to uninstall Pyrseas.

PGXN Client
~~~~~~~~~~~

The PGXN `client <http://pypi.python.org/pypi/pgxnclient>`_ (available
at PyPI) can be used to download and install Pyrseas from PGXN.  Usage
is::

 pgxn install pyrseas
