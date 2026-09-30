-- Denominator: present, validated results measured on/before the explicit as-of date.
WITH scoped AS (
 SELECT b.product, t.* FROM test_results t JOIN batches b USING(batch_id)
 WHERE t.measured_on <= :as_of AND b.manufactured_on <= :as_of
)
SELECT product, test_type, method, unit, spec_low, spec_high,
 COUNT(*) AS measured_records, COUNT(value) AS judgeable_records,
 SUM(value IS NULL) AS missing_records,
 SUM(CASE WHEN value < spec_low OR value > spec_high THEN 1 ELSE 0 END) AS outside_range_records,
 ROUND(100.0 * SUM(CASE WHEN value < spec_low OR value > spec_high THEN 1 ELSE 0 END)
       / NULLIF(COUNT(value), 0), 2) AS outside_range_pct
FROM scoped GROUP BY product, test_type, method, unit, spec_low, spec_high
ORDER BY product, test_type, method, unit, spec_low, spec_high;
