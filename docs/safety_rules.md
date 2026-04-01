# Safety Rules

## Scope

This system evaluates visible workers in active construction scenes.

## Required PPE

- Helmet
- High-visibility vest

## Worker Rules

A worker is COMPLIANT if:

- a helmet is detected on the head region
- a vest is detected on the torso region

A worker is a VIOLATION if:

- helmet is missing
- vest is missing

A worker is REVIEW if:

- the worker is too small in the frame
- the worker is heavily occluded
- the model confidence is too low to decide reliably

## Scene Rules

- UNSAFE: at least one violating worker
- REVIEW: no violation, but one or more uncertain workers
- SAFE: all visible workers are compliant
