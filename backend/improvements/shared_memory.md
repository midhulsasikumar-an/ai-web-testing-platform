# Shared Memory

## What Is Shared

The multi-agent runtime shares:

- browser storage state path
- sessionStorage snapshot
- auth session details
- discovered routes
- screenshots
- workflow states
- detected bugs
- API failures
- navigation paths
- per-agent results

## Safety Model

Shared memory is protected by an async lock and versioned on every mutation. This keeps parallel agents from stepping on each other’s state.
