-- Report queries for SQLite (the default dev database: db.sqlite3). For PostgreSQL see REPORT_QUERIES.sql.
-- Run: sqlite3 db.sqlite3 < docs/REPORT_QUERIES_SQLITE.sql

-- 1. Work orders grouped by status
SELECT status, COUNT(*) AS work_order_count FROM service_workorder GROUP BY status ORDER BY status;

-- 2. Work orders grouped by priority (most urgent first)
SELECT priority, COUNT(*) AS work_order_count FROM service_workorder GROUP BY priority
ORDER BY CASE priority WHEN 'URGENT' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'NORMAL' THEN 3 ELSE 4 END;

-- 3. Active orders older than 7 days
SELECT id, title, priority, status, created_at, customer_id, technician_id FROM service_workorder
WHERE status IN ('OPEN','ASSIGNED','IN_PROGRESS') AND created_at < datetime('now','-7 days') ORDER BY created_at;

-- 4. Active workload per technician
SELECT u.id, u.username, COUNT(w.id) AS active_orders
FROM auth_user u JOIN service_workorder w ON w.technician_id = u.id
WHERE w.status IN ('ASSIGNED','IN_PROGRESS') GROUP BY u.id, u.username ORDER BY active_orders DESC;

-- 5. Average hours to complete (completed/closed orders)
SELECT ROUND(AVG((julianday(completed_at) - julianday(created_at)) * 24), 2) AS avg_hours_to_complete
FROM service_workorder WHERE completed_at IS NOT NULL;

-- 6. Requests per customer in the last 30 days
SELECT u.id, u.username, COUNT(w.id) AS request_count
FROM auth_user u JOIN service_workorder w ON w.customer_id = u.id
WHERE w.created_at >= datetime('now','-30 days') GROUP BY u.id, u.username ORDER BY request_count DESC;

-- 7. Unassigned (OPEN) orders, highest priority first
SELECT id, title, priority, created_at FROM service_workorder WHERE technician_id IS NULL AND status = 'OPEN'
ORDER BY CASE priority WHEN 'URGENT' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'NORMAL' THEN 3 ELSE 4 END, created_at;

-- 8. Full work history (audit trail) for one work order (change the id)
SELECT e.created_at, e.event_type, e.from_value, e.to_value, e.note, a.username AS actor
FROM service_workorderevent e LEFT JOIN auth_user a ON a.id = e.actor_id WHERE e.work_order_id = 1 ORDER BY e.created_at, e.id;

-- 9. Completed/closed orders per technician
SELECT u.username, COUNT(w.id) AS finished_orders
FROM auth_user u JOIN service_workorder w ON w.technician_id = u.id
WHERE w.status IN ('COMPLETED','CLOSED') GROUP BY u.username ORDER BY finished_orders DESC;

-- 10. Comments and attachments per work order
SELECT w.id, w.title,
  (SELECT COUNT(*) FROM service_comment c WHERE c.work_order_id = w.id) AS comments,
  (SELECT COUNT(*) FROM service_attachment a WHERE a.work_order_id = w.id) AS attachments
FROM service_workorder w ORDER BY w.id;

-- 11. Customers with their order counts (including customers with none)
SELECT u.username, p.company, COUNT(w.id) AS orders
FROM auth_user u JOIN service_profile p ON p.user_id = u.id LEFT JOIN service_workorder w ON w.customer_id = u.id
WHERE p.role = 'CUSTOMER' GROUP BY u.id ORDER BY orders DESC;
