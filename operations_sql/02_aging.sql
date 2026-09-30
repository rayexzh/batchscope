-- These are illustrative age bands, not regulatory limits or risk ratings.
WITH scoped AS (
 SELECT b.product, d.category,
 CAST(julianday(:as_of)-julianday(d.opened_on) AS INTEGER) AS age_days
 FROM deviations d JOIN batches b USING(batch_id)
 WHERE d.opened_on <= :as_of AND b.manufactured_on <= :as_of
  AND (d.closed_on IS NULL OR d.closed_on > :as_of)
)
SELECT product, category, COUNT(*) AS open_records,
 SUM(CASE WHEN age_days <= 7 THEN 1 ELSE 0 END) AS age_0_7,
 SUM(CASE WHEN age_days BETWEEN 8 AND 30 THEN 1 ELSE 0 END) AS age_8_30,
 SUM(CASE WHEN age_days BETWEEN 31 AND 60 THEN 1 ELSE 0 END) AS age_31_60,
 SUM(CASE WHEN age_days > 60 THEN 1 ELSE 0 END) AS age_61_plus,
 MAX(age_days) AS oldest_open_days
FROM scoped GROUP BY product, category ORDER BY oldest_open_days DESC, product, category;
