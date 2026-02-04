-- SQL script to create test users
-- Run this in SQLite database browser or via command line

-- Delete existing test users if any
DELETE FROM users WHERE email IN ('admin@altayar.com', 'employee@altayar.com', 'customer@altayar.com');

-- Insert Admin
INSERT INTO users (
    id, email, password_hash, phone, first_name, last_name, 
    role, status, language, email_verified, email_verified_at, 
    created_at, updated_at
) VALUES (
    lower(hex(randomblob(16))),
    'admin@altayar.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYCNqJ4tK',
    '+966500000001',
    'Admin',
    'User',
    'ADMIN',
    'ACTIVE',
    'ar',
    1,
    datetime('now'),
    datetime('now'),
    datetime('now')
);

-- Insert Employee
INSERT INTO users (
    id, email, password_hash, phone, first_name, last_name, 
    role, employee_type, status, language, email_verified, email_verified_at,
    created_at, updated_at
) VALUES (
    lower(hex(randomblob(16))),
    'employee@altayar.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYCNqJ4tK',
    '+966500000002',
    'Employee',
    'User',
    'EMPLOYEE',
    'RESERVATION',
    'ACTIVE',
    'ar',
    1,
    datetime('now'),
    datetime('now'),
    datetime('now')
);

-- Insert Customer
INSERT INTO users (
    id, email, password_hash, phone, first_name, last_name,
    role, status, language, email_verified, email_verified_at,
    created_at, updated_at
) VALUES (
    lower(hex(randomblob(16))),
    'customer@altayar.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYCNqJ4tK',
    '+966500000003',
    'Customer',
    'User',
    'CUSTOMER',
    'ACTIVE',
    'ar',
    1,
    datetime('now'),
    datetime('now'),
    datetime('now')
);

-- Verify users were created
SELECT email, role, first_name, last_name FROM users WHERE email IN ('admin@altayar.com', 'employee@altayar.com', 'customer@altayar.com');
