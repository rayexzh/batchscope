-- All actions visible at this date. Parent closure does not complete its actions.
SELECT a.action_id, a.deviation_id, d.batch_id, b.product, d.category, a.owner_role,
 a.created_on, a.due_on, a.completed_on AS completed_on_source,
 CASE WHEN d.closed_on IS NOT NULL AND d.closed_on <= :as_of THEN 'closed' ELSE 'open' END AS parent_status,
 CASE WHEN a.completed_on IS NOT NULL AND a.completed_on <= :as_of THEN 'completed'
      WHEN a.due_on < :as_of THEN 'overdue'
      WHEN a.due_on = :as_of THEN 'due_today'
      WHEN a.due_on <= date(:as_of, '+7 days') THEN 'due_soon'
      ELSE 'later' END AS snapshot_status,
 CASE WHEN a.completed_on IS NOT NULL AND a.completed_on <= :as_of THEN NULL
      ELSE CAST(julianday(a.due_on)-julianday(:as_of) AS INTEGER) END AS days_until_due
FROM actions a JOIN deviations d USING(deviation_id) JOIN batches b USING(batch_id)
WHERE a.created_on <= :as_of AND d.opened_on <= :as_of AND b.manufactured_on <= :as_of
ORDER BY a.due_on, a.action_id;
