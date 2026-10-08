-- Count users matching test email pattern
SELECT COUNT(*) as user_count, email
FROM users
WHERE email LIKE 'test+%@example.com'
GROUP BY email
ORDER BY email DESC
LIMIT 5;
