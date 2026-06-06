# Accessibility Engine

## Purpose
The accessibility engine performs deterministic, observation-based auditing during execution.

## Location
- `backend/accessibility/service.py`

## Checks
- missing labels
- invalid ARIA patterns
- inaccessible forms
- keyboard navigation risk
- contrast risk heuristics
- focus-trap risk around dialogs and overlays

## Inputs
The analyzer works from the canonical `Observation` model, so it remains compatible with the existing Playwright observer and workflow system.

## Outputs
The service returns:
- `accessibility_score`
- `findings`
- `keyboard_navigation_risk`
- `focus_trap_risk`

## Runtime Integration
Accessibility findings are emitted into the live event stream and also stored in the final run summary for reporting.

## Design Goal
Keep accessibility checks deterministic, low-overhead, and tied to semantic page state rather than DOM noise.