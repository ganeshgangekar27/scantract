DELETE FROM users WHERE email LIKE 'qa%@example.com';
SELECT count(1) as deleted_users FROM users WHERE email LIKE 'qa%@example.com';
