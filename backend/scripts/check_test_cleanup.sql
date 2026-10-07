-- Check scantract_test for leftover test data
SELECT 'users' as table_name, count(*) as count FROM users WHERE email LIKE '%@example.com'
UNION ALL
SELECT 'contracts' as table_name, count(*) as count FROM contracts WHERE id >= 900000;
