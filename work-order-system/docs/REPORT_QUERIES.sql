-- PostgreSQL versions of the report queries (set DATABASE_URL to use PostgreSQL).
-- For the default SQLite database use REPORT_QUERIES_SQLITE.sql instead.
-- Django table names are shown; substitute deployed names if customized.

-- Work orders grouped by status
SELECT status, COUNT(*) AS work_order_count
FROM service_workorder
GROUP BY status
ORDER BY status;

-- Work orders grouped by priority
SELECT priority, COUNT(*) AS work_order_count
FROM service_workorder
GROUP BY priority
ORDER BY CASE priority WHEN 'URGENT' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'NORMAL' THEN 3 ELSE 4 END;

-- Open/active orders older than seven days
SELECT id, title, priority, status, created_at, customer_id, technician_id
FROM service_workorder
WHERE status IN ('OPEN', 'ASSIGNED', 'IN_PROGRESS')
  AND created_at < CURRENT_TIMESTAMP - INTERVAL '7 days'
ORDER BY created_at;

-- Active workload per technician
SELECT u.id, u.username, COUNT(w.id) AS active_orders
FROM auth_user u
JOIN service_workorder w ON w.technician_id = u.id
WHERE w.status IN ('ASSIGNED', 'IN_PROGRESS')
GROUP BY u.id, u.username
ORDER BY active_orders DESC;

-- Mean completion time in hours (completed orders)
SELECT AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600.0) AS avg_hours_to_complete
FROM service_workorder
WHERE completed_at IS NOT NULL;

-- Requests by customer in the last 30 days
SELECT u.id, u.username, COUNT(w.id) AS request_count
FROM auth_user u
JOIN service_workorder w ON w.customer_id = u.id
WHERE w.created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY u.id, u.username
ORDER BY request_count DESC;

-- Unassigned (OPEN) orders, highest priority first
SELECT id, title, priority, created_at FROM service_workorder
WHERE technician_id IS NULL AND status = 'OPEN'
ORDER BY CASE priority WHEN 'URGENT' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'NORMAL' THEN 3 ELSE 4 END, created_at;

-- Full work history (audit trail) for one work order
SELECT e.created_at, e.event_type, e.from_value, e.to_value, e.note, a.username AS actor
FROM service_workorderevent e LEFT JOIN auth_user a ON a.id = e.actor_id
WHERE e.work_order_id = 1 ORDER BY e.created_at, e.id;

-- Completed/closed orders per technician
SELECT u.username, COUNT(w.id) AS finished_orders
FROM auth_user u JOIN service_workorder w ON w.technician_id = u.id
WHERE w.status IN ('COMPLETED', 'CLOSED') GROUP BY u.username ORDER BY finished_orders DESC;

-- Comments and attachments per work order
SELECT w.id, w.title,
  (SELECT COUNT(*) FROM service_comment c WHERE c.work_order_id = w.id) AS comments,
  (SELECT COUNT(*) FROM service_attachment a WHERE a.work_order_id = w.id) AS attachments
FROM service_workorder w ORDER BY w.id;

-- Customers with order counts (including customers with none)
SELECT u.username, p.company, COUNT(w.id) AS orders
FROM auth_user u JOIN service_profile p ON p.user_id = u.id LEFT JOIN service_workorder w ON w.customer_id = u.id
WHERE p.role = 'CUSTOMER' GROUP BY u.id, u.username, p.company ORDER BY orders DESC;
