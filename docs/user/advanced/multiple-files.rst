Multiple Files
==============

When running yamltodb in single file mode, the \*.yaml file is loaded into memory and then it deploys the database.

When using --multiple-files, yamltodb will merge all the files in memory and continue processing as if it were a single file.

This page describes how --mutliple-files is merged in memory.

Folder Structure
----------------

yamltodb requires the following --multiple-files folder stucture:

* metadata folder\*
* \*.yaml files in the metadata folder
* schema.<name> sub folders (and matching schema.<name>.yaml files in the metadata folder)
* \*.yaml files in the schema.<name> folder

\* It is possible to rename the metadata folder, see :doc:`configitems` for more information.

Below is a sample folder structure

::

    metadata
    ├── schema.myschema
    │   ├── myschema-file-a.yaml
    │   └── myschema-file-b.yaml  
    ├── schema.public
    │   ├── file.yaml
    │   └── file2.yaml  
    ├── rootfile1.yaml
    ├── rootfile2.yaml
    ├── schema.myschema.yaml
    └── schema.public.yaml


The non-schema files in the metadata folder (rootfile1.yaml, rootfile2.yaml) are concatenated together. Initially schema.*.yaml files are ignored.

When a folder is found starting with "schema.*, then yamltodb will require a matching schema.<name>.yaml file and concatenate it with the other files.  For example, when the folder "schema.public" is found, yamltodb will read the "schema.public.yaml" file.

All \*.yaml files under schema.<name> are added under the "schema <name>" yaml node.

No other subdirectories besides "schema.*" are allowed.

Filenames are ignored.

\*.yaml files can contain 1 or more items. (For example, one table or multiple tables)

Example Scenario
----------------

Mutiple Files Structure
~~~~~~~~~~~~~~~~~~~~~~~

Say you have the following folder structure

::

    metadata
    ├── schema.orders
    │   ├── tables.yaml
    ├── schema.public
    │   └── <empty> 
    ├── extension.yaml
    ├── schema.orders.yaml
    └── schema.public.yaml

metadata/extension.yaml contains:

::

 extension plpgsql:
   description: PL/pgSQL procedural language
   owner: postgres
   schema: pg_catalog
   version: '1.0'

metadata/schema.orders.yaml contains:

::

 schema orders:
   owner: postgres
   privileges:
     - postgres:
       - all


metadata/schema.public.yaml contains:

::

 schema public:
   owner: postgres
   privileges:
     - postgres:
       - all

       
metadata/schema.orders/tables.yaml contains:

::

 table orders:
   columns:
    - order_id:        {not_null: true, type: bigint}
    - order_date:      {not_null: true, type: timestamp with time zone}
   primary_key:
     pk_orders:        { columns: [ order_id ] }
 table order_items:
   columns:
    - order_item_id:   {not_null: true, type: bigint}
    - product:         {not_null: true, type: character varying(100)}
    - quantity:        {not_null: true, type: integer}
    - unit_cost:       {not_null: true, type: money}
   primary_key:
     pk_order_items:   { columns: [ order_item_id ] }

     
Run the following in a terminal window::

 $ ls
 metadata
 $ yamltodb --multiple-files -u -U postgres -W pyrseas_sample


Single File Structure
~~~~~~~~~~~~~~~~~~~~~~~

The above --multiple-files structure will merge in memory to the equavalent single file structure:

::

 extension plpgsql:
   description: PL/pgSQL procedural language
   owner: postgres
   schema: pg_catalog
   version: '1.0'
 schema orders:
   owner: postgres
   privileges:
     - postgres:
       - all
   table orders:
     columns:
      - order_id:        {not_null: true, type: bigint}
      - order_date:      {not_null: true, type: timestamp with time zone}
     primary_key:
       pk_orders:        { columns: [ order_id ] }
   table order_items:
     columns:
      - order_item_id:   {not_null: true, type: bigint}
      - product:         {not_null: true, type: character varying(100)}
      - quantity:        {not_null: true, type: integer}
      - unit_cost:       {not_null: true, type: money}
     primary_key:
       pk_order_items:   { columns: [ order_item_id ] }
 schema public:
   owner: postgres
   privileges:
     - postgres:
       - all

