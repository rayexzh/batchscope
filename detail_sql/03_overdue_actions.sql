-- Only actions matching the overdue summary; include the batch for record tracing.
SELECT a.action_id, a.deviation_id, d.batch_id, b.product, d.category, a.owner_role,
 a.created_on, a.due_on, a.completed_on AS completed_on_source,
 'overdue' AS snapshot_status,
 CAST(julianday(:as_of)-julianday(a.due_on) AS INTEGER) AS overdue_days
FROM actions a JOIN deviations d USING(deviation_id) JOIN batches b USING(batch_id)
WHERE a.created_on <= :as_of AND d.opened_on <= :as_of AND b.manufactured_on <= :as_of
 AND (a.completed_on IS NULL OR a.completed_on > :as_of) AND a.due_on < :as_of
ORDER BY overdue_days DESC, a.action_id;
