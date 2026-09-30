-- Closure after the as-of date does not close a deviation in this snapshot.
WITH scoped AS (
 SELECT d.*, b.product,
  CASE WHEN closed_on IS NULL OR closed_on > :as_of THEN 1 ELSE 0 END AS is_open,
  CAST(julianday(:as_of) - julianday(opened_on) AS INTEGER) AS age_days
 FROM deviations d JOIN batches b USING(batch_id)
 WHERE opened_on <= :as_of AND b.manufactured_on <= :as_of
)
SELECT product, category, COUNT(*) AS opened_to_date,
 SUM(is_open) AS open_records,
 MAX(CASE WHEN is_open = 1 THEN age_days END) AS oldest_open_days,
 ROUND(AVG(CASE WHEN is_open = 1 THEN age_days END), 2) AS mean_open_age_days,
 SUM(1-is_open) AS closed_records,
 ROUND(AVG(CASE WHEN is_open = 0 THEN julianday(closed_on)-julianday(opened_on) END),2)
  AS mean_closed_duration_days
FROM scoped GROUP BY product, category ORDER BY open_records DESC, product, category;
