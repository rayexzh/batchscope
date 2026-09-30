-- Same snapshot and group dimensions as the range summary; retain NULL measurements.
SELECT t.test_id, t.batch_id, b.product, t.test_type, t.method, t.value, t.unit,
 t.spec_low, t.spec_high, t.measured_on,
 CASE WHEN t.value IS NULL THEN 'missing'
      WHEN t.value < t.spec_low OR t.value > t.spec_high THEN 'outside_range'
      ELSE 'within_range' END AS snapshot_status
FROM test_results t JOIN batches b USING(batch_id)
WHERE t.measured_on <= :as_of AND b.manufactured_on <= :as_of
ORDER BY b.product, t.test_type, t.method, t.unit, t.spec_low, t.spec_high, t.test_id;
