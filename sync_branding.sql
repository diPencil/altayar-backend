-- Update Admin Branding
UPDATE users 
SET first_name = 'AltayarVIP', 
    last_name = '', 
    username = 'AltayarVIP' 
WHERE role IN ('ADMIN', 'SUPER_ADMIN');

-- Prefix Membership IDs with ALT- if not already present
UPDATE users 
SET membership_id_display = 'ALT-' || UPPER(membership_id_display)
WHERE membership_id_display IS NOT NULL 
  AND membership_id_display NOT LIKE 'ALT-%';

-- Generate IDs for users without one (using first 8 chars of ID)
UPDATE users 
SET membership_id_display = 'ALT-' || UPPER(SUBSTR(id, 1, 8))
WHERE membership_id_display IS NULL OR membership_id_display = '';
