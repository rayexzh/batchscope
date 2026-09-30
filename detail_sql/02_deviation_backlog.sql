-- Source closure dates may be later than the snapshot; the displayed status is as-of.
SELECT d.deviation_id, d.batch_id, b.product, d.category, d.opened_on,
 d.closed_on AS closed_on_source,
 CASE WHEN d.closed_on IS NULL OR d.closed_on > :as_of THEN 'open' ELSE 'closed' END AS snapshot_status,
 CASE WHEN d.closed_on IS NULL OR d.closed_on > :as_of
      THEN CAST(julianday(:as_of)-julianday(d.opened_on) AS INTEGER) END AS open_age_days,
 CASE WHEN d.closed_on <= :as_of
      THEN CAST(julianday(d.closed_on)-julianday(d.opened_on) AS INTEGER) END AS closed_duration_days
FROM deviations d JOIN batches b USING(batch_id)
WHERE d.opened_on <= :as_of AND b.manufactured_on <= :as_of
ORDER BY b.product, d.category, snapshot_status DESC, open_age_days DESC, d.deviation_id;
