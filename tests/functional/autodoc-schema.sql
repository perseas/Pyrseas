--
-- $Id: regressdatabase.sql,v 1.2 2006/02/13 01:15:56 rbt Exp $
--

BEGIN;
--
-- Foreign key'd structure, check constraints, primary keys
-- and duplicate table names in different schemas
--
CREATE SCHEMA product
 CREATE TABLE product
 ( product_id SERIAL PRIMARY KEY
 , product_code text NOT NULL UNIQUE 
                     CHECK(product_code = upper(product_code))
 , product_description text
 );

CREATE SCHEMA store
 CREATE TABLE store
 ( store_id SERIAL PRIMARY KEY
 , store_code text NOT NULL UNIQUE
                   CHECK(store_code = upper(store_code))
 , store_description text
 )

 CREATE TABLE inventory
 ( store_id integer REFERENCES store
                       ON UPDATE CASCADE ON DELETE RESTRICT
 , product_id integer REFERENCES product.product
                        ON UPDATE CASCADE ON DELETE RESTRICT
 , PRIMARY KEY(store_id, product_id)
 , quantity integer NOT NULL CHECK(quantity > 0)
 );

--
-- Another schema with 
--
CREATE SCHEMA warehouse
 CREATE TABLE warehouse
 ( warehouse_id SERIAL PRIMARY KEY
 , warehouse_code text NOT NULL UNIQUE
                       CHECK(warehouse_code = upper(warehouse_code))
 , warehouse_manager text NOT NULL
 , warehouse_supervisor text UNIQUE
 , warehouse_description text
 , CHECK (upper(warehouse_manager) != upper(warehouse_supervisor))
 )
 CREATE TABLE inventory
 ( warehouse_id integer REFERENCES warehouse 
                          ON UPDATE CASCADE
                          ON DELETE RESTRICT
 , product_id integer REFERENCES product.product
                        ON UPDATE CASCADE
                        ON DELETE RESTRICT
 , PRIMARY KEY(warehouse_id, product_id)
 , quantity integer NOT NULL
                    CHECK(quantity > 0)
 )
 CREATE VIEW products AS
   SELECT DISTINCT product.*
     FROM inventory
     JOIN product.product USING (product_id);

-- Sample index
CREATE INDEX quantity_index ON warehouse.inventory (quantity);

--
-- Simple text comments
--
--COMMENT ON DATABASE IS
--'This database has been created for the purpose of simple
-- tests on PostgreSQL Autodoc.';

COMMENT ON SCHEMA product IS
'This schema stores a list of products and information
 about the product';

COMMENT ON SCHEMA warehouse IS
'A list of warehouses and information on warehouses';

COMMENT ON TABLE warehouse.inventory IS
'Warehouse inventory';

COMMENT ON TABLE store.inventory IS
'Store inventory';

COMMENT ON COLUMN warehouse.warehouse.warehouse_code IS
'Internal code which represents warehouses for
 invoice purposes';

COMMENT ON COLUMN warehouse.warehouse.warehouse_supervisor IS
'Supervisors name for a warehouse when one
 has been assigned.  The same supervisor may not
 be assigned to more than one warehouse, per company
 policy XYZ.';

COMMENT ON COLUMN warehouse.warehouse.warehouse_manager IS
'Name of Warehouse Manager';

--
-- A few simple functions
--
CREATE FUNCTION product.worker(integer, integer) RETURNS integer AS
'SELECT $1 + $1;' LANGUAGE sql;

CREATE FUNCTION warehouse.worker(integer, integer) RETURNS integer AS
'SELECT $1 * $1;' LANGUAGE sql;

COMMENT ON FUNCTION product.worker(integer, integer) IS
'Worker function appropriate for products';

COMMENT ON FUNCTION warehouse.worker(integer, integer) IS
'Worker function appropriate for warehouses.';


--
-- Inheritance
--
CREATE SCHEMA inherit
  CREATE TABLE taba (cola integer)
  CREATE TABLE tabb (colb integer) inherits(taba)
  CREATE TABLE tab1 (col1 integer)
  CREATE TABLE tab1b (col1b integer) inherits(tab1, tabb);

COMMIT;
