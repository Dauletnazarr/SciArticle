DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'django') THEN

      CREATE ROLE django LOGIN;
   END IF;
END
$do$;

ALTER ROLE django CREATEDB;