-- SQL Script to add initial_points column to membership_plans table
-- Run this in your SQLite database

-- Check if table exists
SELECT name FROM sqlite_master WHERE type='table' AND name='membership_plans';

-- If table exists, add the column
ALTER TABLE membership_plans ADD COLUMN initial_points INTEGER NOT NULL DEFAULT 0;

-- Verify the column was added
PRAGMA table_info(membership_plans);

-- Update existing plans with initial points values
-- Adjust these values based on your actual membership tiers

-- Example updates (uncomment and modify as needed):
-- UPDATE membership_plans SET initial_points = 1500 WHERE tier_code = 'SILVER';
-- UPDATE membership_plans SET initial_points = 4000 WHERE tier_code = 'GOLD';
-- UPDATE membership_plans SET initial_points = 8500 WHERE tier_code = 'PLATINUM';
-- UPDATE membership_plans SET initial_points = 18000 WHERE tier_code = 'VIP';
-- UPDATE membership_plans SET initial_points = 47000 WHERE tier_code = 'DIAMOND';
