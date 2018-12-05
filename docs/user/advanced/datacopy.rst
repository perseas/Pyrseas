datacopy
========

Below is a walk through using datacopy to manage static data.

Setup
-----

Create the database::

    CREATE DATABASE pyrseas_datacopy_source;

Then in the database, create the table and sample data::

    CREATE TABLE public.status (
        status_id integer NOT NULL,
        status_name character varying (100),        	
        CONSTRAINT status_pkey PRIMARY KEY(status_id)
    );
    INSERT INTO public.status(status_id, status_name)
    VALUES (1, 'Open');
    INSERT INTO public.status(status_id, status_name)
    VALUES (2, 'Closed');

Create "config.yaml" in an empty directory with the following contents::

  datacopy:
    schema public:
    - status

Create the target database::

    CREATE DATABASE pyrseas_datacopy_target;

Initial Deployment
------------------

Now we're going to export the source database, pyrseas_datacopy_source, and then deploy it to the target database, pyrseas_datacopy_target.

Export the database using dbtoyaml, running this from the directory containing config.yaml::

    $ dbtoyaml -H localhost -U postgres -W -o pyrseas_datacopy.yaml pyrseas_datacopy_source
    Password:

You will have the following file structure::

    Workspace
    ├── metadata
    │   └── schema.public
    │       └── table.status.data
    ├── config.yaml
    └── pyrseas_datacopy.yaml

table.status.data contains the table data in CVS format.

Now let's deploy this to the target database, pyrseas_datacopy_target::

    $ yamltodb -H localhost -U postgres -W -u pyrseas_datacopy_target pyrseas_datacopy.yaml
    Password:
    BEGIN;
    CREATE TABLE status (
        status_id integer NOT NULL,
        status_name character varying(100));

    ALTER TABLE status OWNER TO postgres;

    ALTER TABLE status ADD CONSTRAINT status_pkey PRIMARY KEY (status_id);

    TRUNCATE ONLY status;

    \copy status from 'C:\Users\me\Documents\Workspace\metadata\schema.public\table.status.data' csv

    COMMIT;
    Changes applied


Incremental Deployment
----------------------

Make changes to the static data::
    
    INSERT INTO public.status(status_id, status_name)
    VALUES (3, 'Inactive');

    UPDATE public.status 
    SET status_name = 'Active'
    WHERE status_id = 1;

    DELETE FROM public.status
    WHERE status_id = 2;

Run dbtoyaml::


    $ dbtoyaml -H localhost -U postgres -W -o pyrseas_datacopy.yaml pyrseas_datacopy_source
    Password:

Run yamltodb to modify the target database::

    $ yamltodb -H localhost -U postgres -W -u pyrseas_datacopy_target pyrseas_datacopy.yaml
    Password:
    BEGIN;
    TRUNCATE ONLY status;

    \copy status from 'C:\Users\me\Documents\Workspace\metadata\schema.public\table.status.data' csv

    COMMIT;
    Changes applied

The target database now has the new set of records.