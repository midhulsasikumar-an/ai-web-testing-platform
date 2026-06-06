# Unified Reporting

## Report Composition

The unified report merges:

- all agent results
- consensus findings
- workflow coverage
- navigation graph snapshot
- shared memory snapshot
- reproduction paths
- severity prioritization

## Persistence

The report is serialized through `save_report()` so it is stored alongside other backend QA intelligence reports.
