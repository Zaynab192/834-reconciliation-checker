-- Two tables are loaded by reconcile.py:
--   census (what the employer says)   edi (what the 834 says)

-- name: missing_from_834
-- Active in census, but never sent to the carrier
SELECT c.member_id, c.first_name || ' ' || c.last_name AS name,
       'Active in census but missing from 834' AS detail
FROM census c
LEFT JOIN edi e ON c.member_id = e.member_id
WHERE c.status = 'active' AND e.member_id IS NULL;

-- name: unexpected_in_834
-- Sent to the carrier but not in the employer census
SELECT e.member_id, e.first_name || ' ' || e.last_name AS name,
       'In 834 but not in census' AS detail
FROM edi e
LEFT JOIN census c ON e.member_id = c.member_id
WHERE c.member_id IS NULL;

-- name: dob_mismatch
SELECT DISTINCT c.member_id, c.first_name || ' ' || c.last_name AS name,
       'DOB census=' || c.dob || ' vs 834=' || e.dob AS detail
FROM census c
JOIN edi e ON c.member_id = e.member_id
WHERE c.dob <> e.dob;

-- name: start_date_mismatch
SELECT DISTINCT c.member_id, c.first_name || ' ' || c.last_name AS name,
       'Start census=' || c.coverage_start || ' vs 834=' || e.coverage_start AS detail
FROM census c
JOIN edi e ON c.member_id = e.member_id
WHERE c.coverage_start <> e.coverage_start;

-- name: terminated_but_active
-- Employer terminated them, but the 834 still says "add" (021)
SELECT c.member_id, c.first_name || ' ' || c.last_name AS name,
       'Terminated on ' || c.coverage_end || ' in census, but 834 still shows active' AS detail
FROM census c
JOIN edi e ON c.member_id = e.member_id
WHERE c.status = 'terminated' AND e.action = '021';

-- name: duplicate_records
SELECT member_id, first_name || ' ' || last_name AS name,
       'Appears ' || COUNT(*) || ' times in the 834' AS detail
FROM edi
GROUP BY member_id
HAVING COUNT(*) > 1;


-- name: plan_mismatch
SELECT DISTINCT c.member_id, c.first_name || ' ' || c.last_name AS name,
       'Plan census=' || c.plan || ' vs 834=' || e.plan AS detail
FROM census c
JOIN edi e ON c.member_id = e.member_id
WHERE c.plan <> e.plan;