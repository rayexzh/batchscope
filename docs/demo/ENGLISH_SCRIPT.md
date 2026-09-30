# BatchScope — English demonstration script

Synthetic-data prototype. The supplied video uses Windows synthetic English narration (Microsoft Zira Desktop); it is not the maintainer speaking. Edited from real native-app captures, not an uninterrupted screen recording. Substitute your own narration for interview introductions.

## 00:00:00 — Quality operations, made reviewable

BatchScope is a desktop prototype for reviewing pharmaceutical quality operations. This walkthrough uses fictional data to connect summary metrics with the records behind them.

## 00:00:10 — 01 / Start with reproducible data

The Windows release runs without installing Python. Here, Generate creates a reproducible dataset of one hundred batches, with linked measurements, deviations and actions. All processing stays on the computer.

## 00:00:22 — 02 / Interpret the snapshot

For June thirtieth, the snapshot contains one hundred and ninety-eight measurements. Fourteen are missing, leaving one hundred and eighty-four judgeable results. Missing values remain missing; they are never converted to zero.

## 00:00:35 — 03 / Inspect the evidence

Open a measurement group and filter the underlying records. Values, methods, units and example bounds support review. Seventy-four measurements fall outside fictional ranges; that count is not an industry benchmark or an investigation conclusion.

## 00:00:48 — 04 / Turn the summary into follow-up

The quality review workbench separates overdue actions, actions due today, and actions due within seven days. Its default view focuses on these items. Time urgency helps organize follow-up; it does not measure patient or product risk.

## 00:01:02 — 05 / Check linked records

A separate filter identifies outstanding actions linked to closed deviations. Eleven appear in this snapshot. These require context and follow-up; the software does not automatically label them as procedural violations.

## 00:01:15 — 06 / Trace one batch

Select an action to open its batch overview. The tabs connect measurements, deviations and all actions visible at the same date, including completed actions. This makes record tracing possible without losing the snapshot context.

## 00:01:28 — 07 / Understand the backlog

Backlog age groups show where open deviations accumulate by product and category. The example age bands are mutually exclusive. Their counts reconcile with the twenty-two open deviations, without imposing a regulatory time limit.

## 00:01:41 — 08 / Reconcile monthly movements

Monthly movements separate opening backlog, new openings, closures and ending backlog. In June, twenty plus five minus three equals twenty-two. The final period ends at the analysis date, so a partial month stays clearly bounded.

## 00:01:54 — 09 / Compare the same input at two dates

Now compare June thirtieth with July thirty-first using the same input snapshot. Open deviations decrease from twenty-two to seventeen, while overdue actions rise from thirty to thirty-three. The comparison exposes changes behind these totals.

## 00:02:08 — 10 / Explain the net change

Four actions enter the ending overdue list, while one previously overdue action completes. The net increase is three. Searches and record identifiers support follow-up, while the software avoids claiming that these movements establish root causes.

## 00:02:21 — 11 / Export a reproducible review

The offline bilingual report includes a chart, review tables and input fingerprints. CSV exports and SQLite support further analysis. Hashes identify file contents; they are not electronic signatures or proof of compliance.

## 00:02:35 — From domain knowledge to an explainable workflow

BatchScope demonstrates data modelling, SQL analysis and clear quality-review logic. It is an open-source portfolio prototype, not a validated production system. The next step is independent feedback from teachers or quality professionals.