BEGIN;

ALTER TYPE userrole RENAME TO userrole_old;
CREATE TYPE userrole AS ENUM ('user', 'driver', 'admin', 'superadmin');
ALTER TABLE users ALTER COLUMN role TYPE userrole USING lower(role::text)::userrole;
DROP TYPE userrole_old;

ALTER TYPE language RENAME TO language_old;
CREATE TYPE language AS ENUM ('uz_latin', 'uz_cyrillic', 'russian');
ALTER TABLE users ALTER COLUMN language TYPE language USING lower(language::text)::language;
DROP TYPE language_old;

ALTER TYPE applicationstatus RENAME TO applicationstatus_old;
CREATE TYPE applicationstatus AS ENUM ('pending', 'approved', 'rejected');
ALTER TABLE driver_applications ALTER COLUMN status TYPE applicationstatus USING lower(status::text)::applicationstatus;
DROP TYPE applicationstatus_old;

ALTER TYPE itemtype RENAME TO itemtype_old;
CREATE TYPE itemtype AS ENUM ('document', 'box', 'luggage', 'valuable', 'other');
ALTER TABLE delivery_orders ALTER COLUMN item_type TYPE itemtype USING lower(item_type::text)::itemtype;
DROP TYPE itemtype_old;

ALTER TYPE orderstatus RENAME TO orderstatus_old;
CREATE TYPE orderstatus AS ENUM ('pending', 'accepted', 'completed', 'cancelled');
ALTER TABLE taxi_orders ALTER COLUMN status TYPE orderstatus USING lower(status::text)::orderstatus;
ALTER TABLE delivery_orders ALTER COLUMN status TYPE orderstatus USING lower(status::text)::orderstatus;
DROP TYPE orderstatus_old;

COMMIT;
