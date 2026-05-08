-- AlterTable: add soft-delete and TOS acceptance timestamps to User
-- Both columns are nullable — existing rows remain valid with NULL values.
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "tosAcceptedAt" TIMESTAMP(3);
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "deletedAt" TIMESTAMP(3) DEFAULT NULL;
