PRAGMA foreign_keys = ON;
CREATE TABLE batches (
 batch_id TEXT PRIMARY KEY, product TEXT NOT NULL, manufactured_on TEXT NOT NULL
);
CREATE TABLE test_results (
 test_id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES batches(batch_id),
 test_type TEXT NOT NULL, method TEXT NOT NULL, value REAL, unit TEXT NOT NULL,
 spec_low REAL NOT NULL, spec_high REAL NOT NULL, spec_unit TEXT NOT NULL,
 measured_on TEXT NOT NULL, CHECK(spec_low <= spec_high)
);
CREATE TABLE deviations (
 deviation_id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES batches(batch_id),
 category TEXT NOT NULL, opened_on TEXT NOT NULL, closed_on TEXT
);
CREATE TABLE actions (
 action_id TEXT PRIMARY KEY, deviation_id TEXT NOT NULL REFERENCES deviations(deviation_id),
 owner_role TEXT NOT NULL, created_on TEXT NOT NULL, due_on TEXT NOT NULL, completed_on TEXT
);
