Configuration
=============

The Pyrseas utilities allow you to configure various options through a
number of YAML specification files, none of which are required--but
the system configuration file is provided by the normal installation.

If a configuration parameter is specified in more than one file, the
latter file in the list of files below overrides any earlier
specification.  Any configuration item specified on the command line
takes precedence over any such item in a configuration file.

Configuration File Name
-----------------------

The default configuration file name is ``config.yaml``.  If desired,
you can override this with the environment variable
``PYRSEAS_CONFIG_FILE``, but be aware that this will affect all three
levels below.

System Configuration
--------------------

The system configuration file is distributed with Pyrseas and is
normally installed in the ``pyrseas`` library directory.

If desired, you can override this using the ``PYRSEAS_SYS_CONFIG``
environment variable.  This can be defined as a full path, including a
file name, or a directory location, in which case the default file
name as mentioned above under `Configuration File Name`_ will be
appended to the path.

Currently, this file includes specifications for functions, triggers
and other objects used by the :program:`dbaugment` utility.  It also
includes the default directory path for storing multiple YAML files in
a VCS repository, and the path to data files for use by the data
import and export facilities.

User Configuration
------------------

Each user can have his or her own configuration file.  The default
location for this depends on the platform.  Under Linux, BSD, OS/X and
other Unix variants, place the file under your home directory, in the
subdirectory ``.config/pyrseas/``.  Under Windows, put the file in
``%APPDATA%\pyrseas\``.

You can override the location of the user configuration file using the
``PYRSEAS_USER_CONFIG`` environment variable.  This can be defined as
a full path, including a file name, or a directory location, in which
case the default file name as mentioned above under `Configuration
File Name`_ will be appended to the path.

If present, the user configuration file will be merged with the system
configuration.

It is recommended that the user configuration file only be used for
non-project-specific purposes.  For example, if you frequently use
Pyrseas against a remote database or on a non-standard port, you can
specify the host or port in your personal configuration file.

Repository Configuration
------------------------

A configuration file can be placed in a version control repository or
project directory, so that it can be under version control together
with other Pyrseas files such as the output from ``dbtoyaml
--multiple-files``.  The default location for the repository can be
specified in the user configuration, using the keys ``repository`` and
``path``, for example::

 repository:
   path: /home/user/project/repo

You can also use the :option:`--repository` command line option to
specify (or override) the directory path to the root of the repository
and the utilities will look for a configuration file in that location.

If present, the repository configuration file will be merged with the
system and user configuration information.

Command Line Configuration
--------------------------

The utilities also allow you to specify a fourth configuration file on
the command line, using the :option:`--config` command line option.
Again, if the file exists, its information will be merged with
previously read files.
