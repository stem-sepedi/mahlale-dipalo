-- Docker init: create the Moodle database + user at first boot.
-- Runs in the postgres container alongside 001_initial_schema.sql.
-- Keep in sync with docker-compose.yml moodle.*_NAME / *_USER / *_PASSWORD.

CREATE ROLE moodle LOGIN PASSWORD 'moodle_3f2d4f7d-5d33-4878-92f8-8ebae619f6e4';
CREATE DATABASE moodle OWNER moodle;
GRANT ALL PRIVILEGES ON DATABASE moodle TO moodle;