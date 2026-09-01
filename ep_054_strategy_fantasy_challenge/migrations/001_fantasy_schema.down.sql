-- migrations/001_fantasy_schema.down.sql — Rollback for the initial isolated EP054 schema.
--
-- VERSION HISTORY
-- v1.0.0 · 2026-09-01 · Provides a clean-database rollback rehearsal without naming or altering shared schemas.

DROP SCHEMA IF EXISTS fantasy CASCADE;
