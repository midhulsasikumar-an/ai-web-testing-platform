# Consensus Validation

## Purpose

Consensus validation merges overlapping findings from multiple agents into root-cause candidates.

## Heuristics

- API latency plus visual regression can indicate a backend degradation that cascades into rendering failure.
- Authentication failures plus navigation failures can indicate session corruption.
- Accessibility findings are clustered when multiple agents report the same form or ARIA issue.

## Output

The engine returns:

- bug cards
- clustered issues
- consensus findings
- agent signal summaries
- severity counts
