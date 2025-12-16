-- Migration: Add initial_stake column to teams table
-- Date: 2025-12-01
-- Description: Adds initial_stake column to store per-team initial stake value

-- Add column with default value
ALTER TABLE teams
ADD COLUMN IF NOT EXISTS initial_stake FLOAT DEFAULT 10.0;

-- Update existing teams to have initial_stake = 10.0
UPDATE teams
SET initial_stake = 10.0
WHERE initial_stake IS NULL;

-- Make column NOT NULL after setting defaults
ALTER TABLE teams
ALTER COLUMN initial_stake SET NOT NULL;

-- Add comment
COMMENT ON COLUMN teams.initial_stake IS 'Initial stake amount for this team (per-team configuration)';
