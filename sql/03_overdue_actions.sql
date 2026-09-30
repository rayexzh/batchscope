-- Due today is not overdue. Completed after the snapshot is still open at the snapshot.
WITH outstanding AS (
 SELECT a.*, d.category, b.product,
  CAST(julianday(:as_of)-julianday(a.due_on) AS INTEGER) AS overdue_days
 FROM actions a JOIN deviations d USING(deviation_id) JOIN batches b USING(batch_id)
 WHERE a.created_on <= :as_of AND d.opened_on <= :as_of AND b.manufactured_on <= :as_of
  AND (a.completed_on IS NULL OR a.completed_on > :as_of) AND a.due_on < :as_of
)
SELECT ROW_NUMBER() OVER (ORDER BY overdue_days DESC, action_id) AS review_order,
 action_id, deviation_id, product, category, owner_role, due_on, overdue_days
FROM outstanding ORDER BY review_order;
